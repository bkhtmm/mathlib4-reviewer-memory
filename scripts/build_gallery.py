"""Render the curated 10-case gallery from openpr_v3_1_all20.jsonl.

Output: gallery/README.md (a single self-contained markdown file).

This is a one-shot script; tweak ROSTER and re-run.
"""
from __future__ import annotations

import json
import re
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "eval" / "openpr_v3_1_all20.jsonl"
OUT = ROOT / "gallery" / "README.md"

PR_URL = "https://github.com/leanprover-community/mathlib4/pull/{n}"
USER_URL = "https://github.com/{u}"

# (tag, verdict, one-line note shown at bottom of card)
ROSTER: list[tuple[str, str, str]] = [
    ("D", "WIN",
     "Tool surfaced two on-target past PRs about minimizing imports — and "
     "independently flagged a duplicate import the human reviewer didn't mention."),
    ("O", "WIN",
     "Near-verbatim hit: tool retrieved a past PR with the exact "
     "`mem_evalFrom_iff_<X>_path` naming template the reviewer ended up asking for."),
    ("K", "PARTIAL + bonus",
     "Right axis (docstring), close direction; bonus: caught two real typos "
     "(`wth`→`with`, `ist`→`is`) that the human reviewer didn't mention."),
    ("S", "PARTIAL",
     "Off the human's exact axis (which was an unnecessary `Fin n` transport), "
     "but surfaced a different concrete concern — instance-diamond risk against "
     "`SimpleGraph.Hom.instFintype` — that is itself a plausible reviewer comment."),
    ("F", "PARTIAL",
     "Off-axis from the human (rename + edge case) but surfaced a real "
     "API-completeness concern: mirror the edge-connectivity convenience lemmas "
     "for the new vertex-connectivity API."),
    ("N", "PARTIAL (interesting)",
     "Human asked for proof-golf. Tool instead surfaced two _higher-level_ "
     "concerns (generalize away from `Valued`; don't expand `Valued`-centric API). "
     "Different axis but real reviewer concerns."),
    ("I", "CORRECT-SILENT",
     "Human asked for an explanatory comment — exactly the kind of advice that "
     "no past reviewer comment can be retrieved for. Tool said `low` and offered "
     "nothing concrete. Right behaviour."),
    ("E", "OFF-AXIS",
     "Cleanest failure mode: surface similarity (same file, similar code area) "
     "tricked the model into a `ppSpace`-formatting suggestion when the human's "
     "actual concern was a design wart (returning a string instead of `Syntax`)."),
    ("T", "MISSED-SILENT",
     "Hunk literally contains `lemma _root_.IsHausdorff.iff_injective`. Human "
     "said \"move it to avoid the ugly `_root_`\". Tool's plausible-concerns "
     "list didn't even include `namespace-organization`. Clear miss."),
    ("W", "MISSED-SILENT + bonus",
     "Human linked two existing similar definitions and asked to unify. Tool's "
     "plausible-concerns list didn't include `unify-with-existing`. Did catch "
     "a real typo (`LinealMap`→`LinearMap`) as a weak observation."),
]


_HDR = re.compile(r"@@\s+-\d+(?:,\d+)?\s+\+(\d+)(?:,(\d+))?\s+@@")


def window_hunk(diff: str, comment_line: float | int | None,
                before: int = 12, after: int = 12) -> str:
    """Return a small slice of the unified diff centered on `comment_line`.

    Mirrors the windowing used at inference time, so the gallery shows the
    same context the model itself looked at.
    """
    if not diff:
        return diff
    lines = diff.splitlines()
    try:
        cline = int(comment_line) if comment_line is not None else None
    except (TypeError, ValueError):
        cline = None

    target = None
    if cline is not None:
        new_no = None
        for i, raw in enumerate(lines):
            if raw.startswith("@@"):
                m = _HDR.search(raw)
                if m:
                    new_no = int(m.group(1))
                continue
            if new_no is None:
                continue
            if raw.startswith("-") and not raw.startswith("---"):
                continue
            if new_no == cline:
                target = i
                break
            new_no += 1

    if target is None:
        if len(lines) <= before + after:
            return diff
        return "\n".join(lines[: before + after]) + f"\n... [{len(lines) - (before + after)} more lines hidden]"

    start = max(0, target - before)
    end = min(len(lines), target + after + 1)
    out: list[str] = []
    if start > 0:
        out.append(f"... [{start} lines above hidden]")
    out.extend(lines[start:end])
    if end < len(lines):
        out.append(f"... [{len(lines) - end} lines below hidden]")
    return "\n".join(out)


def render_card(idx: int, row: dict, verdict: str, note: str) -> str:
    pr_n = row["pr_number"]
    pr_link = PR_URL.format(n=pr_n)
    user = row["reviewer_login"]
    user_link = USER_URL.format(u=user)
    file = row["file"]
    line = row["line"]
    advice_kind = row["advice_kind"]

    badge_color = {
        "WIN": "🟢 WIN",
        "WIN (partial)": "🟢 WIN (partial)",
        "PARTIAL": "🟡 PARTIAL",
        "PARTIAL + bonus": "🟡 PARTIAL + bonus",
        "PARTIAL (interesting)": "🟡 PARTIAL",
        "CORRECT-SILENT": "⚪ CORRECT-SILENT",
        "OFF-AXIS": "🔴 OFF-AXIS",
        "MISSED-SILENT": "🔴 MISSED-SILENT",
        "MISSED-SILENT + bonus": "🔴 MISSED-SILENT (with bonus)",
    }.get(verdict, verdict)

    hunk = window_hunk(row["hunk"], row["line"], before=10, after=10)
    if len(hunk.splitlines()) > 28:
        hunk = "\n".join(hunk.splitlines()[:28]) + "\n... [truncated for gallery]"

    parts = [
        f"## {idx}. [{badge_color}] PR [#{pr_n}]({pr_link}) — `{file}` (line {int(line) if isinstance(line, (int, float)) and line == int(line) else line})",
        "",
        f"**Reviewer:** [@{user}]({user_link}) &nbsp; · &nbsp; **Concern:** _{advice_kind}_",
        "",
        "### New hunk",
        "",
        "```diff",
        hunk,
        "```",
        "",
        "### What the human reviewer actually said",
        "",
    ]

    rs = row["reviewer_said"].strip()
    parts.append("> " + rs.replace("\n", "\n> "))
    parts.append("")

    parts.append(f"### What the tool produced (confidence: **{row['confidence']}**)")
    parts.append("")
    parts.append(f"> {row['summary']}")
    parts.append("")

    if row["strong_matches"]:
        parts.append("**Strong matches:**")
        parts.append("")
        for sm in row["strong_matches"]:
            past_n = sm.get("past_pr")
            past_file = sm.get("past_file", "")
            axis = sm.get("past_concern_axis", "")
            excerpt = (sm.get("past_comment_excerpt", "") or "").strip()
            why = (sm.get("applies_because", "") or "").strip()
            adapt = (sm.get("suggested_adaptation", "") or "").strip()
            counter = (sm.get("why_might_not_apply", "") or "").strip()
            parts.append(f"- **Past PR [#{past_n}]({PR_URL.format(n=past_n)})** &nbsp; · &nbsp; `{past_file}` &nbsp; · &nbsp; axis: `{axis}`")
            if excerpt:
                # quote the past reviewer's words
                quoted = excerpt.replace("\n", "\n  > ")
                parts.append(f"  > _Past reviewer:_ {quoted}")
            if why:
                parts.append(f"  - **Why it applies:** {why}")
            if adapt:
                parts.append(f"  - **Suggested adaptation:** {adapt}")
            if counter:
                parts.append(f"  - **Counter-argument:** {counter}")
            parts.append("")

    if row["weak_observations"]:
        parts.append("**Weak observations:**")
        parts.append("")
        for w in row["weak_observations"]:
            obs = (w.get("observation", "") or "").strip()
            ax = w.get("axis", "")
            sup = w.get("supporting_past_prs", []) or []
            sup_links = ", ".join(f"[#{n}]({PR_URL.format(n=n)})" for n in sup)
            tail = f" &nbsp; (axis: `{ax}`; support: {sup_links})" if sup_links else f" &nbsp; (axis: `{ax}`)" if ax else ""
            parts.append(f"- {obs}{tail}")
        parts.append("")

    parts.append("### Verdict")
    parts.append("")
    parts.append(note)
    parts.append("")
    parts.append("---")
    parts.append("")
    return "\n".join(parts)


def main() -> None:
    rows = {r["tag"]: r for r in (json.loads(l) for l in open(SRC))}
    missing = [t for t, _, _ in ROSTER if t not in rows]
    if missing:
        raise SystemExit(f"missing tags: {missing}")

    n_wins = sum(1 for _, v, _ in ROSTER if v.startswith("WIN"))
    n_partial = sum(1 for _, v, _ in ROSTER if v.startswith("PARTIAL"))
    n_silent = sum(1 for _, v, _ in ROSTER if v == "CORRECT-SILENT")
    n_off = sum(1 for _, v, _ in ROSTER if v == "OFF-AXIS")
    n_miss = sum(1 for _, v, _ in ROSTER if v.startswith("MISSED-SILENT"))

    intro = textwrap.dedent(f"""\
        # mathlib4 reviewer-memory tool — worked-examples gallery

        This is a small read-only gallery of what a retrieval-grounded review-suggestion tool
        produces, run on **{len(ROSTER)} currently-open PRs** in `leanprover-community/mathlib4`.

        Each PR in this gallery is one where a human reviewer left a comment that was *not*
        in the tool's training/retrieval index (the index covers closed PRs only). For each
        case the gallery shows, side by side:

        - the new hunk,
        - what the human reviewer actually wrote,
        - what the tool returned (summary, confidence, the past PRs it cited, and a
          counter-argument it self-generated for each citation).

        ## What this tool is — and is not

        - It is **not an "AI reviewer"**. It cannot replace any of the mathlib maintainers
          or reviewers. The held-out evaluation makes that clear (see the `eval/` link below).
        - It is a **memory** over ~158k past reviewer comments on ~35k closed mathlib4 PRs.
          Given a new hunk, it tries to find past reviewer comments that would plausibly
          apply, and asks an LLM (GPT-5) to ground each suggestion in a specific past
          comment quote — explicitly allowed to say "no relevant past reviews found".
        - It is intended for **contributors** who want to sanity-check a PR for the kinds
          of nits past reviewers have flagged before, *before* sending it to a reviewer.
          For reviewers, it might be a "have we seen this before?" sidekick — but that is
          a maybe, not a claim.

        ## How to read this gallery

        Each card is graded into one of five buckets:

        | Badge | Meaning |
        |---|---|
        | 🟢 **WIN** | The tool surfaced the same concern the human did, or one the human missed but is real. |
        | 🟡 **PARTIAL** | The tool surfaced related/adjacent advice; some genuine overlap with what a reviewer would say. |
        | ⚪ **CORRECT-SILENT** | The tool honestly said it had nothing to suggest, and the human's concern was the kind of thing no past comment could surface. |
        | 🔴 **OFF-AXIS** | The tool was confident but pointed at the wrong concern. Real failure mode. |
        | 🔴 **MISSED-SILENT** | The tool went silent when a clear past precedent existed. Real failure mode. |

        **Composition of this gallery:** {n_wins} WIN, {n_partial} PARTIAL, {n_silent} CORRECT-SILENT, {n_off} OFF-AXIS, {n_miss} MISSED-SILENT.

        Roughly half the gallery is failure modes or honest silences. That's intentional: a
        gallery that hides its failure modes can't be trusted.

        ## A note on prompt tuning (please read before grading)

        The current prompt (v3.1) was iterated by looking at where the previous version (v3)
        failed on a 20-case open-PR sweep — and the 10 cards in this gallery are drawn from
        that same 20-case sweep. So the gallery is best read as **"best-current-prompt on
        PRs the prompt was tuned to handle"**, *not* as a clean held-out evaluation.

        The genuinely held-out quantitative numbers (20 closed-PR queries the prompt has
        never seen, judged by an LLM judge) live in
        [`data/eval/llm_judge_report.md`](../data/eval/llm_judge_report.md). That's the
        un-tuned generalization metric; this gallery is the qualitative companion.

        I'm flagging this because (a) it's true, and (b) without disclosure a skeptical
        reader would reasonably suspect the WIN cards were engineered. They weren't —
        the prompt changes between v3 and v3.1 were a generic *default-include* rule and
        a generic *demotion* rule, not per-case fixes — but the cleanest way to say so
        is to just say it.

        ## What I'd like from you

        If you have 5 minutes, scroll the cards and tell me — for the ones marked WIN or
        PARTIAL — whether the cited past comment is _actually_ the kind of advice you'd
        give on the new hunk. That's the signal I'd use to decide whether this is worth
        improving further or shelving.

        For the failure-mode cards, I'm not asking you to fix them; I'm just being upfront
        about how it fails today.

        ## Roster

    """)

    toc_rows = []
    for i, (tag, verdict, _) in enumerate(ROSTER, start=1):
        r = rows[tag]
        toc_rows.append(f"| {i} | {verdict} | [#{r['pr_number']}]({PR_URL.format(n=r['pr_number'])}) | `{Path(r['file']).name}` | _{r['advice_kind']}_ |")

    toc = (
        "| # | Verdict | PR | File | Reviewer concern |\n"
        "|---|---|---|---|---|\n"
        + "\n".join(toc_rows)
        + "\n\n---\n\n"
    )

    cards = []
    for i, (tag, verdict, note) in enumerate(ROSTER, start=1):
        cards.append(render_card(i, rows[tag], verdict, note))

    appendix = textwrap.dedent("""\
        ## Appendix

        - **Full 20-case run** (raw JSON, including the 10 cases not shown in this gallery): `data/eval/openpr_v3_1_all20.jsonl`
        - **Per-case prompt + completion transcripts** for inspection: `data/eval/transcripts/openpr_*.txt`
        - **Held-out closed-PR evaluation** (LLM-judge report): `data/eval/llm_judge_report.md`
        - **Prompt-engineering ablation** (v1 vs v2, with cost numbers): `data/eval/prompt_ablation_report.md`
        - **The retrieval index itself** (≈35k closed PRs, ≈158k review comments): `data/curated/mathlib4/*.parquet`

        ## Caveats worth saying out loud

        - **n=20.** This gallery is a qualitative sample, not a benchmark. The held-out
          quantitative numbers live in `eval/`. Don't generalise from one card.
        - **Index is "closed PRs only".** Any concern that depends on very recent mathlib
          features (e.g. the new `module` / `@[expose] public section` syntax) will have
          thin coverage in the index, and the tool will tend to miss it. That's a real
          known limitation.
        - **Counter-arguments are self-generated.** Each suggestion ships with the model's
          own "why this might not apply" sentence. Read those, especially when grading.
        - **No claim of correctness.** Some "Past reviewer said" quotes are short paraphrases
          of longer comments. Click the past-PR link to read the full thread.
    """)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(intro + toc + "\n".join(cards) + "\n" + appendix)
    print(f"wrote {OUT}  ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
