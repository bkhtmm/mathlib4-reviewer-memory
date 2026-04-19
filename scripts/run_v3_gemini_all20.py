"""Run SYSTEM_PROMPT_V3 on the same 20 open-PR cases, but via Gemini 2.5 Flash.

Identical pipeline to `run_v3_sweep_all20.py` (same retrieval, same windowing,
same v3 prompt) — only the LLM backend changes. Used for a head-to-head
comparison against `data/eval/openpr_v3_all20.jsonl` (GPT-5 run).

Outputs:
  data/eval/openpr_v3_gemini_all20.jsonl
  data/eval/transcripts/openpr_<tag>_v3_gemini.txt

Usage:
  GEMINI_API_KEY=... VOYAGE_API_KEY=... python3 scripts/run_v3_gemini_all20.py
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
    SYSTEM_PROMPT_V3,
    USER_TEMPLATE,
    ReviewAssistant,
    _hunk_window,
    _truncate,
)

# Same 20 cases as run_v3_sweep_all20.py
CASES = [
    ("D",  36621, "Mathlib/Topology/Category/TopPair.lean", 15.0, "vlad902", "module-structure / file header"),
    ("E",  28349, "Mathlib/Tactic/Ring/NamePolyVars.lean", 288.0, "eric-wieser", "design smell: string output"),
    ("F",  33355, "Mathlib/Combinatorics/SimpleGraph/Connectivity/VertexConnectivity.lean", 130.0, "vihdzp", "naming + edge case"),
    ("G",  26345, "Mathlib/Analysis/LocallyConvex/Bipolar.lean", 99.0, "eric-wieser", "signature change (suggestion block)"),
    ("H",  36731, "Mathlib/Geometry/PlaneCurves.lean", 6.0, "grunweg", "minimise imports"),
    ("I",  31425, "Mathlib/Topology/Defs/Basic.lean", 207.0, "eric-wieser", "needs explanatory comment"),
    ("J",  36698, "Mathlib/Combinatorics/Enumerative/LatinSquare.lean", 257.0, "vlad902", "refactor (suggestion block)"),
    ("K",  33664, "Mathlib/Geometry/Convex/Cone/Pointed/Face/Basic.lean", 44.0, "eric-wieser", "docstring suggestion"),
    ("L",  35287, "Mathlib/AlgebraicTopology/SimplicialSet/CoherentIso.lean", 58.0, "robin-carlier", "additional instances suggestion"),
    ("M",  36621, "Mathlib/Topology/Category/TopPair.lean", 136.0, "vlad902", "naturality definition (suggestion)"),
    ("N", 24627, "Mathlib/Topology/Algebra/Valued/ValuedField.lean", 410.0, "loefflerd", "suggestion block (proof rewrite)"),
    ("O", 23929, "Mathlib/Computability/NFA.lean", 194.0, "meithecatte", "naming (lemma rename)"),
    ("P", 21950, "Mathlib/NumberTheory/Padics/HeightOneSpectrum.lean", 98.0, "Ruben-VandeVelde", "attribute / suggestion block"),
    ("Q", 25218, "Mathlib/AlgebraicGeometry/EllipticCurve/Modular/TateNormalForm.lean", 70.0, "MichaelStollBayreuth", "docstring rewording"),
    ("R", 25427, "Mathlib/LinearAlgebra/Basis/HasCanonicalBasis.lean", 92.0, "lecopivo", "design smell: unnecessary instance"),
    ("S", 22919, "Mathlib/Data/Fintype/Pi.lean", 235.0, "eric-wieser", "refactor (unnecessary transport)"),
    ("T", 20431, "Mathlib/RingTheory/AdicCompletion/Basic.lean", 535.0, "chrisflav", "design smell: _root_ placement"),
    ("U", 22308, "Mathlib/Analysis/Convex/Gauge.lean", 209.0, "Paul-Lez", "suggestion: add helper lemma"),
    ("V", 21624, "Mathlib/CategoryTheory/Pi/Monoidal.lean", 50.0, "b-mehta", "signature / automation suggestion"),
    ("W", 34007, "Mathlib/Algebra/Module/Submodule/Dual.lean", 49.0, "joelriou", "generalize: two modules M₁/M₂ not one"),
]

RC_PATH = REPO / "data/curated/mathlib4/review_comments.parquet"
OUT_JSONL = REPO / "data/eval/openpr_v3_gemini_all20.jsonl"
TRANSCRIPT_DIR = REPO / "data/eval/transcripts"
GEMINI_MODEL = "gemini-2.5-flash"


def find_case(rc, tag, pr, file, line, reviewer, kind):
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


def build_user_msg(hunk, file, pr_marker, comment_line, hits):
    cand_block = "\n".join(
        CANDIDATE_TEMPLATE.format(
            idx=i + 1, sim=h.sim, pr=h.pr_number, file=h.file_path,
            hunk=_hunk_window(h.embedding_text, h.line, before=12, after=12),
            comment=_truncate(h.comment_text, 800),
        )
        for i, h in enumerate(hits)
    )
    return USER_TEMPLATE.format(
        new_pr_marker=pr_marker, new_file=file,
        new_hunk=_hunk_window(hunk, comment_line, before=40, after=40),
        n=len(hits), candidates_block=cand_block,
    )


def write_transcript(case, hits, sug, path, plausible):
    user_msg = build_user_msg(case["hunk"], case["file"], str(case["pr_number"]),
                              case["line"], hits)
    visible = {
        "new_hunk_plausible_concerns": plausible,
        "summary": sug.summary, "confidence": sug.confidence,
        "strong_matches": sug.strong_matches,
        "weak_observations": sug.weak_observations,
    }
    with path.open("w") as f:
        f.write("=" * 100 + "\n")
        f.write(f"CASE {case['tag']}  PR #{case['pr_number']}  (open-pr, v3 prompt, Gemini)\n")
        f.write(f"file: {case['file']}  line: {case['line']}\n")
        f.write(f"reviewer: @{case['reviewer_login']}  on {case['comment_created_at']}\n")
        f.write(f"advice_kind: {case['advice_kind']}\n")
        f.write(f"model: {sug.usage.get('model','?')}  "
                f"prompt_tokens: {sug.usage['prompt_tokens']}  "
                f"completion_tokens: {sug.usage['completion_tokens']}\n")
        f.write("HUMAN reviewer (ground truth):\n")
        for ln in case["reviewer_said"].splitlines():
            f.write("  > " + ln + "\n")
        f.write("=" * 100 + "\n\n")

        f.write("[SYSTEM]\n" + "-" * 100 + "\n")
        f.write(SYSTEM_PROMPT_V3)
        if not SYSTEM_PROMPT_V3.endswith("\n"):
            f.write("\n")
        f.write("\n")

        f.write("[USER]\n" + "-" * 100 + "\n")
        f.write(user_msg)
        if not user_msg.endswith("\n"):
            f.write("\n")
        f.write("\n")

        f.write("[ASSISTANT]\n" + "-" * 100 + "\n")
        f.write(json.dumps(visible, indent=2, ensure_ascii=False) + "\n")


def main():
    rc = pd.read_parquet(RC_PATH)
    print(f"loaded {len(rc):,} review comments", flush=True)
    cases = [find_case(rc, *spec) for spec in CASES]

    TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSONL.parent.mkdir(parents=True, exist_ok=True)

    done: set[str] = set()
    if OUT_JSONL.exists():
        with OUT_JSONL.open("r") as f:
            for ln in f:
                try:
                    done.add(json.loads(ln)["tag"])
                except Exception:
                    pass
        if done:
            print(f"resuming — {len(done)} cases already done: {sorted(done)}",
                  flush=True)
    todo = [c for c in cases if c["tag"] not in done]
    print(f"running v3 on {len(todo)} case(s) via Gemini ({GEMINI_MODEL})\n",
          flush=True)

    R = Retriever()
    asst = ReviewAssistant(
        retriever=R, prompt_version="v3",
        provider="gemini", gemini_model=GEMINI_MODEL,
    )

    rows: list[dict] = []
    mode = "a" if done else "w"
    with OUT_JSONL.open(mode) as out:
        cases = todo  # only iterate what's left
        for c in cases:
            print(f"[{c['tag']}] PR #{c['pr_number']}...", flush=True)
            t0 = time.time()
            qv = R.embed_text(c["hunk"])
            hits = R.search(qv, k=20, max_per_pr=2, date_before=None)
            sug = asst.review_hunk(
                hunk_text=c["hunk"], new_file=c["file"],
                new_pr_marker=str(c["pr_number"]),
                top_k=20, max_per_pr=2,
                precomputed_hits=hits,
                comment_line=c["line"],
                new_window_before=40, new_window_after=40,
                cand_window_before=12, cand_window_after=12,
            )
            dt = time.time() - t0

            plausible = (sug.extras or {}).get("new_hunk_plausible_concerns") or []
            tpath = TRANSCRIPT_DIR / f"openpr_{c['tag']}_v3_gemini.txt"
            write_transcript(c, hits, sug, tpath, plausible)

            row = {
                **c,
                "plausible_concerns": plausible,
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
            axes = [m.get("past_concern_axis", "?") for m in sug.strong_matches]
            print(f"    conf={sug.confidence}  strong={len(sug.strong_matches)} "
                  f"{axes}  weak={len(sug.weak_observations)}  "
                  f"toks={sug.usage['prompt_tokens']}/{sug.usage['completion_tokens']}  "
                  f"{dt:.1f}s",
                  flush=True)
            # Light rate-limiting: Flash free tier allows ~15 RPM; give 3s spacing.
            time.sleep(3)

    # final totals include both pre-existing (resumed) and new rows
    all_rows = [json.loads(ln) for ln in OUT_JSONL.open("r")]
    print(f"\nwrote {OUT_JSONL.relative_to(REPO)}  ({len(all_rows)} rows total)",
          flush=True)
    ti = sum(r["usage"]["prompt_tokens"] for r in all_rows)
    to = sum(r["usage"]["completion_tokens"] for r in all_rows)
    print(f"total tokens: in={ti:,}  out={to:,}", flush=True)


if __name__ == "__main__":
    main()
