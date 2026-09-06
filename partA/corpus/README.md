# A1 — Eval corpus

## What it is

[FLORES-200](https://github.com/facebookresearch/flores/tree/main/flores200) `devtest` split,
downloaded directly from `https://dl.fbaipublicfiles.com/nllb/flores200_dataset.tar.gz`
(public, no gating/auth needed — see [NOTEBOOK.md](../../NOTEBOOK.md) for the exact command).
Released by Meta/FAIR under **CC-BY-SA 4.0**.

**Eight languages** (expanded from six on 2026-09-06, see [NOTEBOOK.md](../../NOTEBOOK.md)
"Revision — 2026-09-06"), all parallel (same 1012 sentences, sentence-aligned, same order in
every file):

| code | language | script | family |
|---|---|---|---|
| eng | English | Latin | Germanic |
| hin | Hindi | Devanagari | Indo-Aryan |
| ben | Bengali | Bengali | Indo-Aryan |
| mar | Marathi | Devanagari | Indo-Aryan |
| kan | Kannada | Kannada | **Dravidian** |
| tam | Tamil | Tamil | **Dravidian** |
| tel | Telugu | Telugu | **Dravidian** |
| mal | Malayalam | Malayalam | **Dravidian** |

That's English + Hindi + all four major Dravidian languages, i.e. 6 languages against the
assignment's "at least 4, including English, Hindi, and two Dravidian" floor for A1 — plus
Bengali and Marathi, added specifically so this corpus also covers all six of the languages
Part C's product ask targets (Hindi, Kannada, Tamil, Telugu, Bengali, Marathi), not just four
of them. Malayalam stays in even though Part C doesn't ask about it, since it satisfies A1's
own Dravidian-coverage requirement and removing it would have thrown away real evidence for no
benefit.

Built by [`../scripts/build_corpus.py`](../scripts/build_corpus.py):

```bash
python3 partA/scripts/build_corpus.py
```

## Size

**1012 sentences per language** (8096 sentence-instances total across 8 languages), vs. the
~10-sentence toy files in `original/corpus_sample/`. That's the full `devtest` split; I didn't
subsample — tokenizing 1012×8 sentences with 4 tokenizers runs in well under a minute (see
[`../scripts/corrected_analysis_output.txt`](../scripts/corrected_analysis_output.txt)), so
there was no reason to throw away statistical power.

## Domain (from `metadata_devtest.tsv`)

| domain | sentences |
|---|---|
| wikinews | 341 |
| wikibooks | 351 |
| wikivoyage | 320 |

All encyclopedic/journalistic/travel-guide register, professionally translated by native
speakers from the same 842 English source articles, with QA per the FLORES paper. This is
**written, edited, formal-register text** — the same register REPORT_v0's 10-sentence sample
happened to resemble.

## Preprocessing

None beyond what `fertility.py` itself does (NFC normalization). I deliberately did **not**
re-clean or filter the corpus — the double-spaces and other artifacts it contains (see
[`../findings.md`](../findings.md), bug 1) are real properties of this data source, and a
"real eval corpus" should surface that, not paper over it before the tokenizer ever sees it.

## What this corpus cannot tell you

- **Register mismatch with the actual product ask.** Part C of this assignment is about making
  chat replies sound *casual*. FLORES is Wikipedia-register text — formal, complete sentences,
  no code-switching, no chat abbreviations, no emoji. Fertility measured here is a reasonable
  proxy for *document/RAG-style* traffic, but will systematically **understate** tokens/request
  for short, fragmentary, emoji- and code-mixed chat messages, and probably understate fertility
  gaps that show up specifically on informal text (informal Indic text leans more on
  transliteration and script-mixing, which tokenizers handle even less consistently).
- **1012 sentences is not small, but it's not infinite either.** Per-language token totals
  (gpt2) range from 27,044 (eng) to 420,171 (tam) — see
  [`../scripts/corrected_analysis_output.txt`](../scripts/corrected_analysis_output.txt). No
  bootstrap/confidence interval is computed in `corrected_analysis.py` — treat our third
  significant figure as illustrative precision from a 1012-sentence sample, not a
  proven-significant digit.
- **One source domain, one translation direction (all translated from English).**
  "Translationese" is a known effect: translated text tends to structurally mirror the source
  language more than organic text would. That plausibly *compresses* the true fertility gap
  between English and the target languages, if anything — organically-written Kannada/Tamil
  text is not obligated to track English sentence structure the way a translation is.
  We cannot tell from this corpus alone how large that effect is.
- **No dialogue, no domain-specific product vocabulary** (support tickets, app UI strings,
  whatever this "assistant" actually serves). If the real traffic is dominated by short
  transactional queries, this corpus's sentence-level statistics don't directly transfer —
  see the A4 memo's monitoring recommendation for how to close that gap in production rather
  than in eval.
