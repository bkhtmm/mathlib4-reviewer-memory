"""Reconstruct and dump the EXACT chat-style transcript that GPT-5 saw for
each of the 12 ablation calls.

Each file has three sections:
  [SYSTEM]    — verbatim v1 or v2 system prompt
  [USER]      — verbatim user message (USER_TEMPLATE filled with new hunk + 20 candidates)
  [ASSISTANT] — verbatim JSON the model returned

For the 3 held-out closed-PR cases the retrieval is loaded from
data/eval/heldout_retrieval.jsonl (deterministic). For the 3 open-PR cases
we re-run Voyage embed + retrieve (also deterministic given the same date
filter and corpus snapshot).

Output: data/eval/transcripts/case{N}_{ver}.txt
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from pipeline.retrieval import Hit, Retriever  # noqa: E402
from product.review_assistant import (  # noqa: E402
    CANDIDATE_TEMPLATE,
    SYSTEM_PROMPT_V1,
    SYSTEM_PROMPT_V2,
    USER_TEMPLATE,
    _truncate,
)

ABL_PATH = REPO / "data/eval/prompt_ablation.jsonl"
HELDOUT_PATH = REPO / "data/eval/heldout_retrieval.jsonl"
OPEN_PATH = Path("/tmp/open_pr_cases.json")
OUT_DIR = REPO / "data/eval/transcripts"

DATE_BEFORE = "2026-03-01"
HELDOUT_PRS = {36007, 37009, 35939}


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


def load_heldout_hits(prs: set[int]) -> dict[int, list[Hit]]:
    found: dict[int, list[Hit]] = {}
    with HELDOUT_PATH.open() as f:
        for line in f:
            j = json.loads(line)
            pr = int(j["query"]["pr_number"])
            if pr in prs and pr not in found:
                found[pr] = [hit_from_dict(h) for h in j["top20_capped"]]
                if len(found) == len(prs):
                    break
    return found


def build_user_msg(hunk: str, file: str, pr_marker: str, hits: list[Hit]) -> str:
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


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    rows = [json.loads(l) for l in ABL_PATH.read_text().splitlines() if l.strip()]
    print(f"loaded {len(rows)} ablation rows")

    heldout_hits = load_heldout_hits(HELDOUT_PRS)
    print(f"loaded heldout hits for PRs: {sorted(heldout_hits)}")

    R = Retriever()

    open_hits_cache: dict[tuple, list[Hit]] = {}

    for i, r in enumerate(rows, 1):
        c = r["case"]
        pr = int(c["pr"])
        kind = c["case_kind"]
        file = c["file"] or "<unknown>"
        hunk = c["hunk"]

        if kind == "heldout-closed":
            hits = heldout_hits[pr]
        else:
            key = (pr, file, c.get("line"))
            if key not in open_hits_cache:
                print(f"  case {i}: re-embedding open-pr hunk for PR #{pr} line {c.get('line')}")
                vec = R.embed_text(hunk)
                open_hits_cache[key] = R.search(vec, k=20, max_per_pr=2, date_before=None)
            hits = open_hits_cache[key]

        user_msg = build_user_msg(hunk, file, str(pr), hits)

        for ver in ("v1", "v2"):
            o = r[ver]
            sys_prompt = SYSTEM_PROMPT_V1 if ver == "v1" else SYSTEM_PROMPT_V2
            visible = {
                "summary": o["summary"],
                "confidence": o["confidence"],
                "strong_matches": o["strong_matches"],
                "weak_observations": o["weak_observations"],
            }
            assistant_text = json.dumps(visible, indent=2, ensure_ascii=False)

            out_path = OUT_DIR / f"case{i}_{ver}.txt"
            with out_path.open("w") as f:
                f.write("=" * 100 + "\n")
                f.write(f"CASE {i}  PR #{pr}  ({kind})\n")
                f.write(f"file: {file}  line: {c.get('line')}\n")
                f.write(f"prompt_version: {ver}\n")
                f.write(f"prompt_tokens: {o['usage']['prompt_tokens']}  "
                        f"completion_tokens: {o['usage']['completion_tokens']}  "
                        f"latency: {o['latency_sec']}s\n")
                rs = (c.get("reviewer_said") or "").strip()
                f.write("HUMAN reviewer (ground truth):\n")
                for ln in rs.splitlines():
                    f.write("  > " + ln + "\n")
                f.write("=" * 100 + "\n\n")

                f.write("[SYSTEM]\n")
                f.write("-" * 100 + "\n")
                f.write(sys_prompt)
                if not sys_prompt.endswith("\n"):
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

            print(f"  wrote {out_path.relative_to(REPO)}  "
                  f"({out_path.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
