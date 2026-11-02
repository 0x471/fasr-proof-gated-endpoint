# Experiment protocols 2 and 3: the timing residue's cause, and the failure-cap trade-off

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

## Commands
```sh
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
```
Protocol 2 takes about 17 minutes per run (six runs); protocol 3 about 9 minutes per run (five runs).
