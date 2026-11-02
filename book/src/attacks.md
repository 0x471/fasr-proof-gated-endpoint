# Attack catalogue

> **In short**
> - Every attack tried so far, by us or by reviewers, with its result and the test that now covers it.
> - {{#include ../../docs/ATTACKS.md:summary}}
> - The ones that still work are all about signalling (timing, failures, keeping the endpoint busy) or about the standard Pi system, which v1 replaces.

What the outcomes mean: **stopped** means the endpoint refuses or neutralises the attack (for example it rejects the answer, or releases nothing the server chose) and a test or a Pi run shows it; it doesn't mean the device stopped working. **Allowed on purpose** means the behaviour is accepted by design. **Still works** means the attack gets something through, with the measured rate where there is one.

How to read a row: **Version** is the endpoint version the attack was tried against; **Level** says how it was shown (on the real Pi, in automated tests, or only proposed); **Result** says what happened; the last column names the test.

{{#include ../../docs/ATTACKS.md:2:}}
