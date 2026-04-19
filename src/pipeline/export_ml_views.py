from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd


def export_rag_documents(curated_root: Path, exports_root: Path) -> Path:
    exports_root.mkdir(parents=True, exist_ok=True)
    review_events_path = curated_root / "review_events.parquet"
    if not review_events_path.exists():
        out_path = exports_root / "rag_documents.parquet"
        pd.DataFrame(columns=["doc_id", "search_text"]).to_parquet(out_path, index=False)
        return out_path

    review_events = pd.read_parquet(review_events_path)
    rag_df = pd.DataFrame(
        {
            "doc_id": review_events["event_id"].astype(str),
            "search_text": review_events["search_text"].fillna(""),
            "pr_number": review_events["pr_number"],
            "event_type": review_events["event_type"],
            "file_path": review_events["file_path"],
            "reviewer": review_events["reviewer"],
            "accepted_proxy": review_events["accepted_proxy"].fillna(False),
            "resolved_proxy": review_events["resolved_proxy"].fillna(False),
            "labels": review_events.get("label_text", ""),
        }
    )
    rag_df["text_hash"] = rag_df["search_text"].map(_sha256)
    out_path = exports_root / "rag_documents.parquet"
    rag_df.to_parquet(out_path, index=False)
    return out_path


def export_classifier_examples(curated_root: Path, exports_root: Path) -> Path:
    exports_root.mkdir(parents=True, exist_ok=True)
    review_events_path = curated_root / "review_events.parquet"
    if not review_events_path.exists():
        out_path = exports_root / "classifier_examples.parquet"
        pd.DataFrame(columns=["example_id", "feature_text"]).to_parquet(out_path, index=False)
        return out_path

    review_events = pd.read_parquet(review_events_path)
    cls_df = pd.DataFrame(
        {
            "example_id": review_events["event_id"].astype(str),
            "feature_text": review_events["search_text"].fillna(""),
            "comment_text": review_events["comment_text"].fillna(""),
            "file_path": review_events["file_path"].fillna(""),
            "event_type": review_events["event_type"].fillna(""),
            "accepted_proxy": review_events["accepted_proxy"].fillna(False),
            "resolved_proxy": review_events["resolved_proxy"].fillna(False),
            "has_diff_text": review_events["has_diff_text"].fillna(False),
            "has_file_path": review_events["has_file_path"].fillna(False),
            "split": review_events["pr_number"].map(_split_for_pr),
        }
    )
    out_path = exports_root / "classifier_examples.parquet"
    cls_df.to_parquet(out_path, index=False)
    return out_path


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _split_for_pr(pr_number: int) -> str:
    if pr_number % 10 == 0:
        return "test"
    if pr_number % 10 == 1:
        return "val"
    return "train"
