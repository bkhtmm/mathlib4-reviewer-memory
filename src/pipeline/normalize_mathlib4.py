from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

from .storage import upsert_parquet


BORS_COMMAND_RE = re.compile(r"(?im)^\s*(bors\s+(r\+|merge|d\+)|maintainer merge)\s*$")


def _coalesce(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def _as_login(user_obj: Any) -> str | None:
    if isinstance(user_obj, dict):
        return user_obj.get("login")
    return None


def _ts_to_year_month(ts: str | None) -> tuple[int | None, int | None]:
    if not ts:
        return None, None
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.year, dt.month
    except ValueError:
        return None, None


def _is_bot_login(login: str | None, bot_patterns: list[str]) -> bool:
    if not login:
        return False
    login_lower = login.lower()
    if login_lower.endswith("[bot]") or login_lower.endswith("bot"):
        return True
    return any(pattern.lower() in login_lower for pattern in bot_patterns)


def _is_bors_command(text: str | None) -> bool:
    if not text:
        return False
    return bool(BORS_COMMAND_RE.search(text))


def _accepted_proxy(title: str | None, merged_at: str | None, body: str | None = None) -> bool:
    if merged_at:
        return True
    title_text = (title or "").lower()
    body_text = (body or "").lower()
    return "[merged by bors]" in title_text or "successfully merged into master" in body_text


@dataclass
class NormalizeResult:
    row_counts: dict[str, int]
    paths: dict[str, str]


def normalize_rows(
    rows_by_entity: dict[str, list[dict[str, Any]]],
    curated_root: Path,
    bot_patterns: list[str],
) -> NormalizeResult:
    curated_root.mkdir(parents=True, exist_ok=True)
    row_counts: dict[str, int] = {}
    paths: dict[str, str] = {}

    # pull requests
    pr_rows = []
    pr_users = []
    for row in rows_by_entity.get("pull_requests", []):
        pr_number = _coalesce(row.get("number"), row.get("pr_number"))
        pr_id = _coalesce(row.get("id"), row.get("node_id"), f"pr_{pr_number}")
        pr_number = _coalesce(row.get("number"), row.get("pr_number"))
        title = row.get("title")
        body = row.get("body")
        author_login = _as_login(row.get("author")) or _as_login(row.get("user"))
        merged_by_login = _as_login(row.get("mergedBy")) or _as_login(row.get("merged_by"))
        created_at = _coalesce(row.get("createdAt"), row.get("created_at"))
        updated_at = _coalesce(row.get("updatedAt"), row.get("updated_at"))
        closed_at = _coalesce(row.get("closedAt"), row.get("closed_at"))
        merged_at = _coalesce(row.get("mergedAt"), row.get("merged_at"))
        state = row.get("state")
        year, month = _ts_to_year_month(updated_at or created_at)
        pr_rows.append(
            {
                "pr_id": pr_id,
                "pr_number": pr_number,
                "title": title,
                "body": body,
                "state": state,
                "created_at": created_at,
                "updated_at": updated_at,
                "closed_at": closed_at,
                "merged_at": merged_at,
                "base_ref": _coalesce(row.get("baseRefName"), (row.get("base") or {}).get("ref")),
                "head_ref": _coalesce(row.get("headRefName"), (row.get("head") or {}).get("ref")),
                "author_login": author_login,
                "merged_by_login": merged_by_login,
                "url": row.get("url"),
                "mergeable": row.get("mergeable"),
                "is_draft": _coalesce(row.get("isDraft"), row.get("draft")),
                "accepted_proxy": _accepted_proxy(title, merged_at),
                "review_phase": _derive_review_phase(state=state, closed_at=closed_at),
                "scraped_at": row.get("scraped_at"),
                "run_id": row.get("run_id"),
                "year": year,
                "month": month,
            }
        )
        if author_login:
            pr_users.append({"login": author_login, "is_bot_author": _is_bot_login(author_login, bot_patterns), "source": "pull_requests"})
        if merged_by_login:
            pr_users.append({"login": merged_by_login, "is_bot_author": _is_bot_login(merged_by_login, bot_patterns), "source": "pull_requests"})

    _upsert_table(
        pr_rows,
        curated_root / "prs.parquet",
        key_cols=["pr_id", "pr_number"],
        row_counts=row_counts,
        paths=paths,
        table_name="prs",
    )

    # labels
    label_rows = []
    for row in rows_by_entity.get("pr_labels", []):
        label_rows.append(
            {
                "pr_number": row.get("pr_number"),
                "pr_node_id": row.get("pr_node_id"),
                "label_id": _coalesce(row.get("id"), row.get("node_id")),
                "label_name": row.get("name"),
                "label_color": row.get("color"),
                "label_description": row.get("description"),
                "scraped_at": row.get("scraped_at"),
                "run_id": row.get("run_id"),
            }
        )
    _upsert_table(
        label_rows,
        curated_root / "pr_labels.parquet",
        key_cols=["pr_number", "label_name"],
        row_counts=row_counts,
        paths=paths,
        table_name="pr_labels",
    )

    # files
    file_rows = []
    for row in rows_by_entity.get("pr_files", []):
        file_rows.append(
            {
                "pr_number": row.get("pr_number"),
                "file_sha": row.get("sha"),
                "file_path": row.get("filename"),
                "status": row.get("status"),
                "additions": row.get("additions"),
                "deletions": row.get("deletions"),
                "changes": row.get("changes"),
                "diff_text": row.get("patch"),
                "blob_url": row.get("blob_url"),
                "raw_url": row.get("raw_url"),
                "contents_url": row.get("contents_url"),
                "scraped_at": row.get("scraped_at"),
                "run_id": row.get("run_id"),
            }
        )
    _upsert_table(
        file_rows,
        curated_root / "pr_files.parquet",
        key_cols=["pr_number", "file_path"],
        row_counts=row_counts,
        paths=paths,
        table_name="pr_files",
    )

    # issue comments
    issue_comment_rows = []
    for row in rows_by_entity.get("issue_comments", []):
        login = _as_login(row.get("user"))
        body = row.get("body")
        issue_comment_rows.append(
            {
                "comment_id": _coalesce(row.get("id"), row.get("node_id")),
                "pr_number": row.get("pr_number"),
                "author_login": login,
                "author_association": row.get("author_association"),
                "body": body,
                "created_at": row.get("created_at"),
                "updated_at": row.get("updated_at"),
                "url": row.get("html_url"),
                "is_bot_author": _is_bot_login(login, bot_patterns),
                "is_bors_command": _is_bors_command(body),
                "accepted_proxy": _accepted_proxy(None, None, body),
                "scraped_at": row.get("scraped_at"),
                "run_id": row.get("run_id"),
            }
        )
        if login:
            pr_users.append({"login": login, "is_bot_author": _is_bot_login(login, bot_patterns), "source": "issue_comments"})
    _upsert_table(
        issue_comment_rows,
        curated_root / "issue_comments.parquet",
        key_cols=["comment_id"],
        row_counts=row_counts,
        paths=paths,
        table_name="issue_comments",
    )

    # reviews
    review_rows = []
    for row in rows_by_entity.get("reviews", []):
        login = _as_login(row.get("user"))
        review_rows.append(
            {
                "review_id": _coalesce(row.get("id"), row.get("node_id")),
                "pr_number": row.get("pr_number"),
                "author_login": login,
                "state": row.get("state"),
                "body": row.get("body"),
                "submitted_at": row.get("submitted_at"),
                "commit_id": row.get("commit_id"),
                "html_url": row.get("html_url"),
                "is_bot_author": _is_bot_login(login, bot_patterns),
                "scraped_at": row.get("scraped_at"),
                "run_id": row.get("run_id"),
            }
        )
        if login:
            pr_users.append({"login": login, "is_bot_author": _is_bot_login(login, bot_patterns), "source": "reviews"})
    _upsert_table(
        review_rows,
        curated_root / "reviews.parquet",
        key_cols=["review_id"],
        row_counts=row_counts,
        paths=paths,
        table_name="reviews",
    )

    # review comments
    review_comment_rows = []
    for row in rows_by_entity.get("review_comments", []):
        login = _as_login(row.get("user"))
        review_comment_rows.append(
            {
                "review_comment_id": _coalesce(row.get("id"), row.get("node_id")),
                "pr_number": row.get("pr_number"),
                "pull_request_review_id": row.get("pull_request_review_id"),
                "in_reply_to_id": row.get("in_reply_to_id"),
                "author_login": login,
                "path": row.get("path"),
                "line": row.get("line"),
                "start_line": row.get("start_line"),
                "side": row.get("side"),
                "start_side": row.get("start_side"),
                "commit_id": row.get("commit_id"),
                "body": row.get("body"),
                "diff_hunk": row.get("diff_hunk"),
                "created_at": row.get("created_at"),
                "updated_at": row.get("updated_at"),
                "html_url": row.get("html_url"),
                "is_bot_author": _is_bot_login(login, bot_patterns),
                "is_bors_command": _is_bors_command(row.get("body")),
                "scraped_at": row.get("scraped_at"),
                "run_id": row.get("run_id"),
            }
        )
        if login:
            pr_users.append({"login": login, "is_bot_author": _is_bot_login(login, bot_patterns), "source": "review_comments"})
    _upsert_table(
        review_comment_rows,
        curated_root / "review_comments.parquet",
        key_cols=["review_comment_id"],
        row_counts=row_counts,
        paths=paths,
        table_name="review_comments",
    )

    # commits
    commit_rows = []
    for row in rows_by_entity.get("commits", []):
        commit_author = (row.get("commit", {}) or {}).get("author", {}) or {}
        commit_committer = (row.get("commit", {}) or {}).get("committer", {}) or {}
        commit_rows.append(
            {
                "pr_number": row.get("pr_number"),
                "sha": row.get("sha"),
                "node_id": row.get("node_id"),
                "author_login": _as_login(row.get("author")),
                "committer_login": _as_login(row.get("committer")),
                "message": (row.get("commit", {}) or {}).get("message"),
                "authored_date": commit_author.get("date"),
                "committed_date": commit_committer.get("date"),
                "html_url": row.get("html_url"),
                "scraped_at": row.get("scraped_at"),
                "run_id": row.get("run_id"),
            }
        )
    _upsert_table(
        commit_rows,
        curated_root / "commits.parquet",
        key_cols=["sha"],
        row_counts=row_counts,
        paths=paths,
        table_name="commits",
    )

    # timeline events
    timeline_rows = []
    for row in rows_by_entity.get("timeline_events", []):
        actor_login = _as_login(row.get("actor"))
        label_obj = row.get("label") or {}
        created_at = _coalesce(row.get("created_at"), row.get("submitted_at"))
        year, month = _ts_to_year_month(created_at)
        source_obj = row.get("source")
        if isinstance(source_obj, (dict, list)):
            source_value = json.dumps(source_obj, ensure_ascii=True, sort_keys=True)
        else:
            source_value = source_obj
        timeline_event_id = _coalesce(row.get("id"), row.get("node_id"))
        timeline_rows.append(
            {
                "timeline_event_id": str(timeline_event_id) if timeline_event_id is not None else None,
                "pr_number": row.get("pr_number"),
                "event": row.get("event"),
                "actor_login": actor_login,
                "label_name": label_obj.get("name"),
                "created_at": created_at,
                "source": source_value,
                "is_bot_author": _is_bot_login(actor_login, bot_patterns),
                "scraped_at": row.get("scraped_at"),
                "run_id": row.get("run_id"),
                "year": year,
                "month": month,
            }
        )
        if actor_login:
            pr_users.append({"login": actor_login, "is_bot_author": _is_bot_login(actor_login, bot_patterns), "source": "timeline_events"})
    _upsert_table(
        timeline_rows,
        curated_root / "timeline_events.parquet",
        key_cols=["timeline_event_id", "pr_number", "event", "created_at"],
        row_counts=row_counts,
        paths=paths,
        table_name="timeline_events",
    )

    # users
    _upsert_table(
        pr_users,
        curated_root / "users.parquet",
        key_cols=["login"],
        row_counts=row_counts,
        paths=paths,
        table_name="users",
    )

    return NormalizeResult(row_counts=row_counts, paths=paths)


def _derive_review_phase(state: str | None, closed_at: str | None) -> str:
    state_upper = (state or "").upper()
    if state_upper == "OPEN":
        return "active-review"
    if state_upper in {"MERGED", "CLOSED"} and closed_at:
        return "closed"
    return "pre-review"


def _upsert_table(
    rows: list[dict[str, Any]],
    path: Path,
    key_cols: list[str],
    row_counts: dict[str, int],
    paths: dict[str, str],
    table_name: str,
) -> None:
    if rows:
        df_new = pd.DataFrame(rows)
    else:
        df_new = pd.DataFrame(columns=key_cols)
    df_merged = upsert_parquet(df_new, path, key_cols=key_cols)
    row_counts[table_name] = int(len(df_merged))
    paths[table_name] = str(path)
