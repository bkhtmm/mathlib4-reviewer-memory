"""Build the clean RAG indexing dataset from curated parquet tables.

Produces data/index/rag_corpus.parquet with two clearly separated fields:
  - embedding_text: the diff_hunk (code context) — used for vector embedding
  - comment_text:   the reviewer's feedback — returned as retrieval payload

Filters applied:
  1. Closed PRs only (excludes open PRs)
  2. Human reviewers only (excludes bots)
  3. Exclude self-comments (PR author commenting on own PR)
  4. Exclude bors commands
  5. Exclude very short noise comments (≤10 chars: "Done.", "Fixed.", etc.)
  6. Require non-empty diff_hunk (>10 chars)
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parent.parent
CURATED = REPO_ROOT / "data" / "curated" / "mathlib4"
OUTPUT_DIR = REPO_ROOT / "data" / "index"

MIN_BODY_LEN = 11
MIN_HUNK_LEN = 11


def build() -> pd.DataFrame:
    rc = pd.read_parquet(CURATED / "review_comments.parquet")
    prs = pd.read_parquet(CURATED / "prs.parquet")
    labels = pd.read_parquet(CURATED / "pr_labels.parquet")

    closed_prs = prs[prs["state"] == "CLOSED"]

    df = rc.merge(
        closed_prs[["pr_number", "author_login", "title"]],
        on="pr_number",
        suffixes=("", "_pr"),
    )

    df = df[~df["is_bot_author"]]
    df = df[df["author_login"] != df["author_login_pr"]]
    df = df[~df["is_bors_command"].fillna(False)]
    df = df[df["body"].str.strip().str.len() >= MIN_BODY_LEN]
    df = df[df["diff_hunk"].notna() & (df["diff_hunk"].str.len() >= MIN_HUNK_LEN)]

    topic_labels = labels[labels["label_name"].str.startswith("t-", na=False)]
    labels_by_pr = (
        topic_labels.groupby("pr_number")["label_name"]
        .apply(lambda x: ",".join(sorted(set(x))))
        .rename("topic_labels")
    )

    df = df.merge(labels_by_pr, on="pr_number", how="left")
    df["topic_labels"] = df["topic_labels"].fillna("")

    has_suggestion = df["body"].str.contains("```suggestion", na=False, regex=False)

    corpus = pd.DataFrame({
        "record_id": df["review_comment_id"].values,
        "pr_number": df["pr_number"].values,
        "pr_title": df["title"].values,
        "file_path": df["path"].values,
        "line": df["line"].values,
        "reviewer": df["author_login"].values,
        "topic_labels": df["topic_labels"].values,
        "has_suggestion": has_suggestion.values,
        "embedding_text": df["diff_hunk"].values,
        "comment_text": df["body"].values,
        "created_at": df["created_at"].values,
    })

    corpus = corpus.drop_duplicates(subset=["record_id"])
    corpus = corpus.sort_values("created_at").reset_index(drop=True)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / "rag_corpus.parquet"
    corpus.to_parquet(out_path, index=False)

    print("Records: {:,}".format(len(corpus)))
    print("Unique PRs: {:,}".format(corpus["pr_number"].nunique()))
    print("Unique reviewers: {:,}".format(corpus["reviewer"].nunique()))
    print("With code suggestion: {:,} ({:.1f}%)".format(
        corpus["has_suggestion"].sum(),
        corpus["has_suggestion"].mean() * 100,
    ))
    print("Embedding text avg length: {:.0f} chars".format(
        corpus["embedding_text"].str.len().mean()
    ))
    print("Comment text avg length: {:.0f} chars".format(
        corpus["comment_text"].str.len().mean()
    ))
    print("Output: {}".format(out_path))
    return corpus


if __name__ == "__main__":
    build()
