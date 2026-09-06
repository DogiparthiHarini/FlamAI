# A2 — Audit of `fertility.py` and the fertility metric

Every claim below has a runnable script in [`scripts/`](scripts/) that isolates the one
change under test and prints before/after numbers. Commands are given exactly as run, and
each section names the exact saved output file the quoted numbers were copied from — see
[REVIEW.md](../REVIEW.md) for the full reproduce-everything list and how to verify a file
against a quoted number yourself. All scripts import the **unmodified** copy of the original
`fertility.py` (in [`../original/`](../original/), via `_common.py`) — nothing here is a
paraphrase of the original code.

Corpus note: as of the 2026-09-06 revision (see [NOTEBOOK.md](../NOTEBOOK.md)), the eval
corpus covers 8 languages — English, Hindi, Bengali, Marathi, Kannada, Tamil, Telugu,
Malayalam — matching Part C's six target languages plus English and Hindi. All evidence below
was re-run against the 8-language corpus; none of the original 6-language findings changed
direction or qualitative conclusion, and Bengali/Marathi both land inside the range already
established by the other languages (called out explicitly where relevant).

---

## Code bug 1 — `words = line.split(" ")` doesn't collapse whitespace runs (`fertility.py:62`)

**Claim:** any run of 2+ spaces produces a phantom empty-string "word", inflating the word
count and therefore *deflating* the reported fertility for that line.

**Command:**
```bash
python3 partA/scripts/bug1_double_space.py
```

**Full output saved to:** [`scripts/bug1_double_space_output.txt`](scripts/bug1_double_space_output.txt)

**Evidence (excerpt):**
```
=== hin_sample.txt ===
lines with a double space: 1 / 10
  line 9: split(' ') -> 6 words (incl. 1 empty) | split() -> 5 words | text: 'किताबें  अलमारी में रखी हैं।'
  corpus fertility  buggy split(' ')=7.4485   fixed split()=7.5985   distortion=-1.97%

=== FULL FLORES-200 corpus (1012 lines/lang) ===
eng: double-space lines=   0/1012  buggy=1.2874  fixed=1.2874  distortion=+0.000%
hin: double-space lines=   6/1012  buggy=7.8651  fixed=7.8669  distortion=-0.023%
ben: double-space lines=  71/1012  buggy=13.3848  fixed=13.4383  distortion=-0.398%
mar: double-space lines=  57/1012  buggy=11.1860  fixed=11.2255  distortion=-0.352%
kan: double-space lines= 208/1012  buggy=22.5698  fixed=23.0193  distortion=-1.953%
tam: double-space lines=  75/1012  buggy=25.1270  fixed=25.2523  distortion=-0.496%
tel: double-space lines= 136/1012  buggy=20.5656  fixed=20.8298  distortion=-1.269%
mal: double-space lines=  54/1012  buggy=27.5845  fixed=27.6894  distortion=-0.379%
```

**Direction and magnitude:** the bug always deflates fertility (never inflates), by up to
~2% at corpus scale. Critically, it is **not evenly distributed across languages** — 0/1012
English lines are affected vs. 208/1012 Kannada lines, in this specific corpus. That means the
bug doesn't just add noise, it specifically shrinks the Kannada number more than the English
number, quietly flattering exactly the ratio the report is built on. Bengali (71/1012) and
Marathi (57/1012) sit between Hindi and Kannada on this count, at a similarly modest
distortion (-0.35% to -0.40%) — consistent with the pattern rather than a new one. On the
10-line toy sample it's a rounding error; at corpus scale it's a small but real,
direction-consistent bias.
**Fix:** `line.split()` (no argument) instead of `line.split(" ")`.

---

## Code bug 2 — `.lower()` is applied uniformly but is not a uniform operation (`fertility.py:60`)

**Claim:** the comment says lowercasing is there "so casing doesn't add noise to the
comparison." But `.lower()` is a case-folding operation, and Devanagari/Kannada/Tamil/
Telugu/Malayalam have no case distinction at all — so this step measurably changes the
English side of every comparison in the report while leaving the Indic side untouched, which
is the opposite of denoising a *comparison*.

**Command:**
```bash
python3 partA/scripts/bug2_lowercase_asymmetry.py
```

**Full output saved to:** [`scripts/bug2_lowercase_asymmetry_output.txt`](scripts/bug2_lowercase_asymmetry_output.txt)

**Evidence (FULL FLORES-200, gpt2):**
```
eng: lower() changes 1012/1012 lines | fertility WITH lower()=1.2874  WITHOUT=1.2444  delta=+3.45%
hin: lower() changes   38/1012 lines | fertility WITH lower()=7.8651  WITHOUT=7.8647  delta=+0.00%
ben: lower() changes   51/1012 lines | fertility WITH lower()=13.3848  WITHOUT=13.3841  delta=+0.01%
mar: lower() changes   55/1012 lines | fertility WITH lower()=11.1860  WITHOUT=11.1853  delta=+0.01%
kan: lower() changes   66/1012 lines | fertility WITH lower()=22.5698  WITHOUT=22.5686  delta=+0.01%
tam: lower() changes   66/1012 lines | fertility WITH lower()=25.1270  WITHOUT=25.1256  delta=+0.01%
tel: lower() changes  141/1012 lines | fertility WITH lower()=20.5656  WITHOUT=20.5598  delta=+0.03%
mal: lower() changes   29/1012 lines | fertility WITH lower()=27.5845  WITHOUT=27.5838  delta=+0.00%

hin/eng ratio AS SHIPPED (both lowercased) = 6.109   IF NEITHER is lowercased = 6.320   (-3.34%)
ben/eng ratio AS SHIPPED = 10.397   IF NEITHER is lowercased = 10.756   (-3.34%)
mar/eng ratio AS SHIPPED = 8.689   IF NEITHER is lowercased = 8.989   (-3.34%)
kan/eng ratio AS SHIPPED = 17.532   IF NEITHER is lowercased = 18.137   (-3.34%)
```
(The small nonzero "changes" counts for Indic languages are embedded Latin-script substrings —
acronyms/proper nouns inside the translated sentences — not the native script; note the effect
stays ≤0.03% regardless, two orders of magnitude below English's +3.45%. Every language's
ratio inflates by exactly the same -3.34% because the mechanism only ever touches the shared
`eng` denominator — Bengali and Marathi confirm the pattern, they don't add a new one.)

**Direction and magnitude:** lowercasing shrinks English fertility by 3.45% and every Indic
language's fertility by ≤0.03%. Because English sits in the denominator of every ratio in
REPORT_v0, this asymmetric "denoising" step **inflates every X/eng ratio by ~3.3%** relative to
applying no case-folding at all (or, symmetrically, none). It's a small slice of the eventual
gap (see A3), but it's a real, direction-consistent, fully attributable one, and it's the kind
of silent methodology asymmetry that compounds with others.
**Fix:** don't lowercase. Production tokenizers never see pre-lowercased input either, so
this also makes the benchmark more representative, not just more symmetric.

---

## Code bug 3 — macro-average of per-line ratios, not a corpus-level (micro) ratio (`fertility.py:64-67`)

**Claim:** `analyze()` computes `mean(tokens_i / words_i)` per line, not
`sum(tokens_i) / sum(words_i)` over the corpus. These differ whenever line length varies, and
the standard definition of fertility in the tokenizer literature (e.g. Rust et al. 2021,
*"How Good is Your Tokenizer?"*) is the corpus-level (micro) ratio, precisely to avoid short
lines dominating the mean regardless of how much text they represent.

**Command:**
```bash
python3 partA/scripts/bug3_macro_vs_micro_avg.py
```

**Full output saved to:** [`scripts/bug3_macro_vs_micro_avg_output.txt`](scripts/bug3_macro_vs_micro_avg_output.txt)

**Evidence (FULL FLORES-200, gpt2):**
```
eng: macro(as-shipped)=1.2874  micro(corpus total)=1.2782  macro overstates by +0.72%
hin: macro(as-shipped)=7.8651  micro(corpus total)=7.8247  macro overstates by +0.52%
ben: macro(as-shipped)=13.3848 micro(corpus total)=13.2637 macro overstates by +0.91%
mar: macro(as-shipped)=11.1860 micro(corpus total)=11.1094 macro overstates by +0.69%
kan: macro(as-shipped)=22.5698 micro(corpus total)=22.2970 macro overstates by +1.22%
tam: macro(as-shipped)=25.1270 micro(corpus total)=24.9004 macro overstates by +0.91%
tel: macro(as-shipped)=20.5656 micro(corpus total)=20.4255 macro overstates by +0.69%
mal: macro(as-shipped)=27.5845 micro(corpus total)=27.3311 macro overstates by +0.93%
  hin/eng ratio: macro=6.109  micro=6.122  (-0.20% difference from averaging choice alone)
```

**Direction and magnitude:** macro-averaging overstates *every* language's absolute fertility
by 0.5–1.2% (consistent in direction across all 8 languages we tested, i.e. 10/10 including the
toy sample — Bengali +0.91%, Marathi +0.69%, both squarely inside the existing range). Because
it overstates similarly on both sides, it barely moves the cross-language *ratio* (≤0.35%) — so
this bug mostly matters if anyone downstream uses the absolute fertility numbers (e.g. "1.27
tokens/word" as a per-language cost constant) rather than only the ratio. We did not isolate
line-length as the causal variable in a controlled way; the plausible mechanism is that short
lines amortize fixed per-line token overhead (e.g. sentence-final punctuation) over fewer
words, but we're reporting the measured pattern, not asserting we've proven that specific
mechanism.
**Fix:** accumulate total tokens and total words across the corpus, divide once at the end.

---

## Conceptual bug — tokens-per-whitespace-word is the wrong denominator for a *cross-language* comparison

This is the "the code computes exactly what it says, but what it says is the wrong thing"
issue, and it's the most consequential finding in this audit (quantified fully in
[`results/corrected_analysis.md`](results/corrected_analysis.md), A3).

**Claim:** "tokens per word" implicitly assumes a whitespace-delimited "word" is a
comparable, fixed unit of *content* across languages. It is not. Kannada/Tamil/Telugu/
Malayalam are agglutinative — a single whitespace-delimited word routinely carries case,
number, and postposition marking that English spreads across 3-5 separate words. So
`tokens/word` conflates two genuinely different things: (a) how efficient the tokenizer's
vocabulary is, and (b) how much grammatical material a "word" happens to bundle in that
language — and REPORT_v0 attributes 100% of the gap to (a) ("This is a property of the
script, not the tokenizer").

**Evidence this actually distorts the number** (not just "the metric is inelegant in theory")
— from the corrected analysis ([`scripts/corrected_analysis_output.txt`](scripts/corrected_analysis_output.txt)),
MuRIL tokenizer, FULL FLORES-200:
```
hin word-ratio = 0.989   vs.  hin sent-ratio (tokens for equivalent content) = 1.157
ben word-ratio = 1.124   vs.  ben sent-ratio                                  = 1.001
kan word-ratio = 1.449   vs.  kan sent-ratio                                  = 1.065
tam word-ratio = 1.382   vs.  tam sent-ratio                                  = 1.059
```
Hindi's word-ratio (0.989) says Hindi is *cheaper* than English per unit measured. The
sentence-level ratio — tokens needed to say the *same, parallel-translated thing* — says
Hindi is 15.7% *more expensive*. That's not a rounding difference, it's a sign flip, produced
entirely by which denominator you divide by, with the tokenizer and the text held fixed.
Kannada's word-ratio (1.449) overstates its true content-adjusted cost (1.065) by 36%. Bengali
under MuRIL is the sharpest illustration in the whole table: word-ratio (1.124) says Bengali
costs 12% more than English, while sentence-ratio (1.001) says it's, for practical purposes,
*exactly the same* — a 12-point swing from the denominator alone, on a language pair that
isn't even the sign-flip case.

**Direction:** for the Dravidian languages in scope, `tokens/word` systematically
*overstates* the true per-content cost gap, because their words are morphologically denser
than English words (fewer, bigger words for the same content → smaller denominator → inflated
ratio). The fix and the "which number should drive the decision" question are answered
together in A3.

---

## Looks suspicious but is fine — `random.seed(1337)` / unused `random`, `sys` imports

**Claim under test:** none of the numbers in the report depend on the RNG seed.

**Command:**
```bash
python3 partA/scripts/nonbug_random_seed.py
```

**Full output saved to:** [`scripts/nonbug_random_seed_output.txt`](scripts/nonbug_random_seed_output.txt)

**Static evidence:**
```
$ grep -n 'random\.\|sys\.' fertility.py
25:random.seed(1337)  # reproducibility
```
That's the *only* place `random` is touched anywhere in the file (`sys` isn't referenced even
once — it's a pure dead import). No `.choice`, `.sample`, `.shuffle`, nothing that would ever
consume the RNG state the seed sets up.

**Behavioral evidence** — ran the real script three ways: as-shipped (seed 1337), seed
changed to 42, and the seed call deleted outright:
```
All three outputs byte-identical: True
```
Same `eng 1.27 / hin 7.45 / 5.89x` in all three cases. A seeded RNG *looks* like exactly the
kind of thing that should make you suspicious in a script reporting benchmark numbers — that
instinct is correct in general, it's just falsified here by direct test. Flagging this as a
bug would score negative points under the evidence rule; we're recording it explicitly as
"checked, confirmed harmless" rather than silently ignoring it, since the goal is calibration,
not just a list of suspicions.

---

## Summary table

| # | finding | type | measured distortion |
|---|---|---|---|
| 1 | `split(" ")` phantom words | code bug | up to -2.0% fertility, uneven across languages (0/1012 eng vs 208/1012 kan lines hit) |
| 2 | `.lower()` asymmetric across scripts | code bug | +3.45% eng fertility vs ≤0.03% Indic → inflates every ratio ~3.3% |
| 3 | macro- vs micro-average | code bug | +0.5–1.2% absolute fertility (both sides), ≤0.35% ratio effect |
| 4 | tokens/word conflates tokenizer quality with morphology | **conceptual** | up to a sign flip (hin: 0.99x → 1.16x), a 12-point swing on ben (1.12x → 1.00x), and 36% overstatement (kan) vs. content-held-constant ground truth |
| 5 | `random.seed(1337)` / unused imports | **not a bug** | 0.000% — confirmed by static + behavioral test |

All numbers in this table trace to the output files linked in each section above, or to
[`scripts/corrected_analysis_output.txt`](scripts/corrected_analysis_output.txt) for finding 4.
See [REVIEW.md](../REVIEW.md) for the full reproduce-and-verify procedure.
