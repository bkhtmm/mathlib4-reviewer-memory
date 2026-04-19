from __future__ import annotations

from datetime import datetime
import re
from pathlib import Path

import pandas as pd

from .storage import upsert_parquet


def _to_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _normalize_text(value: str | None) -> str:
    return (value or "").strip()


def _is_human_comment(is_bot_author: bool | None, body: str | None) -> bool:
    if bool(is_bot_author):
        return False
    text = _normalize_text(body).lower()
    if not text:
        return False
    if text.startswith("bors "):
        return False
    if text == "maintainer merge":
        return False
    return True


def _pick_issue_comment_file(body: str, files_df: pd.DataFrame) -> tuple[str | None, str | None]:
    if files_df.empty:
        return None, None
    lowered = body.lower()
    for _, row in files_df.iterrows():
        path = str(row.get("file_path") or "")
        if path and path.lower() in lowered:
            return path, row.get("diff_text")

    files_sorted = files_df.sort_values(by=["changes", "additions"], ascending=False, na_position="last")
    row = files_sorted.iloc[0]
    return row.get("file_path"), row.get("diff_text")


def _contains_bors_success_text(series: pd.Series) -> bool:
    return series.fillna("").str.contains("successfully merged into master", case=False).any()


def build_review_events(curated_root: Path) -> pd.DataFrame:
    prs = _read_optional_parquet(curated_root / "prs.parquet")
    pr_files = _read_optional_parquet(curated_root / "pr_files.parquet")
    reviews = _read_optional_parquet(curated_root / "reviews.parquet")
    review_comments = _read_optional_parquet(curated_root / "review_comments.parquet")
    issue_comments = _read_optional_parquet(curated_root / "issue_comments.parquet")
    commits = _read_optional_parquet(curated_root / "commits.parquet")
    pr_labels = _read_optional_parquet(curated_root / "pr_labels.parquet")

    if prs.empty:
        df = pd.DataFrame(columns=["event_id"])
        upsert_parquet(df, curated_root / "review_events.parquet", key_cols=["event_id"])
        return df

    pr_meta = prs.set_index("pr_number").to_dict(orient="index")
    labels_by_pr = (
        pr_labels.groupby("pr_number")["label_name"].apply(lambda x: sorted({str(v) for v in x if pd.notna(v)})).to_dict()
        if not pr_labels.empty
        else {}
    )
    commits_by_pr = commits.groupby("pr_number") if not commits.empty else None
    files_by_pr = pr_files.groupby("pr_number") if not pr_files.empty else None

    review_state_by_id = {}
    if not reviews.empty:
        review_state_by_id = reviews.set_index("review_id")["state"].to_dict()

    rows: list[dict] = []

    # review comments are naturally linked to files and lines.
    for _, rc in review_comments.iterrows():
        if not _is_human_comment(rc.get("is_bot_author"), rc.get("body")):
            continue
        pr_number = rc.get("pr_number")
        if pd.isna(pr_number):
            continue
        pr_number = int(pr_number)
        meta = pr_meta.get(pr_number, {})
        files_df = files_by_pr.get_group(pr_number) if files_by_pr is not None and pr_number in files_by_pr.groups else pd.DataFrame()
        file_path = rc.get("path")
        diff_text = None
        if not files_df.empty and file_path in set(files_df["file_path"].dropna().tolist()):
            file_row = files_df[files_df["file_path"] == file_path].head(1)
            diff_text = file_row.iloc[0].get("diff_text")
        if not diff_text:
            diff_text = rc.get("diff_hunk")

        comment_ts = _to_ts(rc.get("created_at"))
        resolved_proxy = False
        if commits_by_pr is not None and pr_number in commits_by_pr.groups and comment_ts is not None:
            cm = commits_by_pr.get_group(pr_number).copy()
            cm["authored_dt"] = cm["authored_date"].map(_to_ts)
            resolved_proxy = bool((cm["authored_dt"] > comment_ts).fillna(False).any())

        review_id = rc.get("pull_request_review_id")
        review_state = review_state_by_id.get(review_id)
        labels = labels_by_pr.get(pr_number, [])
        accepted_proxy = bool(meta.get("accepted_proxy"))
        rows.append(
            {
                "event_id": f"pr_{pr_number}_review_comment_{rc.get('review_comment_id')}",
                "event_type": "review_comment",
                "pr_number": pr_number,
                "pr_title": meta.get("title"),
                "pr_body": meta.get("body"),
                "pr_url": meta.get("url"),
                "pr_state": meta.get("state"),
                "labels": labels,
                "reviewer": rc.get("author_login"),
                "comment_text": rc.get("body"),
                "comment_created_at": rc.get("created_at"),
                "file_path": file_path,
                "line": rc.get("line"),
                "diff_text": diff_text,
                "review_state": review_state,
                "resolved_proxy": resolved_proxy,
                "accepted_proxy": accepted_proxy,
                "search_text": _build_search_text(
                    title=meta.get("title"),
                    body=meta.get("body"),
                    file_path=file_path,
                    diff_text=diff_text,
                    comment_text=rc.get("body"),
                    labels=labels,
                ),
            }
        )

    # issue comments are linked heuristically using changed files in the PR.
    issue_comments_by_pr = issue_comments.groupby("pr_number") if not issue_comments.empty else None
    for _, ic in issue_comments.iterrows():
        if not _is_human_comment(ic.get("is_bot_author"), ic.get("body")):
            continue
        pr_number = ic.get("pr_number")
        if pd.isna(pr_number):
            continue
        pr_number = int(pr_number)
        meta = pr_meta.get(pr_number, {})
        labels = labels_by_pr.get(pr_number, [])
        files_df = files_by_pr.get_group(pr_number) if files_by_pr is not None and pr_number in files_by_pr.groups else pd.DataFrame()
        file_path, diff_text = _pick_issue_comment_file(str(ic.get("body") or ""), files_df)

        comment_ts = _to_ts(ic.get("created_at"))
        resolved_proxy = False
        if commits_by_pr is not None and pr_number in commits_by_pr.groups and comment_ts is not None:
            cm = commits_by_pr.get_group(pr_number).copy()
            cm["authored_dt"] = cm["authored_date"].map(_to_ts)
            resolved_proxy = bool((cm["authored_dt"] > comment_ts).fillna(False).any())

        accepted_proxy = bool(meta.get("accepted_proxy"))
        if not accepted_proxy and issue_comments_by_pr is not None and pr_number in issue_comments_by_pr.groups:
            accepted_proxy = _contains_bors_success_text(issue_comments_by_pr.get_group(pr_number)["body"])

        rows.append(
            {
                "event_id": f"pr_{pr_number}_issue_comment_{ic.get('comment_id')}",
                "event_type": "issue_comment",
                "pr_number": pr_number,
                "pr_title": meta.get("title"),
                "pr_body": meta.get("body"),
                "pr_url": meta.get("url"),
                "pr_state": meta.get("state"),
                "labels": labels,
                "reviewer": ic.get("author_login"),
                "comment_text": ic.get("body"),
                "comment_created_at": ic.get("created_at"),
                "file_path": file_path,
                "line": None,
                "diff_text": diff_text,
                "review_state": None,
                "resolved_proxy": resolved_proxy,
                "accepted_proxy": accepted_proxy,
                "search_text": _build_search_text(
                    title=meta.get("title"),
                    body=meta.get("body"),
                    file_path=file_path,
                    diff_text=diff_text,
                    comment_text=ic.get("body"),
                    labels=labels,
                ),
            }
        )

    review_events = pd.DataFrame(rows)
    if not review_events.empty:
        review_events["label_text"] = review_events["labels"].apply(lambda vals: " ".join(vals) if isinstance(vals, list) else "")
        review_events["has_diff_text"] = review_events["diff_text"].fillna("").str.len() > 0
        review_events["has_file_path"] = review_events["file_path"].fillna("").str.len() > 0
    upsert_parquet(review_events, curated_root / "review_events.parquet", key_cols=["event_id"])
    return review_events


def _build_search_text(
    title: str | None,
    body: str | None,
    file_path: str | None,
    diff_text: str | None,
    comment_text: str | None,
    labels: list[str] | None,
) -> str:
    label_text = " ".join(labels or [])
    parts = [
        _normalize_text(title),
        _normalize_text(body),
        _normalize_text(file_path),
        _normalize_text(diff_text),
        _normalize_text(comment_text),
        label_text,
    ]
    merged = "\n".join(part for part in parts if part)
    merged = re.sub(r"\n{3,}", "\n\n", merged)
    return merged.strip()


def _read_optional_parquet(path: Path) -> pd.DataFrame:
    if path.exists():
        return pd.read_parquet(path)
    return pd.DataFrame()
