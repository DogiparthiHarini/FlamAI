# Tokenizer & serving audit — submission

Start with [`REVIEW.md`](REVIEW.md) for a summary + the exact reproduce-everything command
list, [`NOTEBOOK.md`](NOTEBOOK.md) for the chronological log, and [`AI_USAGE.md`](AI_USAGE.md)
for the honest AI-usage accounting. This README is just setup + a map of what to run.

## Setup

```bash
python3.11 -m venv .venv   # 3.11, not 3.14 -- as of this writing, sentencepiece/tokenizers
source .venv/bin/activate  # don't reliably ship precompiled wheels for cp314 yet
pip install -r requirements.txt
```

`partB/capacity_calc.py` is pure stdlib (`csv`, `pathlib`) — runs with any `python3`, no venv
needed.

`original/` is a copy of the starter kit inputs (`fertility.py`, `REPORT_v0.md`,
`bench/model_spec.md`, `bench/bench_log.csv`, `corpus_sample/`) so this repo is self-contained
and doesn't depend on the original `starter_kit/` directory being present alongside it —
`partA/scripts/_common.py` and `partB/capacity_calc.py` both read from it directly. Kept
deliberately, not accidental duplication; see REVIEW.md.

## Map

| ask | where | run | output saved to |
|---|---|---|---|
| A1 corpus | [`partA/corpus/`](partA/corpus/README.md) | `python3 partA/scripts/build_corpus.py` (needs `raw_downloads/`, see below) | `partA/scripts/build_corpus_output.txt` |
| A2 audit | [`partA/findings.md`](partA/findings.md) | `python3 partA/scripts/{bug1_double_space,bug2_lowercase_asymmetry,bug3_macro_vs_micro_avg,nonbug_random_seed}.py` | `partA/scripts/*_output.txt` |
| A3 corrected analysis | [`partA/results/corrected_analysis.md`](partA/results/corrected_analysis.md) | `python3 partA/scripts/corrected_analysis.py` (downloads 3 HF tokenizers on first run) | `partA/scripts/corrected_analysis_output.txt` |
| A4 memo | [`partA/memo.md`](partA/memo.md) | — | (cites the A3 output file) |
| B1-B4 | [`partB/analysis.md`](partB/analysis.md) | `python3 partB/capacity_calc.py` | `partB/capacity_calc_output.txt` |
| C | [`partC/memo.md`](partC/memo.md) | — | (no code) |

All A2/A3 scripts run from anywhere (paths are resolved relative to the script file, not cwd).
Every number quoted in every `.md` file in this repo is copied from one of these saved
`*_output.txt` files — see REVIEW.md for how to verify that yourself.

## Corpus

8 languages as of the 2026-09-06 revision: English, Hindi, Bengali, Marathi, Kannada, Tamil,
Telugu, Malayalam — matching the six languages Part C's product ask targets, plus English and
Hindi. See [NOTEBOOK.md](NOTEBOOK.md), "Revision — 2026-09-06," for what changed when Bengali
and Marathi were added and why.

## Regenerating the corpus from scratch

The built corpus (`partA/corpus/*.txt`, 1012 parallel sentences × 8 languages) is already
checked in, so nothing downstream needs this step. To rebuild it from the original source:

```bash
mkdir -p raw_downloads && cd raw_downloads
curl -L -o flores200_dataset.tar.gz https://dl.fbaipublicfiles.com/nllb/flores200_dataset.tar.gz
tar -xzf flores200_dataset.tar.gz
cd ..
python3 partA/scripts/build_corpus.py
```

## What's not in the zip

`raw_downloads/` (the full 200-language FLORES tarball, ~100MB extracted), `.venv/`, and
`.hf_cache/` (downloaded tokenizer files) are excluded as regenerable/bulky. Everything they
produce that's actually used downstream (`partA/corpus/*.txt`, the analysis outputs) is checked
in.
