# NOTEBOOK — chronological log

Honesty note up front: this audit was produced in one continuous AI-assisted working
session, not spread across 5 calendar days. The entries below are in the order things
actually happened — hypotheses, commands, real output, and the points where the data
disagreed with what I expected — not reconstructed afterward. Where I guessed wrong, I've
left the guess in rather than editing it out. See `AI_USAGE.md` for what was AI-driven vs.
verified by hand.

---

## 1. Recon before touching anything

Read `fertility.py`, `REPORT_v0.md`, `corpus_sample/*`, `bench/model_spec.md`,
`bench/bench_log.csv` first, before deciding on tooling. Two things jumped out on first read
of `fertility.py`, before running anything:
- `words = line.split(" ")` looked wrong the moment I saw the double space in
  `corpus_sample/eng_sample.txt` line 7 ("books  in") — `split(" ")` doesn't collapse runs.
- `random.seed(1337)` with `random` never used anywhere else read as either a bug or a red
  herring. Flagged both for testing rather than assuming either way.

Checked environment before committing to a plan:
```
python3 --version          -> Python 3.14.3 (system default, via homebrew)
```
3.14 is very new (released ~Oct 2025) — worried compiled wheels for `tokenizers`/
`sentencepiece` might not exist yet for cp314 and I'd be stuck building from source. Checked
for an older interpreter *before* trying to install anything on 3.14 and wasting a cycle:
```
ls /opt/homebrew/bin/python3*   -> found python3.11 alongside python3.14
```
Used 3.11 for the whole venv. This wasn't a dead end exactly — I checked before I hit the
wall — but it's the kind of thing that would have cost real time if I'd installed on 3.14
first and only discovered the wheel problem when `pip install sentencepiece` failed.

## 2. Corpus (A1)

Needed English + Hindi + ≥2 Dravidian languages, real size, parallel if possible. Tried the
direct NLLB publicfiles URL for FLORES-200 before assuming I'd need HF auth / gating:
```bash
curl -s -m 20 -o /dev/null -w "%{http_code}" -L https://dl.fbaipublicfiles.com/nllb/flores200_dataset.tar.gz
-> 200
```
No gating needed — downloaded the full tarball (24MB) directly, ran it in the background
while doing other setup in parallel rather than waiting on it.

Extracted, checked `devtest/` has all 6 languages I want (eng, hin, kan, tam, tel, mal), all
at 1012 lines. Sanity-checked alignment isn't just "same line count" but actually the same
sentence, by eyeballing line 1 across all 6 files (all six are visibly the same "4-month-old
diabetic mice" quote, in eng/hin/kan/tam/tel/mal) — same-length files could still be
misaligned if something upstream dropped a line asymmetrically, so I didn't just trust the
`wc -l` match.

Minor dead end: tried to get the FLORES-200 license from the `flores200/README.md` on GitHub
via WebFetch first — it didn't state a license, only pointed at "a newer version." Had to
re-fetch the repo root page instead to get the actual "CC-BY-SA 4.0" line. Small thing, but
it's a real example of not taking the first page's silence on a fact as the fact being
unknowable — checked one level up before writing "license unknown" into the corpus doc.

Domain check via `metadata_devtest.tsv`: wikinews (341) / wikibooks (351) / wikivoyage (320).
All formal/edited register — flagged this in `partA/corpus/README.md` as a real caveat given
Part C is specifically about *casual* tone; this eval corpus can't speak to that register gap.

## 3. Auditing fertility.py (A2)

Went through the file hypothesis-first (see §1), then tested each hypothesis in isolation
rather than reading the bugs off the code and asserting effect sizes from intuition.

**`split(" ")` (bug 1):** expected a small, roughly uniform bit of noise from occasional
double-spaces. Ran it on the corpus_sample first (matches the report's exact numbers, good
baseline), then on the full FLORES corpus. Result was *not* uniform — surprised to see 208/1012
Kannada lines affected vs. 0/1012 English lines. That's a bigger and more lopsided effect than
I'd guessed from just eyeballing the 10-line sample (which only showed 1 affected line each for
eng/hin). Revised the writeup to say "uneven across languages," not "small uniform noise" —
the sample was too small to show the real shape of this bug.

**`.lower()` (bug 2):** hypothesis was "no-op for Devanagari/Dravidian scripts, real change for
English." First run showed `hin: lower() changes 38/1012 lines` — not the clean 0 I expected,
which made me stop and check *why* before writing anything up. Printed a few of the affected
lines: they contain embedded Latin-script substrings (acronyms, proper nouns) inside the
Hindi/Kannada/etc. sentences, not native-script case-folding. Confirmed the *effect size*
stayed ≤0.03% for all five Indic languages regardless (vs. English's +3.45%), so the
directional claim survives, but I don't say "exactly a no-op" anywhere in `findings.md`
anymore — I say "near-zero, and here's why it's not literally zero."

**Macro vs. micro average (bug 3):** this one behaved exactly as predicted — macro overstates
every language's absolute fertility by a small, consistent amount (0.5-1.2%), barely moves the
cross-language ratio. No surprises here, which is itself worth recording: not every hypothesis
needs a plot twist to be worth testing and reporting.

**`random.seed` (non-bug):** grepped first (`random.` appears exactly once — the seed itself;
`sys.` appears zero times), then ran the actual script three ways (seed 1337 / seed 42 / no
seed call) end to end and diffed stdout. Byte-identical across all three. Glad I did the
behavioral check and not just the grep — a static "looks unused" argument is weaker evidence
than "I ran it three different ways and got the identical numbers," and the assignment's
evidence rule explicitly punishes exactly the kind of claim ("this seed matters") that would
have been easy to make from the grep alone without running anything.

## 4. The conceptual bug, and picking tokenizers for A3

Read A2's hint again ("the code computes exactly what it says, but what it says is the wrong
thing") and A3's hint ("what is the denominator supposed to hold constant") together — landed
on: tokens/word assumes "word" is a constant unit of content across languages, and it isn't for
agglutinative Dravidian languages. This was a hypothesis from reading, not yet evidence — A3 is
where I tested it.

Needed ≥2 tokenizers, one Indic-aware. Tried three candidates against the HF Hub before
picking, in case any were gated (no external API/auth-token budget to assume away):
```
google/muril-base-cased           -> OK, vocab 197258
ai4bharat/IndicBERTv2-MLM-only     -> OK, vocab 250000
facebook/nllb-200-distilled-600M   -> OK, vocab 256204
```
All three worked ungated. Used MuRIL (purpose-built for English+Indian languages, WordPiece)
and NLLB-200 (general 200-language SentencePiece) — two *different* tokenizer families, so a
result that holds for both isn't just "I found one convenient counterexample." Dropped
IndicBERTv2 from the final writeup only to keep the report to a readable size; it wasn't
worse, just redundant with MuRIL's story.

## 5. Corrected analysis (A3) — this is where the report's core claim breaks

First pass: ran `corrected_analysis.py` with 3 tokenizers (gpt2, muril, nllb-200) × 6
languages × 4 denominators, full FLORES corpus. Expected the two multilingual tokenizers to
look *better* than gpt2. Did not expect the size of the gap: gpt2 gives Kannada a 13.6×
sentence-ratio; MuRIL gives it 1.07×, NLLB-200 gives it 1.36×. I had hypothesized "tokenizer
choice matters a lot," not "two different tokenizer families both land within spitting
distance of parity." That looked like a very clean story — almost too clean — so before
writing it up as "swap the tokenizer and the problem basically disappears," I wanted a fourth
data point that wasn't hand-picked from the "built for Indic languages" category.

**Revision:** added `qwen2.5` (Qwen2.5-0.5B) — a modern, genuinely multilingual, widely-used
*decoder LLM* tokenizer, not a BERT-style encoder tokenizer built with Indic balance as an
explicit design goal — specifically to stress-test the "any multilingual tokenizer fixes it"
version of the story before it went into the memo. Result: Kannada under qwen2.5 is **6.92×**
— nowhere near gpt2's 13.58×, but nowhere near muril's 1.07× or nllb's 1.36× either. That's a
real, load-bearing update, not noise: it moved the conclusion from "swap to any decent
multilingual tokenizer" (what the 3-tokenizer version would have supported) to "the residual
gap size tracks specifically how much Indic-language data the tokenizer's training mix
contained — general multilingual competence is not sufficient, and you have to measure the
*specific* tokenizer you're about to ship, not infer it from a 'multilingual' label." Rewrote
`corrected_analysis.md` Finding 2 and the A4 recommendation to say that explicitly, including
narrating the 3-tokenizer version I almost shipped, because it's a real example of a
plausible-and-wrong intermediate conclusion, not just a stronger final one.

Second, smaller surprise while building the "which denominator" argument for A3: found that
MuRIL's Hindi *word*-ratio is 0.989 — i.e. by that (wrong) denominator Hindi looks *cheaper*
than English. I was looking for "word-ratio overstates cost" and found an actual sign flip on
one language, which is a sharper piece of evidence than I went in looking for (a 36%
overstatement on Kannada, no sign flip, would have made the point almost as well). Recorded
both numbers rather than only the more dramatic one. (Qwen2.5's hin word-ratio, added later,
doesn't sign-flip — 3.77 vs. sent-ratio 4.42 — same direction, smaller magnitude; noted both
so the MuRIL example isn't presented as if it were the typical case.)

## 6. Part B — capacity math

Did the KV-cache arithmetic by hand first, then wrote `capacity_calc.py` to redo it
programmatically before trusting the hand version — manual arithmetic on `2×28×8×128×2` is
exactly the kind of thing that's easy to mis-key once. Landed on 112 KiB/token both ways, good
sign. Flagged the "24GB decimal vs. GiB" ambiguity explicitly rather than picking one silently
— computed both (28 vs. 25 max sequences) since the spec doesn't say which, and checked that
either reading is consistent with where the log actually shows sequences start getting
preempted (between batch 24 and batch 32) — it is, either way.

Noticed the long-prompt throughput anomaly (batch 24 peaks at 1607 tok/s, batch 48 drops to
1298.5) directly in the raw CSV before running any script — the numbers are small enough to
eyeball. Formed a hypothesis (KV-cache saturation → preemption → wasted recompute) from the
`kv_cache_util`/`preempted_seqs` columns, then had to figure out what `reported_tok_s` was
actually counting before I could turn "batch 48 is worse" into a quantified goodput number.
Guessed it might be counting prompt+gen tokens together; checked by computing
`(prompt_len+gen_len)*num_requests/wall_clock_s` for every row and comparing to the logged
column — matched to within rounding on all 13 rows, not just the ones I was originally looking
at. That full-table match (rather than checking 2-3 rows and assuming) is what made me
confident enough to state the formula as fact in `partB/analysis.md` rather than "probably."

Derived batch-24 goodput two ways (direct definition, and back-computed from `reported_tok_s`)
specifically because the assignment asks for two independent derivations — they agreed to
within 0.01 tok/s, which is good internal confirmation the formula is exactly right and not a
coincidental approximation.

## 7. Part B, released for Part A: the FLORES formal-register finding is not the same corpus, but rhymes with the goodput mixing

No code here, just a note on why I structured A3 and B3 the way I did: both come down to
"denominator/column conflates two things that shouldn't be averaged together" — tokens/word
conflates tokenizer quality with morphological density; `reported_tok_s` conflates prefill
throughput with decode throughput. Didn't force this parallel into the writeups explicitly
(didn't want to overclaim a deep connection that isn't really there beyond "check what a ratio
is actually holding constant before trusting it"), but it's why both halves of this audit felt
like the same kind of bug in different clothes, and why A3's "what should the denominator hold
constant" framing is also basically the right question to ask about B3's column.

## 8. Part C — no code, but a real revision while writing it

First instinct going in was to recommend (a) SFT, on "best ceiling for the actual ask" grounds
— casual tone is a deep stylistic property, and a rewriter bolted on after the fact seemed like
a weaker fix. Reconsidered once I actually wrote out the constraints side by side: the reviewer
covers only 2 of the 6 required languages. That's not a data-volume problem, it's a "we cannot
verify 4/6 languages this cycle no matter which path we pick" problem, and it argues for
whichever path is easiest to ship narrowly (Hindi+Kannada only) and roll back per-language —
which is (b), not (a). Switched the recommendation mid-draft once the reviewer-language
mismatch became the load-bearing constraint rather than model-quality ceiling. Left this in the
notebook because it's a real example of a first instinct changing once the constraints were
actually laid out in arithmetic rather than argued in prose.

## 9. What I'd do with more time

- Bootstrap/confidence intervals on the A3 ratios (flagged as missing in `partA/corpus/
  README.md` rather than silently presenting point estimates as exact).
- A held-out, organically-written (non-translated) Indic-language sample to check the
  translationese caveat directly instead of just naming it.
- B4's mechanism is argued from the aggregate CSV columns; a real serving stack's
  time-series preemption counter would let me check the *ordering* claim (cache saturates,
  *then* preemptions start) instead of inferring it from two summary numbers per row.

---

## Revision — 2026-09-06 (same day, follow-up pass)

Four follow-up requests came in after the initial submission was delivered: save every
script's raw output to disk, expand the corpus to match Part C's six target languages, remove
`original/` if it turns out not to be needed, and add a top-level `REVIEW.md`. Logging this as
its own dated entry per instruction, rather than quietly editing the numbers already written up
above — everything in §§1-9 stays as it was when originally written, dead ends included.

**Corpus expansion.** Part C's product ask targets Hindi, Kannada, Tamil, Telugu, Bengali, and
Marathi — six languages — but the A1 corpus built earlier only covered four of those (Hindi,
Kannada, Tamil, Telugu) plus Malayalam, missing Bengali and Marathi entirely. FLORES-200
devtest already has both (`ben_Beng.devtest`, `mar_Deva.devtest` — confirmed present in the
same tarball downloaded originally, no new download needed). Added both to
`build_corpus.py`'s `LANGS` dict and to the hardcoded language lists in `bug1/2/3` and
`corrected_analysis.py`, re-ran `build_corpus.py` — still 1012 parallel lines across all 8
files, alignment intact.

Re-ran every A2 script and `corrected_analysis.py` against the 8-language corpus. Went in
expecting either "fits the existing pattern" or "reveals something new" and it came back
cleanly in the *first* camp, which is itself worth recording honestly rather than manufacturing
a finding: bug 1 (double-space) hits ben/mar at 71/1012 and 57/1012 lines respectively, same
modest -0.35% to -0.40% distortion range as the other five languages; bug 2 (lowercase
asymmetry) inflates ben/eng and mar/eng ratios by exactly the same -3.34% as every other
language, because the mechanism only ever touches the shared `eng` denominator; bug 3
(macro/micro) overstates ben/mar fertility by +0.91%/+0.69%, inside the existing 0.5-1.2%
range. One number *is* new and worth flagging: under MuRIL, Bengali's sentence-ratio comes out
to **1.001×** — the closest to exact parity of any language/tokenizer pair in the whole table,
even closer than Hindi's 1.157×. Added it to `findings.md`'s conceptual-bug section and A3's
Finding 1/3 as the sharpest illustration available, since it's a genuinely new, useful data
point, not just a repeat of the existing pattern at a new coordinate.

Updated `findings.md`, `results/corrected_analysis.md`, and `partA/memo.md` to include ben/mar
throughout (tables, ranges, prose) — per the instruction that governs this, memos only get
touched when a number actually changes or a table becomes incomplete relative to the corpus,
and here both were true (the 8-language corpus made every 6-language table in A2/A3 stale, and
A4's headline table would have silently omitted 2 of the 6 languages Part C cares about if left
alone). `partB/analysis.md` and `partC/memo.md` were **not** touched beyond adding output-file
citations — Part B doesn't read the Part A corpus at all (confirmed: re-ran `capacity_calc.py`
and diffed against the numbers already quoted in `analysis.md`, byte-identical), and Part C has
no code and no per-language numbers that the corpus expansion could affect. `AI_USAGE.md` was
left completely untouched, as instructed.

**Output-to-disk.** Every script now writes its full stdout+stderr to a `*_output.txt` file
next to itself (e.g. `bug1_double_space.py` → `bug1_double_space_output.txt`), captured via
plain `> file 2>&1` with nothing filtered out — including the two harmless HuggingFace/PyTorch
warning lines that appear in `corrected_analysis_output.txt`, left in rather than cleaned up,
since "full printed output" should mean full. Went back through `findings.md`,
`corrected_analysis.md`, `memo.md` (A4), and `partB/analysis.md` and added an explicit "full
output saved to" pointer next to every quoted number's source, rather than leaving the
scripts-are-runnable claim implicit. `_common.py` is the one exception: it's an import-only
helper with no `print` calls, so running it directly produces genuinely empty stdout — checked
this directly rather than assuming, and left a one-line note explaining the empty file instead
of just omitting it (an unexplained empty file looks like an oversight; an explained one
doesn't).

**`original/` duplication.** Reconsidered whether the `original/` copy of the starter-kit
inputs (`fertility.py`, `bench_log.csv`, etc.) is actually needed, per the request to remove it
if not. It is: `_common.py` imports `fertility.py` from it (used by `bug1/2/3` and the
non-bug script), and `capacity_calc.py` reads `bench_log.csv` from it. Both paths were
deliberately pointed at this local copy (rather than the sibling `starter_kit/` directory) in
the previous pass specifically so the submission would run standalone if zipped and handed to
someone without `starter_kit/` alongside it — that was the whole point, not an accident. Kept
it, and said so explicitly in `REVIEW.md` rather than silently leaving a folder whose purpose
isn't obvious from its name alone.

**`corrected_analysis.json`.** Was never hand-edited to begin with — it's written by
`out.write_text(json.dumps(...))` at the end of the script, so every prior run already
overwrote it fresh. Re-ran it again as part of the corpus expansion regardless, so the checked-
in copy reflects the current 8-language run, not a stale 6-language one.
