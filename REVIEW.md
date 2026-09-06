# REVIEW.md

One-stop summary + exact reproduction steps for the whole submission. For narrative/reasoning,
see [`NOTEBOOK.md`](NOTEBOOK.md) (chronological log) and [`AI_USAGE.md`](AI_USAGE.md) (honest
AI-usage accounting). This file is deliberately just facts and commands.

## What was done

### Part A — tokenizer audit

Built a real eval corpus (FLORES-200 devtest, 1012 parallel sentences × 8 languages: English,
Hindi, Bengali, Marathi, Kannada, Tamil, Telugu, Malayalam — see
[`partA/corpus/README.md`](partA/corpus/README.md)). Audited `fertility.py` and found three
code bugs (a `split(" ")` double-space bug that hits Kannada far harder than English, an
asymmetric `.lower()` that only ever touches the English side of every ratio, and macro- vs.
micro-averaging) plus one conceptual bug (tokens/word conflates tokenizer quality with
cross-lingual morphological density) — each isolated with a before/after measurement in
[`partA/findings.md`](partA/findings.md). Also confirmed `random.seed(1337)` is genuinely
inert rather than assuming it. Re-ran the corrected fertility analysis across 4 tokenizers × 4
denominators × 8 languages
([`partA/results/corrected_analysis.md`](partA/results/corrected_analysis.md)): REPORT_v0's
"Hindi costs 6×, it's a property of the script" claim does not survive a second tokenizer — the
real gap with an Indic-focused tokenizer (MuRIL/NLLB-200) is ~1.0×-1.5×, not 6-15×, but a
modern general-purpose multilingual tokenizer (Qwen2.5) still shows 4.4×-7.2×, meaning the gap
size tracks how much Indic-language data went into a given tokenizer's training, not just
whether it's "multilingual." Recommendation memo in [`partA/memo.md`](partA/memo.md).

### Part B — capacity reconciliation

Computed KV-cache bytes/token exactly (112 KiB/token) and the max concurrent 4096-token
sequences a single L4-24GB can hold (~28-29) from the model spec alone, then checked that
prediction against `bench_log.csv` — it lines up with exactly where the log's preemption count
goes from 0 to nonzero. Reverse-engineered what the log's `reported_tok_s` column actually
counts (prefill + decode tokens mixed together, confirmed exactly on all 13 rows) and used that
to derive the "honest goodput" of the batch-24 long-prompt row two independent ways (~201
tok/s, not the reported 1607 tok/s), showing the report's "batch 48 → ~3200 tok/s" projection
is wrong in direction as well as magnitude (batch 48 measures *worse* than batch 24). Full
derivation in [`partB/analysis.md`](partB/analysis.md).

### Part C — decision memo

No code — a constraint-driven recommendation memo
([`partC/memo.md`](partC/memo.md)) for making assistant replies sound casual in six Indic
languages under a tight compute/reviewer/timeline budget. Recommends a small inference-time
rewriter (staged behind a zero-cost prompting probe) over an SFT pass on the main model, mainly
because the available native-speaker reviewer only covers 2 of the 6 required languages —
argued through with explicit assumptions, back-of-envelope arithmetic, a numeric success
metric, a kill criterion, and a day-1 experiment.

## Reproduce everything, in order

### Setup (once)

```bash
cd assignment
python3.11 -m venv .venv          # 3.11, not 3.14 -- sentencepiece/tokenizers wheels
source .venv/bin/activate         # aren't reliably available for cp314 as of this writing
pip install -r requirements.txt
```

`partB/capacity_calc.py` needs none of this — it's pure stdlib and runs with any `python3`.

### Part A

```bash
# A1 -- build the corpus (already checked into partA/corpus/*.txt; only needed to rebuild
# from scratch, which first needs raw_downloads/ -- see README.md "Regenerating the corpus")
python3 partA/scripts/build_corpus.py
# -> partA/scripts/build_corpus_output.txt

# A2 -- audit fertility.py (4 independent scripts, run in any order)
python3 partA/scripts/bug1_double_space.py
# -> partA/scripts/bug1_double_space_output.txt
python3 partA/scripts/bug2_lowercase_asymmetry.py
# -> partA/scripts/bug2_lowercase_asymmetry_output.txt
python3 partA/scripts/bug3_macro_vs_micro_avg.py
# -> partA/scripts/bug3_macro_vs_micro_avg_output.txt
python3 partA/scripts/nonbug_random_seed.py
# -> partA/scripts/nonbug_random_seed_output.txt

# A3 -- corrected analysis, 4 tokenizers x 4 denominators x 8 languages
# (downloads muril-base-cased, nllb-200-distilled-600M, qwen2.5-0.5B from HF on first run)
python3 partA/scripts/corrected_analysis.py
# -> partA/scripts/corrected_analysis_output.txt
# -> partA/results/corrected_analysis.json (regenerated fresh by the script every run,
#    never hand-edited)
```

`partA/scripts/_common.py` is a shared import-only helper (no `__main__`, no `print`), not a
standalone script — see [`partA/scripts/_common_output.txt`](partA/scripts/_common_output.txt)
for confirmation it produces empty output when run directly, and why that's expected rather
than an oversight.

### Part B

```bash
python3 partB/capacity_calc.py
# -> partB/capacity_calc_output.txt
```

No corpus dependency — reads only `original/bench/bench_log.csv` and the constants transcribed
from `original/bench/model_spec.md` at the top of the script.

### Part C

No code to run — [`partC/memo.md`](partC/memo.md) is a standalone reasoning memo.

## Verifying a quoted number

Every `.md` file in this repo that quotes a number names the exact `*_output.txt` file it came
from, right next to the quote (search any `.md` for "output saved to" or "output.txt" to find
every such pointer). To verify one:

1. Open the named `*_output.txt` file and find the number.
2. Or regenerate it yourself: run the corresponding command above and diff the new file against
   the checked-in one (`diff partA/scripts/bug1_double_space_output.txt <(python3
   partA/scripts/bug1_double_space.py)`, for example) — it should be byte-identical, since
   every script here is deterministic (no sampling, no unseeded randomness; see `findings.md`'s
   non-bug section for why the one seed in this codebase doesn't affect anything anyway).

If a number in a `.md` file does *not* trace to an `*_output.txt` file this way, that's a bug
in the submission — flag it.
