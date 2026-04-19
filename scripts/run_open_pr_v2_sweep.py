"""Run the v2 review-assistant prompt on 10 hand-picked open-PR comments.

Picks are diverse across topical area, reviewer, and KIND of advice (notation,
naming, attribute, refactor, design smell, docstring, signature, etc.) so that
the failure-mode landscape is broad.

Usage:
  OPENAI_API_KEY=... VOYAGE_API_KEY=... python3 scripts/run_open_pr_v2_sweep.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from pipeline.retrieval import Retriever  # noqa: E402
from product.review_assistant import (  # noqa: E402
    CANDIDATE_TEMPLATE,
    SYSTEM_PROMPT_V2,
    USER_TEMPLATE,
    ReviewAssistant,
    _truncate,
)

# 10 picks: (tag, pr, file, line, reviewer, advice_kind)
CASES = [
    ("D",  36621, "Mathlib/Topology/Category/TopPair.lean", 15.0,
     "vlad902", "module-structure / file header"),
    ("E",  28349, "Mathlib/Tactic/Ring/NamePolyVars.lean", 288.0,
     "eric-wieser", "design smell: string output"),
    ("F",  33355, "Mathlib/Combinatorics/SimpleGraph/Connectivity/VertexConnectivity.lean", 130.0,
     "vihdzp", "naming + edge case"),
    ("G",  26345, "Mathlib/Analysis/LocallyConvex/Bipolar.lean", 99.0,
     "eric-wieser", "signature change (suggestion block)"),
    ("H",  36731, "Mathlib/Geometry/PlaneCurves.lean", 6.0,
     "grunweg", "minimise imports"),
    ("I",  31425, "Mathlib/Topology/Defs/Basic.lean", 207.0,
     "eric-wieser", "needs explanatory comment"),
    ("J",  36698, "Mathlib/Combinatorics/Enumerative/LatinSquare.lean", 257.0,
     "vlad902", "refactor (suggestion block)"),
    ("K",  33664, "Mathlib/Geometry/Convex/Cone/Pointed/Face/Basic.lean", 44.0,
     "eric-wieser", "docstring suggestion"),
    ("L",  35287, "Mathlib/AlgebraicTopology/SimplicialSet/CoherentIso.lean", 58.0,
     "robin-carlier", "additional instances suggestion"),
    ("M",  36621, "Mathlib/Topology/Category/TopPair.lean", 136.0,
     "vlad902", "naturality definition (suggestion)"),
]

RC_PATH = REPO / "data/curated/mathlib4/review_comments.parquet"
OUT_JSONL = REPO / "data/eval/openpr_v2_sweep.jsonl"
TRANSCRIPT_DIR = REPO / "data/eval/transcripts"


def find_case(rc: pd.DataFrame, tag: str, pr: int, file: str, line: float,
              reviewer: str, kind: str) -> dict:
    sub = rc[(rc["pr_number"] == pr) & (rc["path"] == file)
             & (rc["line"] == line) & (rc["author_login"] == reviewer)]
    if sub.empty:
        raise SystemExit(f"could not locate comment for {tag} (PR {pr}, line {line})")
    row = sub.iloc[0]
    return {
        "tag": tag, "pr_number": pr, "file": file, "line": line,
        "reviewer_login": reviewer, "advice_kind": kind,
        "reviewer_said": str(row["body"] or ""),
        "hunk": str(row["diff_hunk"] or ""),
        "comment_created_at": str(row["created_at"]),
        "html_url": str(row["html_url"]),
    }


def build_user_msg(hunk: str, file: str, pr_marker: str, hits: list) -> str:
    cand_block = "\n".join(
        CANDIDATE_TEMPLATE.format(
            idx=i + 1, sim=h.sim, pr=h.pr_number, file=h.file_path,
            hunk=_truncate(h.embedding_text, 1600),
            comment=_truncate(h.comment_text, 800),
        )
        for i, h in enumerate(hits)
    )
    return USER_TEMPLATE.format(
        new_pr_marker=pr_marker, new_file=file,
        new_hunk=_truncate(hunk, 2500),
        n=len(hits), candidates_block=cand_block,
    )


def write_transcript(case: dict, hits: list, sug, path: Path) -> None:
    user_msg = build_user_msg(case["hunk"], case["file"], str(case["pr_number"]), hits)
    visible = {
        "summary": sug.summary, "confidence": sug.confidence,
        "strong_matches": sug.strong_matches,
        "weak_observations": sug.weak_observations,
    }
    assistant_text = json.dumps(visible, indent=2, ensure_ascii=False)

    with path.open("w") as f:
        f.write("=" * 100 + "\n")
        f.write(f"CASE {case['tag']}  PR #{case['pr_number']}  (open-pr, v2 prompt)\n")
        f.write(f"file: {case['file']}  line: {case['line']}\n")
        f.write(f"reviewer: @{case['reviewer_login']}  on {case['comment_created_at']}\n")
        f.write(f"advice_kind: {case['advice_kind']}\n")
        f.write(f"prompt_tokens: {sug.usage['prompt_tokens']}  "
                f"completion_tokens: {sug.usage['completion_tokens']}\n")
        f.write("HUMAN reviewer (ground truth):\n")
        for ln in case["reviewer_said"].splitlines():
            f.write("  > " + ln + "\n")
        f.write("=" * 100 + "\n\n")

        f.write("[SYSTEM]\n" + "-" * 100 + "\n")
        f.write(SYSTEM_PROMPT_V2)
        if not SYSTEM_PROMPT_V2.endswith("\n"):
            f.write("\n")
        f.write("\n")

        f.write("[USER]\n" + "-" * 100 + "\n")
        f.write(user_msg)
        if not user_msg.endswith("\n"):
            f.write("\n")
        f.write("\n")

        f.write("[ASSISTANT]\n" + "-" * 100 + "\n")
        f.write(assistant_text + "\n")


def main() -> None:
    rc = pd.read_parquet(RC_PATH)
    print(f"loaded {len(rc):,} review comments", flush=True)

    cases = [find_case(rc, *spec) for spec in CASES]
    for c in cases:
        snippet = c["reviewer_said"].replace("\n", " / ")[:90]
        print(f"  case {c['tag']}: PR #{c['pr_number']:>5} line {c['line']:>5}  "
              f"@{c['reviewer_login']:<18} -> {snippet}", flush=True)

    print("\nloading retriever + assistant (v2)...", flush=True)
    R = Retriever()
    asst = ReviewAssistant(retriever=R, prompt_version="v2")

    TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSONL.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    with OUT_JSONL.open("w") as out:
        for c in cases:
            print(f"\n[{c['tag']}] PR #{c['pr_number']}...", flush=True)
            t0 = time.time()
            qv = R.embed_text(c["hunk"])
            hits = R.search(qv, k=20, max_per_pr=2, date_before=None)
            sug = asst.review_hunk(
                hunk_text=c["hunk"], new_file=c["file"],
                new_pr_marker=str(c["pr_number"]),
                top_k=20, max_per_pr=2,
                precomputed_hits=hits,
            )
            dt = time.time() - t0

            tpath = TRANSCRIPT_DIR / f"openpr_{c['tag']}_v2.txt"
            write_transcript(c, hits, sug, tpath)

            row = {
                **c,
                "summary": sug.summary, "confidence": sug.confidence,
                "strong_matches": sug.strong_matches,
                "weak_observations": sug.weak_observations,
                "n_candidates": len(hits), "usage": sug.usage,
                "latency_sec": round(dt, 2),
                "transcript_path": str(tpath.relative_to(REPO)),
            }
            rows.append(row)
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            out.flush()
            print(f"    confidence={sug.confidence}  "
                  f"strong={len(sug.strong_matches)}  weak={len(sug.weak_observations)}  "
                  f"toks={sug.usage['prompt_tokens']}/{sug.usage['completion_tokens']}  "
                  f"{dt:.1f}s",
                  flush=True)

    print(f"\nwrote {OUT_JSONL.relative_to(REPO)}", flush=True)
    total_in = sum(r["usage"]["prompt_tokens"] for r in rows)
    total_out = sum(r["usage"]["completion_tokens"] for r in rows)
    cost = total_in / 1e6 * 1.25 + total_out / 1e6 * 10.0
    print(f"total tokens: in={total_in:,}  out={total_out:,}  cost ~${cost:.3f}",
          flush=True)


if __name__ == "__main__":
    main()
