# Experiment protocol 7: does giving the release loop its own CPU remove the timing residue? (written 3 Nov, before any run)

Without spin, fixed release left a small residue: bit-1 answers left slightly earlier than bit-0 answers (Measurements). The leading explanation is the state of the processor when a release is due: after a late answer, the endpoint has just started a proof check, so the CPU that releases is awake and warm; after an early one it has idled for seconds. Protocol 2 tests one form of that (the speed policy). This tests the design route: run the release loop on a CPU that never runs proof checks.

The four CPUs of the Pi 4 share one clock, so this separates two kinds of cause. Effects that belong to one CPU (how deeply it sleeps, what its caches hold) go away when the checks run elsewhere; effects shared by all CPUs (clock speed, memory traffic) don't. The release loop still reads each answer and starts its check itself, so that part of the work stays on its CPU in both conditions.

**Question.** With spin 0 under fixed release, is the residue gone when the event loop has a CPU of its own and every proof check runs on the other three?

**Setup.**
- The experiment image: the 3 Nov evening v1.1 build with the endpoint built from this commit (it has `--release-cpu`) and a signed update whose policy is fixed release, 4 s, **spin 0** (the policy of protocol 2's image). Its sha256 goes into each manifest and into a dated note below before the first run.
- Two conditions, one boot each, set on the boot partition's `cmdline.txt` (edited on the laptop between runs, everything else unchanged):
  - **shared**: the command line as built;
  - **isolated**: the same line plus ` isolcpus=3 pge.release_cpu=3`. The kernel then keeps CPU 3 free of other tasks; the endpoint moves its event loop onto CPU 3 and every helper thread and proof check onto CPUs 0-2. The endpoint refuses to start if it can't (so an answering endpoint means the placement was applied); a check that couldn't move counts as a failed answer.
  Run shared first, then isolated; power-cycle between them.
- Per condition: a timing run (`--mode timing_bits --slot 1.0`, N = 256) then an honest run (N = 256, analysed with the same labels), through `device/image_scenario.sh` with `LABEL` set to the condition. One client. Laptop idle, both VMs stopped.
- Bits: 256 from `random.Random(20261118)`, each `rng.choice('01')`.
- Both runs of each condition are captured on the laptop's interface (`tcpdump -w`, port 8700), as in protocol 6.
- A run counts only if its manifest says `"status": "ok"`, every answer is ok and the server reports no late sends; otherwise it is repeated in full, never patched.

**Primary analysis**, per condition: the held-out threshold decoder (`observer/jitter_test.py --heldout 2000`) on the timing run with the honest run as `--control`. Decision rule as in protocol 1: residue shown if the timing run has p < 0.01 and the control p > 0.05; not detected if the timing run has p > 0.05; otherwise inconclusive.

**How the outcome will be read** (fixed now):
- Shown under shared, not detected under isolated: keeping proof checks off the releasing CPU removes this residue at n = 256; a per-CPU cause is supported, and a release stage on its own CPU is a working design step (not a bound).
- Shown under both: separating the CPUs isn't enough; a shared cause (clock speed, memory) or the loop's own work on each answer remains.
- Not detected under shared: this image shows no residue at spin 0 and n = 256, so the isolated condition can't show an improvement; it is reported, and the question stays open.
- Anything else is reported as it is, without an explanation.

**Secondary** (reported, never used for the decision): mean difference with its permutation p (`--perms 20000`); mutual information with 4 bins (`observer/estimate.py`); `observer/shift_bound.py` with `--per-hour 900`; `observer/pcap_trace.py` on each capture (packet sizes, flags, TTL and window values; capture-time decoder with `--trace`).

**Limits fixed now.** One device, one boot per condition, one client; the endpoint can't show from outside that the kernel kept CPU 3 free of other tasks, only that its own placement was applied. Protocol 2 and this protocol use the same image family but are analysed separately and never pooled.

## Commands
```sh
# Edit cmdline.txt on the card's boot partition between conditions (isolated: append " isolcpus=3 pge.release_cpu=3").
# In a second terminal before each run (sudo), stopped with Ctrl-C after it:
#   mkdir -p runs/p7; IF=$(route get 192.168.2.2 | awk '/interface/{print $2}'); sudo tcpdump -i $IF -w runs/p7/NAME.pcap tcp port 8700
B7=$(python3 -c "import random; r=random.Random(20261118); print(''.join(r.choice('01') for _ in range(256)))")
unset PERIOD_MS CLIENTS; export OUT=runs/p7 IMAGE_SHA=<sha256 of the flashed image>
for C in shared isolated; do   # one condition per boot
  LABEL=$C device/image_scenario.sh timing_$C 256 -- --mode timing_bits --bits $B7 --slot 1.0
  LABEL=$C device/image_scenario.sh honest_$C 256 -- --mode honest
  python3 observer/jitter_test.py runs/p7/timing_$C.trace.jsonl $B7 --control runs/p7/honest_$C.trace.jsonl --perms 20000 --heldout 2000
  python3 observer/estimate.py runs/p7/timing_$C.trace.jsonl $B7 --bins 4 --control runs/p7/honest_$C.trace.jsonl
  python3 observer/shift_bound.py runs/p7/timing_$C.trace.jsonl $B7 --per-hour 900
  for r in timing_$C honest_$C; do python3 observer/pcap_trace.py runs/p7/$r.pcap --trace runs/p7/$r.pcap.jsonl > runs/p7/$r.pcap.summary.json; done
done
```
Each run takes about 17-20 minutes (256 answers at 4 s).

## Notes before the first run
