#!/usr/bin/env python3
"""Refined coverage oracle:
  - filters trivial / short comments (require >= MIN_TOKENS on both sides)
  - widens the retrieval net to top-200 (vs the saved top-30) to see if the
    oracle's twin was just outside our reporting window
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "src")
from pipeline.retrieval import Retriever  # noqa: E402

TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]+|\d+")

STOP = {
    "the", "a", "an", "this", "that", "these", "those", "is", "be", "are",
    "to", "of", "in", "and", "or", "for", "on", "at", "by", "as", "with",
    "we", "i", "you", "it", "but", "if", "not", "so", "do", "should", "would",
    "could", "can", "may", "should", "thanks", "thank", "ok", "okay",
    "lemma", "theorem", "proof", "by", "exact", "have", "let", "fun", "show",
    "rfl", "intro", "apply", "simp", "rw", "use", "suggestion", "lean", "lean4",
}


def tok(s: str) -> set[str]:
    if not s:
        return set()
    return {t.lower() for t in TOKEN_RE.findall(s)}


def content_tokens(s: str) -> set[str]:
    return {t for t in tok(s) if t not in STOP and len(t) > 1}


def f1_filtered(a: set[str], b: set[str]) -> float:
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
    ap.add_argument("--vectors", default="data/index/rag_vectors.npz")
    ap.add_argument("--retrieval", default="data/eval/heldout_retrieval.jsonl")
    ap.add_argument("--cutoff", default="2026-03-01")
    ap.add_argument("--min-tokens", type=int, default=8,
                    help="minimum content-tokens for both query and candidate (filters chitchat)")
    ap.add_argument("--wide-k", type=int, default=200,
                    help="how deep to scan the actual retrieval ranking")
    ap.add_argument("--out-json", default="data/eval/oracle_coverage_v2.json")
    ap.add_argument("--out-csv", default="data/eval/oracle_per_query_v2.csv")
    args = ap.parse_args()

    print("loading corpus...")
    corpus = pd.read_parquet(args.corpus)
    corpus["created_at"] = pd.to_datetime(corpus["created_at"], utc=True)
    cutoff = pd.Timestamp(args.cutoff, tz="UTC")
    corpus["_pre_cutoff"] = corpus["created_at"] < cutoff

    print("computing content-token sets for all comments...")
    t0 = time.time()
    cand_tokens = [content_tokens(s) for s in corpus["comment_text"].tolist()]
    cand_lens = np.array([len(t) for t in cand_tokens], dtype=np.int32)
    cand_pr = corpus["pr_number"].to_numpy()
    cand_rid = corpus["record_id"].astype(str).to_numpy()
    cand_pre = corpus["_pre_cutoff"].to_numpy()
    print(f"  done in {time.time() - t0:.1f}s")

    print("loading retriever for wide-K rerun...")
    R = Retriever(corpus_path=args.corpus, vectors_path=args.vectors)

    print("loading held-out queries...")
    queries = []
    with open(args.retrieval) as f:
        for ln in f:
            r = json.loads(ln)
            queries.append({
                "query": r["query"],
                "saved_top10_rids": [h["record_id"] for h in r["top20_capped"][:10]],
                "saved_top30_rids": [h["record_id"] for h in r["top30_raw"][:30]],
            })
    print(f"  {len(queries)} queries")

    print("running refined oracle + wide retrieval probe...")
    rows = []
    t0 = time.time()
    for i, item in enumerate(queries):
        q = item["query"]
        q_tokens = content_tokens(q["comment_text"])
        q_pr = q["pr_number"]
        q_len = len(q_tokens)

        # only count substantive matches: both >= min_tokens
        if q_len < args.min_tokens:
            verdict = "query_too_short"
            row = {"record_id": q["record_id"], "pr": q_pr, "q_tokens": q_len,
                   "max_f1": 0.0, "oracle_rid": "", "oracle_pr": -1,
                   "in_top10": False, "in_top30": False, "in_top200": False,
                   "verdict": verdict}
            rows.append(row)
            continue

        valid = cand_pre & (cand_pr != q_pr) & (cand_lens >= args.min_tokens)
        max_f1 = 0.0
        max_idx = -1
        for j in np.flatnonzero(valid):
            inter = len(q_tokens & cand_tokens[j])
            if inter == 0:
                continue
            p = inter / q_len
            r = inter / cand_lens[j]
            score = 2 * p * r / (p + r)
            if score > max_f1:
                max_f1 = score
                max_idx = int(j)

        oracle_rid = cand_rid[max_idx] if max_idx >= 0 else ""
        oracle_pr = int(cand_pr[max_idx]) if max_idx >= 0 else -1

        # Wide retrieval probe with the SAME hunk-vector query
        hits200 = R.search_by_record_id(
            q["record_id"], k=args.wide_k,
            exclude_pr=q_pr, date_before=args.cutoff,
        )
        rids200 = [h.record_id for h in hits200]
        rid_set10 = set(item["saved_top10_rids"])
        rid_set30 = set(item["saved_top30_rids"])
        rid_set200 = set(rids200)

        in_top10 = oracle_rid in rid_set10 if oracle_rid else False
        in_top30 = oracle_rid in rid_set30 if oracle_rid else False
        in_top200 = oracle_rid in rid_set200 if oracle_rid else False

        if max_f1 < 0.3:
            verdict = "no_substantive_twin"
        elif in_top10:
            verdict = "found_in_top10"
        elif in_top30:
            verdict = "found_in_top30"
        elif in_top200:
            verdict = "found_in_top200"
        else:
            verdict = "missed_even_in_top200"

        rows.append({"record_id": q["record_id"], "pr": q_pr, "q_tokens": q_len,
                     "max_f1": round(max_f1, 4),
                     "oracle_rid": oracle_rid, "oracle_pr": oracle_pr,
                     "in_top10": in_top10, "in_top30": in_top30, "in_top200": in_top200,
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
    n_subst = int((df["q_tokens"] >= args.min_tokens).sum())
    twin_strong = int((df["max_f1"] >= 0.5).sum())
    twin_med = int(((df["max_f1"] >= 0.3) & (df["max_f1"] < 0.5)).sum())
    twin_weak = int((df["max_f1"] >= 0.3).sum())
    no_twin = int(((df["max_f1"] < 0.3) & (df["q_tokens"] >= args.min_tokens)).sum())

    by_verdict = df["verdict"].value_counts().to_dict()
    where = df[df["max_f1"] >= 0.3]
    where_strong = df[df["max_f1"] >= 0.5]

    summary = {
        "n_queries": n,
        "min_tokens_filter": args.min_tokens,
        "n_queries_substantive": n_subst,
        "queries_too_short": int((df["q_tokens"] < args.min_tokens).sum()),
        "twin_substantive_>=0.5": twin_strong,
        "twin_substantive_>=0.3": twin_weak,
        "twin_med_0.3_to_0.5": twin_med,
        "no_twin_<0.3": int((df["max_f1"] < 0.3).sum()) - int((df["q_tokens"] < args.min_tokens).sum()),
        "verdict_counts": by_verdict,
        "verdict_pct": {k: round(v / n * 100, 1) for k, v in by_verdict.items()},
        "given_strong_twin_exists": {
            "n": len(where_strong),
            "in_top10_rate": float(where_strong["in_top10"].mean()) if len(where_strong) else 0,
            "in_top30_rate": float(where_strong["in_top30"].mean()) if len(where_strong) else 0,
            "in_top200_rate": float(where_strong["in_top200"].mean()) if len(where_strong) else 0,
        },
        "given_weak_twin_exists (>=0.3)": {
            "n": len(where),
            "in_top10_rate": float(where["in_top10"].mean()) if len(where) else 0,
            "in_top30_rate": float(where["in_top30"].mean()) if len(where) else 0,
            "in_top200_rate": float(where["in_top200"].mean()) if len(where) else 0,
        },
        "max_f1_distribution_substantive": {
            "p25": float(df[df.q_tokens >= args.min_tokens]["max_f1"].quantile(0.25)),
            "p50": float(df[df.q_tokens >= args.min_tokens]["max_f1"].quantile(0.5)),
            "p75": float(df[df.q_tokens >= args.min_tokens]["max_f1"].quantile(0.75)),
            "p90": float(df[df.q_tokens >= args.min_tokens]["max_f1"].quantile(0.9)),
            "mean": float(df[df.q_tokens >= args.min_tokens]["max_f1"].mean()),
        },
    }

    Path(args.out_json).write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
