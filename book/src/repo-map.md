# Repository map

Start with the directory table. Expand a section to find a specific implementation or experiment.

| Directory | Purpose |
|---|---|
| `endpoint/` | Rust software running on the device |
| `pge/` | Python reference, compared reply for reply |
| `prover/`, `observer/` | Simulated server, outside client and leakage analysis |
| `device/`, `image/` | Pi experiments and the stripped system image |
| `tests/` | Automated checks and pinned models |
| `docs/`, `book/` | Specifications, evidence and this explanation |
| `.github/workflows/`, `spike/` | CI and side experiments |

<details><summary>Device software: Rust</summary>

| Path | Purpose |
|---|---|
| `endpoint/wire` | Strict parse/re-encode comparison; no unsafe code. Two bounded Kani proofs cover frame-length checking and any 12-byte input for the smallest shape. Larger inputs did not finish. |
| `endpoint/core` | Deterministic release, halt and cap state machine; caller supplies time and events. |
| `endpoint/verify` | EZKL-compatible input encoding; pinned bundle re-hashed per check. |
| `endpoint/update` | Signed key lists, manifests and forward-only state. `pge-sign` signs off-device. |
| `endpoint/endpoint` | One poll loop owns sockets, timers and logs; fresh limited, syscall-filtered child per proof. |
| `endpoint/fuzz` | cargo-fuzz targets for messages, checker input, update files and forward-only state. `seeds.py` supplies seeds. |
| `endpoint/sources.toml`, `endpoint/prepare.sh` | Commit-pinned upstream sources, checked out before each build. |

</details>

<details><summary>Python reference</summary>

| Path in `pge/` | Purpose |
|---|---|
| `service.py` | One model, at most one reply per question; arrival default, immediate v0 or fixed release; proven output/fixed errors and fixed-word logs. |
| `protocol.py` | Strict fixed-size binary messages for the model. |
| `binding.py` | Encode inputs as EZKL does, validate output values, decode proven outputs. |
| `bundle.py` | Load model files only when hashes match. |
| `domain.py` | Refuse questions outside the model's input range. |
| `verdict.py` | ACCEPT, REJECT or ERROR classification. |
| `cli.py` | Limited proof checks through EZKL's official CLI. |
| `proc.py` | Program deadline, output cap and resource limits. |
| `worker.py` | One proof check in a separate process with a deadline. |

</details>

<details><summary>Specifications and records</summary>

| Path in `docs/` | Purpose |
|---|---|
| `THREAT_MODEL.md` | Assets, attackers, boundaries, assumptions, attack surface, channel status and MITRE ATLAS mapping. |
| `ATTACKS.md` | Every catalogued scenario, result and evidence. |
| `SERVICE_SPEC.md` | Exact service behaviour. |
| `BINDING_SPEC.md` | Request binding, pitfalls and test vectors. |
| `UPDATE_SPEC.md` | Signers, formats, rollback and replay rules. |
| `ATTACK_SURFACE.md` | Access by version, including build machines. |
| `EXPERIMENT_PROTOCOL.md` | Spin-repeat protocol, written before data. |
| `EXPERIMENT_PROTOCOL_2.md` | Pre-registered protocols 2-5: timing cause, cap/halt, load, clients and packet captures. |
| `results/` | Complete registered-experiment analysis. |

</details>

<details><summary>Tests, server and observer</summary>

| Path | Purpose |
|---|---|
| `tests/` | Unit, EZKL encoding, end-to-end, parser-fuzz, service and leakage tests. `test_docs.py` checks copied facts for drift. |
| `tests/fixtures/` | Pinned `tiny`: 4 inputs, 3 outputs, range in `domain.json`; `multi`: two inputs and two outputs. |
| `prover/server.py` | Honest or misbehaving server, including timing, order and failure encoders. |
| `observer/client.py` | Sequential, batched, multi-connection or paced questions; reply/time records and decoding. |
| `observer/by_admission.py` | Order multi-client traces by admission. |
| `observer/pcap_trace.py` | Extract outside packet details and reply times. |
| `observer/cap_model.py`, `observer/cap_bound.py`, `observer/cap_check.py` | Cap reference, failure-pattern bound and reply-by-reply comparison. |
| `observer/sleep_vs_fixed.py` | Compare random-sleep and fixed-release models. |
| `observer/analyze_matrix.py` | Summarise release-rule experiments. |
| `observer/jitter_test.py` | Test whether remaining timing follows planted bits. |
| `observer/estimate.py` | Mutual information in bits per answer, null and interval; synthetic `--selftest`. |
| `observer/order_experiment.py` | Local ordering experiment. |

</details>

<details><summary>Pi scripts, images and supporting files</summary>

| Path | Purpose |
|---|---|
| `device/verify_on_pi.sh`, `device/check_verifier.sh` | Copy pinned model; time real-tool acceptance and rejection checks. |
| `device/pi_scenario.sh` | Stock-system experiment: Python or Rust on Pi; server and observer on laptop. |
| `device/image_scenario.sh` | Run against the already-started, login-free image endpoint; record manifest. |
| `device/tcp_scan.py` | Scan every TCP port: open, refused or dropped. |
| `device/rust_verify_cost.py`, `device/endpoint_latency.py` | Rust checker cost and endpoint overhead. |
| `device/pi_matrix.sh` | Every release rule against each signalling method. |
| `device/verify_cost.py` | Verification cost and memory-cap reliability. |
| `device/measure.sh` | Packages, services, processes, open ports and file hashes. |
| `image/` | Buildroot `build.sh`, fragments, firewall/start-up overlay; signed `make_update.sh`; file inventory via `manifest.sh`. |
| `.github/workflows/` | Python, native/static-aarch64 Rust, book, spikes and on-demand independent image build. |
| `book/` | mdBook, including reference files from `docs/`. |
| `book/diagrams/`, `book/render-diagrams.sh` | Mermaid sources rendered to committed SVGs in `book/src/diagrams/`; mdBook has no Mermaid support. |
| `spike/rust-verifier/` | Small Rust EZKL checker experiment. |
| `spike/stwo-verifier/` | Pinned S-two (StarkWare) checker experiment. |

</details>
