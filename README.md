# mathlib4-reviewer-memory

A retrieval-grounded "reviewer memory" tool for `leanprover-community/mathlib4`.

Given a hunk from a new mathlib4 PR, it searches an index of **~158k past
reviewer comments across ~35k closed PRs**, retrieves the most similar
`(past code, past comment)` pairs, and asks an LLM (GPT-5) to identify which
of those past reviewer comments would also apply to the new hunk — grounded
in a specific past PR, file, and verbatim comment quote, with an explicit
"none of these apply" output when the retrieved pool is unrelated.

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

Open the gallery: [gallery/README.md](gallery/README.md). It's a curated
worked-examples gallery — 10 currently-open mathlib4 PRs, each rendered as
a card showing the new hunk, what the human reviewer actually wrote, and
what the tool produced (with clickable past-PR citations). The gallery
includes failure modes on purpose, so you can see what the tool gets wrong
as well as right.

### 2. I want to try it on my own hunk

```bash
uv sync                                          # or: pip install -e .
export OPENAI_API_KEY=sk-...
cat my_hunk.diff | python scripts/review_pr.py --file Mathlib/Path/To/File.lean
```

To use Gemini instead of GPT-5: `pip install -e '.[gemini]'`, set
`GEMINI_API_KEY`, and pass `--provider gemini` to the relevant scripts.

Or `python scripts/review_pr.py --self-test` to run on a held-out query
without preparing a hunk yourself. Output is human-readable; pass `--json`
for the raw structured output.

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

> **On methodology honesty.** The v3.1 prompt used in the gallery was
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
