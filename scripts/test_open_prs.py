#!/usr/bin/env python3
"""Run the v1 assistant on a list of real open-PR hunks and pretty-print results."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from product.review_assistant import ReviewAssistant

cases = json.load(open("/tmp/open_pr_cases.json"))
A = ReviewAssistant()

for i, c in enumerate(cases, 1):
    print("\n" + "=" * 80)
    print(f"OPEN-PR TEST #{i}: PR #{int(c['pr'])} | file {c['file']} | line {c['line']}")
    print(f"  hunk len = {len(c['hunk'])} chars")
    print(f"\n  ACTUAL human reviewer ({c['reviewer']}):")
    print(f"    \"{c['reviewer_said'].strip()[:300]}\"")
    print()

    sug = A.review_hunk(
        hunk_text=c["hunk"],
        new_file=c["file"],
        new_pr_marker=str(int(c["pr"])),
    )

    print(f"  v1 ASSISTANT verdict: confidence={sug.confidence.upper()}")
    print(f"  Summary: {sug.summary}")
    if sug.strong_matches:
        print(f"  STRONG MATCHES ({len(sug.strong_matches)}):")
        for m in sug.strong_matches:
            print(f"    - PR #{m.get('past_pr')} ({m.get('past_file', '')}):")
            print(f"        past comment: \"{m.get('past_comment_excerpt', '')[:200]}\"")
            print(f"        suggests: {m.get('suggested_adaptation', '')[:200]}")
    else:
        print("  STRONG MATCHES: none")
    if sug.weak_observations:
        print(f"  WEAK OBSERVATIONS ({len(sug.weak_observations)}):")
        for o in sug.weak_observations:
            prs = o.get("supporting_past_prs", [])
            print(f"    - {o.get('observation', '')[:250]}  [cf. {prs}]")
    print(f"  [tokens prompt={sug.usage.get('prompt_tokens')} out={sug.usage.get('completion_tokens')}]")
