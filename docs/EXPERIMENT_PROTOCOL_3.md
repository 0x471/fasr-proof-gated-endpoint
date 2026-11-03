# Experiment protocol 6: several clients again, with enough answers to decide (written 3 Nov, before any run)

Protocol 5 (`docs/EXPERIMENT_PROTOCOL_2.md`) ran three clients for 258 answers and came out inconclusive under its rule: the signal run's held-out p was between 0.01 and 0.05 while its control was clean. This repeats it with six times the answers and new bits. It is a new test, not a re-analysis: protocol 5's data is not pooled with this one.

**Question.** With three clients under fixed release, does the server's per-answer delay show in when answers leave?

**Setup.**
- The image frozen for the agent red team (v1.1; its sha256 goes in every manifest), fixed release, 4 s, 5 ms spin, default CPU speed policy. `device/image_scenario.sh` with `CLIENTS=3` (default `GAP_MS=2`): 512 rounds, one request per client per round, 1,536 answers.
- Server `--mode timing_bits --slot 0.1`, as in protocol 5. The bits follow the order requests are admitted (client 0, 1, 2 of round 0, then round 1, ...).
- Bits: 1,536 from `random.Random(20261117)`, each `rng.choice('01')`.
- Control: an honest run with the same clients and rounds, analysed with the same labels.
- Both runs are captured on the laptop's interface (`tcpdump -w`, port 8700), started before and stopped after each run.
- A run counts only if its manifest says `"status": "ok"`, every answer is ok and the server reports no late sends; otherwise it is repeated in full. Laptop idle, both VMs stopped.

**Primary analysis**: reorder each trace with `observer/by_admission.py --clients 3`, then the held-out threshold decoder (`observer/jitter_test.py --heldout 2000`) with the control. Decision rule as in protocol 1: shown if the signal run has p < 0.01 and the control p > 0.05; not detected if the signal run has p > 0.05 (reported as "not detected by this decoder at n = 1,536"); anything else inconclusive.

**How the outcome will be read** (fixed now): not detected means protocol 5's borderline result was not confirmed at six times the answers; shown means fixed release with a 5 ms spin leaks under three clients and the release loop needs work for several clients; inconclusive again means the question stays open and is reported that way.

**Secondary** (reported, never used for the decision):
- mean difference with its permutation p (`--perms 20000`); mutual information with 4 bins (`observer/estimate.py`);
- `observer/shift_bound.py` on the reordered trace, with `--per-hour 2700`;
- packet level: `observer/pcap_trace.py` on both captures. Expected: every reply in one packet of one size, and the same TCP flags, TTL and window values in the signal run as in the control. Any difference is reported as a finding.
- the held-out decoder on the capture times (`--trace`), which leave out the observer program's own scheduling.

## Commands
```sh
# In a second terminal before each run (sudo), stopped with Ctrl-C after it:
#   mkdir -p runs/p6; IF=$(route get 192.168.2.2 | awk '/interface/{print $2}'); sudo tcpdump -i $IF -w runs/p6/NAME.pcap tcp port 8700
B6=$(python3 -c "import random; r=random.Random(20261117); print(''.join(r.choice('01') for _ in range(1536)))")
unset PERIOD_MS; export OUT=runs/p6 IMAGE_SHA=<sha256 of the flashed image> CLIENTS=3
LABEL=clients3 device/image_scenario.sh timing_c3 512 -- --mode timing_bits --bits $B6 --slot 0.1
LABEL=clients3 device/image_scenario.sh honest_c3 512 -- --mode honest
for r in timing_c3 honest_c3; do python3 -c "import json,sys; sys.exit(any(not json.loads(l)['answer']['ok'] for l in open('runs/p6/$r.trace.jsonl')))" || echo "$r has unavailable answers: repeat it"; done
python3 observer/by_admission.py runs/p6/timing_c3.trace.jsonl --clients 3 > runs/p6/timing_c3.ordered.jsonl
python3 observer/by_admission.py runs/p6/honest_c3.trace.jsonl --clients 3 > runs/p6/honest_c3.ordered.jsonl
python3 observer/jitter_test.py runs/p6/timing_c3.ordered.jsonl $B6 --control runs/p6/honest_c3.ordered.jsonl --perms 20000 --heldout 2000
python3 observer/estimate.py runs/p6/timing_c3.ordered.jsonl $B6 --bins 4 --control runs/p6/honest_c3.ordered.jsonl
python3 observer/shift_bound.py runs/p6/timing_c3.ordered.jsonl $B6 --per-hour 2700
for r in timing_c3 honest_c3; do python3 observer/pcap_trace.py runs/p6/$r.pcap --trace runs/p6/$r.pcap.jsonl > runs/p6/$r.pcap.summary.json; done
```
Each run takes about 35-40 minutes (512 rounds at 4 s, three answers per round).
