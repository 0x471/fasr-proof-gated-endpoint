use std::{
    collections::VecDeque,
    io::{self, Read, Write},
    net::TcpStream,
    os::fd::{AsRawFd, RawFd},
    time::Instant,
};

pub enum Input {
    Frame(Vec<u8>),
    Pending,
    Closed,
    Invalid,
    Lost,
}

pub struct Connection {
    stream: TcpStream,
    input: Vec<u8>,
    size: Option<usize>,
    pub started: Option<Instant>,
    output: VecDeque<Vec<u8>>,
    written: usize,
    pub buffered: usize,
}
impl Connection {
    pub fn new(stream: TcpStream) -> io::Result<Self> {
        stream.set_nonblocking(true)?;
        stream.set_nodelay(true)?;
        Ok(Self {
            stream,
            input: Vec::new(),
            size: None,
            started: None,
            output: VecDeque::new(),
            written: 0,
            buffered: 0,
        })
    }
    pub fn fd(&self) -> RawFd {
        self.stream.as_raw_fd()
    }
    pub fn wants_write(&self) -> bool {
        !self.output.is_empty()
    }
    pub fn read(&mut self, limit: usize) -> Input {
        loop {
            if self.size.is_none() && self.input.len() == 4 {
                let Ok(head) = self.input.as_slice().try_into() else {
                    return Input::Invalid;
                };
                match pge_wire::frame_len(head, limit) {
                    Ok(n) => {
                        self.size = Some(n);
                        self.input.clear();
                    }
                    Err(_) => return Input::Invalid,
                }
            }
            if self.size == Some(self.input.len()) {
                self.size = None;
                self.started = None;
                return Input::Frame(std::mem::take(&mut self.input));
            }
            let need = self.size.unwrap_or(4).saturating_sub(self.input.len());
            let mut buf = [0; 8192];
            let n = need.min(buf.len());
            match self.stream.read(&mut buf[..n]) {
                Ok(0) => {
                    return if self.input.is_empty() && self.size.is_none() {
                        Input::Closed
                    } else {
                        Input::Invalid
                    }
                }
                Ok(n) => {
                    if self.started.is_none() {
                        self.started = Some(Instant::now());
                    }
                    self.input.extend_from_slice(&buf[..n]);
                }
                Err(e) if e.kind() == io::ErrorKind::WouldBlock => return Input::Pending,
                Err(e) if e.kind() == io::ErrorKind::Interrupted => return Input::Pending,
                Err(_) => return Input::Lost,
            }
        }
    }
    pub fn send(&mut self, payload: &[u8]) -> io::Result<()> {
        let data = pge_wire::frame(payload).map_err(|_| io::Error::other("frame"))?;
        self.buffered = self
            .buffered
            .checked_add(data.len())
            .ok_or_else(|| io::Error::other("output size"))?;
        self.output.push_back(data);
        self.flush()
    }
    pub fn flush(&mut self) -> io::Result<()> {
        while let Some(front) = self.output.front() {
            match self.stream.write(&front[self.written..]) {
                Ok(0) => return Err(io::Error::other("closed")),
                Ok(n) => {
                    self.written += n;
                    self.buffered -= n;
                    if self.written == front.len() {
                        self.output.pop_front();
                        self.written = 0;
                    }
                }
                Err(e)
                    if matches!(
                        e.kind(),
                        io::ErrorKind::WouldBlock | io::ErrorKind::Interrupted
                    ) =>
                {
                    return Ok(())
                }
                Err(e) => return Err(e),
            }
        }
        Ok(())
    }
}

/// The server connection has to notice a dead peer even when it has nothing to send: after a silent
/// outage it would otherwise stay "connected" and never redial. Probes start after 5 s idle, every
/// 2 s, and 3 missed ones or 10 s of unacknowledged data end the connection (Linux).
pub fn keep_alive(stream: &TcpStream) -> io::Result<()> {
    set(stream, libc::SOL_SOCKET, libc::SO_KEEPALIVE, 1)?;
    #[cfg(target_os = "linux")]
    for (name, value) in [
        (libc::TCP_KEEPIDLE, 5),
        (libc::TCP_KEEPINTVL, 2),
        (libc::TCP_KEEPCNT, 3),
        (libc::TCP_USER_TIMEOUT, 10_000),
    ] {
        set(stream, libc::IPPROTO_TCP, name, value)?;
    }
    Ok(())
}

fn set(
    stream: &TcpStream,
    level: libc::c_int,
    name: libc::c_int,
    value: libc::c_int,
) -> io::Result<()> {
    // The value outlives the call, and setsockopt copies it.
    let size = std::mem::size_of::<libc::c_int>() as libc::socklen_t;
    let r = unsafe {
        libc::setsockopt(
            stream.as_raw_fd(),
            level,
            name,
            (&value as *const libc::c_int).cast(),
            size,
        )
    };
    if r != 0 {
        return Err(io::Error::last_os_error());
    }
    Ok(())
}

#[cfg(all(test, target_os = "linux"))]
mod tests {
    use super::*;
    use std::net::TcpListener;

    fn get(stream: &TcpStream, level: libc::c_int, name: libc::c_int) -> libc::c_int {
        let (mut value, mut size) = (
            0 as libc::c_int,
            std::mem::size_of::<libc::c_int>() as libc::socklen_t,
        );
        let r = unsafe {
            libc::getsockopt(
                stream.as_raw_fd(),
                level,
                name,
                (&mut value as *mut libc::c_int).cast(),
                &mut size,
            )
        };
        assert_eq!(r, 0);
        value
    }

    #[test]
    fn server_connections_probe_a_silent_peer() {
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let stream = TcpStream::connect(listener.local_addr().unwrap()).unwrap();
        assert_eq!(get(&stream, libc::SOL_SOCKET, libc::SO_KEEPALIVE), 0);
        keep_alive(&stream).unwrap();
        assert_eq!(get(&stream, libc::SOL_SOCKET, libc::SO_KEEPALIVE), 1);
        assert_eq!(get(&stream, libc::IPPROTO_TCP, libc::TCP_KEEPIDLE), 5);
        assert_eq!(get(&stream, libc::IPPROTO_TCP, libc::TCP_KEEPINTVL), 2);
        assert_eq!(get(&stream, libc::IPPROTO_TCP, libc::TCP_KEEPCNT), 3);
        assert_eq!(
            get(&stream, libc::IPPROTO_TCP, libc::TCP_USER_TIMEOUT),
            10_000
        );
    }
}
