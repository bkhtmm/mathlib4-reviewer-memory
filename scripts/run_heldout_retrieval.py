"""Run top-K retrieval for a sample of held-out review comments.

Temporal hold-out: pick review comments on CLOSED PRs with created_at >= cutoff,
use their pre-computed document vectors as queries (no API cost), and filter the
index at query time with date_before=cutoff + exclude_pr to simulate retrieval
on a "fresh" PR.

Saves results as JSONL:
  {query: {...}, top30_raw: [...], top20_capped: [...]}

- top30_raw  : top 30 hits with no diversity / per-PR cap (pure vector ranking)
- top20_capped: top 20 hits after enforcing max_per_pr=2
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from pipeline.retrieval import Retriever  # noqa: E402


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cutoff", default="2026-03-01",
                    help="ISO date; comments created on/after are held out.")
    ap.add_argument("--sample-size", type=int, default=500)
    ap.add_argument("--seed", type=int, default=17)
    ap.add_argument("--output", default="data/eval/heldout_retrieval.jsonl")
    ap.add_argument("--stats-output", default="data/eval/heldout_retrieval_stats.json")
    ap.add_argument("--min-comment-len", type=int, default=25,
                    help="Require ground-truth comment to be at least this many chars.")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    out_path = REPO_ROOT / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)

    retriever = Retriever()
    df = retriever.df
    prs = pd.read_parquet(REPO_ROOT / "data" / "curated" / "mathlib4" / "prs.parquet")
    closed_prs = set(prs[prs.state == "CLOSED"].pr_number.astype(int).tolist())

    heldout_mask = (
        (df["created_at"] >= args.cutoff)
        & df["pr_number"].astype(int).isin(closed_prs)
        & (df["comment_text"].str.len() >= args.min_comment_len)
    )
    heldout_pool = df[heldout_mask]
    print(f"held-out pool size (cutoff={args.cutoff}, min_len={args.min_comment_len}): "
          f"{len(heldout_pool):,} / {len(df):,}")

    rng = np.random.default_rng(args.seed)
    sample_size = min(args.sample_size, len(heldout_pool))
    sample_idx = rng.choice(len(heldout_pool), size=sample_size, replace=False)
    sample = heldout_pool.iloc[sample_idx].reset_index(drop=True)
    print(f"sampled {len(sample):,} held-out queries")

    n_written = 0
    t0 = time.time()
    stats = {
        "cutoff": args.cutoff,
        "sample_size": int(sample_size),
        "min_comment_len": args.min_comment_len,
        "n_queries": 0,
        "avg_unique_prs_top20_raw": 0.0,
        "avg_unique_prs_top20_capped": 0.0,
        "avg_sim_top1_raw": 0.0,
        "avg_sim_top1_capped": 0.0,
        "avg_sim_top20_raw": 0.0,
        "avg_sim_top20_capped": 0.0,
        "frac_raw_top20_same_pr_leak": 0.0,
    }
    sum_unique_raw = 0
    sum_unique_capped = 0
    sum_sim1_raw = 0.0
    sum_sim1_cap = 0.0
    sum_sim20_raw = 0.0
    sum_sim20_cap = 0.0
    leak_count = 0

    with open(out_path, "w", encoding="utf-8") as fh:
        for _, qrow in sample.iterrows():
            rid = str(qrow["record_id"])
            q_pr = int(qrow["pr_number"])

            top30 = retriever.search_by_record_id(
                rid, k=30,
                auto_exclude_self=True,
                auto_exclude_pr=True,
                date_before=args.cutoff,
            )
            top20_cap = retriever.search_by_record_id(
                rid, k=20,
                auto_exclude_self=True,
                auto_exclude_pr=True,
                date_before=args.cutoff,
                max_per_pr=2,
            )

            sum_unique_raw += len(set(h.pr_number for h in top30[:20]))
            sum_unique_capped += len(set(h.pr_number for h in top20_cap))
            if top30:
                sum_sim1_raw += top30[0].sim
                sum_sim20_raw += float(np.mean([h.sim for h in top30[:20]])) if len(top30) >= 20 else top30[-1].sim
            if top20_cap:
                sum_sim1_cap += top20_cap[0].sim
                sum_sim20_cap += float(np.mean([h.sim for h in top20_cap]))
            if any(h.pr_number == q_pr for h in top30):
                leak_count += 1

            record = {
                "query": {
                    "record_id": rid,
                    "pr_number": q_pr,
                    "pr_title": str(qrow["pr_title"]),
                    "file_path": str(qrow["file_path"]),
                    "line": float(qrow["line"]) if pd.notna(qrow["line"]) else None,
                    "reviewer": str(qrow["reviewer"]),
                    "topic_labels": str(qrow["topic_labels"]),
                    "has_suggestion": bool(qrow["has_suggestion"]),
                    "comment_text": str(qrow["comment_text"]),
                    "embedding_text": str(qrow["embedding_text"]),
                    "created_at": str(qrow["created_at"]),
                },
                "top30_raw": [h.as_dict() for h in top30],
                "top20_capped": [h.as_dict() for h in top20_cap],
            }
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
            n_written += 1
            if n_written % 50 == 0:
                dt = time.time() - t0
                rate = n_written / dt
                print(f"  {n_written}/{sample_size}  {dt:.1f}s  ({rate:.1f} q/s)", flush=True)

    stats["n_queries"] = n_written
    if n_written:
        stats["avg_unique_prs_top20_raw"] = sum_unique_raw / n_written
        stats["avg_unique_prs_top20_capped"] = sum_unique_capped / n_written
        stats["avg_sim_top1_raw"] = sum_sim1_raw / n_written
        stats["avg_sim_top1_capped"] = sum_sim1_cap / n_written
        stats["avg_sim_top20_raw"] = sum_sim20_raw / n_written
        stats["avg_sim_top20_capped"] = sum_sim20_cap / n_written
        stats["frac_raw_top20_same_pr_leak"] = leak_count / n_written
    stats_path = REPO_ROOT / args.stats_output
    stats_path.parent.mkdir(parents=True, exist_ok=True)
    stats_path.write_text(json.dumps(stats, indent=2))
    print()
    print(f"wrote {n_written} records -> {out_path}")
    print(f"stats                       -> {stats_path}")
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
