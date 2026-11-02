use pge_verify::Verdict;
use std::{
    io::{self, Read, Write},
    os::{fd::AsRawFd, unix::process::CommandExt},
    process::{Child, Command, Stdio},
    thread,
    time::{Duration, Instant},
};

pub const OUTPUT_CAP: usize = 65536;

pub fn classify(code: Option<i32>, out: &[u8], err: &[u8]) -> Verdict {
    match (code, out, err) {
        (Some(0), b"accept\n", b"") => Verdict::Accept,
        (Some(1), b"reject\n", b"") => Verdict::Reject,
        _ => Verdict::Error,
    }
}

fn nonblocking(fd: i32) -> io::Result<()> {
    // The fd is borrowed from a live pipe; fcntl does not take ownership.
    unsafe {
        let flags = libc::fcntl(fd, libc::F_GETFL);
        if flags < 0 || libc::fcntl(fd, libc::F_SETFL, flags | libc::O_NONBLOCK) < 0 {
            return Err(io::Error::last_os_error());
        }
    }
    Ok(())
}
fn kill_group(child: &mut Child) {
    // The leader is not reaped until after this call, so its PID cannot be reused.
    unsafe {
        libc::kill(-(child.id() as i32), libc::SIGKILL);
    }
    let _ = child.kill();
    let _ = child.wait();
}
fn read_chunk(pipe: &mut impl Read, out: &mut Vec<u8>, eof: &mut bool) -> io::Result<()> {
    if *eof {
        return Ok(());
    }
    let mut buf = [0; 8192];
    match pipe.read(&mut buf) {
        Ok(0) => *eof = true,
        Ok(n) => out.extend_from_slice(&buf[..n]),
        Err(e)
            if matches!(
                e.kind(),
                io::ErrorKind::WouldBlock | io::ErrorKind::Interrupted
            ) =>
        {
            ()
        }
        Err(e) => return Err(e),
    }
    Ok(())
}

pub fn run(mut cmd: Command, timeout: Duration, input: &[u8]) -> Verdict {
    if timeout.is_zero() {
        return Verdict::Error;
    }
    let end = match Instant::now().checked_add(timeout) {
        Some(v) => v,
        None => return Verdict::Error,
    };
    cmd.env_clear()
        .env("PATH", "/usr/bin:/bin")
        .env("LC_ALL", "C")
        .env("RAYON_NUM_THREADS", "1")
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .process_group(0);
    let mut child = match cmd.spawn() {
        Ok(c) => c,
        Err(_) => return Verdict::Error,
    };
    let (Some(mut stdout), Some(mut stderr)) = (child.stdout.take(), child.stderr.take()) else {
        kill_group(&mut child);
        return Verdict::Error;
    };
    let mut stdin = child.stdin.take();
    if nonblocking(stdout.as_raw_fd()).is_err()
        || nonblocking(stderr.as_raw_fd()).is_err()
        || stdin
            .as_ref()
            .is_none_or(|p| nonblocking(p.as_raw_fd()).is_err())
    {
        kill_group(&mut child);
        return Verdict::Error;
    }
    let mut offset = 0;
    let (mut out, mut err, mut oe, mut ee) = (Vec::new(), Vec::new(), false, false);
    loop {
        if offset == input.len() {
            stdin.take();
        }
        if let Some(pipe) = stdin.as_mut() {
            match pipe.write(&input[offset..]) {
                Ok(0) => {
                    kill_group(&mut child);
                    return Verdict::Error;
                }
                Ok(n) => offset += n,
                Err(e)
                    if matches!(
                        e.kind(),
                        io::ErrorKind::WouldBlock | io::ErrorKind::Interrupted
                    ) =>
                {
                    ()
                }
                Err(_) => {
                    kill_group(&mut child);
                    return Verdict::Error;
                }
            }
        }
        if Instant::now() >= end
            || read_chunk(&mut stdout, &mut out, &mut oe).is_err()
            || read_chunk(&mut stderr, &mut err, &mut ee).is_err()
            || out.len().saturating_add(err.len()) > OUTPUT_CAP
        {
            kill_group(&mut child);
            return Verdict::Error;
        }
        if oe && ee {
            match child.try_wait() {
                Ok(Some(status)) => {
                    return if offset == input.len() && Instant::now() < end {
                        classify(status.code(), &out, &err)
                    } else {
                        Verdict::Error
                    }
                }
                Ok(None) => (),
                Err(_) => {
                    kill_group(&mut child);
                    return Verdict::Error;
                }
            }
        }
        // Wait for room in the input pipe or output from the child, not a fixed sleep: the job is
        // megabytes and the pipe holds 64 KiB, so a sleep per write added tens of ms per check.
        let mut fds = Vec::with_capacity(3);
        if let Some(pipe) = stdin.as_ref() {
            fds.push(libc::pollfd {
                fd: pipe.as_raw_fd(),
                events: libc::POLLOUT,
                revents: 0,
            });
        }
        for (fd, done) in [(stdout.as_raw_fd(), oe), (stderr.as_raw_fd(), ee)] {
            if !done {
                fds.push(libc::pollfd {
                    fd,
                    events: libc::POLLIN,
                    revents: 0,
                });
            }
        }
        let left = end.saturating_duration_since(Instant::now());
        if fds.is_empty() {
            thread::sleep(Duration::from_millis(1).min(left));
        } else {
            let ms = left.as_millis().clamp(1, 100) as libc::c_int;
            // The fds belong to pipes that stay open for this call; a failed poll just loops.
            unsafe { libc::poll(fds.as_mut_ptr(), fds.len() as libc::nfds_t, ms) };
        }
    }
}

pub fn limits(cpu: u64) -> io::Result<()> {
    if cpu == 0 || cpu > 3600 {
        return Err(io::Error::other("cpu limit"));
    }
    // This runs in a fresh executable before starting any threads or reading hostile data.
    unsafe {
        for (resource, value) in [
            (libc::RLIMIT_CORE, 0),
            (libc::RLIMIT_CPU, cpu),
            (libc::RLIMIT_FSIZE, 0),
            (libc::RLIMIT_NOFILE, 64),
        ] {
            // Only ever lower a limit, soft or hard: never more than the endpoint itself was given.
            let mut old = libc::rlimit {
                rlim_cur: 0,
                rlim_max: 0,
            };
            if libc::getrlimit(resource, &mut old) != 0 {
                return Err(io::Error::last_os_error());
            }
            let value = (value as libc::rlim_t).min(old.rlim_cur).min(old.rlim_max);
            let limit = libc::rlimit {
                rlim_cur: value,
                rlim_max: value,
            };
            if libc::setrlimit(resource, &limit) != 0 {
                return Err(io::Error::last_os_error());
            }
        }
        #[cfg(target_os = "linux")]
        {
            let mut old = libc::rlimit {
                rlim_cur: 0,
                rlim_max: 0,
            };
            if libc::getrlimit(libc::RLIMIT_AS, &mut old) != 0 {
                return Err(io::Error::last_os_error());
            }
            let value = ((256 << 20) as libc::rlim_t)
                .min(old.rlim_cur)
                .min(old.rlim_max);
            let limit = libc::rlimit {
                rlim_cur: value,
                rlim_max: value,
            };
            if libc::setrlimit(libc::RLIMIT_AS, &limit) != 0 {
                return Err(io::Error::last_os_error());
            }
        }
        for sig in [libc::SIGPIPE, libc::SIGXFSZ] {
            if libc::signal(sig, libc::SIG_DFL) == libc::SIG_ERR {
                return Err(io::Error::last_os_error());
            }
        }
    }
    Ok(())
}

/// After `limits`, the checker only computes on what it reads from stdin, so it is confined to
/// the system calls it was traced making (memory, threads, futexes, stdin and stdout). Anything
/// else (opening files, sockets, exec, ptrace, new processes, executable memory) fails with
/// EPERM; a system call from another architecture kills the process.
#[cfg(target_os = "linux")]
pub fn sandbox() -> io::Result<()> {
    #[cfg(target_arch = "aarch64")]
    const ARCH: u32 = 0xc000_00b7;
    #[cfg(target_arch = "x86_64")]
    const ARCH: u32 = 0xc000_003e;
    const KILL: u32 = 0x8000_0000;
    const ALLOW: u32 = libc::SECCOMP_RET_ALLOW;
    const DENY: u32 = libc::SECCOMP_RET_ERRNO | libc::EPERM as u32;
    const NOSYS: u32 = libc::SECCOMP_RET_ERRNO | libc::ENOSYS as u32;
    const NR: u32 = 0;
    const ARGS: u32 = 16;
    let op = |code: u32, k: u32| libc::sock_filter {
        code: code as u16,
        jt: 0,
        jf: 0,
        k,
    };
    let jump = |code: u32, k: u32, jt: u8, jf: u8| libc::sock_filter {
        code: code as u16,
        jt,
        jf,
        k,
    };
    let load = |offset: u32| op(libc::BPF_LD | libc::BPF_W | libc::BPF_ABS, offset);
    let ret = |k: u32| op(libc::BPF_RET | libc::BPF_K, k);
    let eq = |k: u32, jt: u8, jf: u8| jump(libc::BPF_JMP | libc::BPF_JEQ | libc::BPF_K, k, jt, jf);
    let set =
        |k: u32, jt: u8, jf: u8| jump(libc::BPF_JMP | libc::BPF_JSET | libc::BPF_K, k, jt, jf);
    let mut prog = vec![load(4), eq(ARCH, 1, 0), ret(KILL), load(NR)];
    // glibc falls back to clone when clone3 is missing; clone3's flags can't be inspected here.
    prog.extend([eq(libc::SYS_clone3 as u32, 0, 1), ret(NOSYS)]);
    prog.extend([
        eq(libc::SYS_clone as u32, 0, 4),
        load(ARGS),
        set(libc::CLONE_THREAD as u32, 0, 1),
        ret(ALLOW),
        ret(DENY),
    ]);
    for nr in [libc::SYS_mmap, libc::SYS_mprotect] {
        prog.extend([
            eq(nr as u32, 0, 4),
            load(ARGS + 16),
            set(libc::PROT_EXEC as u32, 1, 0),
            ret(ALLOW),
            ret(DENY),
        ]);
    }
    for nr in [
        libc::SYS_read,
        libc::SYS_write,
        libc::SYS_munmap,
        libc::SYS_mremap,
        libc::SYS_brk,
        libc::SYS_madvise,
        libc::SYS_futex,
        libc::SYS_sched_yield,
        libc::SYS_sched_getaffinity,
        libc::SYS_rt_sigprocmask,
        libc::SYS_rt_sigreturn,
        libc::SYS_sigaltstack,
        libc::SYS_getrandom,
        libc::SYS_gettid,
        libc::SYS_set_robust_list,
        libc::SYS_rseq,
        libc::SYS_exit,
        libc::SYS_exit_group,
    ] {
        prog.extend([eq(nr as u32, 0, 1), ret(ALLOW)]);
    }
    prog.push(ret(DENY));
    let fprog = libc::sock_fprog {
        len: u16::try_from(prog.len()).map_err(|_| io::Error::other("filter size"))?,
        filter: prog.as_mut_ptr(),
    };
    // prog outlives both calls; the kernel copies the filter when it is installed.
    unsafe {
        if libc::prctl(libc::PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) != 0
            || libc::prctl(
                libc::PR_SET_SECCOMP,
                libc::SECCOMP_MODE_FILTER,
                &fprog as *const libc::sock_fprog,
            ) != 0
        {
            return Err(io::Error::last_os_error());
        }
    }
    Ok(())
}

#[cfg(not(target_os = "linux"))]
pub fn sandbox() -> io::Result<()> {
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[cfg(target_os = "linux")]
    #[test]
    fn sandbox_blocks_files_sockets_exec_and_executable_memory() {
        // Raw system calls only between fork and _exit: the test harness has other threads.
        let pid = unsafe { libc::fork() };
        assert!(pid >= 0);
        if pid == 0 {
            let code = unsafe {
                let denied = |r: libc::c_long| r == -1 && *libc::__errno_location() == libc::EPERM;
                if sandbox().is_err() {
                    1
                } else if !denied(libc::syscall(
                    libc::SYS_socket,
                    libc::AF_INET,
                    libc::SOCK_STREAM,
                    0,
                )) {
                    2
                } else if !denied(libc::syscall(
                    libc::SYS_openat,
                    libc::AT_FDCWD,
                    c"/".as_ptr(),
                    libc::O_RDONLY,
                )) {
                    3
                } else if !denied(libc::syscall(
                    libc::SYS_execve,
                    c"/bin/true".as_ptr(),
                    std::ptr::null::<*const libc::c_char>(),
                    std::ptr::null::<*const libc::c_char>(),
                )) {
                    4
                } else if libc::mmap(
                    std::ptr::null_mut(),
                    4096,
                    libc::PROT_READ | libc::PROT_EXEC,
                    libc::MAP_PRIVATE | libc::MAP_ANONYMOUS,
                    -1,
                    0,
                ) != libc::MAP_FAILED
                {
                    5
                } else if libc::mmap(
                    std::ptr::null_mut(),
                    4096,
                    libc::PROT_READ | libc::PROT_WRITE,
                    libc::MAP_PRIVATE | libc::MAP_ANONYMOUS,
                    -1,
                    0,
                ) == libc::MAP_FAILED
                {
                    6
                } else if !denied(libc::syscall(
                    libc::SYS_clone,
                    libc::SIGCHLD as libc::c_long,
                    0,
                    0,
                    0,
                    0,
                )) {
                    7
                } else {
                    0
                }
            };
            unsafe { libc::_exit(code) };
        }
        let mut status = 0;
        assert_eq!(unsafe { libc::waitpid(pid, &mut status, 0) }, pid);
        assert!(libc::WIFEXITED(status), "sandboxed child died: {status:#x}");
        assert_eq!(libc::WEXITSTATUS(status), 0, "check that failed");
    }
    fn shell(script: &str, ms: u64) -> Verdict {
        let mut cmd = Command::new("/bin/sh");
        cmd.args(["-c", script]);
        run(cmd, Duration::from_millis(ms), b"")
    }
    #[test]
    fn successful_exit_and_one_marker_are_both_required() {
        assert_eq!(shell("printf 'accept\\n'", 1000), Verdict::Accept);
        assert_eq!(shell("printf 'reject\\n'; exit 1", 1000), Verdict::Reject);
        for script in [
            "printf 'accept\\n'; exit 101",
            "printf 'accept\\n'; kill -KILL $$",
            "printf 'reject\\n'; kill -KILL $$",
            "printf 'accept\\naccept\\n'",
            "printf 'accept\\n'; echo bad >&2",
            "exit 0",
        ] {
            assert_eq!(shell(script, 1000), Verdict::Error, "{script}");
        }
    }
    #[test]
    fn killed_child_cannot_accept() {
        assert_eq!(
            shell("printf 'accept\\n'; kill -KILL $$", 1000),
            Verdict::Error
        );
    }
    #[test]
    fn deadline_kills_grandchildren_too() {
        let path = std::env::temp_dir().join(format!("pge-grandchild-{}", std::process::id()));
        let mut cmd = Command::new("/bin/sh");
        cmd.args(["-c", "sleep 30 & printf '%s' $! > \"$1\"; wait", "probe"])
            .arg(&path);
        assert_eq!(run(cmd, Duration::from_secs(1), b""), Verdict::Error);
        let pid = std::fs::read_to_string(&path).unwrap();
        std::fs::remove_file(path).unwrap();
        let mut stopped = false;
        for _ in 0..100 {
            let status = Command::new("/bin/ps")
                .args(["-o", "stat=", "-p", pid.trim()])
                .output()
                .unwrap();
            let state = String::from_utf8_lossy(&status.stdout);
            if state.trim().is_empty() || state.trim().starts_with('Z') {
                stopped = true;
                break;
            }
            thread::sleep(Duration::from_millis(10));
        }
        if !stopped {
            let _ = Command::new("/bin/kill")
                .args(["-KILL", pid.trim()])
                .status();
        }
        assert!(stopped, "grandchild survived the process-group deadline");
    }
    #[test]
    fn hung_and_flooding_children_are_errors() {
        for script in [
            "printf 'accept\\n'; sleep 30",
            "exec 1>&-; exec 2>&-; sleep 30",
            "while :; do echo xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx; done",
        ] {
            let start = Instant::now();
            assert_eq!(shell(script, 100), Verdict::Error);
            assert!(start.elapsed() < Duration::from_secs(2));
        }
    }
    #[test]
    fn unexpected_exit_is_never_rejection() {
        for code in [None, Some(2), Some(101), Some(127)] {
            assert_eq!(classify(code, b"reject\n", b""), Verdict::Error);
            assert_eq!(classify(code, b"accept\n", b""), Verdict::Error);
        }
    }
}
