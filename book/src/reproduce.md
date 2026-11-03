# Reproduce the results

Run commands from the repository root. The Python commands below reproduce the reference endpoint; the device now runs Rust.

## Tests

```sh
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python "ezkl==23.0.5" onnx numpy pytest
.venv/bin/python -m pytest -q
```

Verification needs the pinned setup file, or [SRS](glossary.md). Tests use `prover/artifacts/kzg.srs` or `$PGE_SRS`; otherwise EZKL downloads it and checks its hash. macOS skips Linux-only memory-limit and device-script tests. CI runs Linux with the real EZKL CLI.

## Run the endpoint yourself

Start the server, then the Python endpoint. It uses EZKL CLI 23.0.5 and is tested on Linux. macOS cannot enforce its memory cap.

```sh
.venv/bin/python prover/server.py --listen 127.0.0.1:8701
python3 -I -c 'import sys; sys.path.insert(0, "."); from pge.service import main; main()' \
  --listen OUTSIDE_IP:8700 --server 127.0.0.1:8701 --bundle BUNDLE_DIR --pins device/tiny.sha256 \
  --cli ./ezkl --domain tests/fixtures/tiny/domain.json --proof-bytes 3072 \
  [--release arrival|immediate|fixed] [--deadline SECONDS] [--spin-ms MS] [--log endpoint.log]
```

Use the outside interface's own address for `OUTSIDE_IP`; `0.0.0.0` would listen everywhere. `BUNDLE_DIR` contains `settings.json`, `vk.key` and `kzg.srs`. Send questions with `observer/client.py`.

## The ordering channel on one machine

```sh
.venv/bin/python observer/order_experiment.py
```

This uses real EZKL proving on localhost: `order_bits`, k = 2, 3, 4 concurrent questions, immediate and arrival release. It prints one JSON line per setting.

## On a Raspberry Pi

<details><summary>Stock-system setup and commands</summary>

| Requirement | Lab setting; change for your setup |
|---|---|
| SSH | `ssh p01` |
| Repository | `~/p01-v1` on the Pi |
| Bundle | `~/p01-v1/bundle`: settings, verification key and SRS matching `device/tiny.sha256` |
| EZKL | aarch64 CLI 23.0.5 at `~/p01-v0/ezkl` |
| Addresses | Laptop `192.168.2.1`, Pi `192.168.2.2` |

```sh
./device/verify_on_pi.sh                     # device checks: accept and reject cases, 20 timed verifies
ssh p01 'cd ~/p01-v1 && python3 -I device/verify_cost.py --cli ~/p01-v0/ezkl --srs ~/p01-v0/kzg.srs --runs 20 --sweep 20'
OUT=runs/matrix device/pi_matrix.sh          # release policies x channels, 4 s budget
python3 observer/analyze_matrix.py runs/matrix
```

`device/pi_scenario.sh NAME RELEASE N BATCH -- SERVER_ARGS` starts server and endpoint, sends questions and writes traces and both logs to `OUT/NAME.*`.

| Setting | Meaning |
|---|---|
| `N`, `BATCH` | Request count and batch size |
| `CLIENTS` | One question per connection per round |
| `DEADLINE` | Check deadline; also release time under fixed release |
| `SPIN_MS` | Busy-wait before release |

The runner refuses dirty checkouts, different Pi endpoint code, or mismatched Pi pins/domain files.

</details>

<details><summary>Residual timing and trace checks</summary>

Use 128 random bits and an honest control. Add `SPIN_MS=5` to both scenario commands for spin.

```sh
B=$(python3 -c "import random; r=random.Random(20261019); print(''.join(r.choice('01') for _ in range(128)))")
OUT=runs/fixed_long DEADLINE=4 device/pi_scenario.sh timing_fixed_long fixed 128 1 -- --mode timing_bits --bits $B --slot 1.0
OUT=runs/fixed_long DEADLINE=4 device/pi_scenario.sh honest_fixed_long fixed 128 1 -- --mode honest
python3 observer/jitter_test.py runs/fixed_long/timing_fixed_long.trace.jsonl $B --control runs/fixed_long/honest_fixed_long.trace.jsonl --heldout 2000
python3 observer/estimate.py runs/fixed_long/timing_fixed_long.trace.jsonl $B --control runs/fixed_long/honest_fixed_long.trace.jsonl
python3 observer/estimate.py --selftest      # the estimator on synthetic channels with known values
```

Each scenario writes `OUT/NAME.manifest.json`, recording:

- Commit captured before the run and settings.
- Pi hashes: endpoint code, bundle, pins, domain, EZKL CLI and Python.
- Server arguments, exit status, row count and whether endpoint logs were copied.

Observer failure, missing rows or uncopied logs cause a non-zero exit. Analyses refuse traces that do not match bits one for one. The registered repeat's exact commands remain in `docs/EXPERIMENT_PROTOCOL.md`.

</details>

## On the v1 image

There is no login. Build and flash the image; its endpoint starts at boot. Run `device/image_scenario.sh NAME N -- SERVER_ARGS` from the laptop.

| Tool or setting | Purpose |
|---|---|
| `IMAGE_SHA` | Identifies the flashed image |
| `PERIOD_MS`, `CLIENTS` | Pace questions; use multiple connections |
| `image/build.sh` | Build on Linux |
| `image/make_update.sh` | Create the signed update |
| `image/manifest.sh` | Inventory every image file |
| `image` CI workflow | Independent clean-runner build for comparison |

Image experiments and commands are pre-registered in `docs/EXPERIMENT_PROTOCOL_2.md`.

## Server modes

`prover/server.py --mode` supports `honest`, `drop`, `delay`, `tamper_output`, `replay`, `duplicate`, `wrong_seq`, `oversize`, `garbage` and `flood`. Flood repeats each answer `--batch` times.

Leakage modes are `timing_bits`, `order_bits`, `fail_position` and `load_bits`, using `--bits`, `--slot` and `--batch`. Load also takes `--period`, `--deadline`, `--lead` and `--shift`. See the server's docstring.
