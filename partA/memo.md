# A4 — Recommendation memo

## Corrected headline numbers

REPORT_v0's "Hindi costs 6× English" used one tokenizer (gpt2) and one denominator
(tokens/word). Both choices were wrong for this decision. Correcting both (see A2/A3 for full
evidence): tokens-per-parallel-sentence, on FLORES-200 (1012 sentences/language, 8 languages
as of the 2026-09-06 corpus revision — see [NOTEBOOK.md](../NOTEBOOK.md)), across four
tokenizers. Every number below is copied from
[`partA/scripts/corrected_analysis_output.txt`](scripts/corrected_analysis_output.txt) —

| tokenizer | hin | ben | mar | kan | tam | tel | mal |
|---|---:|---:|---:|---:|---:|---:|---:|
| gpt2 (current, English-only training) | 7.4× | 9.6× | 7.9× | 13.6× | 15.5× | 13.0× | 15.2× |
| Qwen2.5 (modern multilingual LLM, zh/en-centric) | 4.4× | 5.0× | 4.6× | 6.9× | 6.1× | 7.0× | 7.2× |
| NLLB-200 (200-lang MT, balanced sampling) | 1.2× | 1.3× | 1.3× | 1.4× | 1.4× | 1.3× | 1.5× |
| MuRIL (purpose-built for Indian languages) | 1.2× | **1.0×** | 1.1× | 1.1× | 1.1× | 1.2× | 1.2× |

The "6–15×" number is real *for the currently-deployed tokenizer*, but it is **not a property
of Hindi, Bengali, Marathi, or the Dravidian languages** — it's a property of having picked a
tokenizer trained almost entirely on English text. That's the good news. The complication:
**"multilingual" does not automatically mean "fixed."** Qwen2.5 is a modern, genuinely
multilingual, widely-used LLM tokenizer, and it still carries a real 4.4×-7.2× gap — roughly
halfway between gpt2 and the two Indic-focused tokenizers. The gap size tracks how much a
tokenizer's *training data* specifically weighted Indic languages, not just whether it's
labeled multilingual — Bengali under MuRIL reaches **1.0×, i.e. no measurable gap**, which is
about as clean a confirmation of that mechanism as this data can offer.

## Routing recommendation

**Do not** adopt "route Indic traffic to a separate stack and budget 6× cost" as a permanent
plan — most of that number is a tokenizer-selection artifact, not a fixed cost. But also
**do not** assume any multilingual model swap fixes it automatically:

1. Measure sentence-level fertility (this repo's method) on the *specific* tokenizer attached
   to whichever model is actually being considered, before making a routing/capacity decision
   on it. "It's multilingual" is not sufficient evidence, per Qwen2.5 above.
2. If choosing among multilingual options, prefer one with explicit Indic-language design
   intent (MuRIL/NLLB-family-like) over a general-purpose multilingual LLM tokenizer for Indic
   traffic specifically — the residual gap is meaningfully smaller (~1.0×-1.5× vs. ~4.4×-7.2×).
3. Budget capacity for whatever multiplier that specific measurement gives you — **as low as
   ~1.0×-1.5× with an Indic-focused tokenizer, but potentially still 4-7× with a merely
   "multilingual" one** — not a flat 6× assumption either way.
4. Only consider a fully separate Indic-specialized serving stack if a language-specific
   accuracy or latency need shows up later; the tokenizer choice, not infrastructure
   separation, is what actually buys most of the possible cost improvement.

## Biggest caveat

FLORES-200 is formal, edited, Wikipedia-register text, translated (not organically written)
from English. Two ways this could be wrong in production: (a) the product goal in Part C of
this assignment is *casual, conversational* Indic-language replies — informal/code-mixed text
tokenizes differently (often worse, due to transliteration and script-mixing) than clean
Wikipedia prose, so the true gap on real chat traffic could be larger than measured here for
*any* of these tokenizers; (b) translationese tends to structurally mirror the source language,
which plausibly *compresses* the measured gap relative to organically-authored text. Both push
toward treating every number above as a floor, not a ceiling, until checked against real
traffic — and toward re-running this same measurement on the actual production tokenizer
rather than trusting these four as a permanent answer.

## Metric to monitor in production

**Tokens per UTF-8 byte of input, tracked per language**, on live traffic, with an alert if any
language's ratio to English drifts materially above whatever this method measured for the
tokenizer actually in production. We recommend this specifically because it's the one thing
above computable on live traffic: production requests aren't parallel translations of each
other, so "tokens per parallel sentence" — our recommended *eval* metric — can't be computed
live. Tokens/byte is a noisier proxy (byte counts are also script-encoding-dependent, see A3),
but tracking its trend rather than its absolute value catches the failure mode that matters
most here: silently regressing toward gpt2-like or Qwen2.5-like fertility if a future
model/tokenizer swap changes Indic-language vocabulary coverage without anyone re-measuring it.
