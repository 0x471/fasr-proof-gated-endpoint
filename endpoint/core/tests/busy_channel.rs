// K17: can the server make other clients' requests come back `busy`? Under fixed release every
// admitted request holds its slot until admission + deadline, whatever the server does, so which
// requests are admitted and when replies leave depend only on when clients ask. In arrival order
// the server frees slots by answering early, so `busy` follows the server. Halting is left out:
// it refuses everything after the halt by design (K16). The event loop's own delays are K34.
use pge_core::{Admission, Answer, Cap, Core, Decision, Mode, Policy, Step};

const DEADLINE: u64 = 20;
const STEPS: u64 = 400;

struct Rng(u64);
impl Rng {
    fn below(&mut self, n: u64) -> u64 {
        self.0 ^= self.0 << 13;
        self.0 ^= self.0 >> 7;
        self.0 ^= self.0 << 17;
        self.0 % n
    }
}

#[derive(Debug, PartialEq)]
struct Seen {
    admissions: Vec<(u64, Admission)>,
    releases: Vec<(u64, u64)>,
}

// One run: clients ask at `asks`; the server answers each request at a random time with a random
// verdict, stays silent, or drops its link for a while, all drawn from `server`.
fn run(mode: Mode, cap: Option<Cap>, asks: &[u64], server: u64) -> Seen {
    let mut policy = Policy::new(DEADLINE, 4, None, mode, 0).unwrap();
    if let Some(cap) = cap {
        policy = policy.with_cap(cap);
    }
    let mut core = Core::new(policy);
    let mut rng = Rng(server);
    let mut plans: Vec<(u64, u64, Decision)> = Vec::new();
    let mut down_until = 0;
    let mut seen = Seen {
        admissions: Vec::new(),
        releases: Vec::new(),
    };
    for now in 0..STEPS {
        if now >= down_until && rng.below(40) == 0 {
            core.disconnect("closed");
            down_until = now + 1 + rng.below(DEADLINE);
        }
        let connected = now >= down_until;
        for &(at, seq, decision) in &plans {
            if at == now && connected && core.answer(seq) == Answer::Check {
                core.complete(seq, now, decision);
            }
        }
        for _ in asks.iter().filter(|&&t| t == now) {
            let admission = core.admit(now, connected);
            seen.admissions.push((now, admission));
            if let Admission::Admitted(seq) = admission {
                let decision = match rng.below(4) {
                    0 => Decision::failure("reject", ""),
                    1 => Decision::failure("error", ""),
                    _ => Decision::accept(),
                };
                if rng.below(5) != 0 {
                    plans.push((now + rng.below(2 * DEADLINE), seq, decision));
                }
            }
        }
        core.expire(now);
        while let Step::Release(seq, _) = core.pump(now, false) {
            seen.releases.push((now, seq));
        }
    }
    seen
}

fn asks(rng: &mut Rng) -> Vec<u64> {
    let mut out: Vec<u64> = (0..60).map(|_| rng.below(STEPS - 2 * DEADLINE)).collect();
    out.sort_unstable();
    out
}

#[test]
fn fixed_release_busy_and_release_times_ignore_the_server() {
    let mut rng = Rng(0x9e37_79b9_7f4a_7c15);
    for cap in [None, Some(Cap::new(8, 1, 8).unwrap())] {
        for _ in 0..200 {
            let asks = asks(&mut rng);
            let first = run(Mode::Fixed, cap, &asks, 1 + rng.below(1 << 40));
            assert!(first.admissions.iter().any(|(_, a)| *a == Admission::Busy));
            let admitted: Vec<(u64, u64)> = first
                .admissions
                .iter()
                .filter_map(|&(t, a)| match a {
                    Admission::Admitted(seq) => Some((t + DEADLINE, seq)),
                    _ => None,
                })
                .collect();
            assert_eq!(first.releases, admitted);
            for _ in 0..8 {
                assert_eq!(
                    run(Mode::Fixed, cap, &asks, 1 + rng.below(1 << 40)),
                    first
                );
            }
        }
    }
}

#[test]
fn arrival_order_busy_follows_the_server() {
    let mut rng = Rng(0x2545_f491_4f6c_dd1d);
    let asks = asks(&mut rng);
    let first = run(Mode::Arrival, None, &asks, 1).admissions;
    assert!((2..50).any(|s| run(Mode::Arrival, None, &asks, s).admissions != first));
}
