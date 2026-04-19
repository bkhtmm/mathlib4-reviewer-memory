#!/usr/bin/env python3
"""For the 3 open-PR test cases, dump the actual top-20 retrieval candidates
WITHOUT calling the LLM. Lets us inspect whether the answer was even reachable.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pipeline.retrieval import Retriever

cases = json.load(open("/tmp/open_pr_cases.json"))
R = Retriever()

# We need a way to embed the new hunks, but Voyage is one call per hunk.
# Just embed each query once and dump top-20.
import os
if not os.environ.get("VOYAGE_API_KEY"):
    print("ERROR: VOYAGE_API_KEY not set", file=sys.stderr)
    sys.exit(1)

for i, c in enumerate(cases, 1):
    print("\n" + "=" * 100)
    print(f"OPEN-PR CASE #{i}: PR #{int(c['pr'])}  file={c['file']}  line={c['line']}")
    print(f"\nNEW HUNK (full):\n{c['hunk']}")
    print(f"\nACTUAL REVIEWER COMMENT (target answer):\n  {c['reviewer_said']!r}")
    print()

    qv = R.embed_text(c["hunk"])
    hits = R.search(qv, k=20, max_per_pr=2)
    print(f"--- Top-20 retrieval candidates (sorted by sim desc) ---")
    for j, h in enumerate(hits, 1):
        print(f"\n[#{j}] sim={h.sim:.3f}  PR#{h.pr_number}  file={h.file_path}  line={h.line}")
        print(f"  PAST HUNK (truncated to 250):")
        print("    " + h.embedding_text.strip()[:250].replace("\n", "\n    "))
        print(f"  PAST COMMENT (truncated to 250):")
        print("    " + h.comment_text.strip()[:250].replace("\n", "\n    "))
