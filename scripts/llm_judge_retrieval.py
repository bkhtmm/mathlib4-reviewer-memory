#!/usr/bin/env python3
"""LLM judge for held-out retrieval.

For each sampled held-out query, asks GPT-5 to rate each of the top-10 retrieved
hits on a 0/1/2 rubric against the ground-truth reviewer comment.

Outputs JSONL of per-hit judgments to --out.

Stratified sampling: queries are bucketed by whether any top-10 hit
(a) has lexical F1 >= 0.3 (strong signal), or (b) shares the same file path
(medium), or (c) neither (hard). Samples drawn per bucket to ensure coverage.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time
from pathlib import Path

from openai import OpenAI
from openai import APIError, RateLimitError


TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]+|\d+")


def tokens(text: str) -> set[str]:
    if not text:
        return set()
    return {t.lower() for t in TOKEN_RE.findall(text)}


def f1_score(a: str, b: str) -> float:
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    if inter == 0:
        return 0.0
    p = inter / len(ta)
    r = inter / len(tb)
    return 2 * p * r / (p + r)


def truncate(s: str, n: int) -> str:
    s = s or ""
    if len(s) <= n:
        return s
    return s[: n - 15] + "\n... [truncated]"


SYSTEM_PROMPT = """You are an expert code reviewer for Lean 4 / mathlib4 pull \
requests, evaluating whether a retrieved historical review-comment could have \
helped the author pre-empt the reviewer's actual feedback on a new PR.

For each (query, candidate) pair you are given:
  - QUERY HUNK: a code diff from a new PR
  - GROUND-TRUTH COMMENT: the actual reviewer's comment on that query hunk
  - CANDIDATE HUNK: a code diff from a historical PR
  - CANDIDATE COMMENT: the reviewer's comment on that historical hunk

Rate the CANDIDATE on a 0/1/2 relevance scale:
  - 2 (DIRECT): The candidate comment expresses the same review point as the \
ground-truth comment -- a paraphrase, a template for the same issue, or a \
clearly-analogous fix. An author who read it before submitting would plausibly \
have avoided the reviewer's criticism.
  - 1 (PARTIAL): The candidate touches a related concern (same file/module, \
similar API, same style category) but is not the same issue. It could give \
useful context but is not a direct match.
  - 0 (NONE): Different issue. Not directly useful; at best tangentially on-topic.

Be STRICT for label 2: require substantive overlap in the advice, not just \
shared keywords or file path.

Respond with a single JSON object: {"label": 0|1|2, "rationale": "<short>"}.
"""


USER_TEMPLATE = """QUERY HUNK:
```
{q_hunk}
```

GROUND-TRUTH COMMENT (from reviewer on the query PR):
{q_comment}

---

CANDIDATE HUNK:
```
{c_hunk}
```

CANDIDATE COMMENT (from reviewer on a historical PR):
{c_comment}

Rate the candidate's relevance to the ground-truth comment. Return JSON only.
"""


def pick_samples(records: list[dict], k_per_bucket=(7, 7, 6), seed=42) -> list[dict]:
    """Stratify queries into 3 buckets based on top-10 signal strength."""
    rng = random.Random(seed)
    A, B, C = [], [], []  # lex-hit, same-file-only, neither
    for rec in records:
        q = rec["query"]
        hits = rec["top20_capped"][:10]
        any_lex = any(f1_score(q["comment_text"], h["comment_text"]) >= 0.3 for h in hits)
        any_same_file = any(h["file_path"] == q["file_path"] for h in hits)
        if any_lex:
            A.append(rec)
        elif any_same_file:
            B.append(rec)
        else:
            C.append(rec)

    print(f"buckets: lex-hit={len(A)} same-file-only={len(B)} hard={len(C)}")
    kA, kB, kC = k_per_bucket
    pick = (
        rng.sample(A, min(kA, len(A)))
        + rng.sample(B, min(kB, len(B)))
        + rng.sample(C, min(kC, len(C)))
    )
    while len(pick) < sum(k_per_bucket):
        pool = [r for r in records if r not in pick]
        pick.append(rng.choice(pool))
    return pick


def judge_one(client: OpenAI, model: str, query: dict, hit: dict, max_retries=3) -> dict:
    user = USER_TEMPLATE.format(
        q_hunk=truncate(query["embedding_text"], 2500),
        q_comment=truncate(query["comment_text"], 1500),
        c_hunk=truncate(hit["embedding_text"], 2500),
        c_comment=truncate(hit["comment_text"], 1500),
    )
    for attempt in range(max_retries):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user},
                ],
                response_format={"type": "json_object"},
            )
            raw = resp.choices[0].message.content or "{}"
            data = json.loads(raw)
            label = int(data.get("label", -1))
            if label not in (0, 1, 2):
                raise ValueError(f"bad label: {label}")
            return {
                "label": label,
                "rationale": data.get("rationale", "")[:500],
                "usage": {
                    "in": resp.usage.prompt_tokens,
                    "out": resp.usage.completion_tokens,
                },
            }
        except (RateLimitError, APIError) as e:
            wait = 2 ** attempt
            print(f"  retry {attempt + 1}/{max_retries} after {wait}s: {e}", file=sys.stderr)
            time.sleep(wait)
        except (json.JSONDecodeError, ValueError) as e:
            print(f"  parse error (attempt {attempt + 1}): {e}", file=sys.stderr)
            if attempt == max_retries - 1:
                return {"label": -1, "rationale": f"parse-error: {e}", "usage": {}}
    return {"label": -1, "rationale": "max-retries", "usage": {}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_path", default="data/eval/heldout_retrieval.jsonl")
    ap.add_argument("--out", default="data/eval/llm_judgments.jsonl")
    ap.add_argument("--model", default="gpt-5")
    ap.add_argument("--n-queries", type=int, default=20)
    ap.add_argument("--top-k", type=int, default=10)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--resume", action="store_true",
                    help="skip (query_record_id, hit_record_id) pairs already in --out")
    args = ap.parse_args()

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        sys.exit("OPENAI_API_KEY not set")

    records = [json.loads(ln) for ln in open(args.in_path)]
    print(f"loaded {len(records)} retrieval records from {args.in_path}")
    samples = pick_samples(records, k_per_bucket=(7, 7, 6), seed=args.seed)
    print(f"sampled {len(samples)} queries")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if args.resume and out_path.exists():
        for ln in open(out_path):
            try:
                r = json.loads(ln)
                done.add((r["query_record_id"], r["hit_record_id"]))
            except Exception:
                pass
        print(f"resume: {len(done)} judgments already in {out_path}")

    client = OpenAI(api_key=api_key)
    t0 = time.time()
    total_in = total_out = 0
    n_calls = 0
    n_pairs = sum(min(args.top_k, len(r["top20_capped"])) for r in samples)

    with open(out_path, "a") as out:
        for qi, rec in enumerate(samples):
            q = rec["query"]
            hits = rec["top20_capped"][: args.top_k]
            print(f"\n[{qi + 1}/{len(samples)}] query_pr=#{q['pr_number']} file={q['file_path']}")
            for rank, h in enumerate(hits, 1):
                key = (q["record_id"], h["record_id"])
                if key in done:
                    continue
                j = judge_one(client, args.model, q, h)
                row = {
                    "query_record_id": q["record_id"],
                    "query_pr": q["pr_number"],
                    "query_file": q["file_path"],
                    "hit_rank": rank,
                    "hit_record_id": h["record_id"],
                    "hit_pr": h["pr_number"],
                    "hit_file": h["file_path"],
                    "sim": h["sim"],
                    "same_file": h["file_path"] == q["file_path"],
                    "lex_f1": f1_score(q["comment_text"], h["comment_text"]),
                    "label": j["label"],
                    "rationale": j["rationale"],
                }
                out.write(json.dumps(row, ensure_ascii=False) + "\n")
                out.flush()
                n_calls += 1
                if j["usage"]:
                    total_in += j["usage"].get("in", 0)
                    total_out += j["usage"].get("out", 0)
                print(f"  rank={rank} sim={h['sim']:.3f} label={j['label']}  {j['rationale'][:80]}")

    dt = time.time() - t0
    print(f"\nDONE {n_calls}/{n_pairs} calls in {dt:.0f}s | tokens in={total_in:,} out={total_out:,}")


if __name__ == "__main__":
    main()
