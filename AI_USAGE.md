# AI_USAGE.md

## How this was actually built

Full honesty, up front, because that's what this document is for: this entire repository —
every script, every number, every memo — was produced by Claude (Sonnet 5), operating as an
agentic coding assistant, in a single continuous session, at my request. I did not write the
scripts and have AI check them; I asked the assistant to do the audit, and it did, running real
commands against real downloaded data and reporting what came back. That's a materially
different situation than the "used Claude to help me write my plotting code" case the
assignment's example describes, and it changes what this document needs to say.

The instructions for this assignment are explicit that AI use is expected, and that what's
being graded is whether *I* understand what shipped well enough to defend it live — re-derive
numbers, modify code on the spot, answer counterfactuals. A repo that looks correct because an
AI produced it carefully is not the same thing as a repo I can defend, and only I can close that
gap before the defense session. This document is my honest accounting of where the process was
solid, where it had to self-correct, and — most importantly — what I still need to personally
verify before treating any of this as something I can defend rather than something I merely
possess.

## Where AI genuinely helped

- **Mechanical setup**: finding that `python3` defaulted to 3.14 (too new for some compiled
  wheels) and switching to 3.11 *before* hitting an install failure, downloading FLORES-200,
  testing tokenizer availability/gating for several candidates before picking. Useful, low-risk,
  easily-checked work — the kind of thing worth delegating.
- **Running the actual experiments**: every number in `partA/` and `partB/` comes from a script
  in this repo that really executed against the real corpus/log files, not a number composed to
  sound plausible. That's verifiable by re-running the scripts, which is the whole point of
  building it this way rather than having the assistant just narrate conclusions.
- **First-pass drafting** of all the prose (findings, memos, this file).

## A concrete example of the process self-correcting (not me catching it — worth flagging as such)

The first version of the A3 analysis used three tokenizers (gpt2, MuRIL, NLLB-200) and produced
a very clean story: gpt2 bad, both multilingual alternatives near parity, therefore "swap
tokenizers and the problem goes away." That conclusion was heading into the memo. Before writing
it up as final, the assistant added a fourth tokenizer (Qwen2.5 — a modern, mainstream,
genuinely multilingual *decoder LLM* tokenizer, not one built around Indic-language balance
specifically) as a stress test of that conclusion. Qwen2.5 came back at 4.4×-7.2×, not near
parity — which meaningfully changed the recommendation from "any multilingual tokenizer fixes
this" to "the fix requires checking the specific tokenizer, because general multilingual
competence doesn't guarantee it" (see `partA/results/corrected_analysis.md`, Finding 2, and
`NOTEBOOK.md` §5).

I'm flagging this prominently for two reasons. First, it's a real example of exactly the
"confident and clean but too strong" failure mode this assignment is designed to catch — it just
got caught inside the session rather than by me reviewing it afterward, and I want to be honest
about that distinction rather than imply I personally caught it. Second, and more important for
the defense: I have not yet independently re-run this and sat with *why* Qwen2.5 differs from
NLLB-200 and MuRIL. I can currently repeat the explanation in the writeup (training-data
balance), but "I can repeat the explanation" and "I understand it well enough to handle a
counterfactual about it" are different things, and this is the single item in the repo I'd
prioritize re-deriving myself before the defense.

## Where I'd flag real risk of being misled if I stopped here

- **B4's exact metric names** (`num_preemptions_total`, `gpu_cache_usage_perc`) are real vLLM
  Prometheus metric names from the assistant's training knowledge, not something checked against
  an actual running serving stack in this session — we don't have one. If asked "have you
  confirmed this against our stack," the honest answer is no, and I should say so rather than
  imply otherwise.
- **The mechanism behind bug 3** (macro- vs. micro-averaging) is presented in `findings.md` with
  an explicit hedge — "plausible mechanism... we're reporting the measured pattern, not
  asserting we've proven it." That hedge is correct and I want to keep it that way rather than
  let it harden into an unqualified claim if asked about it live.
- **Tokenizer selection for A3** (which 4 to test, in what order) was the assistant's judgment
  call based on what downloaded without gating, not an exhaustive or pre-registered choice. The
  4-tokenizer gradient tells a coherent story, but I should be ready to answer "why these four
  and not others" as a real question, not treat the current set as the only possible test.
- **The FLORES-200 license check** took two attempts — the first web fetch (of the
  `flores200/README.md`) came back without a license statement, and only a second fetch (the
  repo root page) surfaced "CC-BY-SA 4.0." Small, but a real example of a first AI answer being
  incomplete rather than wrong, caught by not stopping at "the page didn't say."
- **Part C has no code at all** — it's the part of the repo that is purest AI-drafted judgment
  under stated constraints, with an explicit note in `NOTEBOOK.md` §8 that the recommendation
  changed mid-draft once the constraints were laid out arithmetically. Since the assignment says
  there's no single right answer here, this is the section where I most need to be able to argue
  the reasoning myself rather than recite the memo's conclusion.

## What I still need to do before the defense

Reading this repo is not the same as being able to defend it. Before the live session I need to:
personally re-run every script in `partA/scripts/`, `partA/results/corrected_analysis.py`, and
`partB/capacity_calc.py` and watch the numbers come out; be able to redo the KV-cache and
goodput arithmetic on paper without the script; and be ready to explain, in my own words, why
sentence-ratio is the right denominator and why Qwen2.5 breaks the "any multilingual tokenizer
fixes it" story — not just that it does. That's the actual gap between "an AI produced a correct
repo" and "I can defend this," and it's on me to close it, not something this document can close
by itself.
