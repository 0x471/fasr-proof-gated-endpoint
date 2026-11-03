# Threat model

> **In short**
> - We protect weights and the endpoint's controls: model files, code, settings, release rules and logs.
> - The main attacker is the server working with an outside accomplice. Network attackers and signing-key holders also matter.
> - Every outside route must pass through the endpoint. Physical attacks are outside scope.

The server may be hacked or a model acting against its owners. Signing-key attacks apply to later versions. Below, sections 1-5 define assets, attackers, boundaries, assumptions and access. Section 6 lists signals and defences; section 8 maps threats to MITRE ATLAS.

For a plain introduction, read [Leakage](leakage.md) and [Hardening](hardening.md). Terms are in the [glossary](glossary.md).

{{#include ../../docs/THREAT_MODEL.md:2:}}
