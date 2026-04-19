"""Produce a Markdown hand-inspection report of diverse held-out retrieval samples.

Stratifies the sample pool to cover:
  - Queries where at least one top-10 hit has lexical F1 >= 0.3 ("apparent match")
  - Queries where a top-10 hit is from the same file but F1 is low
    (topical-only match — how useful is this?)
  - Queries where nothing obviously matched (failure cases)
  - Mix of ``` suggestion vs prose comments
  - Mix of topic labels
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent

TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]+|`[^`]+`")
STOPWORDS = {
    "the","a","an","of","to","in","is","it","be","for","on","and","or","but","with","that","this",
    "these","those","as","at","by","from","if","then","we","you","i","me","my","your","our","their",
    "they","he","she","them","so","do","does","did","not","no","yes","can","could","should","would",
    "will","may","might","must","have","has","had","are","was","were","been","being","here","there",
    "also","just","any","some","all","one","two","three","use","using","used","make","makes","made",
    "like","very","much","now","thing","things","way","please","thanks","thank","think","maybe",
    "actually","need","needs","prefer","probably","done","fix","fixed","nit","todo","what","which",
    "who","when","where","why","how","out","up","down","over","under","into","onto","about","around",
    "only","than","too","yet","per","its","his","her","hers","im","ive","cant","dont","wont","isnt",
    "arent","shouldnt","wouldnt","couldnt",
}


def tokenize(text: str) -> set[str]:
    if not text:
        return set()
    text = text.lower()
    text = re.sub(r"```[\s\S]*?```", " ", text)
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


def truncate(text: str, max_chars: int = 350) -> str:
    t = (text or "").strip()
    if len(t) <= max_chars:
        return t
    return t[: max_chars - 3].rstrip() + "..."


def classify(rec: dict) -> tuple[str, dict]:
    q = rec["query"]
    top = rec["top30_raw"][:20]
    f1s = [token_f1(q["comment_text"], h["comment_text"]) for h in top]
    same_file = [h["file_path"] == q["file_path"] for h in top]
    max_f1_top10 = max(f1s[:10]) if f1s[:10] else 0.0
    same_file_top10 = any(same_file[:10])
    if max_f1_top10 >= 0.30:
        cls = "A_lexical_hit"
    elif same_file_top10:
        cls = "B_same_file_topical_only"
    else:
        cls = "C_no_obvious_match"
    return cls, {
        "max_f1_top10": max_f1_top10,
        "same_file_top10": same_file_top10,
        "sim_top1": top[0]["sim"] if top else 0.0,
        "has_suggestion_q": bool(q["has_suggestion"]),
    }


def pick_samples(records: list[dict], per_bucket: int, seed: int = 42) -> list[tuple[str, dict]]:
    buckets = defaultdict(list)
    for rec in records:
        cls, meta = classify(rec)
        buckets[cls].append((rec, meta))

    rng = np.random.default_rng(seed)
    picked: list[tuple[str, dict]] = []
    for cls in ["A_lexical_hit", "B_same_file_topical_only", "C_no_obvious_match"]:
        pool = buckets[cls]
        if not pool:
            continue
        n = min(per_bucket, len(pool))
        idxs = rng.choice(len(pool), size=n, replace=False)
        for i in idxs:
            picked.append((cls, pool[int(i)][0]))
    return picked


def render(records_with_class: list[tuple[str, dict]], per_query_k: int = 10) -> str:
    lines: list[str] = []
    lines.append("# Held-out retrieval — hand-inspection report")
    lines.append("")
    lines.append("Each query is a mathlib reviewer comment created on/after **2026-03-01** on a")
    lines.append("CLOSED PR. The index at query time was filtered to **before 2026-03-01** and")
    lines.append("`exclude_pr=query.pr_number` so retrieval must find cross-PR, temporally-earlier")
    lines.append("material. Max 2 hits per PR (MMR-lite). Similarity is cosine.")
    lines.append("")
    lines.append("Bucket legend:")
    lines.append("- **A_lexical_hit**: at least one top-10 hit shares >=30% tokens with ground truth (obvious win)")
    lines.append("- **B_same_file_topical_only**: top-10 pulls from the same `.lean` file but low lexical overlap")
    lines.append("- **C_no_obvious_match**: neither (worst case to inspect)")
    lines.append("")
    by_cls = defaultdict(list)
    for cls, rec in records_with_class:
        by_cls[cls].append(rec)

    for cls in ["A_lexical_hit", "B_same_file_topical_only", "C_no_obvious_match"]:
        recs = by_cls[cls]
        if not recs:
            continue
        lines.append(f"## Bucket: {cls}  ({len(recs)} samples)")
        lines.append("")
        for i, rec in enumerate(recs, 1):
            q = rec["query"]
            top = rec["top30_raw"][:per_query_k]
            f1s = [token_f1(q["comment_text"], h["comment_text"]) for h in top]
            lines.append(f"### {cls} — sample {i}")
            lines.append("")
            lines.append(f"- **Query PR**: #{q['pr_number']} — {truncate(q['pr_title'], 120)}")
            lines.append(f"- **File**: `{q['file_path']}`  (line {q['line']})")
            lines.append(f"- **Reviewer**: `{q['reviewer']}`  **Topics**: `{q['topic_labels'] or '(none)'}`")
            lines.append(f"- **Ground-truth comment** (what the reviewer actually wrote):")
            lines.append("")
            lines.append("  > " + truncate(q["comment_text"], 400).replace("\n", "\n  > "))
            lines.append("")
            lines.append(f"- **Query diff hunk head** (first 220 chars):")
            lines.append("")
            lines.append("  ```")
            lines.append("  " + truncate(q["embedding_text"], 220).replace("\n", "\n  "))
            lines.append("  ```")
            lines.append("")
            lines.append(f"- **Top-{per_query_k} retrieved comments** (from different PRs, strictly before cutoff):")
            lines.append("")
            lines.append("| # | sim | F1 | PR | file | reviewer | comment |")
            lines.append("|---|---|---|---|---|---|---|")
            for rank, (h, f1) in enumerate(zip(top, f1s), 1):
                same = " ← same file" if h["file_path"] == q["file_path"] else ""
                file_short = h["file_path"].replace("Mathlib/", "")
                comment = truncate(h["comment_text"].replace("|", r"\|").replace("\n", " "), 180)
                lines.append(
                    f"| {rank} | {h['sim']:.3f} | {f1:.2f} | #{h['pr_number']} | `{file_short}`{same} | `{h['reviewer']}` | {comment} |"
                )
            lines.append("")
            lines.append("---")
            lines.append("")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="data/eval/heldout_retrieval.jsonl")
    ap.add_argument("--output", default="data/eval/heldout_inspection_report.md")
    ap.add_argument("--per-bucket", type=int, default=10)
    ap.add_argument("--per-query-k", type=int, default=10)
    args = ap.parse_args()

    records = [json.loads(line) for line in (REPO_ROOT / args.input).open()]
    picked = pick_samples(records, per_bucket=args.per_bucket)
    out = render(picked, per_query_k=args.per_query_k)
    out_path = REPO_ROOT / args.output
    out_path.write_text(out)
    print(f"wrote {out_path}  ({len(picked)} samples)")


if __name__ == "__main__":
    main()
