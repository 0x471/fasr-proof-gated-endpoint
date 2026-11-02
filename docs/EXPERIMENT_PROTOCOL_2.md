# Experiment protocols 2-5: the timing residue's cause, the failure-cap trade-off, load, and several clients

Written before collecting the data (2 Nov 2026). Any analysis not listed here is exploratory and is reported as such. Protocol 1 is `EXPERIMENT_PROTOCOL.md`.

## Protocol 2: does the residual timing trace depend on the processor's speed policy?

**Question.** Without spin, the stock system showed a residue under fixed release (bit-1 answers left slightly earlier than bit-0 answers); the stripped image, with spin, showed none in one run. Two explanations are open: how long the processor takes to wake from idle, and its speed changing with load (after a late proof the processor has just been busy and runs fast; after an early one it has idled for seconds). The image's kernel defaults to the `powersave` policy (lowest speed, no scaling) and has no deep idle states (no PSCI idle driver), while the stock system scales speed with load. With spin off, does a residue appear on the image, and under which speed policy?

**Setup.**
- The v1 image from the 2 Nov rebuild, with a signed update whose policy is fixed release, 4 s, **spin 0** (`image/make_update.sh` with `POLICY` changed only in `spin-ms`). Its sha256 goes into each manifest.
- Three conditions, one boot each, set on the boot partition's `cmdline.txt` (edited on the laptop between runs): `cpufreq.default_governor=powersave` (the image default, written explicitly), `ondemand`, `performance`. Run in that order.
- Per condition: a timing run (`--mode timing_bits --slot 1.0`, N = 256) then an honest run (N = 256, analysed with the same labels), via `device/image_scenario.sh` with `LABEL` set to the policy. Laptop idle during runs.
- Bits: 256, `random.Random(20261102)`, each `rng.choice('01')`.
- A run counts only if its manifest says `"status": "ok"`; a failed run is repeated in full, never patched.

**Primary analysis**, per condition: the held-out threshold decoder (`observer/jitter_test.py --heldout 2000`), as in protocol 1. Decision rule as in protocol 1: residue shown if the signal run has p < 0.01 and the honest run p > 0.05; not detected if the signal run has p > 0.05; otherwise inconclusive.

**How the outcome will be read** (fixed now):
- Residue under `ondemand` only: supports the speed-change explanation.
- Residue under all three: speed policy isn't the cause; idle wake-up or something else is.
- Residue under none: no residue on this image without spin at n = 256; the image-versus-stock difference stays unexplained.
- Anything else is reported as it is, without an explanation.

**Secondary** (reported, not decisive): mean difference with its permutation p (`--perms 20000`), and mutual information with 4 bins (`observer/estimate.py`).

## Protocol 3: what does the failure cap cost, and how does it compare with halting?

**Question.** For the failure-position code (one chosen failure per 16 answers), how many planted bits get out and how many answers stay available, with no cap, two cap settings, and a halt at the first failure (Yogi's "block" option)? Do the replies match the reference model exactly?

**Setup.**
- The stock-system card with the Rust endpoint, through `device/pi_scenario.sh` (`ENDPOINT=rust`, `BIN` = the CI musl build of `f8b56ec`, sha256 `6f7f8702...671c`, the same binary as in the 2 Nov images; its hash goes into the manifest), fixed release, `DEADLINE=4 SPIN_MS=5`, one client, N = 128.
- Bits: 32, `random.Random(20261106)`.
- Runs, in this order: `fp_nocap`; `fp_cap_64_1_64` (`CAP="64 1 64"`); `fp_cap_64_2_32` (`CAP="64 2 32"`); `fp_halt1` (`HALT=1`); `honest_cap_64_1_64` (honest server, same cap, no failures expected).
- A run counts only if its manifest says `"status": "ok"`.

**Primary analysis.** For each run, `observer/cap_check.py` with the run's policy: whether every reply matches the model, the decoded bits and bit errors, and the number of ok answers. Required: an exact model match for every capped and halted run; the honest run must have every answer ok. No significance test; these are counts.

**Reported alongside:** the counted upper bound for the same cap and N (`observer/cap_bound.py`), so the measured bits can be read against what any failure-pattern code could carry.

## Protocol 4: does a proof check running at a release move that release? (K34, written 2 Nov)

**Question.** Under fixed release the server can't choose when an answer leaves, but it can choose when the endpoint's checker is busy, by timing the answers it sends. Checks run one at a time in a child process, beside the event loop that releases replies. Does a check that overlaps a release shift that release enough for an observer to read?

**Setup.**
- The hardened image (`aa2896...53bd`, its own policy: fixed release, 4 s, 5 ms spin), the default CPU speed policy (no `cmdline.txt` change), `device/image_scenario.sh` with `PERIOD_MS=1000`: one connection, one request a second, not waiting for answers.
- Server `--mode load_bits --period 1.0 --deadline 4.0 --lead 0.05 --shift 0.5`: exactly one answer per second either way; for bit k = 1 the answer to request k+1 is sent `--lead` before request k's release, so its check (the Rust checker's time per check is on the Measurements page, several times `--lead`) overlaps that release; for a 0 it is sent `--lead` + `--shift` before, so the check ends well before that release and starts well after the previous one.
- Bits: 255 from `random.Random(20261109)`, each `rng.choice('01')`, then a final `0` (request 255 has no next answer to carry a bit). N = 256.
- Control: the same server with 256 zeros (the same load every second, never at a release), analysed with the same labels.
- A run counts only if its manifest says `"status": "ok"` (every answer ok, no late send by the server).

**Primary analysis**: the held-out threshold decoder (`observer/jitter_test.py --heldout 2000`) on the load run with the control as `--control`; decision rule as in protocol 1 (shown if the load run has p < 0.01 and the control p > 0.05; not detected if the load run has p > 0.05; otherwise inconclusive).

**How the outcome will be read** (fixed now): shown means a server can move releases through load alone, and the bound for fixed release has to include it; not detected means one overlapping check per release isn't enough on this image at n = 256, not that load is harmless (several overlapping checks, flooding the loop with stale answers, and several clients are untested).

**Secondary**: mean difference with its permutation p (`--perms 20000`); mutual information with 4 bins (`observer/estimate.py`).

## Protocol 5: does the timing code get through fixed release with several clients? (written 2 Nov)

**Question.** Every fixed-release result so far used one client at a time. With several clients, releases fall a few milliseconds apart and the endpoint spins for at most one of them per loop pass, and the server's delays decide when each check runs relative to the other clients' releases. Does the server's per-answer delay still show in when answers leave?

**Setup.**
- The hardened image (`aa2896...53bd`, fixed release, 4 s, 5 ms spin), default CPU speed policy, `device/image_scenario.sh` with `CLIENTS=3` (default `GAP_MS=2`): 86 rounds, one request per client per round, 258 answers.
- Server `--mode timing_bits --slot 0.1`: a 1 delays that answer by a tenth of a second. The laptop proves one answer at a time, so with three clients the third answer of a round already comes late in the budget (the 29 Oct three-client run, Measurements); a small slot keeps every answer inside the 4 s budget (revised from a quarter second on 2 Nov, before any run). The bits follow the order requests are admitted (client 0, 1, 2 of round 0, then round 1, ...), which is also the order the server answers them.
- Bits: 258 from `random.Random(20261110)`, each `rng.choice('01')`.
- Control: an honest run with the same clients and rounds, analysed with the same labels.
- A run counts only if its manifest says `"status": "ok"` **and every answer is ok**: an `unavailable` answer means a proof missed the deadline, which is the failure channel, not timing; such a run is repeated in full.

**Primary analysis**: reorder each trace with `observer/by_admission.py --clients 3`, then the held-out threshold decoder (`observer/jitter_test.py --heldout 2000`) with the control; decision rule as in protocol 1.

**How the outcome will be read** (fixed now): not detected means three clients don't open a timing channel that one client didn't at n = 258; shown means the one-client result doesn't carry over, and the spin or the release loop needs work for several clients.

**Secondary**: mean difference with its permutation p (`--perms 20000`); mutual information with 4 bins (`observer/estimate.py`).

## Packet captures (protocols 2, 4 and 5; added 2 Nov, before any run)

Each run in protocols 2, 4 and 5 is also captured on the laptop's interface to the Pi (`tcpdump -w`, port 8700 only, started before the run and stopped after it). Two secondary analyses, reported next to the primary one and never replacing it:
- **Packet level**: `observer/pcap_trace.py` summarises what the endpoint's packets looked like. Expected: every reply complete in one packet of one fixed size, and the same TCP flags and TTL in the signal run as in its control. Any difference between signal and control is reported as a finding, whatever the primary result.
- **Capture times**: the same held-out decoder and decision rule on the capture's times (`--trace`), which leave out the observer program's scheduling. A residue that shows only here is reported as such.

## Commands
```sh
# In a second terminal before each run (sudo), stopped with Ctrl-C after it:
#   mkdir -p runs/pN; IF=$(route get 192.168.2.2 | awk '/interface/{print $2}'); sudo tcpdump -i $IF -w runs/pN/NAME.pcap tcp port 8700
# then: python3 observer/pcap_trace.py runs/pN/NAME.pcap --trace runs/pN/NAME.pcap.jsonl
B2=$(python3 -c "import random; r=random.Random(20261102); print(''.join(r.choice('01') for _ in range(256)))")
# per condition, after booting with cmdline.txt set to that policy:
export OUT=runs/p2 IMAGE_SHA=<sha256 of the flashed image>
LABEL=powersave device/image_scenario.sh timing_ps 256 -- --mode timing_bits --bits $B2 --slot 1.0
LABEL=powersave device/image_scenario.sh honest_ps 256 -- --mode honest
python3 observer/jitter_test.py runs/p2/timing_ps.trace.jsonl $B2 --control runs/p2/honest_ps.trace.jsonl --perms 20000 --heldout 2000
python3 observer/estimate.py runs/p2/timing_ps.trace.jsonl $B2 --bins 4 --control runs/p2/honest_ps.trace.jsonl

B3=$(python3 -c "import random; r=random.Random(20261106); print(''.join(r.choice('01') for _ in range(32)))")
export OUT=runs/p3 ENDPOINT=rust DEADLINE=4 SPIN_MS=5 BIN=<path to the f8b56ec CI binary>
device/pi_scenario.sh fp_nocap fixed 128 1 -- --mode fail_position --batch 16 --bits $B3
CAP="64 1 64" device/pi_scenario.sh fp_cap_64_1_64 fixed 128 1 -- --mode fail_position --batch 16 --bits $B3
CAP="64 2 32" device/pi_scenario.sh fp_cap_64_2_32 fixed 128 1 -- --mode fail_position --batch 16 --bits $B3
HALT=1 device/pi_scenario.sh fp_halt1 fixed 128 1 -- --mode fail_position --batch 16 --bits $B3
CAP="64 1 64" device/pi_scenario.sh honest_cap_64_1_64 fixed 128 1 -- --mode honest
python3 observer/cap_check.py runs/p3/fp_cap_64_1_64.trace.jsonl $B3 --cap 64 1 64
python3 observer/cap_bound.py --window 64 --failures 1 --cooldown 64 --n 128

B4=$(python3 -c "import random; r=random.Random(20261109); print(''.join(r.choice('01') for _ in range(255)) + '0')")
Z4=$(python3 -c "print('0' * 256)")
export OUT=runs/p4 IMAGE_SHA=<sha256 of the flashed image> PERIOD_MS=1000
LABEL=load device/image_scenario.sh load_bits 256 -- --mode load_bits --bits $B4 --period 1.0 --deadline 4.0 --lead 0.05 --shift 0.5
LABEL=load device/image_scenario.sh load_zero 256 -- --mode load_bits --bits $Z4 --period 1.0 --deadline 4.0 --lead 0.05 --shift 0.5
python3 observer/jitter_test.py runs/p4/load_bits.trace.jsonl $B4 --control runs/p4/load_zero.trace.jsonl --perms 20000 --heldout 2000
python3 observer/estimate.py runs/p4/load_bits.trace.jsonl $B4 --bins 4 --control runs/p4/load_zero.trace.jsonl

B5=$(python3 -c "import random; r=random.Random(20261110); print(''.join(r.choice('01') for _ in range(258)))")
unset PERIOD_MS; export OUT=runs/p5 IMAGE_SHA=<sha256 of the flashed image> CLIENTS=3
LABEL=clients3 device/image_scenario.sh timing_c3 86 -- --mode timing_bits --bits $B5 --slot 0.1
LABEL=clients3 device/image_scenario.sh honest_c3 86 -- --mode honest
for r in timing_c3 honest_c3; do python3 -c "import json,sys; sys.exit(any(not json.loads(l)['answer']['ok'] for l in open('runs/p5/$r.trace.jsonl')))" || echo "$r has unavailable answers: repeat it"; done
python3 observer/by_admission.py runs/p5/timing_c3.trace.jsonl --clients 3 > runs/p5/timing_c3.ordered.jsonl
python3 observer/by_admission.py runs/p5/honest_c3.trace.jsonl --clients 3 > runs/p5/honest_c3.ordered.jsonl
python3 observer/jitter_test.py runs/p5/timing_c3.ordered.jsonl $B5 --control runs/p5/honest_c3.ordered.jsonl --perms 20000 --heldout 2000
python3 observer/estimate.py runs/p5/timing_c3.ordered.jsonl $B5 --bins 4 --control runs/p5/honest_c3.ordered.jsonl
```
Protocol 2 takes about 17 minutes per run (six runs); protocol 3 about 9 minutes per run (five runs); protocol 4 about 5 minutes per run (two runs); protocol 5 about 6 minutes per run (two runs).
