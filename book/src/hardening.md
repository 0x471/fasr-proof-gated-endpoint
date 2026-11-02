# How hard the endpoint is to attack

> **In short**
> - The endpoint is built in layers: check only what it computed itself, accept only one exact message format, contain the proof checker, and run on a system with almost nothing else on it.
> - {{#include ../../docs/ATTACKS.md:summary}}
> - Code reviews found six real bugs: five in the code that holds answers back until their turn, one that let the server write log records without limit; all fixed, each now covered by a test that fails on the old code.

## The layers

**1. Check only what the endpoint computed itself.** The endpoint never trusts the server's account of the question or the model. It encodes the question itself, pins the approved model's files by hash, fixes the proof length, and reads the output only from the proven values. See [How the endpoint works](tour.md#how-a-proof-is-tied-to-the-question).

**2. Accept one exact message format.** Questions, forwarded questions and replies have one fixed size and layout for the model in use. The server's answer is a fixed part plus the proof, which may be up to 64 KiB on the wire and must then be exactly the pinned length. Anything else is rejected: oversized or truncated messages, wrong types, numbers that aren't finite. A fuzz test throws 10,500 random and mutated messages at each parser.

**3. Contain the proof checker.** The checker is a separate program with hard limits: 256 MiB of memory (enforced on Linux, which the Pi runs), CPU time up to the deadline, no file growth, 64 open files, no crash dumps. It is killed if it runs past its deadline or prints too much. A checker that hits a limit counts as a failed check, never as a pass. In the Rust endpoint on Linux, the checker also runs under a system-call allow-list once its limits are set: it can't open files or network connections, run programs, start processes or map executable memory, so a bug in the proof code can't reach anything outside it (it could still print a wrong verdict).

**4. Say nothing the server chose.** Users only ever see the proven output or a fixed error (`unavailable`, or `bad_request` for a well-formed question the model can't answer); a malformed message just closes the connection. The endpoint's log uses a fixed vocabulary, never text from the server; it still records a counter, a hash of the question and the time taken, and which events happen and when still follow the server. The server can't make it write more records than there are questions: answers that are late, repeated or for a question never asked are logged, but never more of them in total than questions asked so far; one more ends the link (K51).

**5. Run on a minimal system (v1).** The standard Pi system has ssh and other services listening. The v1 image is built for the endpoint alone: one static Rust binary running as an unprivileged user, a read-only system, one open port behind a firewall built into the kernel (the endpoint won't start without its rules), no ssh and no scheduled jobs. The 2 Nov rebuild also locks the kernel down (no kernel modules on the image and module loading switched off at boot, kernel lockdown, no raw memory, debugger or tracing interfaces, nothing for IPv6, radios, sound or USB) and removes every login prompt; its check on the Pi is pending.

**6. Accept only signed changes.** The model files and the release policy come from a signed update: the endpoint refuses rollbacks, replays, updates for another device and unknown or revoked keys (catalogue rows K36-K48). The update files' parsers and the forward-only rule are also fuzzed. Still planned (v2): secure boot, so the board starts only a system we signed, and a counter in a TPM so a whole older copy of the store can't be restored (K43).

## Catalogued scenarios

{{#include ../../docs/ATTACKS.md:outcomes}}

Every scenario has a row in the [Attack catalogue](attacks.md) with its result and its evidence, or says that there is none yet.

## Bugs found by review

Independent reviews of the code (run with AI tools) found six real bugs, five of them in the code that holds answers back until it is their turn:

- an answer that was already checked could still leave after the endpoint had decided to stop answering;
- in arrival order, under a stalled event loop, a checked answer could leave after its own deadline;
- answers waiting their turn didn't count towards the endpoint's capacity limit, so the queue could grow without bound;
- with fixed-time release and the spin option, a later answer could overtake an earlier one whose deadline had nearly passed, so the server could choose the order of two failures again;
- with spin, a disconnect or halt that decided many answers at once chained one busy-wait per answer, stalling the endpoint for tens of milliseconds;
- every late, repeated or never-asked-for answer wrote a log record, without limit, and on the v1 image the log is kept in memory, so a server could fill it (and hide what it did next) or use up memory.

Each now has a test that fails on the old code (catalogue rows K30, K31, K33, K35 and K51).

## What isn't hardened yet

Both sides still share one cable, so nothing physically forces the server's traffic through the endpoint; there is no secure boot; a whole older copy of the update store is accepted (K43); a new update needs a new image or an offline step; the verifier's own verdict is trusted; the Linux kernel, though trimmed, is still large, and two builds of it can't yet be compared byte for byte; and the log stays on the device, where a client working with the server can still fill it at the rate it sends questions. See [Limitations and open questions](limitations.md).
