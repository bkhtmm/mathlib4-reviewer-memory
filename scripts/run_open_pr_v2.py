"""Run the v2 review-assistant prompt on 3 hand-picked open-PR comments.

For each case:
  1. Extract the new diff hunk + the human reviewer comment
  2. Run the v2 prompt (top-20 retrieval + GPT-5 with structural-pattern protocol)
  3. Save the FULL chat transcript (system / user / assistant) to disk
  4. Print a side-by-side summary

Cases (chosen for topical / advice diversity):
  A. PR #33664  — convex cones      — eric-wieser, line 244 — \\inter notation
  B. PR #35287  — simplicial sets   — robin-carlier, line 51 — universe w convention
  C. PR #22361  — NFA               — EtienneC30, line 90    — docstring rewrite

Usage:
  OPENAI_API_KEY=... VOYAGE_API_KEY=... python3 scripts/run_open_pr_v2.py
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

CASES = [
    {
        "tag": "A",
        "pr_number": 33664,
        "file": "Mathlib/Geometry/Convex/Cone/Pointed/Basic.lean",
        "line": 244.0,
        "reviewer_login": "eric-wieser",
    },
    {
        "tag": "B",
        "pr_number": 35287,
        "file": "Mathlib/AlgebraicTopology/SimplicialSet/CoherentIso.lean",
        "line": 51.0,
        "reviewer_login": "robin-carlier",
    },
    {
        "tag": "C",
        "pr_number": 22361,
        "file": "Mathlib/Computability/NFA.lean",
        "line": 90.0,
        "reviewer_login": "EtienneC30",
    },
]

RC_PATH = REPO / "data/curated/mathlib4/review_comments.parquet"
OUT_JSON = REPO / "data/eval/openpr_v2_results.jsonl"
TRANSCRIPT_DIR = REPO / "data/eval/transcripts"


def find_case(rc: pd.DataFrame, spec: dict) -> dict:
    sub = rc[
        (rc["pr_number"] == spec["pr_number"])
        & (rc["path"] == spec["file"])
        & (rc["line"] == spec["line"])
        & (rc["author_login"] == spec["reviewer_login"])
    ]
    if sub.empty:
        raise SystemExit(f"could not locate comment for {spec}")
    row = sub.iloc[0]
    return {
        **spec,
        "reviewer_said": str(row["body"] or ""),
        "hunk": str(row["diff_hunk"] or ""),
        "comment_created_at": str(row["created_at"]),
        "html_url": str(row["html_url"]),
    }


def build_user_msg(hunk: str, file: str, pr_marker: str, hits: list) -> str:
    cand_block = "\n".join(
        CANDIDATE_TEMPLATE.format(
            idx=i + 1,
            sim=h.sim,
            pr=h.pr_number,
            file=h.file_path,
            hunk=_truncate(h.embedding_text, 1600),
            comment=_truncate(h.comment_text, 800),
        )
        for i, h in enumerate(hits)
    )
    return USER_TEMPLATE.format(
        new_pr_marker=pr_marker,
        new_file=file,
        new_hunk=_truncate(hunk, 2500),
        n=len(hits),
        candidates_block=cand_block,
    )


def write_transcript(case: dict, hits: list, sug, path: Path) -> None:
    user_msg = build_user_msg(case["hunk"], case["file"], str(case["pr_number"]), hits)
    visible = {
        "summary": sug.summary,
        "confidence": sug.confidence,
        "strong_matches": sug.strong_matches,
        "weak_observations": sug.weak_observations,
    }
    assistant_text = json.dumps(visible, indent=2, ensure_ascii=False)

    with path.open("w") as f:
        f.write("=" * 100 + "\n")
        f.write(f"CASE {case['tag']}  PR #{case['pr_number']}  (open-pr, v2 prompt)\n")
        f.write(f"file: {case['file']}  line: {case['line']}\n")
        f.write(f"reviewer: @{case['reviewer_login']}  on {case['comment_created_at']}\n")
        f.write(f"url: {case['html_url']}\n")
        f.write(f"prompt_tokens: {sug.usage['prompt_tokens']}  "
                f"completion_tokens: {sug.usage['completion_tokens']}\n")
        f.write("HUMAN reviewer (ground truth):\n")
        for ln in case["reviewer_said"].splitlines():
            f.write("  > " + ln + "\n")
        f.write("=" * 100 + "\n\n")

        f.write("[SYSTEM]\n")
        f.write("-" * 100 + "\n")
        f.write(SYSTEM_PROMPT_V2)
        if not SYSTEM_PROMPT_V2.endswith("\n"):
            f.write("\n")
        f.write("\n")

        f.write("[USER]\n")
        f.write("-" * 100 + "\n")
        f.write(user_msg)
        if not user_msg.endswith("\n"):
            f.write("\n")
        f.write("\n")

        f.write("[ASSISTANT]\n")
        f.write("-" * 100 + "\n")
        f.write(assistant_text + "\n")


def main() -> None:
    rc = pd.read_parquet(RC_PATH)
    print(f"loaded {len(rc):,} review comments", flush=True)

    cases = [find_case(rc, spec) for spec in CASES]
    for c in cases:
        print(f"  case {c['tag']}: PR #{c['pr_number']} line {c['line']} "
              f"by @{c['reviewer_login']}", flush=True)

    print("\nloading retriever + assistant (v2)...", flush=True)
    R = Retriever()
    asst = ReviewAssistant(retriever=R, prompt_version="v2")

    TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    with OUT_JSON.open("w") as out:
        for c in cases:
            print(f"\n[{c['tag']}] retrieving + reasoning for PR #{c['pr_number']}...",
                  flush=True)
            t0 = time.time()
            query_vec = R.embed_text(c["hunk"])
            hits = R.search(query_vec, k=20, max_per_pr=2, date_before=None)
            sug = asst.review_hunk(
                hunk_text=c["hunk"],
                new_file=c["file"],
                new_pr_marker=str(c["pr_number"]),
                top_k=20,
                max_per_pr=2,
                precomputed_hits=hits,
            )
            dt = time.time() - t0

            tpath = TRANSCRIPT_DIR / f"openpr_{c['tag']}_v2.txt"
            write_transcript(c, hits, sug, tpath)

            row = {
                "case_tag": c["tag"],
                "pr_number": c["pr_number"],
                "file": c["file"],
                "line": c["line"],
                "reviewer_login": c["reviewer_login"],
                "reviewer_said": c["reviewer_said"],
                "html_url": c["html_url"],
                "summary": sug.summary,
                "confidence": sug.confidence,
                "strong_matches": sug.strong_matches,
                "weak_observations": sug.weak_observations,
                "n_candidates": len(hits),
                "usage": sug.usage,
                "latency_sec": round(dt, 2),
                "transcript_path": str(tpath.relative_to(REPO)),
            }
            rows.append(row)
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            out.flush()
            print(f"    confidence={sug.confidence}  "
                  f"strong={len(sug.strong_matches)}  weak={len(sug.weak_observations)}  "
                  f"toks={sug.usage['prompt_tokens']}/{sug.usage['completion_tokens']}  "
                  f"{dt:.1f}s  -> {tpath.relative_to(REPO)}",
                  flush=True)

    print(f"\nwrote {OUT_JSON.relative_to(REPO)}", flush=True)
    print("\n" + "=" * 100, flush=True)
    print("SUMMARY", flush=True)
    print("=" * 100, flush=True)
    total_in = sum(r["usage"]["prompt_tokens"] for r in rows)
    total_out = sum(r["usage"]["completion_tokens"] for r in rows)
    cost = total_in / 1e6 * 1.25 + total_out / 1e6 * 10.0
    print(f"total tokens: in={total_in:,}  out={total_out:,}  cost ~${cost:.3f}",
          flush=True)


if __name__ == "__main__":
    main()
