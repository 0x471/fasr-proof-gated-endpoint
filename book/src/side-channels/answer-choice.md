# Choosing among valid answers

> **In short**
> - A proof fixes the content only if it leaves the server no choice about the answer.
> - Real language models sample their words, so many answers are valid and the server could pick one.
> - Pinning every source of freedom closes this; a model that hides messages itself is a different problem.

## Why our test model has no such channel

Our test model is small and deterministic: one question always gives exactly one answer. So a valid proof leaves the server no choice, and nothing can hide in the content. All the measurements in this book describe that setting.

## Why real language models are different

A language model gives probabilities for the next word. After "The weather today is", it might rate "nice" as most likely, then "sunny", then "lovely". An honest server rolls a random number and picks according to those probabilities.

A hacked server could instead **choose** the word to carry bits. It might send the most likely word for a 0 and the second most likely for a 1. Cleverer schemes keep the text statistically normal, so it looks like honest random output. Every such answer is still a valid output of the approved model. A proof that only says "this text could come from the model" lets every choice through.

## Every source of freedom must be pinned

The real requirement is that **the proof leaves the server no choice about the output**. In real model serving, freedom comes from several places:

| Source of freedom | How it can be removed |
|---|---|
| Random word choice | the randomness comes from a seed the server cannot choose, for example derived from a nonce the gate supplies; or decoding always takes the most likely word |
| Small numeric differences between GPU runs | prove an exact integer version of the model instead of tolerating small differences |
| Tolerance in the check | accept only an exact match; any tolerance is room to hide bits |
| Where the reply stops | the proof must cover the stopping rule |
| Which valid proof is sent | never release or log the proof, since proofs are randomised |

## What exists today

- **Rinberg et al. (2025)** name this channel. If the attacker can choose or steer the randomness, "the sampler itself becomes a covert channel". Their defence is randomness bound to the request that the attacker cannot influence.
- **Sable** (MoonMath, 2026) proves sampled replies with a seed derived from the client's nonce, the model commitment, the prompts and the settings, "so the server cannot choose the randomness". It is not zero-knowledge, however: many proofs together reveal the model's weights. Its proofs are also very large.
- **FlashProve** (Anthropic, 2026) hides the weights, but proves only that each word is the model's top choice. It says nothing about sampling.

No system we found does both: proving sampled replies with outside randomness while keeping the weights secret. Petrie, Muhlhauser and Drotos (2026) make the same point in general terms: their bound holds only if the proof system leaves "zero prover freedom".

## A different problem: the model hides messages itself

Sometimes the hidden message is not the server's choice but the model's own. Language models can learn to hide messages in what they write. [Karpov et al. (2025)](https://arxiv.org/abs/2505.03439) found such skills rudimentary today, but much stronger when the model is given an explicit method.

Here the hidden message **is** the approved model's genuine answer. The proof correctly says the approved model produced it, so the endpoint must release it. Supplying the randomness does not help either, because the model shapes which words are likely in the first place.

So proof-gating guarantees **which model** answered, not that the model is harmless. Monitoring outputs, testing models and alignment work are the defences there. This is outside the endpoint's scope; see [Limitations](../limitations.md).

## Where this leaves our results

Our measurements of timing, order and failures describe what remains **after** the content freedom is removed. A gate in front of a real model needs both: pinned content and controlled behaviour.
