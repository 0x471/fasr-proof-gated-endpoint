# How hard the endpoint is to attack

> **In short**
> - Each layer limits what an attacker can send, change or reach.
> - Review found six bugs. All were fixed, with tests that fail on the old code.
> - The checker still trusts the proof system's verdict. Physical protection and secure boot remain outside the demonstrated result.

## The layers

### 1. Change the answer or model

The endpoint encodes the question itself and pins the approved model's files by [hash](glossary.md). It fixes the proof length and reads outputs only from proven values. The [binding rules](tour.md#how-a-proof-is-tied-to-the-question) explain each check.

### 2. Send a malformed message

Questions, forwarded questions and replies have one fixed layout for the approved model. A server answer adds a proof: up to 64 KiB on the wire, then checked against its exact pinned length.

Wrong types, non-finite numbers, oversized messages and truncated messages are refused. A [fuzz test](glossary.md) tries 10,500 random and mutated messages per parser.

### 3. Take over the proof checker

Each check runs in a separate process with [resource limits](tour.md#the-checker): 256 MiB of memory on Linux, bounded CPU time and 64 open files. File growth and crash dumps are disabled. A deadline or excessive output kills the process; hitting a limit never counts as a pass.

On Linux, the Rust checker then installs a system-call allow-list. It cannot open files or sockets, run programs, start processes or map executable memory. This contains a compromised checker, but cannot detect a wrong verdict: the checker could still say a bad proof passed.

### 4. Take over the endpoint itself

The main process reads every question and every server answer, so a bug there is the most exposed one. Once its sockets, log and model files are open, the device build confines itself.

[Landlock](glossary.md) stops it opening any file and lets it run only its own binary, to start checkers. A system-call allow-list then blocks every call it wasn't traced making, including other kinds of socket and executable memory. If either can't be applied, it refuses to start.

This limits what a takeover can reach, not what it can release. A taken-over endpoint is the gate, so it can send anything to clients. The binary also sits at a fixed address: this Rust target can't build a position-independent static binary. CI checks its other protections: no loader, a non-executable stack, read-only relocations and no writable code. See the [catalogue row](attacks.md#the-client-side-and-the-device-itself) (K53).

### 5. Write chosen text into replies or logs

Users receive proven output or a fixed error. An impossible but well-formed question gets `bad_request`; a server failure gets `unavailable`. Malformed user messages close the connection.

Logs use fixed words, never server text. They still record a counter, a question hash and elapsed time. The server influences which events occur and when.

Late, repeated and never-requested answers share a log allowance: no more than the number of questions issued. Exceeding it drops the link. See [device-output attacks](attacks.md#the-devices-own-outputs) for the tested rule and remaining client-driven log growth.

### 6. Reach the operating system

The stock Pi has SSH and other listening services. The v1 image runs one static Rust binary as an unprivileged user on a read-only system. It has one open port, no SSH and no scheduled jobs.

The firewall is built into the kernel; the endpoint refuses to start without its rules. The image has no login prompts and a locked-down kernel:

- No kernel modules in the image; module loading disabled at boot.
- Kernel lockdown; no raw-memory, debugger, tracing or performance-counter interfaces.
- No IPv6, sound, USB, raw packet sockets, io_uring, hypervisor or 32-bit programs. The radio chip is also switched off in the boot settings.
- Freed memory is wiped, and the kernel checks its own memory lists.
- The processor's protections against speculative-execution attacks are on. The pinned kernel left them off by default, and every image before 3 Nov ran that way.
- The root file system is checked block by block with [dm-verity](glossary.md). A changed program stops the boot. Without secure boot, though, someone who can rewrite the card can also rewrite the hash it is checked against.
- Memory-backed folders have size limits and can't run programs.
- The endpoint refuses to start unless every kernel setting reads back as written.

The 2 Nov image booted on the Pi with its start-up checks passing and only port 8700 answering. The 3 Nov night image, with everything above, has so far booted only in an emulator of the Pi 4. [Measurements](results.md#attack-surface) separates these observations from properties checked only during the build.

### 7. Replace the model or policy

Signed updates supply model files and release policy. They reject older or repeated updates, updates for another device, and unknown or revoked keys. Their parsers and forward-only rule are fuzzed.

Restoring an entire older store is still possible. A [TPM](glossary.md) counter to prevent that, and secure boot to require a signed system, are planned for v2. See [update attacks](attacks.md#updates).

## Catalogued scenarios

{{#include ../../docs/ATTACKS.md:summary}}

{{#include ../../docs/ATTACKS.md:outcomes}}

The [catalogue](attacks.md) gives each scenario's result and evidence, or says that evidence is missing. "Stopped" means the attack was refused or neutralised in a test or run, not that the device stopped working.

## Bugs found by review

Independent reviews of the code (run with AI tools) found six real bugs. Five affected answers held until their release turn.

| Bug | Fix or evidence |
|---|---|
| A checked answer could leave after a halt | Re-check when releasing |
| In arrival order, a stalled event loop could release a checked answer past its deadline | Re-check the deadline when releasing |
| Held answers did not count towards capacity; the queue could grow without bound | Count held answers |
| Spin let a later answer overtake an earlier one near its deadline, restoring a choice of error order | One ordered queue; only the next answer spins |
| A disconnect or halt chained busy-waits for many answers, stalling the loop for tens of milliseconds | Schedule the pump; at most one spin per run |
| Unexpected answers wrote unlimited logs, filling the image's RAM log, hiding later events or exhausting memory | Bound those records by issued questions |

Each fix has a test that fails on the old code. Evidence is in the [client/device rows](attacks.md#the-client-side-and-the-device-itself) and [log row](attacks.md#the-devices-own-outputs).

## What remains

Both sides share one cable; traffic is not physically forced through the endpoint. Secure boot, protection against whole-store rollback and on-device update delivery are unfinished.

The verifier's verdict remains trusted, and the trimmed Linux kernel remains large. Logs stay on the device; a client cooperating with the server can fill them at its request rate. See [Limitations](limitations.md).
