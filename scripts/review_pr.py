#!/usr/bin/env python3
"""CLI for the v1 review assistant.

Usage:
  # From a file:
  python scripts/review_pr.py --hunk-file path/to/hunk.diff --file Mathlib/X.lean

  # From stdin:
  cat hunk.diff | python scripts/review_pr.py --file Mathlib/X.lean

  # Pull a real held-out hunk (smoke test):
  python scripts/review_pr.py --self-test

Output: human-readable report. Pass --json to get the raw structured output.
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
