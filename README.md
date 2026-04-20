# mathlib4-reviewer-memory

A retrieval-grounded "reviewer memory" tool for `leanprover-community/mathlib4`.

Given a hunk from a new mathlib4 PR, it searches an index of **~97k filtered
reviewer comments from ~15k closed PRs** (drawn from a raw scrape of ~158k
comments across ~35k closed PRs — bots, self-comments, and trivial comments
are filtered out before indexing) for the most similar `(past code, past comment)` pairs. There are two ways to use the result:

- **LLM mode** (default): GPT-5 reads the retrieved pairs and identifies
which past comments would also apply to your hunk — grounded in a specific
past PR + verbatim quote, allowed to say "none apply." This is what the
gallery below is built from.
- **Search mode** (`--search`): no LLM in the loop, no possibility of
hallucination. Returns the retrieved pairs verbatim, each tagged ✓ ACCEPTED
/ ✗ NOT ACCEPTED depending on whether the past PR was integrated into
mathlib. Useful as a transparent index lookup — and as a check against
"is my code similar to anything that already got rejected?".

## Why this exists

I'm an ML engineer with a math-olympiad background who recently got pulled
into Lean and the AI-for-formal-math space — it genuinely fascinates me.
Very quickly I hit the obvious newcomer question: mathlib4 has ~35k closed
PRs, so a lot of the mistakes I'm about to make have probably already been
made — and politely pointed out — by some reviewer in there. Could I
just... search that?

So I scraped them, filtered them down, embedded them, and put a search
index on top. That's the half of this repo I trust most: pure retrieval
over past `(code, reviewer-comment)` pairs, no LLM in the loop, no
hallucination surface.

The other half I half-expected to be a disaster: feeding the retrieved
pairs to GPT-5 and asking it to pick which past comments would *also*
apply to the new hunk. I assumed it would mostly invent plausible-sounding
nonsense. On a sample of currently-open PRs... it didn't, mostly. Some of
the suggestions it grounded in past comments were genuinely the kind of
thing a human reviewer would say; some were off-axis; some missed obvious
things. The [gallery](gallery/README.md) is 10 of those runs graded (2 WIN, 4 PARTIAL, 1 CORRECT-SILENT, 3 real failures) so you can
see the actual shape of it.

My Lean is early and my own WIN/MISS calls in the gallery are best-effort,
so this is half "here's what I built" and half "please tell me where I'm
wrong" — concrete asks in [Feedback](#feedback) at the bottom.

---

## Three ways to look at this repo

### 1. See what it produces (gallery)

The [gallery](gallery/README.md) is 10 currently-open mathlib4 PRs run
through the LLM-mode tool, side-by-side with what the human reviewer
actually wrote. If you have 5 minutes and know mathlib, the most useful
thing you can tell me is whether any of my WIN / PARTIAL / MISS calls on
those cards are wrong — that's the signal I'd actually act on.

### 2. I want to try it on my own hunk

```bash
uv sync                                          # or: pip install -e .
export OPENAI_API_KEY=sk-...                     # for the LLM mode (default)
export VOYAGE_API_KEY=pa-...                     # for query embedding
cat my_hunk.diff | python scripts/review_pr.py --file Mathlib/Path/To/File.lean
```

Two modes (described above):

```bash
# LLM mode — GPT-5 picks which past comments apply (gallery uses this):
cat my_hunk.diff | python scripts/review_pr.py --file Mathlib/X.lean

# Search mode — pure retrieval, no LLM, no hallucination:
cat my_hunk.diff | python scripts/review_pr.py --search --file Mathlib/X.lean

# Search mode + filter to past PRs that didn't make it into mathlib:
cat my_hunk.diff | python scripts/review_pr.py --search --not-accepted-only \
                                                --file Mathlib/X.lean
```

Search mode only needs `VOYAGE_API_KEY` (the query embedding); no OpenAI
key, no API cost beyond the embedding. To use Gemini instead of GPT-5 in
LLM mode: `pip install -e '.[gemini]'`, set `GEMINI_API_KEY`, pass
`--provider gemini`. Pass `--self-test` to run on a held-out query without
preparing a hunk, or `--json` for structured output.

> **Heads up:** this requires the embedding index
> (`data/index/rag_vectors.npz` and `data/curated/mathlib4/*.parquet`),
> which is not committed here due to size (~1 GB). See
> [Dataset & reproducing the index](#dataset--reproducing-the-index) below
> to grab a copy or rebuild it locally.

### 3. I want the methodology, the eval numbers, or the dataset

**Polished reports** (Markdown, ready to skim):

- [data/eval/llm_judge_report.md](data/eval/llm_judge_report.md) — held-out
retrieval evaluated by an LLM judge (GPT-5) with a `0` / `1` / `2` rubric:
Hit@K table, label distribution, similarity-vs-label breakdown, per-query
details. **n = 20 queries × top-10 retrieved = 200 judgments.**
- [data/eval/heldout_inspection_report.md](data/eval/heldout_inspection_report.md)
— hand-inspection format of those same 20 held-out queries: each one's
full diff hunk, the ground-truth reviewer comment, and the top-10
retrieved comments with similarity + lexical-F1 scores. ~85 KB,
scrollable; this is the file to read if you want to get a feel for what
retrieval is actually doing.
- [data/eval/prompt_ablation_report.md](data/eval/prompt_ablation_report.md)
— comparison of two prompt versions (v1 vs v2) on 6 cases, with token
usage, cost numbers, and per-case win/loss notes.

> The gallery uses the v3.1 prompt, which was tuned on the same 20 open
> PRs the gallery is drawn from — so the gallery is "best-current-prompt
> on tuned-for PRs", not a clean held-out test. The clean number is
> `llm_judge_report.md` above. Longer note on this in the
> [gallery README](gallery/README.md#a-note-on-prompt-tuning-please-read-before-grading).

**Source:**

- Prompts (4 versions, v1 → v3.1): [src/product/review_assistant.py](src/product/review_assistant.py)
- Pipeline (scrape → normalize → embed → retrieve): [src/pipeline/](src/pipeline/) + [scripts/](scripts/)
- Per-case prompt + completion transcripts: [data/eval/transcripts/](data/eval/transcripts/)

---

## Dataset & reproducing the index

The curated parquets (~158k review comments + linked code chunks across
~35k closed PRs) and the embedding index aren't committed (~1 GB). Two
options:

- **Grab a copy.** Open an issue or ping me and I'll package it as a
  Hugging Face Dataset (or a tarball). Easier to do once than to have
  everyone re-scrape.
- **Rebuild it yourself:**
  ```bash
  export GITHUB_TOKEN=ghp_...
  python scripts/scrape_mathlib4.py --mode backfill   # ~few hours, GitHub-API-bound
  python scripts/build_rag_index_data.py
  python scripts/embed_rag_corpus.py                  # ~1 hour, OpenAI embeddings
  ```

The eval outputs and gallery here were produced from a snapshot taken on
2026-04-18.

---

## Feedback

Three things I'd most like to hear from people who know mathlib:

1. **Are my WIN / PARTIAL / MISS calls in the gallery wrong?** My Lean
   judgment is the weakest link in this whole pipeline, so corrections
   here are the most useful.
2. **Is the LLM-mode output actually useful, or am I being charmed by
   plausible-sounding text?** "Technically not wrong but a real reviewer
   would never say this" is exactly what I can't catch myself.
3. **Is the underlying dataset worth releasing as a Hugging Face Dataset?**
   Happy to package it once if anyone has a use for it.

Open an issue, ping me on Zulip, or reach out directly. One-line "card #4
is wrong because X" is great; "this whole framing is off, here's why" is
also welcome.

License: MIT.
