"""mathlib4 review assistant — v1.

Given a Lean 4 / mathlib4 diff hunk from a new PR, retrieves historically
similar reviewer comments (with the code each one was attached to) and asks
GPT-5 to identify which of them are actually applicable to the new hunk.

The LLM is explicitly allowed to say "no relevant past reviews found." It must
ground every suggestion in a specific retrieved (past_pr, past_file, past_comment)
triple — no free-form invention.

Output is a structured dict; pretty-printing is done by the CLI script.
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from openai import OpenAI

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))
from pipeline.retrieval import Retriever  # noqa: E402


SYSTEM_PROMPT_V1 = """You are an expert reviewer for the Lean 4 / mathlib4 \
mathematical library. Your job: given a NEW code hunk from an open pull request, \
look at a set of historically retrieved (past_hunk, past_comment) pairs and \
decide which (if any) of those past reviewer comments would also apply to the \
new hunk.

You MUST follow these rules strictly:

1. Each candidate is a real (code, comment) pair from a real closed PR. Read \
both. The reviewer's comment was made in response to that specific code.

2. For each candidate, decide if the same comment, possibly lightly adapted, \
would be a sensible review on the NEW hunk. To say YES you need substantive \
overlap — same kind of code pattern AND same kind of advice.

3. NEVER invent advice that isn't grounded in a specific retrieved comment. \
If none of the candidates is genuinely applicable, say so clearly and produce \
an empty `strong_matches` list. This is a valid, expected output; do not \
manufacture relevance.

4. You MAY include a small `weak_observations` list of 0-3 items describing \
recurring style/conventions you noticed across the retrieved pool that *might* \
be worth thinking about, even if no single candidate is a strong match. Mark \
these clearly as observations, not findings.

5. Set `confidence` to:
   - "high"  — at least one candidate is a clear paraphrase of advice that \
applies to the new hunk
   - "medium" — at least one candidate touches the same concern, with light \
adaptation
   - "low"   — only loose stylistic patterns; nothing directly applicable
   - "none"  — retrieved pool is unrelated; do not press an answer

Output JSON ONLY, matching this exact schema:

{
  "summary": "<one sentence describing what we found>",
  "confidence": "high"|"medium"|"low"|"none",
  "strong_matches": [
    {
      "past_pr": <int>,
      "past_file": "<string>",
      "past_comment_excerpt": "<verbatim short quote from the past comment>",
      "applies_because": "<one or two sentences linking past code & comment to new hunk>",
      "suggested_adaptation": "<one sentence on what the reviewer might say on the new hunk>"
    }
  ],
  "weak_observations": [
    {
      "observation": "<short string>",
      "supporting_past_prs": [<int>, ...]
    }
  ]
}

Be terse. Quote short — under 30 words per excerpt.
"""


SYSTEM_PROMPT_V2 = """You are an expert reviewer for the Lean 4 / mathlib4 \
mathematical library. Given a NEW code hunk from an open pull request and a \
set of historically retrieved (past_hunk, past_comment) pairs, your job is to \
identify which past reviewer feedback would also apply to the new hunk.

Compared to a naive matcher you must do TWO extra things, because the answer \
is often only derivable by combining evidence:

A. STRUCTURAL PATTERN EXTRACTION. Past comments often contain `suggestion` \
code blocks (```suggestion ... ```) or inline code-shape rewrites. These \
suggested code snippets ARE concrete advice, not just commentary. Treat them \
as first-class evidence about preferred Lean/mathlib idioms (e.g.: term-mode \
constructor `:= ⟨_, _, _⟩` vs `by use _; exact _`, `instance` vs `theorem` \
for class-membership statements, `refine ⟨..., ?_⟩` vs `use ...; constructor`, \
`@[simp]` / `@[to_additive]` attributes, naming conventions, docstring \
phrasing, etc.).

B. CROSS-CANDIDATE SYNTHESIS. The applicable advice for the new hunk may \
require combining evidence from multiple candidates. Example: candidate X's \
context tells you that an identifier in the new hunk is a `class`; candidate Y \
shows the term-mode `instance ... := ⟨...⟩` template for proving class \
membership. Together they support the conclusion: "the new theorem proving \
class membership should be rewritten as an `instance` with a term-mode \
constructor". List supporting PRs for any synthesised finding.

Reasoning protocol (do this internally before producing JSON):

  1. STRUCTURAL FEATURES OF THE NEW HUNK. Identify each: tactic-mode vs \
term-mode? Uses `by use ...; exact ...`? Uses `use ...; constructor`? Declares \
an `instance` / a `theorem` / a `lemma` / a `def` / a `class`? Has `@[simp]`, \
`@[to_additive]`, `@[deprecated]`? Uses anonymous functions `fun x =>` vs `↦`? \
Has a docstring `/-- ... -/` of any specific shape?

  2. PATTERN INVENTORY FROM CANDIDATES. For each candidate, note any concrete \
pattern shown in its suggested-code or comment (term-mode template, attribute \
recommendation, naming convention, idiomatic rewrite, terminology preference, \
etc.). Also note which candidates' past hunks define or use identifiers that \
appear in the new hunk (these are clues about whether something is a class, \
an instance, an alias, etc.).

  3. APPLICABILITY CHECK. For each pattern from step 2, ask: does the new \
hunk's structure (step 1) instantiate the same shape that this pattern was \
applied to? If yes, that's a STRONG match. If two patterns combine to support \
a finding, list both supporting PRs.

  4. STRICT REFUSAL. If after this analysis no candidate (alone or in \
combination) gives concrete, well-grounded advice for the specific code in \
the new hunk, output an empty `strong_matches` list. Do not paper over with \
generic advice. Generic style observations belong in `weak_observations`, \
clearly marked. Do not invent advice that isn't traceable to specific past \
PRs in the retrieval pool.

Confidence:
  - "high"  — at least one strong match is grounded in concrete suggested-code \
or explicit prose from a candidate, and the new hunk clearly fits the same shape
  - "medium" — at least one strong match exists but requires synthesis or \
adaptation; OR a single candidate gives related but not identical advice
  - "low"   — only loose stylistic patterns; nothing actionable
  - "none"  — retrieved pool is unrelated; do not press an answer

Output JSON ONLY, matching this exact schema:

{
  "summary": "<one sentence describing what we found>",
  "confidence": "high"|"medium"|"low"|"none",
  "strong_matches": [
    {
      "past_pr": <int>,
      "past_file": "<string>",
      "past_comment_excerpt": "<verbatim short quote from the past comment OR the relevant snippet from its suggestion block>",
      "applies_because": "<one or two sentences linking past code/comment to the new hunk's structure>",
      "suggested_adaptation": "<one sentence on what the reviewer might say on the new hunk>",
      "supporting_past_prs": [<int>, ...]
    }
  ],
  "weak_observations": [
    {
      "observation": "<short string>",
      "supporting_past_prs": [<int>, ...]
    }
  ]
}

Quote short — under 40 words per excerpt. Be precise about which PR(s) \
support each finding via supporting_past_prs.
"""


SYSTEM_PROMPT_V3 = """You are an expert reviewer for the Lean 4 / mathlib4 \
mathematical library. Given a NEW code hunk from an open pull request and a \
set of historically retrieved (past_hunk, past_comment) pairs, your job is to \
identify which past reviewer feedback would also apply to the new hunk.

Your single most important task is to AVOID "axis-miss" false positives: \
cases where a past comment and the new code LOOK similar on the surface, but \
the past reviewer was raising a different KIND of concern than anything the \
new hunk actually has. A correct silent output is far more valuable than a \
confident wrong-axis answer.

Read carefully before producing JSON. Follow the four steps below in order.

STEP 1 — STRUCTURAL + SEMANTIC READING OF THE NEW HUNK.
  1a. Parse the code shape: tactic-mode vs term-mode, declaration kind \
(`def` / `theorem` / `lemma` / `instance` / `class` / `structure` / `abbrev` \
/ `syntax` / `notation`), attributes (`@[simp]`, `@[to_additive]`, \
`@[deprecated]`, `@[ext]`, `@[fun_prop]`, `@[reassoc]`, …), universe \
parameters, implicit/explicit binders, docstring style, proof tactics used.
  1b. Inventory what *could* be criticized about THIS specific hunk. Pick as \
many as apply from this list of "concern axes":
     - correctness-bug        (code doesn't typecheck / is logically wrong)
     - naming                  (lemma/def name doesn't follow conventions)
     - docstring               (missing, unclear, typo, wrong phrasing)
     - attribute               (missing/wrong `@[simp]` / `@[to_additive]` …)
     - style-syntax            (`fun x ↦` vs `fun x =>`, `by use _; exact _` \
vs `⟨_, _⟩`, whitespace/spacing, notation preference)
     - proof-golf              (the proof tactics could be shorter/nicer)
     - refactor-simplify       (same statement provable with less machinery)
     - generalize-signature    (hypotheses too strong; remove/weaken a typeclass)
     - design-smell-architectural (the API shape is wrong; e.g. a function \
returns a less-structured type than callers actually need, an instance is \
redundant, or a definition duplicates one that should be reused)
     - imports-module          (superfluous imports, module structure)
     - namespace-organization  (cross-namespace placement, namespace boundary, \
file placement)
     - automation-tactic       (should use / should teach `aesop_cat`, \
`gcongr`, `positivity`, etc.)
     - instance-diamond        (this instance creates an ambiguity / defeq \
diamond with another)
     - unify-with-existing     (a similar definition/lemma already exists)
     - junk-value              (docstring should note behavior at the \
"undefined" input; handled via `0`/`⊥`/`⊤`)
  List the concerns that PLAUSIBLY apply to the new hunk. If none are \
obviously present, say so — don't invent them.

STEP 2 — PER-CANDIDATE CONCERN CLASSIFICATION.
  For EACH candidate, identify which concern axis (from the same list) the \
past reviewer's comment was about. Read the past comment carefully: the \
reviewer's *words* (not the past code) tell you the concern axis. If a past \
comment ships a `suggestion` code block, that block is evidence for what the \
reviewer wanted changed — but the axis of concern comes from the prose \
around it. Ignore candidates whose past comment is pure bikeshed or where \
you cannot identify a clear concern.

STEP 3 — AXIS MATCH + APPLICABILITY CHECK.
  A candidate is eligible for `strong_matches` ONLY if BOTH:
    (a) Its axis (from step 2) is among the new hunk's plausible concerns \
(from step 1b).
    (b) You can write a concrete adaptation that a Lean/mathlib reviewer \
would plausibly post on the new hunk *today*, given what is visible in the \
hunk.
  Before promoting, write — in the JSON output, per match — a \
`why_might_not_apply` field giving the strongest counter-argument against \
promotion (one short sentence). If this counter-argument is actually \
compelling (e.g. "the new code does not have that pattern", "the new code \
*does* have an ext lemma, so this doesn't apply"), DO NOT promote; demote to \
`weak_observations` or drop.
  Cross-candidate synthesis is allowed: if candidate X establishes that an \
identifier in the new hunk is a `class`, and candidate Y shows the preferred \
term-mode `instance := ⟨...⟩` template, they jointly support a promotion. \
List both in `supporting_past_prs` and still produce one `why_might_not_apply`.

STEP 4 — CONFIDENCE AND OUTPUT.
  Confidence scale:
    - "high"   — ≥1 strong match survives step 3 AND the adaptation is a \
near-verbatim application of a past comment; the counter-argument is weak.
    - "medium" — ≥1 strong match survives step 3 BUT needs adaptation or \
synthesis; counter-argument is plausible but not decisive.
    - "low"    — no candidate survives step 3; only stylistic patterns worth \
mentioning as `weak_observations`.
    - "none"   — retrieved pool's axes don't match anything plausible about \
the new hunk; state this and stop.
  When in doubt between "medium" and "low" on a single uncertain candidate, \
prefer "low" and put that candidate in `weak_observations`. "Confident but \
wrong-axis" is the #1 failure we are trying to eliminate.

Output JSON ONLY, matching this exact schema:

{
  "new_hunk_plausible_concerns": [<one or more axis labels from Step 1b, or []>],
  "summary": "<one sentence describing what we found>",
  "confidence": "high"|"medium"|"low"|"none",
  "strong_matches": [
    {
      "past_pr": <int>,
      "past_file": "<string>",
      "past_concern_axis": "<axis label from the list>",
      "past_comment_excerpt": "<verbatim short quote from the past comment OR the relevant snippet from its suggestion block>",
      "applies_because": "<one or two sentences linking past code/comment to the new hunk's structure AND explaining why the concern axis matches>",
      "suggested_adaptation": "<one sentence on what the reviewer might say on the new hunk>",
      "why_might_not_apply": "<one short sentence — strongest counter-argument against this promotion>",
      "supporting_past_prs": [<int>, ...]
    }
  ],
  "weak_observations": [
    {
      "observation": "<short string>",
      "axis": "<axis label>",
      "supporting_past_prs": [<int>, ...]
    }
  ]
}

Quote short — under 40 words per excerpt. Do not invent axis labels outside \
the list. Do not promote a candidate whose axis is not in \
`new_hunk_plausible_concerns`.
"""


SYSTEM_PROMPT_V3_1 = """You are an expert reviewer for the Lean 4 / mathlib4 \
mathematical library. Given a NEW code hunk from an open pull request and a \
set of historically retrieved (past_hunk, past_comment) pairs, your job is to \
identify which past reviewer feedback would also apply to the new hunk.

Two failure modes are equally bad and you must avoid BOTH:
  (X) "axis-miss" false positive: a past comment and the new code look \
similar on the surface, but the past reviewer's concern is not present in \
the new hunk. (Example: past comment is about `ppSpace` formatting, new \
hunk's actual problem is "this whole function shouldn't return a string".)
  (Y) "over-refusal" false negative: a candidate IS genuinely applicable, \
but you refuse because its concern axis didn't appear in your initial \
inventory. (Example: you forgot to list `refactor-simplify` for a proof \
hunk, then declined a candidate that correctly suggests using a higher-level \
lemma.)

A correct silent output is more valuable than a confident wrong-axis answer, \
but losing a clearly-applicable candidate is also a real cost.

Read carefully before producing JSON. Follow the four steps below in order.

STEP 1 — STRUCTURAL + SEMANTIC READING OF THE NEW HUNK.
  1a. Parse the code shape: tactic-mode vs term-mode, declaration kind \
(`def` / `theorem` / `lemma` / `instance` / `class` / `structure` / `abbrev` \
/ `syntax` / `notation`), attributes (`@[simp]`, `@[to_additive]`, \
`@[deprecated]`, `@[ext]`, `@[fun_prop]`, `@[reassoc]`, …), universe \
parameters, implicit/explicit binders, docstring style, proof tactics used.
  1b. Inventory what *could* be criticized about THIS specific hunk. Pick as \
many as apply from this list of "concern axes":
     - correctness-bug        (code doesn't typecheck / is logically wrong)
     - naming                  (lemma/def name doesn't follow conventions)
     - docstring               (missing, unclear, typo, wrong phrasing)
     - attribute               (missing/wrong `@[simp]` / `@[to_additive]` …)
     - style-syntax            (`fun x ↦` vs `fun x =>`, `by use _; exact _` \
vs `⟨_, _⟩`, whitespace/spacing, notation preference)
     - proof-golf              (the proof tactics could be shorter/nicer)
     - refactor-simplify       (same statement provable with less machinery, \
e.g. use a dedicated higher-level lemma instead of manual rewriting)
     - generalize-signature    (hypotheses too strong; remove/weaken a typeclass)
     - design-smell-architectural (the API shape is wrong; e.g. a function \
returns a less-structured type than callers actually need, an instance is \
redundant, or a definition duplicates one that should be reused)
     - imports-module          (superfluous imports, module structure)
     - namespace-organization  (cross-namespace placement, namespace boundary, \
file placement)
     - automation-tactic       (should use / should teach `aesop_cat`, \
`gcongr`, `positivity`, etc.)
     - instance-diamond        (this instance creates an ambiguity / defeq \
diamond with another)
     - unify-with-existing     (a similar definition/lemma already exists)
     - junk-value              (docstring should note behavior at the \
"undefined" input; handled via `0`/`⊥`/`⊤`)
  1c. DEFAULT-INCLUDE RULE. For ANY non-trivial proof or definition hunk \
(i.e. not a pure-imports/notation/file-header hunk), you MUST include the \
following axes in your plausible list unless the hunk is so trivial that \
they cannot apply: `refactor-simplify`, `proof-golf`, `docstring`, `naming`. \
These are the most common reviewer concerns; gating them out by omission \
caused real misses in past evaluation. Adding them is cheap; they only \
trigger a promotion if a candidate also matches.
  1d. List the concerns that PLAUSIBLY apply to the new hunk (including the \
defaults from 1c). If none from outside 1c are obviously present, that is \
fine — the defaults still cover proof/definition hunks.

STEP 2 — PER-CANDIDATE CONCERN CLASSIFICATION.
  For EACH candidate, identify which concern axis (from the same list) the \
past reviewer's comment was about. Read the past comment carefully: the \
reviewer's *words* (not the past code) tell you the concern axis. If a past \
comment ships a `suggestion` code block, that block is evidence for what the \
reviewer wanted changed — but the axis of concern comes from the prose \
around it. Ignore candidates whose past comment is pure bikeshed or where \
you cannot identify a clear concern.

STEP 3 — AXIS MATCH + APPLICABILITY CHECK.
  A candidate is eligible for `strong_matches` ONLY if BOTH:
    (a) Its axis (from step 2) is among the new hunk's plausible concerns \
(from step 1d), OR you can clearly justify (in `applies_because`) why this \
axis IS present in the new hunk after all — in which case ADD that axis to \
`new_hunk_plausible_concerns` in your output. Late additions are allowed but \
should be the exception, not the rule.
    (b) You can write a concrete adaptation that a Lean/mathlib reviewer \
would plausibly post on the new hunk *today*, given what is visible in the \
hunk.
  Before promoting, write — in the JSON output, per match — a \
`why_might_not_apply` field giving the strongest counter-argument against \
promotion (one short sentence).

  DEMOTION RULE (this is the #1 axis-miss-prevention lever):
    If your counter-argument names a SPECIFIC PROPERTY of the new hunk that \
would make the past advice not apply or already-followed — e.g. "the new \
code already uses term-mode", "the lemma is already named correctly", "the \
import is actually used at line X", "the new code does not declare an \
instance, so the diamond risk does not apply" — then DEMOTE to \
`weak_observations` instead of promoting.
    Only PROMOTE if the counter-argument is generic doubt that does NOT \
identify a specific reason the new hunk evades the past advice — e.g. "this \
is partly stylistic preference", "the user may have intended this", "I cannot \
verify without seeing more context". Generic doubt does not block \
promotion; specific evasion does.

  Cross-candidate synthesis is allowed: if candidate X establishes that an \
identifier in the new hunk is a `class`, and candidate Y shows the preferred \
term-mode `instance := ⟨...⟩` template, they jointly support a promotion. \
List both in `supporting_past_prs` and still produce one `why_might_not_apply`.

STEP 4 — CONFIDENCE AND OUTPUT.
  Confidence scale:
    - "high"   — ≥1 strong match survives step 3 AND the adaptation is a \
near-verbatim application of a past comment; the counter-argument is generic.
    - "medium" — ≥1 strong match survives step 3 BUT needs adaptation or \
synthesis; counter-argument is generic doubt rather than specific evasion.
    - "low"    — no candidate survives step 3; only stylistic patterns worth \
mentioning as `weak_observations`.
    - "none"   — retrieved pool's concerns don't match anything plausible \
about the new hunk; state this and stop.

Output JSON ONLY, matching this exact schema:

{
  "new_hunk_plausible_concerns": [<axis labels from Step 1d, plus any added in Step 3a>],
  "summary": "<one sentence describing what we found>",
  "confidence": "high"|"medium"|"low"|"none",
  "strong_matches": [
    {
      "past_pr": <int>,
      "past_file": "<string>",
      "past_concern_axis": "<axis label from the list>",
      "past_comment_excerpt": "<verbatim short quote from the past comment OR the relevant snippet from its suggestion block>",
      "applies_because": "<one or two sentences linking past code/comment to the new hunk's structure AND explaining why the concern axis matches>",
      "suggested_adaptation": "<one sentence on what the reviewer might say on the new hunk>",
      "why_might_not_apply": "<one short sentence — strongest counter-argument against this promotion>",
      "supporting_past_prs": [<int>, ...]
    }
  ],
  "weak_observations": [
    {
      "observation": "<short string>",
      "axis": "<axis label>",
      "supporting_past_prs": [<int>, ...]
    }
  ]
}

Quote short — under 40 words per excerpt. Do not invent axis labels outside \
the list.
"""


USER_TEMPLATE = """NEW HUNK from open PR #{new_pr_marker} (file: {new_file}):
```
{new_hunk}
```

RETRIEVED CANDIDATES (top-{n} by hunk-embedding similarity, sorted by sim desc):

{candidates_block}

Decide which candidates' comments genuinely apply to the NEW hunk. If none, \
say so. Output JSON only.
"""


CANDIDATE_TEMPLATE = """--- candidate {idx} (sim={sim:.3f}, past_pr=#{pr}, file={file}) ---
PAST HUNK:
```
{hunk}
```
PAST COMMENT (from reviewer):
{comment}
"""


def _truncate(s: str, n: int) -> str:
    s = s or ""
    return s if len(s) <= n else s[: n - 15] + "\n... [truncated]"


_HUNK_HEADER_RE = __import__("re").compile(r"\+(\d+)(?:,(\d+))?")


def _hunk_window(
    diff_hunk: str,
    comment_line: float | int | None,
    before: int = 40,
    after: int = 40,
) -> str:
    """Extract a window of a unified diff centered on the commented line.

    `comment_line` is the NEW-file line the reviewer commented on (GitHub's
    PR-review `line` field). We parse @@ hunk headers to track new-file line
    numbers, advance through context / addition lines (skipping `-` deletions),
    and return roughly `before+after+1` lines centered on the match.

    On failure (no header, no match, missing line) we fall back to keeping the
    first (before+after) lines — same behavior as `_truncate` but line-aware.
    An @@ header line is always preserved at the top when we've clipped above
    it so the model can see where in the file the window sits.
    """
    if not diff_hunk:
        return diff_hunk
    lines = diff_hunk.splitlines()

    if comment_line is not None:
        try:
            comment_line = int(comment_line)
        except (TypeError, ValueError):
            comment_line = None

    target_idx: int | None = None
    if comment_line is not None:
        new_line_no: int | None = None
        for i, raw in enumerate(lines):
            if raw.startswith("@@"):
                m = _HUNK_HEADER_RE.search(raw)
                if m:
                    new_line_no = int(m.group(1))
                continue
            if new_line_no is None:
                continue
            if raw.startswith("-") and not raw.startswith("---"):
                continue
            if new_line_no == comment_line:
                target_idx = i
                break
            new_line_no += 1

    limit = before + after
    if target_idx is None:
        if len(lines) <= limit:
            return diff_hunk
        return "\n".join(lines[:limit]) + f"\n... [{len(lines) - limit} more lines hidden]"

    start = max(0, target_idx - before)
    end = min(len(lines), target_idx + after + 1)

    header_line: str | None = None
    for i in range(target_idx - 1, -1, -1):
        if lines[i].startswith("@@"):
            header_line = lines[i]
            break

    out: list[str] = []
    if header_line is not None and (start == 0 or not lines[start].startswith("@@")):
        # keep header for location context if we're clipping above it
        if start > 0 and lines[start - 1] is not header_line:
            out.append(header_line)
            if start > 0:
                out.append(f"... [{start} lines above hidden]")
    elif start > 0:
        out.append(f"... [{start} lines above hidden]")

    out.extend(lines[start:end])
    if end < len(lines):
        out.append(f"... [{len(lines) - end} lines below hidden]")
    return "\n".join(out)


@dataclass
class ReviewSuggestion:
    summary: str
    confidence: str
    strong_matches: list[dict]
    weak_observations: list[dict]
    raw_candidates: list[dict]
    usage: dict
    extras: dict | None = None  # for v3's new_hunk_plausible_concerns etc.


@dataclass
class SearchResult:
    """Output of the no-LLM search mode.

    Pure retrieval: every field comes verbatim from the index, with no LLM
    rephrasing or judgment. The windowed hunks are slices of the original
    diffs, never paraphrases. `pr_accepted=False` flags hits whose past PR
    was closed without acceptance into mathlib (proxy for "reviewers wanted
    changes the author didn't make"); `True` means it was accepted; `None`
    means unknown (older corpus parquet).
    """
    hits: list[dict]
    new_hunk_window: str
    n_total: int
    n_not_accepted: int
    n_accepted: int


class ReviewAssistant:
    def __init__(
        self,
        retriever: Retriever | None = None,
        openai_model: str = "gpt-5",
        prompt_version: str = "v1",
        provider: str = "openai",
        gemini_model: str = "gemini-2.5-pro",
    ) -> None:
        self.R = retriever or Retriever()
        if prompt_version not in ("v1", "v2", "v3", "v3.1"):
            raise ValueError(
                f"prompt_version must be 'v1'|'v2'|'v3'|'v3.1', got {prompt_version!r}"
            )
        self.prompt_version = prompt_version
        if provider not in ("openai", "gemini"):
            raise ValueError(f"provider must be 'openai'|'gemini', got {provider!r}")
        self.provider = provider
        self.model = gemini_model if provider == "gemini" else openai_model
        # LLM clients are constructed lazily on first review_hunk() call so
        # that the no-LLM `.search()` mode doesn't require an API key.
        self.client: OpenAI | None = None
        self._gemini = None

    def _ensure_llm_client(self) -> None:
        if self.provider == "openai" and self.client is None:
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise RuntimeError("OPENAI_API_KEY must be set for LLM mode")
            self.client = OpenAI(api_key=api_key)
        elif self.provider == "gemini" and self._gemini is None:
            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                raise RuntimeError("GEMINI_API_KEY must be set for LLM mode")
            from google import genai
            self._gemini = genai.Client(api_key=api_key)

    def search(
        self,
        hunk_text: str,
        top_k: int = 20,
        max_per_pr: int = 2,
        date_before: str | None = None,
        precomputed_hits: list | None = None,
        comment_line: float | int | None = None,
        new_window_before: int = 40,
        new_window_after: int = 40,
        cand_window_before: int = 12,
        cand_window_after: int = 12,
        not_accepted_only: bool = False,
    ) -> SearchResult:
        """Pure-retrieval mode: no LLM call, no possibility of hallucination.

        Returns the top-K most similar past (code, reviewer-comment) pairs
        from the index, exactly as they were written. No model decides which
        ones "apply"; the caller does.

        `not_accepted_only=True` filters down to hits whose past PR was closed
        without acceptance into mathlib — useful for "is anything like my code
        already in a PR that didn't make it?".
        """
        if precomputed_hits is not None:
            hits = precomputed_hits
        else:
            query_vec = self.R.embed_text(hunk_text)
            hits = self.R.search(
                query_vec,
                k=top_k,
                max_per_pr=max_per_pr,
                date_before=date_before,
            )

        if not_accepted_only:
            hits = [h for h in hits if getattr(h, "pr_accepted", None) is False]

        n_accepted = sum(1 for h in hits if getattr(h, "pr_accepted", None) is True)
        n_not_accepted = sum(1 for h in hits if getattr(h, "pr_accepted", None) is False)

        new_window = _hunk_window(
            hunk_text, comment_line,
            before=new_window_before, after=new_window_after,
        )

        out_hits: list[dict] = []
        for h in hits:
            d = h.as_dict() if hasattr(h, "as_dict") else dict(h)
            d["embedding_text_window"] = _hunk_window(
                h.embedding_text, h.line,
                before=cand_window_before, after=cand_window_after,
            )
            out_hits.append(d)

        return SearchResult(
            hits=out_hits,
            new_hunk_window=new_window,
            n_total=len(out_hits),
            n_accepted=n_accepted,
            n_not_accepted=n_not_accepted,
        )

    def review_hunk(
        self,
        hunk_text: str,
        new_file: str = "<unknown>",
        new_pr_marker: str = "<NEW>",
        top_k: int = 20,
        max_per_pr: int = 2,
        date_before: str | None = None,
        precomputed_hits: list | None = None,
        comment_line: float | int | None = None,
        new_window_before: int = 40,
        new_window_after: int = 40,
        cand_window_before: int = 12,
        cand_window_after: int = 12,
    ) -> ReviewSuggestion:
        if precomputed_hits is not None:
            hits = precomputed_hits
        else:
            query_vec = self.R.embed_text(hunk_text)
            hits = self.R.search(
                query_vec,
                k=top_k,
                max_per_pr=max_per_pr,
                date_before=date_before,
            )

        # Step 2: assemble prompt
        # Window each candidate around its own commented line (h.line); window
        # the new hunk around `comment_line` if we know it (in eval we do; in
        # true-open-PR inference the line is unknown and we fall back to a
        # first-N slice which is still bounded to 80 lines, not to the first
        # 2500 chars).
        cand_block = "\n".join(
            CANDIDATE_TEMPLATE.format(
                idx=i + 1,
                sim=h.sim,
                pr=h.pr_number,
                file=h.file_path,
                hunk=_hunk_window(
                    h.embedding_text, h.line,
                    before=cand_window_before, after=cand_window_after,
                ),
                comment=_truncate(h.comment_text, 800),
            )
            for i, h in enumerate(hits)
        )
        user_msg = USER_TEMPLATE.format(
            new_pr_marker=new_pr_marker,
            new_file=new_file,
            new_hunk=_hunk_window(
                hunk_text, comment_line,
                before=new_window_before, after=new_window_after,
            ),
            n=len(hits),
            candidates_block=cand_block,
        )

        system_prompt = {
            "v1": SYSTEM_PROMPT_V1,
            "v2": SYSTEM_PROMPT_V2,
            "v3": SYSTEM_PROMPT_V3,
            "v3.1": SYSTEM_PROMPT_V3_1,
        }[self.prompt_version]

        self._ensure_llm_client()

        if self.provider == "openai":
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg},
                ],
                response_format={"type": "json_object"},
            )
            raw = resp.choices[0].message.content or "{}"
            prompt_tokens = resp.usage.prompt_tokens
            completion_tokens = resp.usage.completion_tokens
        else:
            from google.genai import types as _gtypes
            import time, re
            cfg = _gtypes.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
            )
            resp = None
            last_err: Exception | None = None
            for attempt in range(8):
                try:
                    resp = self._gemini.models.generate_content(
                        model=self.model, contents=user_msg, config=cfg,
                    )
                    break
                except Exception as e:
                    last_err = e
                    msg = str(e)
                    retryable = any(code in msg for code in (
                        "429", "RESOURCE_EXHAUSTED",
                        "503", "UNAVAILABLE",
                        "500", "INTERNAL",
                        "504", "DEADLINE_EXCEEDED",
                    ))
                    if not retryable:
                        raise
                    m = re.search(r"retry in (\d+(?:\.\d+)?)s", msg, re.IGNORECASE)
                    wait = float(m.group(1)) + 2.0 if m else min(10.0 * (2 ** attempt), 120.0)
                    time.sleep(wait)
                    continue
            if resp is None:
                raise RuntimeError(f"gemini call failed after retries: {last_err}")
            raw = (resp.text or "{}").strip()
            um = getattr(resp, "usage_metadata", None)
            prompt_tokens = int(getattr(um, "prompt_token_count", 0) or 0)
            completion_tokens = int(getattr(um, "candidates_token_count", 0) or 0)

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = {
                "summary": "(parse error)",
                "confidence": "none",
                "strong_matches": [],
                "weak_observations": [],
            }

        _known = {"summary", "confidence", "strong_matches", "weak_observations"}
        extras = {k: v for k, v in data.items() if k not in _known}
        return ReviewSuggestion(
            summary=data.get("summary", ""),
            confidence=data.get("confidence", "none"),
            strong_matches=data.get("strong_matches", []) or [],
            weak_observations=data.get("weak_observations", []) or [],
            raw_candidates=[h.as_dict() if hasattr(h, "as_dict") else h for h in hits],
            usage={
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "provider": self.provider,
                "model": self.model,
            },
            extras=extras or None,
        )
