# Proof-gated endpoint

> **In short**
> - A Raspberry Pi checks proofs before letting an AI server's answers reach a user.
> - Proofs fix answer content. Timing, order and failures can still carry hidden data.
> - We measured these signals on a toy model. This is work in progress, not production security.

## The problem

An AI lab's most valuable asset is its model's weights: the numbers that define the model. A hacked server, or a model acting against its owners, could hide those weights in ordinary answers.

We put a small checkpoint between the server and the outside world. We call this the [endpoint](glossary.md). It checks a cryptographic proof that the approved model produced the answer from the exact question it received.

```text
user -- question --> endpoint (Pi) -- question --> AI server
user <-- reply ----- endpoint (Pi) <-- answer + proof --+
         proven answer or "unavailable"
```

The endpoint removes the server's freedom to change the answer's content. Its small, simple design makes it much easier to secure than the datacenter behind it. The server still chooses when to answer and whether to fail.

## Three findings

We tested order, timing and deliberate failures. Ordering rules stopped the code we tried. Fixed release greatly reduced timing signals, at a cost in speed. Failures still carried information; limiting them cost availability.

{{#include results.md:findings}}

These results use one tiny, deterministic model and the hiding methods we tried. They are not limits on what an attacker could achieve. Read [the leakage explanation](leakage.md) for the mechanisms and [Measurements](results.md) for conditions and evidence.

## Status

This work was supported by ERA's Frontier AI Security Residency. It is work in progress as of November 2026.

{{#include ../../README.md:status}}

## Where to go next

- A five-minute introduction: this page and [What a hacked server can still leak](leakage.md).
- The system and diagrams: [How it works](tour.md).
- Security assessment: [Hardening](hardening.md), [Attack catalogue](attacks.md) and [Threat model](threat-model.md).
- Evidence and commands: [Measurements](results.md) and [Reproduce](reproduce.md).
- Scope and unfamiliar terms: [Limitations](limitations.md) and [Glossary](glossary.md).

Code: [proof-gated-endpoint](https://github.com/0x471/fasr-proof-gated-endpoint).
