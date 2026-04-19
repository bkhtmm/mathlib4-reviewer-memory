"""Prompt-engineering ablation for the v1 review assistant.

Runs the SAME retrieval pool through TWO different system prompts (v1, v2) on
6 hand-picked cases, then prints a side-by-side comparison.

Cases:
  3 OPEN-PR cases from /tmp/open_pr_cases.json (PR #38109)
  2 known-good held-out closed-PR cases (PR #36007, PR #37009; LLM judge gave label=2)
  1 known-hard held-out closed-PR case   (PR #35939; LLM judge max label=0)

For each case we:
  1. retrieve once (or load precomputed retrieval for held-out cases)
  2. call GPT-5 with the v1 prompt
  3. call GPT-5 with the v2 prompt
  4. dump everything to data/eval/prompt_ablation.jsonl
  5. print a Markdown comparison report

Usage:
  OPENAI_API_KEY=... VOYAGE_API_KEY=... python scripts/run_prompt_ablation.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from pipeline.retrieval import Hit, Retriever  # noqa: E402
from product.review_assistant import ReviewAssistant  # noqa: E402


HELDOUT_CASES = {
    36007: "known-good (LLM judge label=2)",
    37009: "known-good (LLM judge label=2)",
    35939: "hard      (LLM judge max label=0)",
}

HELDOUT_PATH = REPO / "data/eval/heldout_retrieval.jsonl"
OPEN_CASES_PATH = Path("/tmp/open_pr_cases.json")
OUT_PATH = REPO / "data/eval/prompt_ablation.jsonl"
REPORT_PATH = REPO / "data/eval/prompt_ablation_report.md"

DATE_BEFORE = "2026-03-01"


def hit_from_dict(d: dict) -> Hit:
    return Hit(
        rank=int(d["rank"]),
        sim=float(d["sim"]),
        record_id=str(d["record_id"]),
        pr_number=int(d["pr_number"]),
        pr_title=str(d.get("pr_title") or ""),
        file_path=str(d.get("file_path") or ""),
        line=d.get("line"),
        reviewer=str(d.get("reviewer") or ""),
        topic_labels=str(d.get("topic_labels") or ""),
        has_suggestion=bool(d.get("has_suggestion") or False),
        comment_text=str(d.get("comment_text") or ""),
        embedding_text=str(d.get("embedding_text") or ""),
        created_at=str(d.get("created_at") or ""),
    )


def load_heldout_cases(path: Path, prs: list[int]) -> list[dict]:
    wanted = set(prs)
    found: dict[int, dict] = {}
    with path.open() as f:
        for line in f:
            j = json.loads(line)
            pr = int(j["query"]["pr_number"])
            if pr in wanted and pr not in found:
                found[pr] = j
                if len(found) == len(wanted):
                    break
    cases = []
    for pr in prs:
        if pr not in found:
            print(f"  [warn] PR {pr} not found in heldout retrieval", file=sys.stderr)
            continue
        j = found[pr]
        q = j["query"]
        hits = [hit_from_dict(h) for h in j["top20_capped"]]
        cases.append({
            "case_kind": "heldout-closed",
            "case_label": HELDOUT_CASES[pr],
            "pr": pr,
            "file": q["file_path"],
            "line": q.get("line"),
            "reviewer": q.get("reviewer", ""),
            "reviewer_said": q.get("comment_text", ""),
            "hunk": q.get("embedding_text", ""),
            "precomputed_hits": hits,
        })
    return cases


def load_open_cases(path: Path) -> list[dict]:
    with path.open() as f:
        raw = json.load(f)
    cases = []
    for r in raw:
        cases.append({
            "case_kind": "open-pr",
            "case_label": "live open PR (no precomputed hits)",
            "pr": r["pr"],
            "file": r["file"],
            "line": r["line"],
            "reviewer": r.get("reviewer", ""),
            "reviewer_said": r["reviewer_said"],
            "hunk": r["hunk"],
            "precomputed_hits": None,
        })
    return cases


def run_one(
    assistant: ReviewAssistant,
    case: dict,
    *,
    label: str,
) -> dict:
    t0 = time.time()
    sug = assistant.review_hunk(
        hunk_text=case["hunk"],
        new_file=case["file"] or "<unknown>",
        new_pr_marker=str(case["pr"]),
        top_k=20,
        max_per_pr=2,
        date_before=DATE_BEFORE if case["case_kind"] == "heldout-closed" else None,
        precomputed_hits=case.get("precomputed_hits"),
    )
    dt = time.time() - t0
    return {
        "prompt_version": label,
        "summary": sug.summary,
        "confidence": sug.confidence,
        "strong_matches": sug.strong_matches,
        "weak_observations": sug.weak_observations,
        "n_candidates": len(sug.raw_candidates),
        "usage": sug.usage,
        "latency_sec": round(dt, 2),
    }


def truncate(s: str, n: int) -> str:
    s = s or ""
    return s if len(s) <= n else s[: n - 3] + "..."


def render_report(rows: list[dict]) -> str:
    lines = []
    lines.append("# Prompt-engineering ablation report")
    lines.append("")
    lines.append(f"Date: {time.strftime('%Y-%m-%d %H:%M')}  Cases: {len(rows)}")
    lines.append("")

    total_v1_in = sum(r["v1"]["usage"]["prompt_tokens"] for r in rows)
    total_v1_out = sum(r["v1"]["usage"]["completion_tokens"] for r in rows)
    total_v2_in = sum(r["v2"]["usage"]["prompt_tokens"] for r in rows)
    total_v2_out = sum(r["v2"]["usage"]["completion_tokens"] for r in rows)
    cost_v1 = total_v1_in / 1e6 * 1.25 + total_v1_out / 1e6 * 10.0
    cost_v2 = total_v2_in / 1e6 * 1.25 + total_v2_out / 1e6 * 10.0
    lines.append("## Token usage and cost (gpt-5 pricing: $1.25/M in, $10/M out)")
    lines.append("")
    lines.append(f"- v1: prompt={total_v1_in:,}  completion={total_v1_out:,}  ~${cost_v1:.3f}")
    lines.append(f"- v2: prompt={total_v2_in:,}  completion={total_v2_out:,}  ~${cost_v2:.3f}")
    lines.append("")

    for i, r in enumerate(rows, 1):
        c = r["case"]
        lines.append("---")
        lines.append("")
        lines.append(f"## Case {i}: PR #{c['pr']} ({c['case_kind']}, {c['case_label']})")
        lines.append("")
        lines.append(f"**File:** `{c['file']}` line={c['line']}")
        lines.append("")
        lines.append("**New hunk (truncated):**")
        lines.append("")
        lines.append("```")
        lines.append(truncate(c["hunk"], 1200))
        lines.append("```")
        lines.append("")
        lines.append("**Human reviewer said:**")
        lines.append("")
        lines.append("> " + truncate(c["reviewer_said"], 600).replace("\n", "\n> "))
        lines.append("")

        for ver in ("v1", "v2"):
            o = r[ver]
            lines.append(f"### Prompt {ver}  (confidence={o['confidence']}, "
                         f"strong={len(o['strong_matches'])}, "
                         f"weak={len(o['weak_observations'])}, "
                         f"tokens={o['usage']['prompt_tokens']}/{o['usage']['completion_tokens']}, "
                         f"{o['latency_sec']}s)")
            lines.append("")
            lines.append(f"_summary_: {o['summary']}")
            lines.append("")
            if o["strong_matches"]:
                lines.append("**Strong matches:**")
                lines.append("")
                for sm in o["strong_matches"]:
                    pr = sm.get("past_pr", "?")
                    ex = truncate(sm.get("past_comment_excerpt", ""), 300)
                    why = truncate(sm.get("applies_because", ""), 400)
                    sug = truncate(sm.get("suggested_adaptation", ""), 400)
                    sup = sm.get("supporting_past_prs") or []
                    lines.append(f"- PR #{pr}  (support: {sup})")
                    lines.append(f"  - excerpt: {ex}")
                    lines.append(f"  - why: {why}")
                    lines.append(f"  - adapt: {sug}")
                lines.append("")
            else:
                lines.append("_no strong matches_")
                lines.append("")
            if o["weak_observations"]:
                lines.append("**Weak observations:**")
                for w in o["weak_observations"]:
                    obs = truncate(w.get("observation", ""), 300)
                    sup = w.get("supporting_past_prs") or []
                    lines.append(f"- {obs}  (support: {sup})")
                lines.append("")
    return "\n".join(lines)


def main() -> None:
    print("Loading retriever...", flush=True)
    R = Retriever()
    asst_v1 = ReviewAssistant(retriever=R, prompt_version="v1")
    asst_v2 = ReviewAssistant(retriever=R, prompt_version="v2")

    print("Loading cases...", flush=True)
    cases = []
    cases += load_open_cases(OPEN_CASES_PATH)
    cases += load_heldout_cases(HELDOUT_PATH, [36007, 37009, 35939])

    print(f"  total {len(cases)} cases", flush=True)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    with OUT_PATH.open("w") as out:
        for i, c in enumerate(cases, 1):
            print(f"[{i}/{len(cases)}] PR #{c['pr']} ({c['case_kind']})", flush=True)
            print("  v1...", flush=True)
            v1 = run_one(asst_v1, c, label="v1")
            print(f"    confidence={v1['confidence']} strong={len(v1['strong_matches'])} "
                  f"toks={v1['usage']['prompt_tokens']}/{v1['usage']['completion_tokens']} "
                  f"{v1['latency_sec']}s", flush=True)
            print("  v2...", flush=True)
            v2 = run_one(asst_v2, c, label="v2")
            print(f"    confidence={v2['confidence']} strong={len(v2['strong_matches'])} "
                  f"toks={v2['usage']['prompt_tokens']}/{v2['usage']['completion_tokens']} "
                  f"{v2['latency_sec']}s", flush=True)
            row = {
                "case": {k: v for k, v in c.items() if k != "precomputed_hits"},
                "v1": v1,
                "v2": v2,
            }
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            out.flush()
            rows.append(row)

    print(f"\nWrote {OUT_PATH}", flush=True)
    md = render_report(rows)
    REPORT_PATH.write_text(md)
    print(f"Wrote {REPORT_PATH}", flush=True)


if __name__ == "__main__":
    main()
