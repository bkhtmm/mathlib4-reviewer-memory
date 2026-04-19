# mathlib4-reviewer-memory

A retrieval-grounded "reviewer memory" tool for `leanprover-community/mathlib4`.

Given a hunk from a new mathlib4 PR, it searches an index of **~97k filtered
reviewer comments from ~15k closed PRs** (drawn from a raw scrape of ~158k
comments across ~35k closed PRs — bots, self-comments, and trivial comments
are filtered out before indexing) for the most similar `(past code, past
comment)` pairs. There are two ways to use the result:

- **LLM mode** (default): GPT-5 reads the retrieved pairs and identifies
  which past comments would also apply to your hunk — grounded in a specific
  past PR + verbatim quote, allowed to say "none apply." This is what the
  gallery below is built from.
- **Search mode** (`--search`): no LLM in the loop, no possibility of
  hallucination. Returns the retrieved pairs verbatim, each tagged ✓ ACCEPTED
  / ✗ NOT ACCEPTED depending on whether the past PR was integrated into
  mathlib. Useful as a transparent index lookup — and as a check against
  "is my code similar to anything that already got rejected?".

## A note on context

I'm an ML engineer with a math background, currently learning Lean and
following the AI-for-formal-math space. I built this as an experiment, not
as a mathlib insider — so the gallery of worked examples below is what this
thing actually produces today, with my own best-effort grading of where it
works and where it doesn't.

If you know mathlib well and any of my "WIN" / "MISS" calls in the gallery
are wrong, I'd genuinely like to hear it: that's the signal that would help
me decide what to fix, what to throw out, and whether the underlying index
is useful to anyone besides me — contributors, reviewers, or researchers
working on AI for formal math.

---

## Three ways to look at this repo

### 1. I just want to see what it produces

Open the gallery: [gallery/README.md](gallery/README.md).

**What it is.** A small set of worked examples — 10 cards, one per
currently-open mathlib4 PR. Each card runs the tool in **LLM mode** (the
default — retrieval + GPT-5 deciding which past comments apply) on a fresh
hunk from that PR, then sets the tool's output side-by-side with what the
human reviewer actually wrote. The point is to let you judge "is what this
thing says useful?" on cases where there's a real reviewer comment to
compare against — not on handpicked easy wins.

**Why it exists.** Numbers (`Hit@K`, judge labels — see section 3) tell you
*how often* retrieval lands something relevant; they don't tell you *what
the output looks like* or *whether the LLM-on-top-of-retrieval actually
adds something*. The gallery is the qualitative companion: real hunks,
real comments, with my own best-effort grading.

**Sneak peek of the result.** Out of 10 cards: a few times the tool
surfaced the same concern the human did (or one the human missed but is
real), more often it surfaced *adjacent* advice that's still plausibly
useful, once it correctly stayed silent, and a few times it confidently
pointed at the wrong thing or stayed silent when it shouldn't have. The
failure-mode cards are in the gallery on purpose — a gallery that hides
its failures isn't worth reading.

### 2. I want to try it on my own hunk

```bash
uv sync                                          # or: pip install -e .
export OPENAI_API_KEY=sk-...                     # for the LLM mode (default)
export VOYAGE_API_KEY=pa-...                     # for query embedding
cat my_hunk.diff | python scripts/review_pr.py --file Mathlib/Path/To/File.lean
```

There are two modes:

**LLM mode (default).** Retrieves the top-K most similar past
`(code, reviewer-comment)` pairs from the index and asks GPT-5 to identify
which past comments would also apply to your new hunk — grounded in
specific past PR + verbatim quote, with explicit refusal allowed.

**Search mode (`--search`).** Pure retrieval, no LLM call, no possibility
of hallucination. Returns the top-K most similar past
`(code, reviewer-comment)` pairs verbatim — you decide which apply.
Each hit is tagged ✓ ACCEPTED or ✗ NOT ACCEPTED based on whether the past
PR was integrated into mathlib (proxy for "reviewers wanted changes the
author didn't make"). Add `--not-accepted-only` to filter to just hits from
PRs that didn't make it — useful for *"is my code similar to anything that
already got rejected/abandoned?"*. Search mode only needs `VOYAGE_API_KEY`
(no OpenAI/Gemini key, no API costs except the embedding).

```bash
# LLM judgment on top of retrieval (the gallery is built from this mode):
cat my_hunk.diff | python scripts/review_pr.py --file Mathlib/X.lean

# Pure retrieval, no LLM, no hallucination:
cat my_hunk.diff | python scripts/review_pr.py --search --file Mathlib/X.lean

# Only show hits from past PRs that were NOT accepted into mathlib:
cat my_hunk.diff | python scripts/review_pr.py --search --not-accepted-only \
                                                --file Mathlib/X.lean
```

To use Gemini instead of GPT-5 in LLM mode: `pip install -e '.[gemini]'`,
set `GEMINI_API_KEY`, and pass `--provider gemini`.

Or `python scripts/review_pr.py --self-test` to run on a held-out query
without preparing a hunk yourself. Pass `--json` for raw structured output
in either mode.

> **Heads up:** this requires the embedding index
> (`data/index/rag_vectors.npz` and `data/curated/mathlib4/*.parquet`),
> which is not committed here due to size (~1 GB). See
> [Reproducing the index](#reproducing-the-index) below to build it locally,
> or [Dataset access](#dataset-access) if you'd rather grab a pre-built copy.

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

> The v3.1 prompt used in the gallery was
> iterated by observing failures of v3 on the same 20 open PRs the gallery
> is drawn from, so the gallery is a "best-current-prompt on tuned-for PRs"
> artifact, not a clean held-out test. The held-out generalization number
> is `llm_judge_report.md` above (20 closed-PR queries the prompt has never
> seen). The
> [gallery's own note on prompt tuning](gallery/README.md#a-note-on-prompt-tuning-please-read-before-grading)
> has the longer version.

**The actual prompts** (4 versions, v1 → v3.1, all in one file):
[src/product/review_assistant.py](src/product/review_assistant.py).

**Pipeline source** (scrape → normalize → embed → retrieve):
[src/pipeline/](src/pipeline/) and the runnable scripts in
[scripts/](scripts/).

**Per-case prompt + completion transcripts** (raw text dumps for
inspection): [data/eval/transcripts/](data/eval/transcripts/) — one file
per (case, prompt-version) combo for the gallery and the held-out runs.

---

## Dataset access

The curated parquets (~158k review comments + linked code chunks across
~35k closed PRs) and the OpenAI embedding index are not committed here due
to size. If you'd like them packaged as a Hugging Face Dataset for your own
experiments — or just a tarball — open an issue or ping me and I'll
publish it. Easier to do once than to have everyone re-scrape.

---

## Reproducing the index

If you'd rather rebuild it yourself, the raw GitHub payloads, the curated
parquets, and the embedding index can all be regenerated from scratch:

```bash
export GITHUB_TOKEN=ghp_...
python scripts/scrape_mathlib4.py --mode backfill   # ~few hours, GitHub-API-bound
python scripts/build_rag_index_data.py
python scripts/embed_rag_corpus.py                  # ~1 hour, OpenAI-embeddings
```

The eval outputs and gallery in this repo were produced from a snapshot
taken on 2026-04-18.

---

## Feedback

If you read the gallery and have thoughts — which suggestions are useful,
where the tool is wrong, what would make the index more useful for *your*
workflow, or whether the dataset itself is worth releasing — open an issue,
comment on Zulip, or reach out directly. That's the signal I'd use to
decide where to take this next.

License: MIT.
