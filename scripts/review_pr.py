#!/usr/bin/env python3
"""CLI for the review assistant.

Usage:
  # LLM mode (default): retrieves + asks GPT-5 which past comments apply.
  cat hunk.diff | python scripts/review_pr.py --file Mathlib/X.lean

  # Search mode: pure retrieval, no LLM call, no possibility of hallucination.
  # Returns the top-K most similar past (code, reviewer-comment) pairs verbatim.
  cat hunk.diff | python scripts/review_pr.py --search --file Mathlib/X.lean

  # Search mode + filter to past PRs that were NOT accepted into mathlib —
  # useful for "is this code similar to anything that already got rejected?".
  cat hunk.diff | python scripts/review_pr.py --search --not-accepted-only \\
                --file Mathlib/X.lean

  # Smoke test on a held-out query (no need to prepare a hunk):
  python scripts/review_pr.py --self-test

LLM mode requires OPENAI_API_KEY (or GEMINI_API_KEY with --provider gemini).
Search mode only requires VOYAGE_API_KEY (used to embed the query hunk).

Output: human-readable report by default; pass --json for structured output.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from product.review_assistant import ReviewAssistant  # noqa: E402


COLORS = {
    "high":   "\033[1;32m",  # bold green
    "medium": "\033[1;33m",  # bold yellow
    "low":    "\033[33m",    # yellow
    "none":   "\033[2;37m",  # dim
    "reset":  "\033[0m",
    "bold":   "\033[1m",
    "dim":    "\033[2m",
    "cyan":   "\033[36m",
}


def fmt(text: str, *, color: str) -> str:
    if not sys.stdout.isatty():
        return text
    return f"{COLORS.get(color, '')}{text}{COLORS['reset']}"


def print_search_report(result, no_color: bool = False) -> None:
    """Render the no-LLM search-mode output."""
    if no_color:
        for k in COLORS:
            COLORS[k] = ""

    n = result.n_total
    print(fmt(f"\n=== Search mode (no LLM) — {n} hit{'s' if n != 1 else ''} ===", color="bold"))
    if n == 0:
        print(fmt("No matching past comments in the index.", color="dim"))
        return

    print(fmt(
        f"  ✓ {result.n_accepted} from accepted PRs   "
        f"✗ {result.n_not_accepted} from PRs NOT accepted into mathlib",
        color="dim",
    ))
    print()

    for h in result.hits:
        sim = h.get("sim", 0.0)
        pr = h.get("pr_number", "?")
        title = (h.get("pr_title") or "").strip()
        title_short = (title[:80] + "…") if len(title) > 80 else title
        path = h.get("file_path", "?")
        line = h.get("line")
        line_str = f"  line {int(line)}" if isinstance(line, (int, float)) and line == int(line) else ""
        reviewer = h.get("reviewer", "?")
        accepted = h.get("pr_accepted")

        if accepted is True:
            badge = fmt("✓ ACCEPTED", color="dim")
        elif accepted is False:
            badge = fmt("✗ NOT ACCEPTED into mathlib", color="medium")
        else:
            badge = fmt("? acceptance unknown", color="dim")

        rank = h.get("rank", "?")
        print(fmt(
            f"[{rank}] sim={sim:.3f}   PR #{pr}  —  {title_short}",
            color="cyan",
        ))
        print(f"    file: {path}{line_str}")
        print(f"    reviewer: @{reviewer}   status: {badge}")
        comment = (h.get("comment_text") or "").strip()
        for ln in comment.splitlines():
            print(f"    > {ln}")
        print()

    print(fmt(
        "Note: 'NOT ACCEPTED' is a proxy — a closed PR can mean rejected, "
        "abandoned, superseded, or broken into smaller PRs. Click the past PR "
        "to read the discussion before drawing conclusions.",
        color="dim",
    ))


def print_report(suggestion, no_color: bool = False) -> None:
    if no_color:
        for k in COLORS:
            COLORS[k] = ""

    conf = suggestion.confidence.upper()
    print(fmt(f"\n=== Review Assistant — confidence: {conf} ===", color=suggestion.confidence))
    print(fmt(f"Summary: {suggestion.summary}\n", color="bold"))

    if suggestion.strong_matches:
        print(fmt(f"FINDINGS ({len(suggestion.strong_matches)}):", color="bold"))
        for i, m in enumerate(suggestion.strong_matches, 1):
            print(fmt(f"\n  [{i}] PR #{m.get('past_pr', '?')} — {m.get('past_file', '?')}", color="cyan"))
            print(f"      Past comment: \"{m.get('past_comment_excerpt', '').strip()}\"")
            print(f"      Why relevant: {m.get('applies_because', '').strip()}")
            print(fmt(f"      Suggested: {m.get('suggested_adaptation', '').strip()}", color="bold"))
    else:
        print(fmt("No strong matches found.", color="dim"))

    if suggestion.weak_observations:
        print(fmt(f"\nGENERAL OBSERVATIONS ({len(suggestion.weak_observations)}):", color="bold"))
        for obs in suggestion.weak_observations:
            prs = obs.get("supporting_past_prs", [])
            ref = f"  (cf. PRs: {', '.join('#' + str(p) for p in prs)})" if prs else ""
            print(f"  - {obs.get('observation', '').strip()}{fmt(ref, color='dim')}")

    print(fmt(
        f"\n[{len(suggestion.raw_candidates)} candidates retrieved | "
        f"prompt {suggestion.usage.get('prompt_tokens')} tok | "
        f"output {suggestion.usage.get('completion_tokens')} tok]",
        color="dim",
    ))


def self_test(assistant: ReviewAssistant) -> None:
    """Pull a held-out query from the eval set and run end-to-end."""
    eval_path = REPO_ROOT / "data" / "eval" / "heldout_retrieval.jsonl"
    with open(eval_path) as f:
        first = json.loads(f.readline())
    q = first["query"]
    print(fmt(f"[self-test] using held-out query from PR #{q['pr_number']}, file {q['file_path']}", color="cyan"))
    print(fmt(f"[self-test] ground-truth comment was:\n  {q['comment_text'][:200]!r}\n", color="dim"))
    sug = assistant.review_hunk(
        hunk_text=q["embedding_text"],
        new_file=q["file_path"],
        new_pr_marker=str(q["pr_number"]),
        date_before="2026-03-01",
    )
    print_report(sug)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hunk-file", help="path to a file containing the diff hunk; if omitted, read stdin")
    ap.add_argument("--file", default="<unknown>", help="file path the hunk applies to (for context)")
    ap.add_argument("--pr", default="NEW", help="PR number / marker for display")
    ap.add_argument("--top-k", type=int, default=20)
    ap.add_argument("--max-per-pr", type=int, default=2)
    ap.add_argument("--date-before", help="hide index entries with created_at >= this date (eval setup)")
    ap.add_argument("--json", action="store_true", help="print raw JSON output")
    ap.add_argument("--no-color", action="store_true")
    ap.add_argument("--self-test", action="store_true",
                    help="run on a held-out query from data/eval/heldout_retrieval.jsonl")
    ap.add_argument("--search", action="store_true",
                    help="no-LLM mode: pure retrieval, no possibility of hallucination. "
                         "Returns top-K most similar past (code, comment) pairs verbatim.")
    ap.add_argument("--not-accepted-only", action="store_true",
                    help="(search mode) keep only hits whose past PR was NOT accepted "
                         "into mathlib — useful for 'is my code similar to anything that "
                         "got rejected/abandoned?'.")
    args = ap.parse_args()

    assistant = ReviewAssistant()

    if args.self_test:
        self_test(assistant)
        return

    if args.hunk_file:
        hunk = Path(args.hunk_file).read_text()
    else:
        if sys.stdin.isatty():
            print("Paste the hunk, then Ctrl-D:", file=sys.stderr)
        hunk = sys.stdin.read()

    if not hunk.strip():
        print("ERROR: empty hunk", file=sys.stderr)
        sys.exit(2)

    if args.search:
        result = assistant.search(
            hunk_text=hunk,
            top_k=args.top_k,
            max_per_pr=args.max_per_pr,
            date_before=args.date_before,
            not_accepted_only=args.not_accepted_only,
        )
        if args.json:
            print(json.dumps({
                "mode": "search",
                "n_total": result.n_total,
                "n_accepted": result.n_accepted,
                "n_not_accepted": result.n_not_accepted,
                "hits": result.hits,
            }, indent=2, default=str))
        else:
            print_search_report(result, no_color=args.no_color)
        return

    if args.not_accepted_only:
        print("ERROR: --not-accepted-only only makes sense with --search", file=sys.stderr)
        sys.exit(2)

    sug = assistant.review_hunk(
        hunk_text=hunk,
        new_file=args.file,
        new_pr_marker=args.pr,
        top_k=args.top_k,
        max_per_pr=args.max_per_pr,
        date_before=args.date_before,
    )

    if args.json:
        print(json.dumps({
            "summary": sug.summary,
            "confidence": sug.confidence,
            "strong_matches": sug.strong_matches,
            "weak_observations": sug.weak_observations,
            "n_candidates": len(sug.raw_candidates),
            "usage": sug.usage,
        }, indent=2))
    else:
        print_report(sug, no_color=args.no_color)


if __name__ == "__main__":
    main()
