# Repository map

## The device's endpoint (`endpoint/`, Rust)

| Path | What it does |
|---|---|
| `endpoint/wire` | The message format: parse, then re-encode and compare, so every message has one accepted form; no unsafe code; two bounded Kani proofs (the frame length check, and any 12-byte input for the smallest model shape; larger inputs did not finish) |
| `endpoint/core` | The release rules, halt and failure cap as a deterministic state machine; the caller supplies time and events |
| `endpoint/verify` | Binding (encodes the question like EZKL) and the pinned bundle, re-hashed for every check |
| `endpoint/update` | Signed updates: the key list, the manifest, the forward-only state; `pge-sign` makes signatures off the device |
| `endpoint/endpoint` | The binary: one poll loop owning the sockets, timers and log; each proof checked in a fresh child process with resource limits and a system-call filter |
| `endpoint/fuzz` | cargo-fuzz targets: the message format, the checker's input, the update files and the forward-only rule (`seeds.py` writes their seed inputs) |
| `endpoint/sources.toml`, `endpoint/prepare.sh` | EZKL and other upstream sources pinned by commit, checked out before every build |

## The reference endpoint (`pge/`, Python)

| File | What it does |
|---|---|
| `pge/service.py` | The endpoint service: one approved model, at most one answer per question, three release rules (arrival order by default, immediate as in v0, fixed time); replies are the proven output or one fixed error; logs use fixed words only |
| `pge/protocol.py` | The message format: fixed-size binary messages for the approved model, parsed strictly |
| `pge/binding.py` | Encodes the question exactly as EZKL does, checks the server's output values, decodes proven outputs |
| `pge/bundle.py` | Loads the model's files only if each matches its pinned hash |
| `pge/domain.py` | The range of questions the test model can answer, so impossible ones are refused up front |
| `pge/verdict.py` | Turns a proof check into ACCEPT, REJECT or ERROR |
| `pge/cli.py` | Checks proofs with EZKL's official command-line tool, under resource limits |
| `pge/proc.py` | Runs a program with a deadline, an output cap and resource limits |
| `pge/worker.py` | Runs one check in a separate process with a deadline (Python version) |

## Documents (`docs/`)

| File | What it covers |
|---|---|
| `docs/THREAT_MODEL.md` | Assets, attackers, trust boundaries, assumptions, attack surface, side channels and their status, the MITRE ATLAS mapping |
| `docs/ATTACKS.md` | Every catalogued scenario, its result and its evidence |
| `docs/SERVICE_SPEC.md` | The endpoint service's exact behaviour |
| `docs/BINDING_SPEC.md` | The request-binding rules, pitfalls and test vectors |
| `docs/UPDATE_SPEC.md` | Signed updates: who signs what, file formats, the rollback and replay rules |
| `docs/ATTACK_SURFACE.md` | Every way in, version by version, and the machines that build the device's software |
| `docs/EXPERIMENT_PROTOCOL.md` | The spin repeat's protocol, written before the data |
| `docs/EXPERIMENT_PROTOCOL_2.md` | Protocols 2-5 (the timing residue's cause, cap versus halt, load, several clients) and the packet captures, written before the data |
| `docs/results/` | Complete analysis output for registered experiments |

## Tests and experiments

| Path | What it is |
|---|---|
| `tests/` | Unit tests, comparisons against EZKL's own encoding, end-to-end checks, a parser fuzz test, service tests including the leakage encoders, and `test_docs.py`, which fails when a fact copied between pages drifts from its home |
| `tests/fixtures/` | Two pinned test models: `tiny` (4 inputs, 3 outputs, with its input range in `domain.json`) and `multi` (two inputs, two outputs) |
| `prover/server.py` | The laptop AI server: honest, or misbehaving in one of several ways, including hiding bits in timing, order or failures |
| `observer/client.py` | The outside observer: sends questions (one at a time, in batches, from several connections, or at a fixed pace), records each answer and its time, decodes hidden bits |
| `observer/by_admission.py` | Puts a several-client trace in the order the endpoint admitted the questions |
| `observer/pcap_trace.py` | Answer times and packet details from a capture of the outside link |
| `observer/cap_model.py`, `observer/cap_bound.py`, `observer/cap_check.py` | The failure cap: its reference model, the bound on what the failure pattern can carry, and a reply-by-reply check of a run against the model |
| `observer/sleep_vs_fixed.py` | The random-sleep model compared with fixed release |
| `observer/analyze_matrix.py` | Summarises a release-rule experiment |
| `observer/jitter_test.py` | Tests whether leftover timing differences follow the server's hidden bits |
| `observer/estimate.py` | Estimates leakage as mutual information (bits per answer), with a null and an interval; `--selftest` checks it on synthetic channels |
| `observer/order_experiment.py` | The ordering experiment on one machine |

## Running on the Pi (`device/`)

| File | What it does |
|---|---|
| `device/verify_on_pi.sh`, `device/check_verifier.sh` | Copy the pinned model to the Pi and check accept and reject cases with the real tool, timed |
| `device/pi_scenario.sh` | One experiment on the stock system: the endpoint (Python or Rust) on the Pi, the server and observer on this machine |
| `device/image_scenario.sh` | One experiment against the v1 image, which has no login: the endpoint already runs; writes a manifest per run |
| `device/tcp_scan.py` | Connect scan of every TCP port: open, refused or dropped |
| `device/rust_verify_cost.py`, `device/endpoint_latency.py` | What one Rust check costs, and what the endpoint itself adds to each answer |
| `device/pi_matrix.sh` | Every release rule against every signalling method |
| `device/verify_cost.py` | What one check costs on the Pi, and how reliable each memory limit is |
| `device/measure.sh` | Snapshot of the device's attack surface: packages, services, processes, open ports, file hashes |

## Other

| Path | What it is |
|---|---|
| `image/` | Builds the v1 system with Buildroot (`build.sh`, the option fragments, the overlay with the firewall and start-up checks), signed updates for it (`make_update.sh`), and a file-by-file listing of a built image (`manifest.sh`) |
| `.github/workflows/` | CI: Python tests, the Rust endpoint (native and static aarch64), the book, the spikes, and a second build of the image on demand |
| `book/` | This book (mdBook); the reference pages include the files in `docs/` |
| `book/diagrams/`, `book/render-diagrams.sh` | Diagram sources (Mermaid) and the script that renders them to `book/src/diagrams/*.svg`; mdBook has no Mermaid support, so the SVGs are committed |
| `spike/rust-verifier/` | Side experiment: EZKL's checker as a small Rust program |
| `spike/stwo-verifier/` | Side experiment: a pinned checker for S-two (StarkWare) proofs |
