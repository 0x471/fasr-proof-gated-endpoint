#![forbid(unsafe_code)]

pub const MAX_ID: u64 = 1 << 53;
pub const PROOF_MAX: usize = 65536;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Invalid;

#[derive(Debug, Clone, PartialEq)]
pub enum Message {
    Request(u64, Vec<f64>),
    Forward(u64, Vec<f64>),
    Answer(u64, Vec<[u8; 32]>, Vec<u8>),
    Reply(u64, Reply),
}

#[derive(Debug, Clone, PartialEq)]
pub enum Reply {
    Ok(Vec<f64>),
    BadRequest,
    Unavailable,
}

#[derive(Debug, Clone, Copy)]
pub struct Wire {
    inputs: usize,
    outputs: usize,
    pub request_size: usize,
    pub answer_fixed: usize,
    pub answer_max: usize,
    pub reply_size: usize,
}

impl Wire {
    pub fn new(inputs: usize, outputs: usize) -> Result<Self, Invalid> {
        if inputs == 0 || outputs == 0 {
            return Err(Invalid);
        }
        let request_size = inputs
            .checked_mul(8)
            .and_then(|n| n.checked_add(9))
            .ok_or(Invalid)?;
        let answer_fixed = outputs
            .checked_mul(32)
            .and_then(|n| n.checked_add(9))
            .ok_or(Invalid)?;
        let answer_max = answer_fixed.checked_add(PROOF_MAX).ok_or(Invalid)?;
        let reply_size = outputs
            .checked_mul(8)
            .and_then(|n| n.checked_add(10))
            .ok_or(Invalid)?;
        for n in [request_size, answer_max, reply_size] {
            u32::try_from(n).map_err(|_| Invalid)?;
        }
        Ok(Self {
            inputs,
            outputs,
            request_size,
            answer_fixed,
            answer_max,
            reply_size,
        })
    }

    pub fn parse(&self, kind: u8, raw: &[u8]) -> Result<Message, Invalid> {
        if raw.first() != Some(&kind) {
            return Err(Invalid);
        }
        let id = u64::from_be_bytes(
            raw.get(1..9)
                .ok_or(Invalid)?
                .try_into()
                .map_err(|_| Invalid)?,
        );
        if id >= MAX_ID {
            return Err(Invalid);
        }
        let message = match kind {
            1 | 2 if raw.len() == self.request_size => {
                let x = floats(&raw[9..])?;
                if kind == 1 {
                    Message::Request(id, x)
                } else {
                    Message::Forward(id, x)
                }
            }
            3 if raw.len() > self.answer_fixed && raw.len() <= self.answer_max => {
                let outputs = raw[9..self.answer_fixed]
                    .chunks_exact(32)
                    .map(|b| b.try_into().map_err(|_| Invalid))
                    .collect::<Result<_, _>>()?;
                Message::Answer(id, outputs, raw[self.answer_fixed..].to_vec())
            }
            4 if raw.len() == self.reply_size => {
                let reply = match raw[9] {
                    0 => Reply::Ok(floats(&raw[10..])?),
                    1 if raw[10..].iter().all(|b| *b == 0) => Reply::BadRequest,
                    2 if raw[10..].iter().all(|b| *b == 0) => Reply::Unavailable,
                    _ => return Err(Invalid),
                };
                Message::Reply(id, reply)
            }
            _ => return Err(Invalid),
        };
        if self.encode(&message)? != raw {
            return Err(Invalid);
        }
        Ok(message)
    }

    pub fn encode(&self, message: &Message) -> Result<Vec<u8>, Invalid> {
        let (kind, id) = match message {
            Message::Request(id, _) => (1, id),
            Message::Forward(id, _) => (2, id),
            Message::Answer(id, _, _) => (3, id),
            Message::Reply(id, _) => (4, id),
        };
        if *id >= MAX_ID {
            return Err(Invalid);
        }
        let mut out = vec![kind];
        out.extend(id.to_be_bytes());
        match message {
            Message::Request(_, x) | Message::Forward(_, x) => {
                put_floats(&mut out, x, self.inputs)?
            }
            Message::Answer(_, outputs, proof) => {
                if outputs.len() != self.outputs || proof.is_empty() || proof.len() > PROOF_MAX {
                    return Err(Invalid);
                }
                for f in outputs {
                    out.extend(f);
                }
                out.extend(proof);
            }
            Message::Reply(_, Reply::Ok(y)) => {
                out.push(0);
                put_floats(&mut out, y, self.outputs)?;
            }
            Message::Reply(_, status) => {
                out.push(if *status == Reply::BadRequest { 1 } else { 2 });
                out.resize(self.reply_size, 0);
            }
        }
        Ok(out)
    }
}

fn floats(raw: &[u8]) -> Result<Vec<f64>, Invalid> {
    raw.chunks_exact(8)
        .map(|b| {
            let x = f64::from_be_bytes(b.try_into().map_err(|_| Invalid)?);
            if x.is_finite() {
                Ok(x)
            } else {
                Err(Invalid)
            }
        })
        .collect()
}

fn put_floats(out: &mut Vec<u8>, values: &[f64], n: usize) -> Result<(), Invalid> {
    if values.len() != n || values.iter().any(|x| !x.is_finite()) {
        return Err(Invalid);
    }
    for x in values {
        out.extend(x.to_be_bytes());
    }
    Ok(())
}

pub fn frame(payload: &[u8]) -> Result<Vec<u8>, Invalid> {
    let len = u32::try_from(payload.len()).map_err(|_| Invalid)?;
    if len == 0 {
        return Err(Invalid);
    }
    let mut out = len.to_be_bytes().to_vec();
    out.extend(payload);
    Ok(out)
}

pub fn frame_len(header: [u8; 4], limit: usize) -> Result<usize, Invalid> {
    let n = u32::from_be_bytes(header) as usize;
    if n == 0 || n > limit {
        Err(Invalid)
    } else {
        Ok(n)
    }
}

// Bounded proofs with Kani (`cargo kani` in endpoint/wire), for the smallest shape (one input, one
// output): the layout code has no per-shape branches, but these proofs say nothing about larger shapes.
// Plain assert!, not assert_eq!: the latter makes Kani model Debug formatting of floats.
#[cfg(kani)]
mod proofs {
    use super::*;

    fn wire() -> Wire {
        Wire::new(1, 1).unwrap()
    }

    // Any bytes of these lengths, any kind: parse never panics, and what it accepts encodes back to
    // the same bytes. 17 = a request, 18 = a reply, 42-44 = an answer with a 1-3 byte proof.
    fn any_input<const N: usize>() {
        let raw: [u8; N] = kani::any();
        if let Ok(message) = wire().parse(kani::any(), &raw) {
            assert!(wire().encode(&message).unwrap() == raw);
        }
    }

    #[kani::proof]
    #[kani::unwind(10)]
    #[kani::solver(cadical)]
    fn any_short_input() {
        any_input::<12>();
    }

    #[kani::proof]
    #[kani::unwind(10)]
    #[kani::solver(cadical)]
    fn any_request_sized_input() {
        any_input::<17>();
    }

    #[kani::proof]
    #[kani::unwind(10)]
    #[kani::solver(cadical)]
    fn any_reply_sized_input() {
        any_input::<18>();
    }

    #[kani::proof]
    #[kani::unwind(34)]
    #[kani::solver(cadical)]
    fn any_answer_sized_input() {
        any_input::<44>();
    }

    // Everything the endpoint itself writes is accepted back: no valid message is refused.
    #[kani::proof]
    #[kani::unwind(10)]
    #[kani::solver(cadical)]
    fn every_valid_request_parses_back() {
        let id: u64 = kani::any();
        kani::assume(id < MAX_ID);
        let x: f64 = kani::any();
        kani::assume(x.is_finite());
        let forward: bool = kani::any();
        let message = if forward {
            Message::Forward(id, vec![x])
        } else {
            Message::Request(id, vec![x])
        };
        let raw = wire().encode(&message).unwrap();
        assert!(wire().parse(if forward { 2 } else { 1 }, &raw) == Ok(message));
    }

    #[kani::proof]
    #[kani::unwind(10)]
    #[kani::solver(cadical)]
    fn every_valid_reply_parses_back() {
        let id: u64 = kani::any();
        kani::assume(id < MAX_ID);
        let y: f64 = kani::any();
        kani::assume(y.is_finite());
        let reply = match kani::any::<u8>() % 3 {
            0 => Reply::Ok(vec![y]),
            1 => Reply::BadRequest,
            _ => Reply::Unavailable,
        };
        let message = Message::Reply(id, reply);
        let raw = wire().encode(&message).unwrap();
        assert!(wire().parse(4, &raw) == Ok(message));
    }

    #[kani::proof]
    fn frame_len_accepts_only_one_to_limit() {
        let header: [u8; 4] = kani::any();
        let limit: usize = kani::any();
        let n = u32::from_be_bytes(header) as usize;
        match frame_len(header, limit) {
            Ok(got) => assert!(got == n && n >= 1 && n <= limit),
            Err(_) => assert!(n == 0 || n > limit),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn request_matches_python_bytes() {
        let wire = Wire::new(4, 3).unwrap();
        let message = Message::Request(7, vec![0.5, -0.0, 0.0, 1.0]);
        let raw = wire.encode(&message).unwrap();
        assert_eq!(
            &raw[..17],
            &[1, 0, 0, 0, 0, 0, 0, 0, 7, 63, 224, 0, 0, 0, 0, 0, 0]
        );
        assert_eq!(raw.len(), 41);
        assert_eq!(wire.encode(&wire.parse(1, &raw).unwrap()).unwrap(), raw);
    }
}
