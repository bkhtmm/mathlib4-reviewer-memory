"""Analyze the held-out retrieval JSONL with lightweight, non-LLM signals.

For each query we have:
  - ground-truth reviewer comment (what the reviewer ACTUALLY said on this PR)
  - top-20/30 retrieved past comments

We compute signals that correlate with usefulness WITHOUT an LLM judge:
  1. Token-F1 overlap between ground-truth comment and each retrieved comment.
  2. Same-file hit: any retrieved comment from the same file_path.
  3. Same-directory hit: same Mathlib/<top-level>/<second-level> prefix.
  4. Topic-label overlap: any retrieved comment sharing a t-* label.
  5. Suggestion alignment: both query and retrieved have ```suggestion.
  6. Aggregate similarity distribution.

The headline metric is "Hit@K for F1>=threshold", i.e. does any of the top-K
retrieved comments share a significant lexical chunk with the ground truth?
This is a LOWER BOUND on semantic relevance (LLM judge would likely rate more
hits as relevant even without token overlap), but it's cheap, deterministic,
and free of model bias.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent

TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]+|`[^`]+`")
STOPWORDS = {
    "the","a","an","of","to","in","is","it","be","for","on","and","or","but","with",
    "that","this","these","those","as","at","by","from","if","then","we","you","i","me",
    "my","your","our","their","they","he","she","them","so","do","does","did","not","no",
    "yes","can","could","should","would","will","may","might","must","have","has","had",
    "are","was","were","been","being","here","there","also","just","any","some","all",
    "one","two","three","use","using","used","make","makes","made","like","very","much",
    "now","thing","things","way","please","thanks","thank","think","maybe","actually",
    "need","needs","prefer","probably","done","fix","fixed","nit","todo","what","which",
    "who","when","where","why","how","out","up","down","over","under","into","onto",
    "about","around","only","than","too","yet","per","its","his","her","hers","im","ive",
    "cant","dont","wont","isnt","arent","dont","shouldnt","wouldnt","couldnt",
}


def tokenize(text: str) -> set[str]:
    if not text:
        return set()
    text = text.lower()
    text = re.sub(r"```[\s\S]*?```", " ", text)  # strip code blocks
    tokens = TOKEN_RE.findall(text)
    return {t for t in tokens if len(t) >= 3 and t not in STOPWORDS}


def token_f1(a: str, b: str) -> float:
    ta, tb = tokenize(a), tokenize(b)
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    if inter == 0:
        return 0.0
    prec = inter / len(tb)
    rec = inter / len(ta)
    return 2 * prec * rec / (prec + rec)


def directory(path: str) -> str:
    parts = path.split("/")
    return "/".join(parts[:3]) if len(parts) >= 3 else path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="data/eval/heldout_retrieval.jsonl")
    ap.add_argument("--output", default="data/eval/heldout_analysis.json")
    ap.add_argument("--f1-threshold", type=float, default=0.30)
    args = ap.parse_args()

    path = REPO_ROOT / args.input
    records = [json.loads(line) for line in path.open()]
    print(f"loaded {len(records)} records")

    Ks = [1, 3, 5, 10, 20]
    f1_thr = args.f1_threshold

    metrics = {
        "n_queries": len(records),
        "f1_threshold": f1_thr,
        "hit_at_k_f1": {str(k): 0 for k in Ks},
        "mean_max_f1_at_k": {str(k): [] for k in Ks},
        "same_file_hit_at_k": {str(k): 0 for k in Ks},
        "same_dir_hit_at_k":  {str(k): 0 for k in Ks},
        "topic_overlap_hit_at_k": {str(k): 0 for k in Ks},
        "same_file_hit_at_k_capped": {str(k): 0 for k in Ks},
        "topic_overlap_hit_at_k_capped": {str(k): 0 for k in Ks},
        "hit_at_k_f1_capped": {str(k): 0 for k in Ks},
        "suggestion_query_frac": 0,
        "suggestion_alignment_when_query_has": 0,
        "per_topic": {},
        "f1_score_distribution_top20_raw": {"p50":0,"p75":0,"p90":0,"p95":0,"max":0,"mean":0},
        "sim_distribution_top1_raw": {"p50":0,"p75":0,"p90":0,"p95":0,"max":0,"mean":0},
        "f1_vs_rank": [],
    }

    f1_by_rank = [[] for _ in range(30)]
    all_top20_f1 = []
    all_top1_sim = []

    suggestion_q = 0
    suggestion_aligned = 0

    topic_hits = {}  # topic -> {"n": int, "hit10_f1": int, "hit10_file": int}

    for rec in records:
        q = rec["query"]
        q_text = q["comment_text"]
        q_file = q["file_path"] or ""
        q_dir = directory(q_file)
        q_topics = set(filter(None, q["topic_labels"].split(",")))
        q_has_sugg = bool(q["has_suggestion"])
        if q_has_sugg:
            suggestion_q += 1

        top_raw = rec["top30_raw"][:20]
        top_cap = rec["top20_capped"]

        # f1 per hit (raw)
        f1_raw = [token_f1(q_text, h["comment_text"]) for h in top_raw]
        f1_cap = [token_f1(q_text, h["comment_text"]) for h in top_cap]

        for rank, v in enumerate(f1_raw):
            f1_by_rank[rank].append(v)
        all_top20_f1.extend(f1_raw)
        if top_raw:
            all_top1_sim.append(top_raw[0]["sim"])

        for k in Ks:
            window_raw = f1_raw[:k]
            window_cap = f1_cap[:k]
            if any(v >= f1_thr for v in window_raw):
                metrics["hit_at_k_f1"][str(k)] += 1
            if any(v >= f1_thr for v in window_cap):
                metrics["hit_at_k_f1_capped"][str(k)] += 1
            metrics["mean_max_f1_at_k"][str(k)].append(
                max(window_raw) if window_raw else 0.0
            )
            if any(h["file_path"] == q_file for h in top_raw[:k]):
                metrics["same_file_hit_at_k"][str(k)] += 1
            if any(h["file_path"] == q_file for h in top_cap[:k]):
                metrics["same_file_hit_at_k_capped"][str(k)] += 1
            if any(directory(h["file_path"] or "") == q_dir for h in top_raw[:k]):
                metrics["same_dir_hit_at_k"][str(k)] += 1
            if q_topics and any(
                set(filter(None, h["topic_labels"].split(","))) & q_topics
                for h in top_raw[:k]
            ):
                metrics["topic_overlap_hit_at_k"][str(k)] += 1
            if q_topics and any(
                set(filter(None, h["topic_labels"].split(","))) & q_topics
                for h in top_cap[:k]
            ):
                metrics["topic_overlap_hit_at_k_capped"][str(k)] += 1

        if q_has_sugg and any(h["has_suggestion"] for h in top_raw[:10]):
            suggestion_aligned += 1

        # per-topic breakdown (primary topic = first label)
        primary_topic = sorted(q_topics)[0] if q_topics else "(no-topic)"
        bucket = topic_hits.setdefault(primary_topic, {
            "n": 0, "hit10_f1": 0, "hit10_file": 0, "mean_max_f1_top10": []
        })
        bucket["n"] += 1
        top10_f1 = f1_raw[:10]
        if any(v >= f1_thr for v in top10_f1):
            bucket["hit10_f1"] += 1
        if any(h["file_path"] == q_file for h in top_raw[:10]):
            bucket["hit10_file"] += 1
        bucket["mean_max_f1_top10"].append(max(top10_f1) if top10_f1 else 0.0)

    for k in Ks:
        metrics["mean_max_f1_at_k"][str(k)] = float(np.mean(metrics["mean_max_f1_at_k"][str(k)])) if records else 0.0
    metrics["suggestion_query_frac"] = suggestion_q / len(records)
    metrics["suggestion_alignment_when_query_has"] = (
        suggestion_aligned / suggestion_q if suggestion_q else 0.0
    )

    arr_f1 = np.asarray(all_top20_f1)
    arr_sim = np.asarray(all_top1_sim)
    for k, q in [("p50", 50), ("p75", 75), ("p90", 90), ("p95", 95)]:
        metrics["f1_score_distribution_top20_raw"][k] = float(np.percentile(arr_f1, q))
        metrics["sim_distribution_top1_raw"][k] = float(np.percentile(arr_sim, q))
    metrics["f1_score_distribution_top20_raw"]["max"] = float(arr_f1.max())
    metrics["f1_score_distribution_top20_raw"]["mean"] = float(arr_f1.mean())
    metrics["sim_distribution_top1_raw"]["max"] = float(arr_sim.max())
    metrics["sim_distribution_top1_raw"]["mean"] = float(arr_sim.mean())

    metrics["f1_vs_rank"] = [float(np.mean(v)) if v else 0.0 for v in f1_by_rank]

    per_topic_out = {}
    for topic, bucket in sorted(topic_hits.items(), key=lambda kv: -kv[1]["n"]):
        if bucket["n"] < 10:
            continue
        per_topic_out[topic] = {
            "n": bucket["n"],
            "hit10_f1_rate": bucket["hit10_f1"] / bucket["n"],
            "same_file_hit10_rate": bucket["hit10_file"] / bucket["n"],
            "mean_max_f1_top10": float(np.mean(bucket["mean_max_f1_top10"])),
        }
    metrics["per_topic"] = per_topic_out

    out_path = REPO_ROOT / args.output
    out_path.write_text(json.dumps(metrics, indent=2))
    print(f"wrote {out_path}")
    print()
    # Printable summary
    print(f"--- RAW (no per-PR cap) top-K lexical-relevance signal (F1>={f1_thr}) ---")
    print(f"{'K':>4} {'Hit@K':>9} {'mean max-F1':>14} {'same-file':>11} {'same-dir':>10} {'topic':>9}")
    for k in Ks:
        hit = metrics["hit_at_k_f1"][str(k)] / len(records) * 100
        mmf = metrics["mean_max_f1_at_k"][str(k)]
        sf = metrics["same_file_hit_at_k"][str(k)] / len(records) * 100
        sd = metrics["same_dir_hit_at_k"][str(k)] / len(records) * 100
        tp = metrics["topic_overlap_hit_at_k"][str(k)] / len(records) * 100
        print(f"{k:>4} {hit:>8.1f}% {mmf:>14.3f} {sf:>10.1f}% {sd:>9.1f}% {tp:>8.1f}%")
    print()
    print(f"--- CAPPED (max 2/PR) top-K ---")
    print(f"{'K':>4} {'Hit@K':>9} {'same-file':>11} {'topic':>9}")
    for k in Ks:
        hit = metrics["hit_at_k_f1_capped"][str(k)] / len(records) * 100
        sf = metrics["same_file_hit_at_k_capped"][str(k)] / len(records) * 100
        tp = metrics["topic_overlap_hit_at_k_capped"][str(k)] / len(records) * 100
        print(f"{k:>4} {hit:>8.1f}% {sf:>10.1f}% {tp:>8.1f}%")
    print()
    print(f"Queries with ```suggestion        : {metrics['suggestion_query_frac']*100:.1f}%")
    print(f"  of those, top-10 has suggestion : {metrics['suggestion_alignment_when_query_has']*100:.1f}%")
    print()
    print("F1 by raw rank (mean):")
    print("  rank 1  3  5  10  15  20")
    ranks = [1,3,5,10,15,20]
    vals = [metrics['f1_vs_rank'][r-1] for r in ranks]
    print("  " + "  ".join(f"{v:.3f}" for v in vals))
    print()
    print("--- per-topic (Hit@10 with F1>=threshold) ---")
    for topic, d in list(per_topic_out.items())[:15]:
        print(f"  {topic:<30} n={d['n']:>4}  hit10={d['hit10_f1_rate']*100:>5.1f}%  same_file={d['same_file_hit10_rate']*100:>5.1f}%  mean_max_f1={d['mean_max_f1_top10']:.3f}")


if __name__ == "__main__":
    main()
