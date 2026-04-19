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

    pr_cols = ["pr_number", "author_login", "title"]
    if "accepted_proxy" in closed_prs.columns:
        pr_cols.append("accepted_proxy")
    if "merged_by_login" in closed_prs.columns:
        pr_cols.append("merged_by_login")

    df = rc.merge(
        closed_prs[pr_cols],
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

    # PR-acceptance signal. Used by the no-LLM "search" mode of the CLI to
    # surface "this similar past code is from a PR that was NOT accepted into
    # mathlib" — a useful, conservative proxy for "reviewers wanted changes
    # that didn't happen". Not the same as "rejected" (could be abandoned,
    # superseded, etc.); we surface the fact and let the user decide.
    if "accepted_proxy" in df.columns:
        pr_accepted = df["accepted_proxy"].astype("boolean")
    else:
        pr_accepted = pd.Series([pd.NA] * len(df), dtype="boolean")

    if "merged_by_login" in df.columns:
        merged_by = df["merged_by_login"].fillna("").astype(str)
    else:
        merged_by = pd.Series([""] * len(df), dtype="object")

    corpus = pd.DataFrame({
        "record_id": df["review_comment_id"].values,
        "pr_number": df["pr_number"].values,
        "pr_title": df["title"].values,
        "file_path": df["path"].values,
        "line": df["line"].values,
        "reviewer": df["author_login"].values,
        "topic_labels": df["topic_labels"].values,
        "has_suggestion": has_suggestion.values,
        "pr_accepted": pr_accepted.values,
        "merged_by": merged_by.values,
        "embedding_text": df["diff_hunk"].values,
        "comment_text": df["body"].values,
        "created_at": df["created_at"].values,
    })

    corpus = corpus.drop_duplicates(subset=["record_id"])
    corpus = corpus.sort_values("created_at").reset_index(drop=True)

    # If an embedded vectors file already exists, align the corpus to it so
    # we don't break the Retriever (which requires record_id-by-record_id
    # alignment between corpus and vectors). New rows not yet embedded are
    # simply dropped here; rerun scripts/embed_rag_corpus.py to add them.
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    vectors_path = OUTPUT_DIR / "rag_vectors.npz"
    if vectors_path.exists():
        import numpy as np

        vec_rids = [
            str(r) for r in np.load(vectors_path, allow_pickle=True)["record_ids"]
        ]
        before = len(corpus)
        corpus["record_id"] = corpus["record_id"].astype(str)
        corpus = corpus.set_index("record_id").reindex(vec_rids).reset_index()
        # reindex inserts NaN rows for record_ids that exist in vectors but
        # not in the rebuilt corpus — that shouldn't happen, but guard anyway.
        if corpus["pr_number"].isna().any():
            n_missing = int(corpus["pr_number"].isna().sum())
            raise RuntimeError(
                f"{n_missing} record_ids present in vectors file but missing "
                f"from rebuilt corpus — vectors and curated data are out of sync"
            )
        dropped = before - len(corpus)
        if dropped:
            print(
                f"[align] dropped {dropped:,} corpus row(s) not yet embedded "
                f"(rerun scripts/embed_rag_corpus.py to embed them)"
            )

    out_path = OUTPUT_DIR / "rag_corpus.parquet"
    corpus.to_parquet(out_path, index=False)

    print("Records: {:,}".format(len(corpus)))
    print("Unique PRs: {:,}".format(corpus["pr_number"].nunique()))
    print("Unique reviewers: {:,}".format(corpus["reviewer"].nunique()))
    print("With code suggestion: {:,} ({:.1f}%)".format(
        corpus["has_suggestion"].sum(),
        corpus["has_suggestion"].mean() * 100,
    ))
    if corpus["pr_accepted"].notna().any():
        n_accepted = int(corpus["pr_accepted"].fillna(False).sum())
        n_unknown = int(corpus["pr_accepted"].isna().sum())
        n_total = len(corpus)
        n_not_accepted = n_total - n_accepted - n_unknown
        print("Past PR acceptance: {:,} accepted, {:,} not accepted, {:,} unknown".format(
            n_accepted, n_not_accepted, n_unknown,
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
