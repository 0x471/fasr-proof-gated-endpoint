# Limitations and open questions

> **In short**
> - Not built yet: two physically separate ports, secure boot, a counter that stops a whole older store being restored, update delivery on the device, a hash-chained log.
> - Not measured yet: a real upper bound on leakage, several users at once, packet-level signals, the speed-versus-leakage trade-off.
> - The results assume all of the server's traffic goes through the endpoint, one approved model, and a sound proof system.

## Not built yet

- **Two physical ports.** The v1 image runs the endpoint, but the server side and the outside still share one cable; a board with a second wired port is planned.
- **v2:** secure boot (which permanently writes a key into the board, so it needs a spare board); a TPM counter so a whole older copy of the update store can't be restored (K43); a power-loss test of update installation on the Pi's file system; a hash-chained log sent to a separate collector.
- **Update delivery on the device.** The image has no login; a new update comes as a new image or is applied to the card's store on another machine, where the same rollback and replay rules apply because the state lives on the card.
- **The failure channel** is only reduced. The Rust endpoint caps failures per window, which bounds what the failure pattern alone can carry, and one Pi run showed far fewer hidden bits getting out at a large cost in availability ([Measurements](results.md)). Timing, logs and restarts need their own accounting.

## Not measured yet

- **A capacity bound.** The numbers are achieved rates for planted bits and one binned mutual-information statistic (`observer/estimate.py`, checked on synthetic channels with known values). Checking an estimator on known distributions is not a bound on what an arbitrary encoder and observer can achieve; no such bound is claimed.
- **Several clients at once,** other loads, and a packet capture on the outside link.
- **The `busy` channel:** under fixed release, which requests come back `busy` doesn't depend on the server (a state-machine test, K17); in arrival order it does, and under load the event loop's own delays (K34) are not measured.
- **The budget trade-off:** fixed release was run with one budget (4 s); leakage and lost answers against the budget are not measured.
- **The residual timing trace** under fixed release: its mechanism (two candidates: how long the processor takes to wake from idle, and its speed changing with load; the v1 image's kernel defaults to the lowest processor speed, which may be why its run showed nothing), and whether the redesigned spin removes it. {{#include results.md:spin-verdict}} Settling it needs more answers, and several clients are untested.

## Assumptions the results rest on

- Every path from the server to the outside goes through the device. With one shared cable this is not enforced physically.
- One pinned model and circuit; the binding rules are specific to EZKL 23.0.5.
- The endpoint binary, with EZKL's verifier inside it, is trusted, with its failures contained: if the verifier wrongly said ACCEPT, the endpoint couldn't tell. On the v1 image the model files, the domain file and the release policy come from the signed store and are checked at start; the bundle's hashes are checked again before every check. The binary itself relies on the read-only image (and, in v2, secure boot). The Python reference endpoint additionally trusts the EZKL command-line tool and the interpreter.
- The proof system is sound. Its soundness is out of scope.
- The machines that build the device's software weren't compromised. The endpoint binary is built on GitHub's CI from pinned sources; the image is built in a virtual machine on the laptop from hash-checked sources and checked afterwards. A second build on a clean runner matched it file by file except for build metadata ([Measurements](results.md)), but the kernel can't yet be compared byte for byte, so a compromised build machine could still change the kernel unnoticed (`docs/ATTACK_SURFACE.md`).

## Out of scope

Physical attacks and physical side channels (power, electromagnetic, acoustic, thermal), what ordinary correct outputs reveal about a model (extraction from many answers), and the soundness of the proof system itself.

## Open questions

1. After a failed check, should the device keep answering (and count failures) or stop until reset? Halting is a denial-of-service lever and still reveals where the halting failure was.
2. Which replay property matters: never delivering an answer twice, or proving each answer was freshly computed?
3. Should answers be ordered across all clients (a silent request then delays everyone) or per client (the server can then order answers across clients)?
4. Who may read the device's logs? The log still carries the number and timing of events.
5. How much latency and how many lost answers are acceptable in exchange for less leakage?
