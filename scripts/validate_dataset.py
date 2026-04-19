#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from pipeline.config import load_config


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate curated mathlib4 dataset quality.")
    parser.add_argument("--config", default="config/scraper.yaml", help="Path to scraper config.")
    parser.add_argument("--sample-size", type=int, default=100, help="Sample size for acceptance sanity spot-check.")
    return parser.parse_args()


def _read(path: Path) -> pd.DataFrame:
    if path.exists():
        return pd.read_parquet(path)
    return pd.DataFrame()


def _null_rate(df: pd.DataFrame, column: str) -> float | None:
    if df.empty or column not in df.columns:
        return None
    return float(df[column].isna().mean())


def _duplicate_count(df: pd.DataFrame, keys: list[str]) -> int | None:
    if df.empty or not all(k in df.columns for k in keys):
        return None
    return int(df.duplicated(subset=keys, keep=False).sum())


def main() -> None:
    args = parse_args()
    config = load_config(REPO_ROOT / args.config)
    curated = REPO_ROOT / config.paths.curated_root

    prs = _read(curated / "prs.parquet")
    issue_comments = _read(curated / "issue_comments.parquet")
    review_comments = _read(curated / "review_comments.parquet")
    reviews = _read(curated / "reviews.parquet")
    review_events = _read(curated / "review_events.parquet")

    report = {
        "row_counts": {
            "prs": int(len(prs)),
            "reviews": int(len(reviews)),
            "review_comments": int(len(review_comments)),
            "issue_comments": int(len(issue_comments)),
            "review_events": int(len(review_events)),
        },
        "null_rates": {
            "prs.pr_number": _null_rate(prs, "pr_number"),
            "prs.title": _null_rate(prs, "title"),
            "review_comments.pr_number": _null_rate(review_comments, "pr_number"),
            "review_comments.body": _null_rate(review_comments, "body"),
            "issue_comments.pr_number": _null_rate(issue_comments, "pr_number"),
            "issue_comments.body": _null_rate(issue_comments, "body"),
            "review_events.event_id": _null_rate(review_events, "event_id"),
            "review_events.search_text": _null_rate(review_events, "search_text"),
        },
        "duplicate_keys": {
            "prs": _duplicate_count(prs, ["pr_id", "pr_number"]),
            "reviews": _duplicate_count(reviews, ["review_id"]),
            "review_comments": _duplicate_count(review_comments, ["review_comment_id"]),
            "issue_comments": _duplicate_count(issue_comments, ["comment_id"]),
            "review_events": _duplicate_count(review_events, ["event_id"]),
        },
    }

    # Referential integrity: review_comments.pr_number should exist in prs.pr_number.
    if not prs.empty and not review_comments.empty and "pr_number" in prs.columns and "pr_number" in review_comments.columns:
        prs_keys = set(prs["pr_number"].dropna().astype(int).tolist())
        bad_refs = review_comments["pr_number"].dropna().astype(int)
        missing_ref_count = int((~bad_refs.isin(prs_keys)).sum())
    else:
        missing_ref_count = None
    report["referential_integrity"] = {"review_comments_missing_pr_refs": missing_ref_count}

    # Bot/human diagnostics.
    issue_bot_rate = _null_rate(issue_comments, "is_bot_author")
    review_bot_rate = _null_rate(review_comments, "is_bot_author")
    if not issue_comments.empty and "is_bot_author" in issue_comments.columns:
        issue_bot_rate = float(issue_comments["is_bot_author"].fillna(False).mean())
    if not review_comments.empty and "is_bot_author" in review_comments.columns:
        review_bot_rate = float(review_comments["is_bot_author"].fillna(False).mean())
    report["bot_human_ratio"] = {
        "issue_comments_bot_rate": issue_bot_rate,
        "review_comments_bot_rate": review_bot_rate,
    }

    # Acceptance label sanity checks on sample rows.
    sanity = {"sample_size": 0, "accepted_proxy_true": 0, "accepted_with_bors_signal": 0}
    if not review_events.empty:
        sample = review_events.head(args.sample_size)
        sanity["sample_size"] = int(len(sample))
        if "accepted_proxy" in sample.columns:
            sanity["accepted_proxy_true"] = int(sample["accepted_proxy"].fillna(False).sum())
        if "comment_text" in sample.columns:
            sanity["accepted_with_bors_signal"] = int(
                sample["comment_text"].fillna("").str.contains("successfully merged into master", case=False).sum()
            )
    report["acceptance_sanity"] = sanity

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
