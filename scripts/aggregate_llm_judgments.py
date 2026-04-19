#!/usr/bin/env python3
"""Aggregate LLM judgments into Hit@K metrics, per-query score distributions,
LLM vs lexical agreement, and a Markdown summary report."""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median


def load_judgments(path: str):
    return [json.loads(ln) for ln in open(path)]


def per_query(judgments: list[dict]) -> dict[str, list[dict]]:
    by_q = defaultdict(list)
    for j in judgments:
        by_q[j["query_record_id"]].append(j)
    for q in by_q:
        by_q[q].sort(key=lambda r: r["hit_rank"])
    return by_q


def hit_at_k(by_q: dict, ks=(1, 3, 5, 10)) -> dict:
    """Strict (>=2) and lenient (>=1) hit rates."""
    n = len(by_q)
    out = {"strict": {}, "lenient": {}}
    for k in ks:
        s = sum(1 for q in by_q.values()
                if any(h["label"] >= 2 for h in q[:k] if h["label"] >= 0))
        l = sum(1 for q in by_q.values()
                if any(h["label"] >= 1 for h in q[:k] if h["label"] >= 0))
        out["strict"][k] = (s, n, s / n)
        out["lenient"][k] = (l, n, l / n)
    return out


def label_distribution(judgments: list[dict]) -> dict:
    c = Counter(j["label"] for j in judgments)
    total = sum(c.values())
    return {str(k): (c[k], c[k] / total) for k in sorted(c)}


def per_query_max_label(by_q: dict) -> list[int]:
    return [max((h["label"] for h in q if h["label"] >= 0), default=-1) for q in by_q.values()]


def lexical_vs_llm(judgments: list[dict]) -> dict:
    """Confusion: high-lex (>=0.3) vs LLM label."""
    out = {"high_lex": Counter(), "low_lex": Counter()}
    for j in judgments:
        bucket = "high_lex" if j["lex_f1"] >= 0.3 else "low_lex"
        out[bucket][j["label"]] += 1
    return {k: dict(v) for k, v in out.items()}


def same_file_vs_llm(judgments: list[dict]) -> dict:
    out = {"same_file": Counter(), "diff_file": Counter()}
    for j in judgments:
        bucket = "same_file" if j["same_file"] else "diff_file"
        out[bucket][j["label"]] += 1
    return {k: dict(v) for k, v in out.items()}


def sim_vs_llm(judgments: list[dict]) -> dict:
    """Mean similarity per LLM label."""
    by_label = defaultdict(list)
    for j in judgments:
        by_label[j["label"]].append(j["sim"])
    return {str(k): {"n": len(v), "mean_sim": mean(v), "median_sim": median(v)}
            for k, v in sorted(by_label.items())}


def render_report(judgments, by_q, out_md: Path, retrieval_path: str):
    """Produce a Markdown report with metrics + 5 example queries."""
    n_q = len(by_q)
    n_j = len(judgments)
    hatk = hit_at_k(by_q)
    label_dist = label_distribution(judgments)
    max_labels = per_query_max_label(by_q)
    max_label_counts = Counter(max_labels)
    lex_v = lexical_vs_llm(judgments)
    sf_v = same_file_vs_llm(judgments)
    sim_v = sim_vs_llm(judgments)

    queries = {}
    for rec in (json.loads(ln) for ln in open(retrieval_path)):
        rid = rec["query"]["record_id"]
        if rid in by_q:
            queries[rid] = rec

    lines = []
    P = lines.append
    P(f"# LLM Judge (GPT-5) Held-Out Retrieval Report\n")
    P(f"- Queries judged: **{n_q}**")
    P(f"- Judgments total: **{n_j}** (top-10 per query)\n")

    P("## Rubric\n")
    P("- **2 (DIRECT)**: paraphrase / template / close analogue of ground-truth comment.")
    P("- **1 (PARTIAL)**: same file/module or related concern, but not the same advice.")
    P("- **0 (NONE)**: different issue, not directly useful.\n")

    P("## Hit@K (LLM-judged)\n")
    P("| K | Strict (any label = 2) | Lenient (any label >= 1) |")
    P("|---:|:---|:---|")
    for k in (1, 3, 5, 10):
        s_h, s_n, s_p = hatk["strict"][k]
        l_h, l_n, l_p = hatk["lenient"][k]
        P(f"| {k} | {s_h}/{s_n} = **{s_p:.0%}** | {l_h}/{l_n} = **{l_p:.0%}** |")
    P("")

    P("## Per-judgment label distribution (across all 200 hits)\n")
    P("| Label | Count | Share |")
    P("|---:|---:|---:|")
    for lab in ("0", "1", "2"):
        if lab in label_dist:
            c, p = label_dist[lab]
            P(f"| {lab} | {c} | {p:.0%} |")
    if "-1" in label_dist:
        c, p = label_dist["-1"]
        P(f"| -1 (parse-error) | {c} | {p:.0%} |")
    P("")

    P("## Per-query best label (out of top-10)\n")
    P("| Best label achieved | # queries |")
    P("|---:|---:|")
    for lab in (2, 1, 0, -1):
        if lab in max_label_counts:
            P(f"| {lab} | {max_label_counts[lab]} |")
    P("")

    P("## LLM label vs. lexical-F1 bucket\n")
    P("| Lex F1 bucket | label=0 | label=1 | label=2 |")
    P("|:---|---:|---:|---:|")
    for b in ("high_lex", "low_lex"):
        d = lex_v[b]
        total = sum(d.values())
        c0 = d.get(0, 0); c1 = d.get(1, 0); c2 = d.get(2, 0)
        P(f"| {b} (n={total}) | {c0} | {c1} | {c2} |")
    P("")

    P("## LLM label vs. same-file flag\n")
    P("| Same-file? | label=0 | label=1 | label=2 |")
    P("|:---|---:|---:|---:|")
    for b in ("same_file", "diff_file"):
        d = sf_v[b]
        total = sum(d.values())
        c0 = d.get(0, 0); c1 = d.get(1, 0); c2 = d.get(2, 0)
        P(f"| {b} (n={total}) | {c0} | {c1} | {c2} |")
    P("")

    P("## Similarity score vs. LLM label\n")
    P("| Label | n | mean cosine sim | median |")
    P("|---:|---:|---:|---:|")
    for lab, st in sim_v.items():
        if lab == "-1":
            continue
        P(f"| {lab} | {st['n']} | {st['mean_sim']:.3f} | {st['median_sim']:.3f} |")
    P("")

    P("---\n")
    P("## Per-query summary table\n")
    P("| # | PR | File | top-10 labels | best | any 2? |")
    P("|---:|---:|:---|:---|---:|:---:|")
    for i, (qid, hits) in enumerate(by_q.items(), 1):
        labs = [h["label"] for h in hits]
        best = max((l for l in labs if l >= 0), default=-1)
        any2 = "YES" if 2 in labs else ""
        q = queries[qid]["query"]
        file_short = q["file_path"].split("/")[-1]
        P(f"| {i} | {q['pr_number']} | `{file_short}` | {','.join(str(l) for l in labs)} | **{best}** | {any2} |")
    P("")

    P("---\n")
    P("## Example: queries with at least one DIRECT (label=2) hit\n")
    shown = 0
    for qid, hits in by_q.items():
        if not any(h["label"] == 2 for h in hits):
            continue
        if shown >= 5:
            break
        q = queries[qid]["query"]
        P(f"\n### PR #{q['pr_number']} — `{q['file_path']}`")
        P(f"**Ground-truth reviewer comment:**")
        P(f"> {q['comment_text'].strip()[:600]}\n")
        P(f"**Query hunk (excerpt):**")
        P("```")
        P(q["embedding_text"].strip()[:400])
        P("```\n")
        P(f"**Top-10 LLM labels:** {[h['label'] for h in hits]}")
        for h in hits:
            if h["label"] == 2:
                full_hits = queries[qid]["top20_capped"][:10]
                cand = next((c for c in full_hits if c["record_id"] == h["hit_record_id"]), None)
                P(f"\n  - **Rank {h['hit_rank']} (label=2, sim={h['sim']:.3f}):**")
                P(f"    - File: `{h['hit_file']}` (PR #{h['hit_pr']})")
                P(f"    - Rationale: {h['rationale']}")
                if cand:
                    P(f"    - Candidate comment: > {cand['comment_text'].strip()[:400]}")
        shown += 1
    P("")

    P("\n## Example: hard queries (best label = 0)\n")
    shown = 0
    for qid, hits in by_q.items():
        labs = [h["label"] for h in hits if h["label"] >= 0]
        if labs and max(labs) > 0:
            continue
        if shown >= 3:
            break
        q = queries[qid]["query"]
        P(f"\n### PR #{q['pr_number']} — `{q['file_path']}`")
        P(f"**Ground-truth reviewer comment:** > {q['comment_text'].strip()[:400]}")
        P(f"**Top-3 rationales:**")
        for h in hits[:3]:
            P(f"  - rank {h['hit_rank']} (sim {h['sim']:.3f}): {h['rationale'][:250]}")
        shown += 1

    out_md.write_text("\n".join(lines))
    print(f"wrote {out_md}")

    summary = {
        "n_queries": n_q,
        "n_judgments": n_j,
        "hit_at_k": {k: {"strict": hatk["strict"][k][2], "lenient": hatk["lenient"][k][2]}
                     for k in (1, 3, 5, 10)},
        "label_distribution": label_dist,
        "per_query_best_label": dict(max_label_counts),
        "lex_vs_llm": lex_v,
        "same_file_vs_llm": sf_v,
        "sim_per_label": sim_v,
    }
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--judgments", default="data/eval/llm_judgments.jsonl")
    ap.add_argument("--retrieval", default="data/eval/heldout_retrieval.jsonl")
    ap.add_argument("--out-md", default="data/eval/llm_judge_report.md")
    ap.add_argument("--out-json", default="data/eval/llm_judge_summary.json")
    args = ap.parse_args()

    judgments = load_judgments(args.judgments)
    by_q = per_query(judgments)
    summary = render_report(judgments, by_q, Path(args.out_md), args.retrieval)
    Path(args.out_json).write_text(json.dumps(summary, indent=2))
    print(f"wrote {args.out_json}")


if __name__ == "__main__":
    main()
