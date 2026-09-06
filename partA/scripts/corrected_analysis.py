#!/usr/bin/env python3
"""
A3 -- corrected cross-language fertility analysis.

Fixes applied relative to fertility.py (see partA/findings.md for the
evidence behind each):
  - split() instead of split(" ")                      [bug 1]
  - no forced .lower()                                  [bug 2 -- see note below]
  - micro (corpus-total) average instead of macro        [bug 3]
  - four denominators instead of one, computed on the
    SAME parallel corpus so they are directly comparable  [conceptual bug]

Note on casing: we deliberately do NOT lowercase. A production tokenizer
never sees pre-lowercased user input, and .lower() is asymmetric across
scripts (bug 2), so leaving case as-is is both more realistic and more
symmetric. NFC normalization (already correct in the original script)
is kept.

Tokenizers: gpt2 (tiktoken, English-centric BPE -- what the original
report used) vs muril-base-cased (WordPiece, purpose-built for English +
Indian languages) vs nllb-200-distilled-600M (SentencePiece unigram,
200-language MT model) -- two independent, unrelated multilingual
tokenizers, so the comparison isn't an artifact of picking one
alternative.
"""
import json
import unicodedata
import regex
import pathlib
from _common import CORPUS_FULL

LANGS = ["eng", "hin", "ben", "mar", "kan", "tam", "tel", "mal"]

TOKENIZERS = {}


def _gpt2():
    import tiktoken
    enc = tiktoken.get_encoding("gpt2")
    return enc.encode


def _hf(repo_id):
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(repo_id)
    return lambda s: tok.encode(s, add_special_tokens=False)


TOKENIZER_LOADERS = {
    "gpt2": _gpt2,
    "muril-base-cased": lambda: _hf("google/muril-base-cased"),
    "nllb-200-distilled-600M": lambda: _hf("facebook/nllb-200-distilled-600M"),
    "qwen2.5": lambda: _hf("Qwen/Qwen2.5-0.5B"),
}


def read_lines(path):
    lines = []
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            line = unicodedata.normalize("NFC", line)
            lines.append(line)
    return lines


def grapheme_len(s):
    return len(regex.findall(r"\X", s))


def corpus_totals(lines, encode):
    tot_tokens = tot_words = tot_graphemes = tot_bytes = 0
    for line in lines:
        tot_tokens += len(encode(line))
        tot_words += len(line.split())
        tot_graphemes += grapheme_len(line)
        tot_bytes += len(line.encode("utf-8"))
    return {
        "tokens": tot_tokens,
        "words": tot_words,
        "graphemes": tot_graphemes,
        "bytes": tot_bytes,
        "sentences": len(lines),
    }


def main():
    corpora = {lang: read_lines(CORPUS_FULL / f"{lang}.txt") for lang in LANGS}
    n_sent = {lang: len(corpora[lang]) for lang in LANGS}
    assert len(set(n_sent.values())) == 1, f"corpus not parallel: {n_sent}"

    all_results = {}
    for tok_name in TOKENIZER_LOADERS:
        print(f"\n{'='*90}\nTOKENIZER: {tok_name}\n{'='*90}")
        encode = TOKENIZER_LOADERS[tok_name]()
        results = {}
        for lang in LANGS:
            totals = corpus_totals(corpora[lang], encode)
            results[lang] = totals
        all_results[tok_name] = results

        header = f"{'lang':<6}{'tokens':>10}{'tok/word':>12}{'tok/graph':>12}{'tok/byte':>12}{'tok/sent':>12}"
        print(header)
        print("-" * len(header))
        for lang in LANGS:
            t = results[lang]
            tok_word = t["tokens"] / t["words"]
            tok_graph = t["tokens"] / t["graphemes"]
            tok_byte = t["tokens"] / t["bytes"]
            tok_sent = t["tokens"] / t["sentences"]
            print(f"{lang:<6}{t['tokens']:>10}{tok_word:>12.3f}{tok_graph:>12.4f}{tok_byte:>12.4f}{tok_sent:>12.2f}")

        print(f"\n-- ratio to eng, by denominator ({tok_name}) --")
        base = results["eng"]
        print(f"{'lang':<6}{'word-ratio':>12}{'graph-ratio':>12}{'byte-ratio':>12}{'sent-ratio':>12}")
        for lang in LANGS[1:]:
            t = results[lang]
            r_word = (t["tokens"] / t["words"]) / (base["tokens"] / base["words"])
            r_graph = (t["tokens"] / t["graphemes"]) / (base["tokens"] / base["graphemes"])
            r_byte = (t["tokens"] / t["bytes"]) / (base["tokens"] / base["bytes"])
            r_sent = (t["tokens"] / t["sentences"]) / (base["tokens"] / base["sentences"])
            print(f"{lang:<6}{r_word:>12.3f}{r_graph:>12.3f}{r_byte:>12.3f}{r_sent:>12.3f}")

    out = pathlib.Path(__file__).resolve().parents[1] / "results" / "corrected_analysis.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(all_results, indent=2))
    print(f"\nRaw totals written to {out}")


if __name__ == "__main__":
    main()
