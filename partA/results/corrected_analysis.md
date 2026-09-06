# A3 — Corrected cross-language analysis

**Command:**
```bash
python3 partA/scripts/corrected_analysis.py
```
**Full output saved to:** [`../scripts/corrected_analysis_output.txt`](../scripts/corrected_analysis_output.txt)
(raw per-language totals also written to [`corrected_analysis.json`](corrected_analysis.json),
regenerated fresh by the script itself, never hand-edited).

Corpus: FLORES-200 devtest, 1012 parallel sentences/language, **8 languages** as of the
2026-09-06 revision — eng, hin, ben, mar, kan, tam, tel, mal (see [A1](../corpus/README.md)
and [NOTEBOOK.md](../../NOTEBOOK.md)). Fixes applied vs. `fertility.py`: `split()` not
`split(" ")` (bug 1), no forced `.lower()` (bug 2), micro/corpus-total average not macro
(bug 3) — see [`findings.md`](../findings.md).

## Four tokenizers

| tokenizer | family | what it represents |
|---|---|---|
| `gpt2` (tiktoken) | byte-level BPE | what REPORT_v0 actually used — English/Latin-web-text-trained |
| `qwen2.5` (0.5B) | byte-level BPE, decoder-only LLM | a modern, genuinely multilingual (~29 languages) production-grade LLM tokenizer — Chinese/English-centric training mix |
| `facebook/nllb-200-distilled-600M` | SentencePiece unigram | 200-language MT tokenizer, explicitly balanced multilingual sampling |
| `google/muril-base-cased` | WordPiece | purpose-built for English + 16 Indian languages (all 4 Dravidian languages here, plus Bengali and Marathi) |

I added `qwen2.5` after the first pass with only 3 tokenizers (see [NOTEBOOK.md](../../NOTEBOOK.md)
§5) specifically to test a modern, general-purpose, genuinely-multilingual *decoder* LLM
tokenizer, not just encoder-style (WordPiece/BERT) tokenizers built with Indic languages as an
explicit design goal. That test changed the conclusion in an important way — see Finding 2.

## Four denominators, ratio to English (X/eng) — all 8 languages × 4 tokenizers

Every number below is copied from [`corrected_analysis_output.txt`](../scripts/corrected_analysis_output.txt), not retyped from memory.

| lang | tokenizer | word-ratio | grapheme-ratio | byte-ratio | **sentence-ratio** |
|---|---|---:|---:|---:|---:|
| hin | gpt2 | 6.34 | 11.39 | 2.91 | **7.42** |
| hin | qwen2.5 | 3.77 | 6.78 | 1.73 | **4.42** |
| hin | nllb-200 | 1.04 | 1.86 | 0.47 | **1.21** |
| hin | muril | 0.99 | 1.78 | 0.45 | **1.16** |
| ben | gpt2 | 10.79 | 15.52 | 3.64 | **9.61** |
| ben | qwen2.5 | 5.64 | 8.12 | 1.90 | **5.03** |
| ben | nllb-200 | 1.43 | 2.06 | 0.48 | **1.28** |
| ben | muril | 1.12 | 1.62 | 0.38 | **1.00** |
| mar | gpt2 | 9.03 | 12.91 | 2.92 | **7.86** |
| mar | qwen2.5 | 5.31 | 7.59 | 1.72 | **4.62** |
| mar | nllb-200 | 1.45 | 2.07 | 0.47 | **1.26** |
| mar | muril | 1.22 | 1.75 | 0.40 | **1.06** |
| kan | gpt2 | 18.48 | 19.84 | 4.78 | **13.58** |
| kan | qwen2.5 | 9.41 | 10.11 | 2.44 | **6.92** |
| kan | nllb-200 | 1.85 | 1.99 | 0.48 | **1.36** |
| kan | muril | 1.45 | 1.56 | 0.38 | **1.07** |
| tam | gpt2 | 20.28 | 20.56 | 4.87 | **15.54** |
| tam | qwen2.5 | 7.98 | 8.09 | 1.92 | **6.11** |
| tam | nllb-200 | 1.85 | 1.87 | 0.44 | **1.42** |
| tam | muril | 1.38 | 1.40 | 0.33 | **1.06** |
| tel | gpt2 | 16.77 | 22.35 | 4.84 | **12.97** |
| tel | qwen2.5 | 9.04 | 12.05 | 2.61 | **6.99** |
| tel | nllb-200 | 1.72 | 2.29 | 0.50 | **1.33** |
| tel | muril | 1.56 | 2.07 | 0.45 | **1.20** |
| mal | gpt2 | 22.24 | 25.19 | 4.86 | **15.16** |
| mal | qwen2.5 | 10.60 | 12.01 | 2.32 | **7.23** |
| mal | nllb-200 | 2.19 | 2.48 | 0.48 | **1.49** |
| mal | muril | 1.74 | 1.97 | 0.38 | **1.18** |

## Finding 1: the "6× / property-of-the-script" claim does not survive a second tokenizer

REPORT_v0: *"Root cause: Hindi simply has more Unicode characters per word, so any tokenizer
will struggle. This is a property of the script, not the tokenizer."*

That is a falsifiable empirical claim, and it's false as stated. Same text, same
sentence-ratio metric, four tokenizers, all 7 non-English languages now in scope:

| | hin | ben | mar | kan | tam | tel | mal |
|---|---:|---:|---:|---:|---:|---:|---:|
| gpt2 | 7.42× | 9.61× | 7.86× | 13.58× | 15.54× | 12.97× | 15.16× |
| qwen2.5 | 4.42× | 5.03× | 4.62× | 6.92× | 6.11× | 6.99× | 7.23× |
| nllb-200 | 1.21× | 1.28× | 1.26× | 1.36× | 1.42× | 1.33× | 1.49× |
| muril | 1.16× | **1.00×** | 1.06× | 1.07× | 1.06× | 1.20× | 1.18× |

Swapping only the tokenizer — same corpus, same script — moves Kannada's measured cost from
"13.6× worse" to "1.07× worse," and moves Bengali all the way to **1.00×, i.e. no measurable
gap at all** under MuRIL. That range is overwhelmingly a property of **which tokenizer's
vocabulary you picked**, not an inherent property of any of these scripts. The report's
root-cause claim is wrong.

## Finding 2: "use a multilingual tokenizer" is not, by itself, the fix — and this only shows up because a 4th tokenizer was added

The first pass of this analysis used only `gpt2`, `nllb-200`, and `muril`, and both
multilingual alternatives happened to land close to parity (1.0×-1.5×). That would support a
clean but **too-strong** story: "swap gpt2 for any competent multilingual tokenizer and the
gap nearly disappears." Adding `qwen2.5` — a modern, widely-deployed, genuinely multilingual
LLM tokenizer, not a legacy English-only one — breaks that story: it still shows a **4.4×-7.2×**
sentence-ratio gap across all 7 non-English languages, roughly halfway between gpt2 and the
Indic-focused tokenizers, not anywhere near parity.

The pattern across all four is monotonic and explains why: **the size of the gap tracks how
much a tokenizer's training data explicitly weighted Indic-language text**, not just whether
it's "multilingual" in general:
- `gpt2` — essentially English-only training data → worst (7.4×-15.5×)
- `qwen2.5` — broad multilingual coverage (~29 languages), but a Chinese/English-centric
  training mix with Indic languages as a smaller slice → real improvement, real residual gap
  (4.4×-7.2×)
- `nllb-200` — 200-language *MT* corpus with deliberately balanced per-language sampling →
  close to parity (1.2×-1.5×)
- `muril` — Indian languages named in the design goal → closest to parity (1.0×-1.2×,
  Bengali reaching exact parity)

**This matters for the recommendation in A4:** it is not safe to tell leadership "just deploy
with a multilingual model and this problem goes away." A team that swaps gpt2 for a
general-purpose multilingual LLM tokenizer (plausible — that's most of what "multilingual LLM"
means in practice right now) could still be carrying a genuine 4-7× cost gap and believe,
incorrectly, that it's been fixed. The only way to know is to measure the fertility of the
*specific* tokenizer under consideration — which is exactly what `corrected_analysis.py` does,
and exactly the kind of check REPORT_v0 skipped by testing only one tokenizer.

## Finding 3: which denominator you pick can flip the qualitative conclusion, not just the number

MuRIL's Hindi row: **word-ratio = 0.99** (Hindi looks *cheaper* than English) vs.
**sentence-ratio = 1.16** (Hindi costs 16% more for the same content) — the denominator alone
flips the sign. MuRIL's Bengali row is the sharpest example in the whole table: **word-ratio =
1.12** (Bengali looks 12% *more expensive*) vs. **sentence-ratio = 1.00** (no real gap at all)
— a 12-point swing with no sign flip, on the language that turns out to be closest to true
parity. Kannada/muril: word-ratio (1.45) overstates the true content-adjusted cost (1.07,
sentence-ratio) by 36%. This is the conceptual bug from `findings.md`: Dravidian/Indo-Aryan
languages pack more grammatical material into each whitespace "word," so dividing by word
count mixes morphological density into what's supposed to be a tokenizer-efficiency number.

## What should hold constant across languages — and which number should drive the decision

A routing/cost decision needs: *for the same request (same amount of user-intended content),
how many tokens does language X cost vs. language Y?* The denominator must hold **content**,
not any particular surface unit, constant. Checking each candidate against that bar:

- **per word** — fails. A "word" is 1 morpheme's worth of content in English and 3-5
  morphemes' worth in Kannada/Tamil/Telugu/Malayalam (agglutinative morphology); Bengali and
  Marathi sit somewhere in between. Confirmed above: it can flip the sign of the conclusion or
  swing it by double digits.
- **per grapheme cluster** — fails, in the *opposite* direction. Brahmic-script graphemes
  (aksharas) are syllable-sized and pack more phonetic content than one Latin letter, so
  counting graphemes 1:1 across scripts *overstates* the Indic-language gap (grapheme-ratio is
  the largest number in every row above). It's a genuine improvement over raw codepoints —
  `len(line)` in `fertility.py` overcounts Devanagari/Kannada "characters" because conjuncts
  are multiple codepoints per grapheme (verified: "ನಮಸ್ತೆ"-style strings are ~5 codepoints/4
  graphemes in our checks) — but it's still a script-complexity artifact, not a content measure.
- **per UTF-8 byte** — fails for the same reason in reverse. Devanagari/Bengali/Kannada/Tamil/
  Telugu/Malayalam codepoints are 3 bytes in UTF-8 vs. 1 byte for ASCII English, which is why
  byte-ratio is the *smallest* number in every row (sometimes <0.5, i.e. "cheaper" than
  English) — purely an artifact of how Unicode assigns code points to scripts, unrelated to
  tokenizer or content.
- **per parallel sentence** — holds content constant *directly*, because FLORES-200's
  sentences are professional, meaning-matched translations of the same 1012 source sentences.
  It's the only one of the four that isn't mediated by a script-dependent proxy unit.

**Recommendation: tokens-per-parallel-sentence (equivalently, total corpus tokens, since
sentence count is fixed) is the number that should drive the routing/cost decision,** computed
on the *specific* tokenizer under consideration (Finding 2) — not assumed from its general
multilingual reputation. Use word/grapheme/byte ratios as *diagnostics* for **why** a gap
exists (tokenizer vocabulary gap vs. script-encoding artifact vs. morphology), never as the
headline decision number.

**Caveat for production use:** you only get "per parallel sentence" when you *have* parallel
content, which eval sets provide and live traffic does not — a Kannada support query and an
English support query aren't translations of each other. That's why the A4 memo recommends
monitoring **tokens per UTF-8 byte of input** in production: it's the roughest of the four
proxies for "content," but it's the only one of the four you can compute on ordinary,
non-parallel live traffic without an MT-quality parallel corpus alongside it.
