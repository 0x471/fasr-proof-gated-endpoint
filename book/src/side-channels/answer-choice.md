# Choosing among valid answers

> **In short**
> - A proof fixes the content only if it leaves the server no choice about the answer.
> - When sampling allows several accepted outputs, the server may be able to encode a choice.
> - Fixing that choice does not stop a model from hiding messages in its approved output.

## Why our test model has no such channel

Our test model is deterministic: the same encoded input has one approved output. Under the proof and binding assumptions, the server cannot substitute a different output. This removes its choice of content, not information already present in the approved answer. All the measurements in this book describe that setting.

## Why real language models are different

A language model scores possible next tokens, the pieces of text that make up words. For illustration, after "The weather today is", it might favour "nice", then "sunny", then "lovely". Sampling uses randomness to choose from the distribution. Greedy decoding instead takes the highest-scoring token.

A hacked server could choose the most likely token for a 0 and the second most likely for a 1. That simple code may change the distribution; more careful encodings can resemble ordinary sampling. A check that accepts both choices can leave room for this channel. A proof of exact sampling with fixed randomness would make a different claim.

## Every source of freedom must be pinned

To remove this channel, **the proof must fix the output** for the agreed input and settings. Possible sources of freedom need separate treatment:

| Source of freedom | How it can be removed |
|---|---|
| Random token choice | use trusted randomness bound to the request, with fixed settings and controls on retries; or specify greedy decoding including ties |
| Small numeric differences between runs on graphics processors (GPUs) | specify exact arithmetic; an integer model is one option, but changes the computation being approved |
| Tolerance in the check | determine whether multiple distinguishable outputs can pass and be selected by the attacker; tolerance alone does not establish a usable channel |
| Where the reply stops | the proof must cover the stopping rule |
| Which valid proof is sent | discard proof bytes and hashes; randomised proofs can differ even for the same output |

## What exists today

Zero-knowledge proofs of model computation, often called zkML, aim to check computation while hiding private data such as weights. The systems below make different claims about output choice. This table summarises their descriptions; we have not run or audited them.

| System | Output rule described | Weight privacy claimed | Limit of that claim |
|---|---|---|---|
| [FlashProve][flashprove] | top token under exact match; a separate tolerance policy accepts alternatives | yes, with declared disclosures | only the checked token range; sampling is not covered, and reply-end checks remain external |
| [DeepProve][deepprove] | computation through next-token argmax, meaning the highest score | yes | the README does not establish externally fixed sampling |
| [zkLLM][zkllm] (Sun et al., 2024) | model computation; sampling is described, not specified as a proved draw from fixed randomness | yes | no demonstrated closure of sampling choice in this paper |
| [Sable][sable] | greedy or sampled, fixed by the statement's inputs | no | the caller must fix those inputs, including the nonce and policy |
| [VerInf][verinf] | bounds unexplained information in observed output | yes | bounds residual information rather than requiring one exact output |

- [Rinberg et al. (2025)](https://arxiv.org/abs/2511.02620) require trusted randomness bound to the request, with no attacker control through seeds, settings or retries. [Token-DiFR](https://arxiv.org/abs/2511.20621) checks outputs against a same-seed reference despite numerical variation. It is a statistical check, not a cryptographic proof.
- Sable derives its seed from a client nonce, the model commitment, prompts and settings. A nonce is a value supplied to distinguish requests. Fixing these inputs prevents later seed choice, but does not make an attacker-controlled client trustworthy. Its integer model differs from the floating-point model, its proofs are large, and accumulated proofs can reveal weights.
- FlashProve's [limits][flashlimits] distinguish exact match from its weaker tolerance policy. They also separate protocol theorems from the implementation and require the caller to check coverage and reply endings. DeepProve's README describes next-token argmax; that alone is not evidence that every serving choice is fixed.
- VerInf reports a bound per token, not per word, on information the approved computation does not explain. Its reported bound does not rule out a short secret over enough tokens, but is not a demonstrated rate for transmitting one. The README calls it an unaudited prototype and warns that deployment must account for repeated attempts to obtain favourable proof challenges.

These descriptions do not establish a deployed, weight-private service that fixes every sampling choice against our attacker. That is a limit of this comparison, not a claim that no such system exists.

Petrie, Muhlhauser and Drotos (2026) require fixed intermediate computations when proving predicted output probabilities. Otherwise the prover could change those probabilities and understate unexplained information. Their phrase "zero prover freedom" concerns that calculation; it does not require every permitted output to be deterministic.

## A different problem: the model hides messages itself

Sometimes the hidden message is not the server's choice but the model's own. [Karpov et al. (2025)](https://arxiv.org/abs/2505.03439) found rudimentary abilities in the models they tested, improving substantially with explicit guidance.

Here the hidden message is already part of an approved output. The proof can accept that content because it is consistent with the pinned computation. External randomness alone does not establish that the model's output contains no secret.

A proof of output consistency does not establish which software actually ran, or that the approved model is harmless. Output monitoring, model testing and alignment address a separate problem. This is outside the endpoint's scope; see [Limitations](../limitations.md).

## Where this leaves our results

Our timing, order and failure measurements assume the deterministic toy relation and correct binding. Applying them to a real model also requires fixing or bounding content choice. This prototype has not demonstrated that extension.

[flashprove]: https://github.com/anthropics/FlashProve/blob/9e2bdd8ff5bf9c62f18263d7dac189b0400b260c/README.md
[flashlimits]: https://github.com/anthropics/FlashProve/blob/9e2bdd8ff5bf9c62f18263d7dac189b0400b260c/docs/limits.md
[deepprove]: https://github.com/Lagrange-Labs/deep-prove/blob/9d1a53e2ef49ffa2c902b8689cd3c58057a4e662/README.md
[zkllm]: https://arxiv.org/abs/2404.16109
[sable]: https://github.com/moonmath-ai/Sable/blob/0bc6b549afef2f8eb9b8bc4c2f24d6e554dbaacb/README.md
[verinf]: https://github.com/JamesPetrie/VerInf/blob/7947bb9a6c7ec86ea97927c76370b3920b6269f6/README.md
