#!/usr/bin/env python3
"""Coverage vs retrieval failure decomposition via lexical oracle search.

For each held-out query, find the comment in the index (excluding same PR
and post-cutoff records) with maximum lexical F1 against the ground-truth
reviewer comment. Then cross-reference our actual hunk-retrieval top-K to
classify each query into:

  - true_success      : oracle's twin is in our top-K
  - retrieval_failure : a high-F1 twin exists but we missed it
  - coverage_failure  : no high-F1 twin exists anywhere in the corpus

Outputs a JSON summary and a per-query CSV.
"""
from __future__ import annotations

import argparse
import json
import re
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]+|\d+")


def tok(s: str) -> set[str]:
    if not s:
        return set()
    return {t.lower() for t in TOKEN_RE.findall(s)}


def f1(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    if inter == 0:
        return 0.0
    p = inter / len(a)
    r = inter / len(b)
    return 2 * p * r / (p + r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="data/index/rag_corpus.parquet")
    ap.add_argument("--retrieval", default="data/eval/heldout_retrieval.jsonl")
    ap.add_argument("--cutoff", default="2026-03-01",
                    help="hide candidates with created_at >= this date (matches eval setup)")
    ap.add_argument("--top-k", type=int, default=10)
    ap.add_argument("--f1-strong", type=float, default=0.5,
                    help="F1 threshold for 'strong twin' (paraphrase-like)")
    ap.add_argument("--f1-weak", type=float, default=0.3,
                    help="F1 threshold for 'weak twin' (related advice)")
    ap.add_argument("--out-json", default="data/eval/oracle_coverage.json")
    ap.add_argument("--out-csv", default="data/eval/oracle_per_query.csv")
    ap.add_argument("--limit", type=int, default=0,
                    help="if >0, only process first N queries (for smoke testing)")
    args = ap.parse_args()

    print("loading corpus...")
    corpus = pd.read_parquet(args.corpus)
    corpus["created_at"] = pd.to_datetime(corpus["created_at"], utc=True)
    cutoff = pd.Timestamp(args.cutoff, tz="UTC")
    cand_mask = corpus["created_at"] < cutoff
    cands = corpus[cand_mask].reset_index(drop=True)
    print(f"  total corpus = {len(corpus):,}, candidates (pre-cutoff) = {len(cands):,}")

    print("tokenizing candidate comments...")
    t0 = time.time()
    cand_tokens = [tok(s) for s in cands["comment_text"].tolist()]
    cand_lens = np.array([len(t) for t in cand_tokens], dtype=np.int32)
    cand_pr = cands["pr_number"].to_numpy()
    cand_rid = cands["record_id"].astype(str).to_numpy()
    print(f"  done in {time.time() - t0:.1f}s")

    print("loading held-out queries...")
    queries = []
    with open(args.retrieval) as f:
        for ln in f:
            r = json.loads(ln)
            queries.append({
                "query": r["query"],
                "top_hits": r["top20_capped"][: args.top_k],
            })
    if args.limit:
        queries = queries[: args.limit]
    print(f"  {len(queries)} queries (top-{args.top_k} retrieval each)")

    print("running oracle search...")
    rows = []
    t0 = time.time()
    for i, item in enumerate(queries):
        q = item["query"]
        q_tokens = tok(q["comment_text"])
        q_pr = q["pr_number"]
        if not q_tokens:
            rows.append({"record_id": q["record_id"], "pr": q_pr,
                         "max_f1": 0.0, "oracle_rid": "", "oracle_pr": -1,
                         "in_topk": False, "verdict": "empty_query"})
            continue
        max_f1 = 0.0
        max_idx = -1
        same_pr_mask = cand_pr != q_pr
        for j, ctoks in enumerate(cand_tokens):
            if not same_pr_mask[j]:
                continue
            inter = len(q_tokens & ctoks)
            if inter == 0:
                continue
            denom_p = len(q_tokens)
            denom_r = cand_lens[j]
            if denom_r == 0:
                continue
            p = inter / denom_p
            r = inter / denom_r
            score = 2 * p * r / (p + r)
            if score > max_f1:
                max_f1 = score
                max_idx = j

        oracle_rid = cand_rid[max_idx] if max_idx >= 0 else ""
        oracle_pr = int(cand_pr[max_idx]) if max_idx >= 0 else -1
        topk_rids = {h["record_id"] for h in item["top_hits"]}
        in_topk = oracle_rid in topk_rids if oracle_rid else False

        if max_f1 >= args.f1_weak:
            verdict = "true_success" if in_topk else "retrieval_failure"
        else:
            verdict = "coverage_failure"

        rows.append({"record_id": q["record_id"], "pr": q_pr,
                     "max_f1": round(max_f1, 4),
                     "oracle_rid": oracle_rid,
                     "oracle_pr": oracle_pr,
                     "in_topk": in_topk,
                     "verdict": verdict})

        if (i + 1) % 50 == 0:
            elapsed = time.time() - t0
            rate = (i + 1) / elapsed
            eta = (len(queries) - i - 1) / rate
            print(f"  [{i + 1}/{len(queries)}] rate={rate:.1f} q/s eta={eta:.0f}s")

    df = pd.DataFrame(rows)
    df.to_csv(args.out_csv, index=False)
    print(f"wrote {args.out_csv}")

    n = len(df)
    by_verdict = Counter(df["verdict"])
    f1_dist = {
        "max_f1_p25": float(df["max_f1"].quantile(0.25)),
        "max_f1_p50": float(df["max_f1"].quantile(0.50)),
        "max_f1_p75": float(df["max_f1"].quantile(0.75)),
        "max_f1_p90": float(df["max_f1"].quantile(0.90)),
        "max_f1_p95": float(df["max_f1"].quantile(0.95)),
        "max_f1_max": float(df["max_f1"].max()),
        "max_f1_mean": float(df["max_f1"].mean()),
    }
    coverage_rates = {
        "twin_strong (max_f1 >= %.2f)" % args.f1_strong: int((df["max_f1"] >= args.f1_strong).sum()),
        "twin_weak (max_f1 >= %.2f)" % args.f1_weak:    int((df["max_f1"] >= args.f1_weak).sum()),
        "twin_any (max_f1 >= 0.10)":                    int((df["max_f1"] >= 0.10).sum()),
        "no_twin (max_f1 < %.2f)" % args.f1_weak:       int((df["max_f1"] < args.f1_weak).sum()),
    }

    weak_twin = df[df["max_f1"] >= args.f1_weak]
    strong_twin = df[df["max_f1"] >= args.f1_strong]
    decomposition = {
        "n_queries": n,
        "f1_threshold_weak": args.f1_weak,
        "f1_threshold_strong": args.f1_strong,
        "verdicts (using weak threshold)": dict(by_verdict),
        "verdict_pct (weak)": {k: round(v / n * 100, 1) for k, v in by_verdict.items()},
        "given_weak_twin_exists": {
            "n": len(weak_twin),
            "in_topk_rate": float(weak_twin["in_topk"].mean()) if len(weak_twin) else 0.0,
        },
        "given_strong_twin_exists": {
            "n": len(strong_twin),
            "in_topk_rate": float(strong_twin["in_topk"].mean()) if len(strong_twin) else 0.0,
        },
        "coverage_counts": coverage_rates,
        "coverage_pct": {k: round(v / n * 100, 1) for k, v in coverage_rates.items()},
        "max_f1_distribution_per_query": f1_dist,
    }

    Path(args.out_json).write_text(json.dumps(decomposition, indent=2))
    print(f"wrote {args.out_json}")
    print(json.dumps(decomposition, indent=2))


if __name__ == "__main__":
    main()
