# Measurements

## Summary

<!-- ANCHOR: findings -->
| Signal | Basic endpoint | Best result so far | Cost |
|---|---|---|---|
| Changed answer content | Blocked by proof | Blocked | About 0.24 s per check on the Pi |
| Reply order | Leaks | Tested ordering code blocked: replies follow question order | A slow reply delays later ones |
| Reply timing | Leaks | Much reduced. Fixed release prevents early replies; a small trace remained without spin. With spin, a 512-answer test was inconclusive on stock OS and found nothing on the stripped image, one run | 4.0 s per answer instead of about 0.8 s |
| Chosen failures | Leaks | Cap: 8 of 32 planted bits recovered instead of 32/32. Stopping at the first failure released nothing readable; pre-registered, 2 Nov | Cap: 54 of 128 answers ok instead of 120 during continued failures; an honest server loses none. Stopping answers nothing after the first failure |
<!-- ANCHOR_END: findings -->

> **In short**
> - Arrival order stopped the ordering code tried. Fixed release reduced timing signals; failures still leaked.
> - The registered spin test was inconclusive on the stock system and detected nothing on the stripped image, once each.
> - Failure caps reduced leakage at a large availability cost. Random sleeps kept leaking in a model.

Unless stated otherwise, runs used one Raspberry Pi 4 with 2 GB and 64-bit Raspberry Pi OS Lite. An Apple M4 Pro laptop ran the Python EZKL prover and outside observer over direct Ethernet. Dates are 2026.

A fixed decoder tries to recover planted bits. "16/16" means it recovered every bit. A decoding failure means this decoder missed this message in this run. The achieved rates are not channel-capacity bounds; tests use one sequential client unless stated otherwise.

[Leakage](leakage.md) explains the mechanisms. The [glossary](glossary.md) explains the statistical terms.

## Checking one proof

### What does verification cost?

The tiny circuit takes about 0.1 s in the proof tool alone. The complete Rust check takes 0.19 s; the Python reference takes 0.24 s with all safety limits.

<details><summary>CLI runs and the Python cost breakdown</summary>

Each CLI run includes process start-up, loading and verification.

| Date | Runs | Result |
|---|---|---|
| 13 Oct | 20 | 99-103 ms |
| 16 Oct | 20 | min 101, median 103, max 106 ms |
| 19 Oct | 20 | min 101, median 103, max 280 ms (one cold run just after boot) |

The full-path breakdown uses medians of 20 checks on 19 Oct (`device/verify_cost.py`).

<!-- ANCHOR: verify-cost -->
| Path | ms |
|---|---|
| Raw CLI, default threads (4 cores) | 97-98 |
| Raw CLI, one thread (`RAYON_NUM_THREADS=1`) | 163 |
| With the endpoint's resource limits (single-threaded launcher) | 207 |
| Re-checking the bundle's hashes (includes a 4 MB setup file) | 28 |
| Reading and canonicalising the proof | 2 |
| Full endpoint check | 239 |
<!-- ANCHOR_END: verify-cost -->

The raw test proof is 3,072 bytes. The 64-bit ARM EZKL CLI, version 23.0.5, is 36 MB (36,091,376 bytes). It includes proving and setup code too.

One thread costs 1.7x; Python launcher start-up costs about 45 ms. A static launcher and hashing once on a read-only image could reduce these costs. On the laptop, proving takes about 0.5-0.8 s; in-process verification takes 8-14 ms.

</details>

### How much memory is enough?

<!-- ANCHOR: memory -->
Near the limit, address-space randomisation makes outcomes vary. 128 MiB passed 20 of 20 runs; 144 and 160 MiB passed about half. At the configured 256 MiB, every recorded check passed: 231 of 231.
<!-- ANCHOR_END: memory -->

More memory did not improve acceptance steadily. A false error counts as server failure, so a margin matters. The cap is enforced only on Linux.

<details><summary>Memory sweep and reliability limits</summary>

One sweep on 19 Oct ran 20 checks per limit. Unaccepted checks aborted and became endpoint errors.

| Limit | Accepted |
|---|---|
| 96 MiB | 0/20 |
| 112 MiB | 18/20 |
| 128 MiB | 20/20 |
| 144 MiB | 11/20 |
| 160 MiB | 9/20 |
| 192 MiB | 20/20 |
| 224 MiB | 20/20 |
| 256 MiB (the endpoint's setting) | 20/20 |
| 320 MiB | 20/20 |

Other checks that day at 256 MiB comprised one first check, then 200/200 and 10/10. Together with the sweep, that gives 231 of 231. At 192 MiB another run passed 200/200; at 160 MiB a later sweep passed 4/10.

Address-space layout randomisation was on. Zero failures in 231 independent runs puts the failure rate below about 1.3 % at 95 % confidence. Independence is an assumption; this is not proven zero and covers only this circuit on this Pi.

</details>

## Attack surface

### What could a network attacker reach?

We scanned each version and recorded its services. The development image had no endpoint; later images ran one. A quiet scan alone therefore does not show a working hardened endpoint.

<details><summary>Network scans and image conditions, by version</summary>

<!-- ANCHOR: attack-surface -->
| Version | Seen from outside | Notes |
|---|---|---|
| v1.1, 3 Nov night (`b037c669...`, then the freeze candidate `c22954ee...` with pinned file-system ids; both booted on the Pi 3 Nov) | TCP 8700 only: 1 open, 0 refused, 65,534 dropped (both) | The endpoint started, so on the device the dm-verity root mounted, every kernel setting read back, the firewall loaded and the endpoint confined itself. 16/16 honest answers ok on each, within 4000.7-4001.4 ms of being sent; a flooding server was dropped (4/4 `unavailable`, each released at its 4 s time). Kernel options, CPU mitigations and the radio switch-off: checked in the build and in QEMU, not observable on the device |
| v0 (stock OS, 16 Oct) | TCP 22 (ssh) and 8700 (the endpoint); UDP 5353 (mDNS) | 633 packages, 13 running services |
| v0 (stock OS, 29 Oct, endpoint not running) | TCP 22 only (`nmap -p-`); 691 TCP ports showed as filtered, most likely an artefact of the scan (on the v1 image the same pattern re-probed one by one came back closed); UDP not scanned. On the device: UDP 5353 (mDNS) and two unattributed UDP ports | 633 packages, 13 running services, 66 kernel modules (Wi-Fi and Bluetooth drivers loaded); per-port software in `docs/ATTACK_SURFACE.md` |
| v1 hardened image (2 Nov, `aa289680...`, booted on the Pi 2 Nov) | TCP 8700 only: 1 open, 0 refused, 65,534 dropped (connect scan of every port from the laptop) | The endpoint started, so both start-up checks passed on the device: firewall rules loaded, module loading switched off. 16/16 honest answers ok, each 4000.8-4002.0 ms after it was sent. Locked-down kernel and no login: checked in the build (`image/build.sh`), not observed on the device (no screen attached, no login by design) |
| v1 image with the update store and firewall (30 Oct, booted on the Pi) | TCP 8700 only; all 65,534 other TCP ports dropped (no reply at all, where the image without the firewall refused them); ping dropped | Model and release policy from the signed update store on a writable data partition; nftables rules built into the kernel; the endpoint won't start without the rules |
| v1 image with the Rust endpoint (30 Oct, booted on the Pi) | TCP 8700 only (connect scan of all 65,535 ports from the laptop; every other port refused) | One static endpoint binary as user `pge`, fixed release 4 s, read-only root, no Python, no SSH; UDP not scanned |
| v1 development image (16 Oct, `sdcard.img` 159 MB) | 0 of 65,535 TCP ports open; top 100 UDP ports closed; no IPv6 | No endpoint was running on this image yet, so this shows a quiet base system, not a working hardened endpoint |
<!-- ANCHOR_END: attack-surface -->

</details>

### Can another machine reproduce the image?

The first hardened build matched user space apart from build metadata. v1.1 then made the kernel reproducible too, excluding signing-key-dependent files. That 2 Nov v1.1 build never booted on the Pi. The 3 Nov night freeze candidate did, and rebuilt from scratch it gives the same image byte for byte on the laptop VM, once the file-system ids that `mkfs` picks at random are pinned (otherwise the root hash differs). It has not yet been compared with CI.

<details><summary>Two independent builds, then the reproducible v1.1 build, 2 Nov</summary>

The hardened image used identical `image/` files and the same CI endpoint binary. One build ran in the laptop's Linux VM; another ran on a clean GitHub runner through `.github/workflows/image.yml`. The runner signed its update with a throwaway key. `image/manifest.sh` compared every file.

779 of 796 files matched, including the endpoint and every configuration file. Five differed by design: `root.pub`, the key list, two signatures and store state.

The other 12 differences were build metadata:

- BusyBox's build time.
- A padded directory string in 9 xz, kmod and nftables binaries and libraries. The runner's directory was 4 characters shorter.
- Host paths in a gdb helper script.
- The kernel's user@host, build number, time and newly generated module-signing certificate, which shifted the rest of the file.

This checked user space file by file. Comparing kernels byte for byte required fixed build time and path, plus handling the generated signing key.

v1.1 enables Buildroot's reproducible mode and uses the same build directory everywhere. The kernel has no module-signing key, so embeds no certificate; lockdown then prevents any module loading.

Two GitHub ARM-runner builds used the same commit and CI endpoint binary. 791 of 796 files matched, including the kernel. The other 5 depended on the throwaway key.

A third build used the laptop's Linux VM and demo keys. It also matched 791 of 796 files, including the kernel and endpoint. The same 5 signing-key-dependent files differed by design. Thus different machines reproduced the image subject to those key-dependent differences.

</details>

## The Rust endpoint on the Pi (29 Oct)

### Did the Rust port preserve behaviour and improve speed?

The device runs a static 64-bit ARM CI binary, without Python or the EZKL CLI. These checks used the same Pi and setup described above. Raw data is in git-ignored `runs/2026-10-29_rust/`.

| Check | Result |
|---|---|
| Checker alone (`device/rust_verify_cost.py`, one thread, n = 20) | valid accepted, changed output / changed input / garbage proof rejected, truncated job an error; 189 ms per check (Python endpoint path: 239 ms) |
| Endpoint alone, local stub server (`device/endpoint_latency.py`, n = 30, two runs each, interleaved) | Rust 192 / 193 ms, Python 241 / 242 ms per answer |
| End to end with the laptop prover (honest, arrival, n = 16, two runs each, interleaved) | Rust 1008 / 1023 ms, Python 1065 / 1074 ms |
| Misbehaving server (the table above, plus wrong id and dropped answers) | same outcomes as the Python endpoint; a proof made for another question is rejected |
| Leak matrix (arrival and fixed release, the bits in the next section) | same as the Python endpoint: timing leaks 16/16 under arrival release; order blocked; failure position leaks 16/16 under both |
| Failure cap on (W = 64, F = 1, C = 64; fixed release, 64 answers) | all 64 replies match `observer/cap_model.py`; 4 of 16 planted bits got out (16/16 without the cap); 18 of 64 answers ok (60 of 64 without it) |
| Three connections at once (arrival and fixed, honest and order code) | all answers ok; the order code decoded to a constant |
| 5 ms spin, 512 answers, the same pre-registered protocol | inconclusive again: held-out decoder 0.44 / 0.48 errors, p = 0.0325; received 0.8-2.8 ms after the release time |

<details><summary>Why Rust was initially slower</summary>

Each check originally hashed the 4 MB bundle three times. This Pi lacks SHA instructions; each pass costs about 25-28 ms. The supervisor also slept 1 ms after every 64 KiB written to the checker, costing about 66 ms per check.

Before fixing those issues, Rust was about 65 ms slower per answer end to end. Both fixes made it faster than the Python path.

</details>

### How much of the release budget does honest traffic use?

One client used medians of 810-901 ms and at most 979 ms. Three concurrent connections used a median of 1,824 ms and at most 2,936 ms. All 72 honest answers passed, so this load caused no failures for the cap to count.

<details><summary>Runs, queueing and scope</summary>

Computed on 2 Nov from honest arrival and immediate runs on 19 and 29 Oct, using the laptop prover. Times run from sending a question to reading its answer. The one-client results comprise three runs of 16; the three-connection run has 24 answers from 29 Oct.

The laptop proves one answer at a time. A round's third question waits for the first two. Fixed release turns an unchecked answer into `unavailable` at the deadline, so the budget must cover the busiest proving queue, not just one proof.

With three clients, the 4 s budget left about a second. Leakage under other budgets has not been measured.

</details>

### Did the v1 images work on the Pi?

<details><summary>30 Oct smoke checks</summary>

The first image used its own settings: fixed release, 4 s and 5 ms spin, with the laptop as server.

- Honest answers: 9/9, received 4001-4003 ms after sending.
- Changed outputs: 3/3 refused; garbage frames: 3/3 refused. Both gave `unavailable`.
- The endpoint reconnected within about 2 s after a server restart.
- One timing-code run got 11 of 16 bits wrong, with answer times of 4000.8-4001.6 ms.
- Failure position still leaked 16/16; this image had no cap.

Both leakage runs used the matrix's bits and overlapped a port scan. Their timing is a smoke check only.

The update-store/firewall image brought port 8700 back about 21 s after power-on. Honest replies were 9/9 at 4001-4005 ms, using fixed release from the signed manifest. Changed outputs and garbage were each refused 3/3. Replayed answers for the same question were accepted 3/3 by design.

</details>

### Does the root check stop a changed card? (3 Nov night)

Can someone who edits the card while the device is off change the software it runs? The 3 Nov night image mounts its root through dm-verity, which checks each block against a hash tree when it is read.

- One flipped bit in the first block of `/bin/busybox`, on the card, written from the Mac with `images/tamper_card.sh` (only after the sector matched the image): the Pi did not come up. Port 8700 stayed closed and the Pi didn't answer on the network for 2 minutes, though powered.
- The same bit written back, same cable and power: port 8700 open at once, 8/8 honest answers ok.
- The same kernel and image in QEMU's Pi 4 model, where the console is visible: `data block 2994 is corrupted`, init couldn't run, and the kernel stopped.

This stops edits to the root file system. It doesn't stop someone who rewrites the card's boot partition too, because the hash it checks against is stored there. Secure boot would close that; it isn't built. The update store has its own signatures.

<details><summary>How much code the device runs (3 Nov night build)</summary>

- Kernel image: 15,024,640 bytes, down from 15,897,088 in the 3 Nov day build.
- C source linked into the kernel: 1,976 files, 1,641,153 lines, headers and assembly not counted (objects from `vmlinux.a`).
- Target packages: 19, including BusyBox (about 162k C lines compiled), glibc, nftables, kmod and xz. Nothing on the image loads modules, so kmod and xz could go.
- Our Rust: 3,732 lines in five crates; `Cargo.lock` lists 206 packages, mostly EZKL's.

</details>

### Did the stripped image remove the timing trace?

The registered 512-answer test detected nothing with this decoder on the v1 image. That does not show the image removed the trace: each system had one run on different days. A better decoder could still find a signal.

<details><summary>30 Oct repeat and the unexplained late controls</summary>

The test repeated `docs/EXPERIMENT_PROTOCOL.md` with 5 ms spin. Held-out error rates were 0.49 and 0.52, p = 0.50; the honest control gave p = 0.69. The registered verdict is "not detected by this decoder at n = 512".

Signal replies arrived 0.8-2.3 ms after release time. The same test was inconclusive on stock systems: Python on 20 Oct, Rust on 29 Oct. The honest image control had six late answers, one 28.6 ms late; their cause is unknown.

</details>

## The endpoint end to end

### Did correct answers pass and bad server behaviour fail?

| Date | Software | Result |
|---|---|---|
| 16 Oct | v0 (JSON, immediate release) | about 0.9-1.05 s per answer (mostly proving on the laptop); `y` matches the float model within quantisation |
| 19 Oct | v1 (binary, arrival order, limits, fixed-word logs) | 5/5 ok, 0.79-0.89 s per answer |

The v0 output `y` matched the float model within quantisation. Against v1 on 19 Oct:

| Server behaviour | What the endpoint did |
|---|---|
| Changes an output value | proof rejected; client gets `unavailable` |
| Replays an earlier answer for the same request | accepted, by design: the same request gives the same output, so the server has no choice there |
| Answers twice | one answer to the client; the duplicate is dropped and counted |
| Sends garbage or an oversized frame | server link dropped; the pending request fails, the next gets `unavailable` in under 1 ms |

The first timing test, on 16 Oct v0, delayed answers by 1 s for a one bit. The observer recovered 16 of 16 bits at 0.69 bit/s. Honest answers varied by 81 ms.

## Release policies on the Pi

### Which release rules stopped the planted messages?

The core experiment ran on 19 Oct: one run per cell, 16 planted bits per channel, a 4 s budget for every policy. `device/pi_matrix.sh` ran it; `observer/analyze_matrix.py` summarised it.

<!-- ANCHOR: matrix -->
| Channel the server uses | immediate (v0) | arrival (v1) | fixed |
|---|---|---|---|
| Timing: delay an answer by 1 s for a 1 | 16/16 recovered | 16/16 recovered | not recovered (12/16 wrong); answer times spread over 2.0 ms |
| Ordering: answer 3 concurrent requests in a chosen order | 16/16 recovered | decoded bits constant | decoded bits constant |
| Failure position: fail one chosen answer in each 16 | 16/16 recovered | 16/16 recovered | 16/16 recovered |
| No signal (honest server, timing decoder) | 8/16 wrong | 10/16 wrong | 7/16 wrong |
| Honest answer time, median | 0.81 s | 0.83 s | 4.0 s |
<!-- ANCHOR_END: matrix -->

- Ordering: arrival and fixed release produced constant decoded bits regardless of the planted message. On one connection, admission-order replies and increasing client ids enforce this by construction.
- Timing: fixed release stopped recovery of the 1 s code, but left a smaller trace. Each answer waited the budget, about 5 times the honest median in this sequential run.
- Failure position: every policy leaked the message.

A separate localhost v0 run recovered floor(log2 k!) bits per batch of k concurrent questions without errors. It recovered 16/16, 32/32 and 64/64 bits for k = 2, 3, 4.

<!-- ANCHOR: failure-leak -->
Only 4 of 64 answers failed: one chosen position per block of 16. All 16 bits got through, or 0.25 bit per request with this encoder.
<!-- ANCHOR_END: failure-leak -->

### How the failure code scales

One failure per batch of B answers carries log2(B) bits in its position. Thus n answers carry (n/B) log2(B) bits with n/B failures.

Sending 512 bits needs 128 failures among 2,048 answers with B = 16. With B = 1,024, it needs 52 failures among 53,248 answers. Fewer failures cost more answers.

That is one encoder. For any encoder using only failure positions:

<!-- ANCHOR: failure-scaling -->
| What the server may do | Bits it can carry |
|---|---|
| Fail any answers it likes, no cap | up to 1 bit per answer (512 answers carry 512 bits) |
| Fail exactly k of n answers | log2 C(n, k), e.g. 168.9 bits for 32 failures among 512 answers |
| Any pattern the failure cap allows (W = 64, F = 1, C = 64, `observer/cap_bound.py`) | at most 11.02 bits in 64 replies, 63.05 in 512, 472.71 in 4,096 (about 0.12 bit per reply) |
<!-- ANCHOR_END: failure-scaling -->

These bounds count failure patterns only. Timing, busy replies and logs are separate; see the `observer/cap_bound.py` docstring.

### What fixed release leaves

The first longer run used 128 random bits and 128 honest-control requests. It asked whether the remaining 2 ms of jitter followed the server's choices.

| Run | Bit-1 minus bit-0 answer time | Permutation test |
|---|---|---|
| Server encoding bits | -0.66 ms (-0.73 and -0.60 in each half) | p < 0.0001 |
| Honest server, same labels | +0.19 ms | p = 0.13 |
| Server encoding bits, with a 5 ms spin before release (old spin code) | +0.08 ms | p = 0.31 |
| Honest server, with the spin (old spin code) | +0.09 ms | p = 0.20 |
| Server encoding bits, spin, fixed code, n = 512 (20 Oct) | -0.06 ms | p = 0.071 |
| Honest server, spin, fixed code, n = 512 (20 Oct) | -0.02 ms | p = 0.48 |

<!-- ANCHOR: no-spin-trace -->
Without spin, one-bit answers left 0.66 ms earlier than zero-bit answers: 128 answers, p < 0.0001; the honest control showed nothing. A decoder trained on one half and tested on the other got about three bits in four right.
<!-- ANCHOR_END: no-spin-trace -->

<!-- ANCHOR: spin-verdict -->
With a 5 ms spin, no mean shift was detected. A pre-registered 512-answer test was inconclusive: its better half decoded 143 of 256 correctly, about 56 %, p = 0.041. The rule requires p < 0.01 for a leak and p > 0.05 for "not detected".

This decoder finds little, but the trace is not shown to be gone. A cleverer decoder might find more. On the stripped v1 image, the same test found nothing on 30 Oct: p = 0.50, one run. The residue may depend on the surrounding system; this has not been isolated.
<!-- ANCHOR_END: spin-verdict -->

<details><summary>Earlier decoder results and why the spin test was repeated</summary>

Without spin, `observer/jitter_test.py --heldout` got 25 % and 28 % wrong on its two halves. Independent, symmetric binary errors would imply about 0.14-0.19 bit per answer. That is a model-based figure, not measured throughput; one half's two error kinds were not symmetric.

The first 5 ms spin run woke early and busy-waited until release (`--spin-ms 5`). Its mean shift was +0.08 ms, p = 0.31. Held-out errors were 34 % on one half and 44 % on the other; honest controls were 39-59 %.

A null test refitted the decoder to shuffled labels and did that well only 0.75 % of the time. This run preceded the spin-ordering fix and recorded 0.1 ms timestamps, so it was repeated.

</details>

<details><summary>The registered repeat, 20 Oct: results and limitations</summary>

`docs/EXPERIMENT_PROTOCOL.md` was written before the data. It specified 512 seeded random bits, 249 of them ones, corrected spin code, microsecond timestamps and 512 honest-control requests.

Both runs completed 512 of 512, all accepted. Replies arrived 4000.96-4003.84 ms after sending, or 0.96-3.84 ms after their 4 s release time, including the network.

The primary held-out decoder missed 118 and 113 of 256, or 46 % and 44 %. Its refitted null matched the better half 4.1 % of the time: p = 0.041. The honest control missed 131 and 134 of 256, p = 0.77.

The registered rule calls a residue only below p = 0.01, and "not detected" only above 0.05. Hence the verdict is inconclusive. Its better half got 143 of 256 right, about 56 %, against 72-75 % without spin at n = 128 on 19 Oct.

This does not show the channel is gone or bound a cleverer observer. Separate days also cannot show that spin caused the difference. Idle wake-up latency is an unisolated hypothesis. Complete output: `docs/results/2026-10-20_spin5_512.md`.

</details>

<details><summary>Protocol deviation: discarded partial runs</summary>

The first signal and control attempts stopped at 149 of 512 because the observer had a fixed 600 s timeout. Commit `cd0086c` changed only `device/pi_scenario.sh` to scale that limit with run length. The Pi endpoint's code hash stayed unchanged; both runs were repeated fully.

An edit to the script while it ran also disturbed the first attempt. Its signal run lacks a manifest and endpoint log. Its honest run has 149 rows but 150 logged accepts. The partial-run analysis was printed but is not used; the registered decision rule stayed unchanged.

</details>

<details><summary>A second statistic: binned mutual information</summary>

`observer/estimate.py` measures how much the hidden bit is associated with answer time. It uses 4 quantile bins, small-sample bias correction, a shuffled-label null and a bootstrap interval. `tests/test_estimate.py` first checked it on synthetic channels with known values.

This describes one binned statistic, not a lower or upper bound on timing leakage.

| Run | n | Mutual information, bit per answer (4 bins) | p |
|---|---|---|---|
| Fixed release, server encoding bits | 128 | 0.17 | 0.0005 |
| Fixed release, honest server | 128 | about 0 | 0.68 |
| Fixed release with spin (old code), server encoding bits | 128 | 0.05 | 0.012 |
| Fixed release with spin (old code), honest server | 128 | about 0 | 0.73 |
| Spin, fixed code, server encoding bits | 512 | 0.006 (bootstrap interval -0.003 to 0.026) | 0.069 |
| Spin, fixed code, honest server | 512 | -0.004 (bootstrap interval -0.004 to 0.011) | 0.94 |

Negative estimates are bias-correction noise, not negative information. Bootstrap intervals assume exchangeable answers within one run. They do not cover variation between sessions, days or encoders.

With 2 or 8 bins, the no-spin result holds at p = 0.0005. The old spin result is not significant: p = 0.46 and 0.09. The corrected 512-answer run is also not significant with 4 bins, p = 0.069.

The 128-answer runs rounded times to 0.1 ms, leaving only 19-30 distinct values per run. Their old spin code could let a later answer overtake an earlier one with several in flight, as review found. The 512-answer repeat fixes both limitations.

</details>

### What the timing data can rule out (3 Nov, analysis of earlier runs)

"Not detected" is not "small". This asks how large a shift between bit-1 and bit-0 answers each fixed-release run still allows, and what such a shift could carry. Tool: `observer/shift_bound.py`. It takes a 95% bootstrap interval for the mean shift and a robust noise estimate, then applies the Gaussian channel formula at the larger end of the interval.

<!-- ANCHOR: timing-limits -->
| Run | Answers | Shift (ms) | 95% interval (ms) | Noise (ms) | Model-based upper estimate (bit/answer) |
|---|---|---|---|---|---|
| Stripped image, spin, timing code (30 Oct) | 512 | -0.018 | -0.046 to +0.009 | 0.093 | 0.042 |
| Its honest control, same labels | 512 | +0.078 | -0.081 to +0.343 | 0.227 | 0.33 |
| Load code, protocol 4 (2 Nov) | 256 | -0.046 | -0.397 to +0.314 | 1.92 | 0.008 |
| Three clients, protocol 5 (2 Nov) | 258 | +0.057 | -0.014 to +0.129 | 0.205 | 0.069 |
<!-- ANCHOR_END: timing-limits -->

At one client and 4 s per answer, 0.042 bit/answer is about 38 bits per hour. The honest control comes out higher than the signal run: one 28.6 ms late answer widens its interval. These numbers measure what the data can rule out, not leakage.

Near zero shift and with comparable noise, the estimate falls roughly as 1/n: the interval narrows as the square root of the answer count, and the bits grow with the square of the shift. Reaching 0.001 bit/answer would take about 40 times the answers, about 22 hours of Pi time at one client.

<details><summary>What this does and doesn't bound</summary>

It bounds the encoder each run used, read as a mean shift, under a Gaussian noise model. Another encoder may shift times further. Noise that isn't Gaussian can let a code carry more: for a given spread, Gaussian noise is the worst case for the sender. No finite run rules out a code hidden in the fine detail of the time distribution. A guaranteed bound has to come from design, for example a release stage that can't see what the checker or the server did.

</details>

### Giving the release loop its own CPU (3 Nov, protocol 7)

Does the residue go away when the event loop has a CPU of its own and every proof check runs on the others? Pre-registered in `docs/EXPERIMENT_PROTOCOL_4.md`: the experiment image (`36b18e84...`, fixed release, 4 s, spin 0), one client, 256 answers per run with the 1 s timing code, and an honest control per condition. The two conditions differ only in the kernel command line.

<!-- ANCHOR: own-cpu -->
| Condition | Held-out errors, two halves | Held-out p | Control p | Mean difference (p) | Verdict |
|---|---|---|---|---|---|
| Shared (as built) | 0.45 / 0.48 | 0.32 | 0.57 | -0.10 ms (0.17) | not detected |
| Isolated (`isolcpus=3`, release loop on CPU 3) | 0.53 / 0.52 | 0.86 | 0.14 | -0.006 ms (0.93) | not detected |
<!-- ANCHOR_END: own-cpu -->

The reading was fixed in advance: with nothing detected under shared, the isolated condition can't show an improvement, so the question stays open. Unlike the stock system earlier, this hardened image showed no residue at spin 0 at this sample size; protocol 2 is the registered test of why.

<details><summary>Secondary measures, captures and deviations</summary>

- Mutual information with 4 bins: about zero in both (p = 0.61 shared, 0.59 isolated).
- `observer/shift_bound.py`: the data allow a shift of up to 0.25 ms (shared) and 0.15 ms (isolated), at most 0.063 and 0.017 bit per answer under the Gaussian model.
- Packets: in all four runs every reply was one 38-byte packet with TTL 64 and the same TCP window; the timing runs and the honest runs look the same at packet level. The isolated capture holds all 512 replies.
- Deviations, declared before analysis: one capture per condition instead of one per run, and about 1.5 minutes of the honest shared run (16 of 256 replies) uncaptured after a capture was restarted under the same file name. `observer/pcap_trace.py --partial` reads the capture that starts mid-connection.
- From outside, the run can't show that the kernel kept CPU 3 free of other tasks, only that the endpoint started with its placement, which it refuses to do otherwise.

</details>

### Random sleeps instead of a fixed release time (a model, 2 Nov)

Does adding random delay hide the server's chosen delay? In this model, it keeps leaking; fixed release gives no timing signal. This is not a device measurement.

The model is `observer/sleep_vs_fixed.py`, with tests in `tests/test_sleep_vs_fixed.py`. The server answers on time or a fixed amount late. The endpoint adds a uniform sleep from 0 to R, or releases at a fixed time after admission.

<details><summary>Analytic model and simulations</summary>

For a two-level code shifted by d, uniform sleeps alone reveal exactly d/R bit per answer when d is at most R. Only the first and last d of the window reveal the bit. Extra noise only lowers that information.

A server allowed delay up to A can carry up to log2(1 + A/R) bit per answer, exact when A/R is an integer. The sleep must therefore grow with the server's freedom. Fixed release removes that timing choice; a missed deadline becomes a failure signal instead.

The simulation used honest-time noise with sd 20 ms, a 200 ms shift and 4,096 answers. The 4-bin estimator understates the exact value. Every tested random sleep remained significant, including 0-4 s sleeps that add 2 s on average.

<!-- ANCHOR: random-sleeps -->
| Release rule | Added wait on average | Upper bound, d/R | Binned estimate | p (500 shuffles) |
|---|---|---|---|---|
| Random sleep 0-0.5 s | 0.25 s | 0.4 bit | 0.26 bit | 0.002 |
| Random sleep 0-1 s | 0.5 s | 0.2 bit | 0.062 bit | 0.002 |
| Random sleep 0-2 s | 1 s | 0.1 bit | 0.016 bit | 0.002 |
| Random sleep 0-4 s | 2 s | 0.05 bit | 0.005 bit | 0.002 |
| Fixed release, 4 s | 3.2 s | 0 | 0.000 bit | 1.0 |
<!-- ANCHOR_END: random-sleeps -->

With a 50 ms shift and 512 answers, sleeps from 0-0.5 s upwards were not significant: p = 0.076 to 0.53. Yet d/R remains 0.1 down to 0.0125 bit per answer. Finding nothing at one sample size does not establish that random sleep closed the channel.

</details>

### Several connections (smoke runs, 20 Oct)

These short checks tested the new runner and several-client observer. They used `CLIENTS=3`, a 4 s budget, and one run each; they were not registered experiments. The single-client smoke row below used a 1 s release time.

| Run | Result |
|---|---|
| One client, fixed release, 5 ms spin, 3 answers | 3/3 ok; received 1.39-2.22 ms after the 1 s release time; the manifest records the commit and the Pi's file hashes |
| 3 connections, arrival release, honest server, 2 rounds | 6/6 ok, replies in client order every round |
| 3 connections, server answers each round in a chosen order (8 bits), immediate release | 8/8 bits read back from the order replies arrived across connections |
| The same, arrival release | decoded bits constant (`00000000`): the order across connections didn't follow the server |

The chosen order reached the observer across connections under immediate release. Arrival order stopped this code in this run: 8 bits per rule, with all three clients on one machine. The planned two-client deadline-pressure experiment remains the substantive test.

### Load and several clients on the hardened image (2 Nov, protocols 4 and 5)

Could overlapping proof checks or concurrent clients shift releases? One overlapping check was not detected; the three-client timing test was inconclusive. Every answer in every run was accepted.

Both tests were pre-registered in `docs/EXPERIMENT_PROTOCOL_2.md`. They used image `aa289680...`, fixed release 4 s, 5 ms spin and an idle laptop.

<!-- ANCHOR: load-and-clients -->
| Protocol | Runs | Held-out decoder (signal / control) | Secondary | Verdict (rule fixed in advance) |
|---|---|---|---|---|
| 4: a proof check timed to overlap a release, one per second | `load_bits` and the zero-bit control, 256 answers each | errors 0.50 / 0.51, null p = 0.58; control 0.51 / 0.51, p = 0.65 | mean difference -0.05 ms (p = 0.80); mutual information -0.004 bit per answer (p = 0.68) | not detected by the registered decoder in this run: one overlapping check per release, on this image, at n = 256 |
| 5: the 0.1 s timing code from three clients at once | `timing_c3` and the honest control, 86 rounds = 258 answers each | errors 0.50 / 0.39, null p = 0.0175; control 0.50 / 0.55, p = 0.75 | mean difference +0.06 ms (p = 0.11); mutual information -0.006 bit per answer (p = 0.85) | inconclusive: one half of the held-out test decoded better than chance and the other didn't; the secondary measures show nothing |
<!-- ANCHOR_END: load-and-clients -->

Protocol 4 does not cover stacked checks across one release, flooding, or forcing checker and event loop onto one core.

<details><summary>Missing captures and the pre-run server fix</summary>

No packet captures were taken: they required `sudo` on the laptop. This deviated from the protocols, leaving only the primary and secondary analyses above.

Before collecting data, a Pi dry run showed `load_bits` sending late. EZKL's Python proving call blocked the server event loop for about half a second. The server now proves each distinct question once. Neither recorded run had late sends.

</details>

### Three clients with six times the answers (4 Nov, protocol 6)

Does the 0.1 s timing code get through fixed release when three clients ask at once? Protocol 5 was inconclusive at 258 answers, so protocol 6 repeated it with new bits and six times the answers. Pre-registered in `docs/EXPERIMENT_PROTOCOL_3.md`: the freeze candidate image (`c22954ee...`, fixed release, 4 s, 5 ms spin), three clients, 512 rounds or 1,536 answers per run, then an honest control.

<!-- ANCHOR: clients-p6 -->
| Analysis | Held-out errors, two halves | Held-out p | Control p | Mean difference (p) | Verdict |
|---|---|---|---|---|---|
| Registered, all answers | 0.47 / 0.48 | 0.043 | 0.77 | +9.3 ms (0.25), set by one delayed round | inconclusive |
| Without the delayed round (exploratory, declared before analysis) | 0.47 / 0.49 | 0.042 | 0.77 | +0.029 ms (0.08) | inconclusive |
<!-- ANCHOR_END: clients-p6 -->

The reading was fixed in advance: inconclusive again means the question stays open. Both three-client tests landed between the rule's thresholds, which fits a very small trace or chance; this sample size doesn't separate them. Without the delayed round, the data allow a shift of at most 0.06 ms, at most 0.007 bit per answer under the Gaussian model, or about 19 bits an hour at three clients.

<details><summary>What disturbed the runs, and the captures</summary>

- During the timing run the laptop's network bridge to the Pi went away for about 7 seconds. The three replies of round 238 arrived 10.8 s after they were sent instead of about 4 s; every answer was still ok and the run counted under the rule. The exploratory row drops that round from both runs.
- The first honest run was cut off when the cable was unplugged. Afterwards the endpoint did not reconnect to the test server, most likely because its old connection was left half open with nothing to send; the Pi was restarted and the control ran about an hour after the timing run, on a fresh boot. All of this was recorded before any analysis.
- Mutual information with 4 bins: p = 0.03 with all answers, 0.056 without the delayed round; the control was clean (p = 0.34 and 0.41).
- Packets: every reply was one 38-byte packet with TTL 64 and the same TCP window, in the timing run and in the honest runs. The timing capture holds 1,143 of the run's 1,536 replies (the outage and a restart left gaps).

</details>

### Failure cap versus stopping (2 Nov, protocol 3)

How much information remains, and how many answers are lost? Each run matched `observer/cap_model.py` reply for reply. Stopping leaked least but gave the server an off switch. Caps kept some answers flowing; the availability cost appeared only when the attacker caused failures.

Pre-registered in `docs/EXPERIMENT_PROTOCOL_2.md`. Runs used stock OS, Rust CI binary `f8b56ec` (`6f7f8702...`), fixed release 4 s, 5 ms spin and one client. Each run had 128 answers, with 32 planted random bits encoded by failing one chosen answer per 16.

<!-- ANCHOR: cap-vs-halt -->
| Failure policy | Planted bits read back (of 32) | Answers ok (of 128) | At most, for any failure code (`observer/cap_bound.py`) |
|---|---|---|---|
| No cap | 32 (no errors) | 120 | 128 bits (one per answer) |
| Cap: a 2nd failure within 64 replies starts 64 unavailable | 8 | 54 | 19.48 bits |
| Cap: a 3rd failure within 64 replies starts 32 unavailable | 12 | 62 | 34.99 bits |
| Stop after the first failure | none (the first answer failed; every later reply was `unavailable`) | 0 | the stopping position: at most log2(129) = 7.0 bits, once, until someone restarts it |
| Honest server, same cap as the second row | (no bits planted) | 128 | |
<!-- ANCHOR_END: cap-vs-halt -->

### Choosing the cap's settings (a model, 3 Nov)

What does each setting allow, and what does it cost an honest server? A tighter cap carries fewer bits but trips on honest faults too. `observer/cap_curves.py` computes both exactly from the cap's reference model, over 4,096 replies from an empty cap. The bound is `observer/cap_bound.py`'s, for any code that uses which replies fail. The cost assumes an honest server whose answers fail independently, at a fault rate of p.

<!-- ANCHOR: cap-settings -->
| W | F | C | bits per reply, at most | honest replies lost, p = 0.001 | honest replies lost, p = 0.01 |
|---|---|---|---|---|---|
| 16 | 1 | 16 | 0.290 | 0.02 % | 1.92 % |
| 32 | 1 | 32 | 0.186 | 0.09 % | 6.29 % |
| 64 | 1 | 32 | 0.182 | 0.18 % | 9.20 % |
| 64 | 1 | 64 | 0.115 | 0.36 % | 16.79 % |
| 64 | 1 | 128 | 0.078 | 0.71 % | 28.59 % |
| 64 | 2 | 32 | 0.236 | 0.01 % | 2.73 % |
| 64 | 2 | 64 | 0.156 | 0.01 % | 5.30 % |
| 128 | 1 | 128 | 0.070 | 1.31 % | 34.38 % |
<!-- ANCHOR_END: cap-settings -->

The device's setting is window 64, 1 failure, cooldown 64. At a fault rate of one answer in a thousand it loses under half a percent of honest replies; at one in a hundred, about a sixth. Allowing 2 failures with a shorter cooldown loses far fewer honest replies, for about twice the bound. Faults in a real deployment are rarely independent, so this is a guide for choosing, not a prediction. The honest server on the Pi lost no answers under the cap (protocol 3, above).

### From a per-reply bound to time (a model, 3 Nov)

How long would a key take at the bound? The table gives the fewest replies after which the failure pattern could carry 256 or 2,048 bits, counted exactly from an empty cap with `observer/cap_bound.py`'s model. Real codes carry less and need room for errors, so these are lower limits on the time an attacker needs, not estimates.

<!-- ANCHOR: key-time -->
| Failure policy | Replies before 256 bits could get out | 2,048 bits | 256 bits at 900 replies an hour (one client, 4 s) | 256 bits at 1,000 replies a second |
|---|---|---|---|---|
| No cap | 256 | 2,048 | 17 minutes | under a second |
| Window 64, 1 failure, cooldown 64 (the device's) | 2,200 | 17,879 | 2.4 hours | 2.2 seconds |
| Window 64, 2 failures, cooldown 32 | 1,071 | 8,707 | 1.2 hours | 1.1 seconds |
| Window 128, 1 failure, cooldown 128 | 3,645 | 29,750 | 4.0 hours | 3.6 seconds |
<!-- ANCHOR_END: key-time -->

The cap limits the rate per reply, not the total. At a busy deployment's traffic, a key's worth of bits fits in seconds at the bound, and several endpoints each with their own cap add up. A real budget has to count over time: a limit on failures per hour or per day, or accounting like Petrie, Muhlhauser and Drotos (2026). This is a model of the counted bound only; timing and logs are separate channels.

## What these results don't show

- Generality across devices, networks or loads. Most tests use one sequential client; ordering uses concurrent requests. Protocols 4 and 5 each add one load or several-client run. Packet sizes and TCP behaviour remain unmeasured.
- Repeated-run reliability for leakage cells. The core matrix has one 16-bit run per cell, followed by the 128-bit residual tests and 512-bit spin repeat.
- Leakage under other release budgets. We chose 4 s by hand and measured honest use of it, not the leakage trade-off.
- A limit on a cleverer encoder's achieved leakage. The failure-pattern counts above cover only their specified observation and policy.
