from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import time
from typing import Any, Iterator

from .config import ScraperConfig
from .github_client import GitHubClient, RepoRef
from .state import ScraperState, utc_now_iso
from .storage import append_json, utc_date_str, write_jsonl


PULL_REQUESTS_QUERY = """
query PullRequests($owner: String!, $name: String!, $first: Int!, $after: String, $states: [PullRequestState!]) {
  rateLimit { cost remaining resetAt }
  repository(owner: $owner, name: $name) {
    pullRequests(first: $first, after: $after, states: $states, orderBy: {field: UPDATED_AT, direction: DESC}) {
      pageInfo {
        hasNextPage
        endCursor
      }
      nodes {
        id
        number
        title
        body
        state
        createdAt
        updatedAt
        closedAt
        mergedAt
        url
        mergeable
        isDraft
        author { login }
        mergedBy { login }
        baseRefName
        headRefName
        labels(first: 100) {
          nodes { id name color description }
        }
        files(first: 100) {
          totalCount
          nodes { path additions deletions changeType }
        }
        reviews(first: 30) {
          totalCount
          nodes {
            id
            author { login }
            state
            body
            createdAt
            comments(first: 30) {
              totalCount
              nodes {
                id
                author { login }
                body
                path
                originalLine
                diffHunk
                createdAt
                updatedAt
              }
            }
          }
        }
        comments(first: 30) {
          totalCount
          nodes {
            id
            author { login }
            body
            createdAt
            updatedAt
          }
        }
        commits(first: 100) {
          totalCount
          nodes {
            commit {
              oid
              message
              authoredDate
              committedDate
              author { user { login } }
              committer { user { login } }
              url
            }
          }
        }
      }
    }
  }
}
"""


OVERFLOW_REVIEWS_QUERY = """
query OverflowReviews($owner: String!, $name: String!, $prNumber: Int!, $after: String) {
  rateLimit { cost remaining resetAt }
  repository(owner: $owner, name: $name) {
    pullRequest(number: $prNumber) {
      reviews(first: 30, after: $after) {
        totalCount
        pageInfo { hasNextPage endCursor }
        nodes {
          id
          author { login }
          state
          body
          createdAt
          comments(first: 30) {
            totalCount
            nodes {
              id
              author { login }
              body
              path
              originalLine
              diffHunk
              createdAt
              updatedAt
            }
          }
        }
      }
    }
  }
}
"""

OVERFLOW_REVIEW_COMMENTS_QUERY = """
query OverflowReviewComments($owner: String!, $name: String!, $prNumber: Int!, $reviewId: ID!, $after: String) {
  rateLimit { cost remaining resetAt }
  repository(owner: $owner, name: $name) {
    pullRequest(number: $prNumber) {
      reviews(first: 1) {
        nodes { id }
      }
    }
  }
  node(id: $reviewId) {
    ... on PullRequestReview {
      comments(first: 30, after: $after) {
        totalCount
        pageInfo { hasNextPage endCursor }
        nodes {
          id
          author { login }
          body
          path
          originalLine
          diffHunk
          createdAt
          updatedAt
        }
      }
    }
  }
}
"""

OVERFLOW_ISSUE_COMMENTS_QUERY = """
query OverflowIssueComments($owner: String!, $name: String!, $prNumber: Int!, $after: String) {
  rateLimit { cost remaining resetAt }
  repository(owner: $owner, name: $name) {
    pullRequest(number: $prNumber) {
      comments(first: 30, after: $after) {
        totalCount
        pageInfo { hasNextPage endCursor }
        nodes {
          id
          author { login }
          body
          createdAt
          updatedAt
        }
      }
    }
  }
}
"""


@dataclass
class ExtractResult:
    run_id: str
    rows_by_entity: dict[str, list[dict[str, Any]]]
    counts_by_entity: dict[str, int]


def _parse_ts(ts: str | None) -> datetime | None:
    if not ts:
        return None
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc)


_CHANGE_TYPE_MAP = {
    "ADDED": "added",
    "DELETED": "removed",
    "MODIFIED": "modified",
    "RENAMED": "renamed",
    "COPIED": "copied",
}


def _flatten_graphql_pr(pr: dict[str, Any], run_id: str) -> dict[str, list[dict[str, Any]]]:
    """Convert a single GraphQL PR node into flat entity rows matching the
    field names the normalizer expects (REST-style where needed)."""
    pr_number = int(pr["number"])
    now = utc_now_iso()
    base = {"scraped_at": now, "run_id": run_id, "pr_number": pr_number}

    result: dict[str, list[dict[str, Any]]] = {
        "pr_files": [],
        "issue_comments": [],
        "reviews": [],
        "review_comments": [],
        "commits": [],
    }

    for f in (pr.get("files") or {}).get("nodes") or []:
        result["pr_files"].append({
            **base,
            "filename": f.get("path"),
            "additions": f.get("additions"),
            "deletions": f.get("deletions"),
            "changes": (f.get("additions") or 0) + (f.get("deletions") or 0),
            "status": _CHANGE_TYPE_MAP.get(f.get("changeType", ""), f.get("changeType")),
        })

    for ic in (pr.get("comments") or {}).get("nodes") or []:
        author = ic.get("author") or {}
        result["issue_comments"].append({
            **base,
            "id": ic.get("id"),
            "node_id": ic.get("id"),
            "user": {"login": author.get("login")},
            "body": ic.get("body"),
            "created_at": ic.get("createdAt"),
            "updated_at": ic.get("updatedAt"),
        })

    for rv in (pr.get("reviews") or {}).get("nodes") or []:
        rv_author = rv.get("author") or {}
        review_id = rv.get("id")
        result["reviews"].append({
            **base,
            "id": review_id,
            "node_id": review_id,
            "user": {"login": rv_author.get("login")},
            "state": rv.get("state"),
            "body": rv.get("body"),
            "submitted_at": rv.get("createdAt"),
        })
        for rc in (rv.get("comments") or {}).get("nodes") or []:
            rc_author = rc.get("author") or {}
            result["review_comments"].append({
                **base,
                "id": rc.get("id"),
                "node_id": rc.get("id"),
                "pull_request_review_id": review_id,
                "user": {"login": rc_author.get("login")},
                "body": rc.get("body"),
                "path": rc.get("path"),
                "line": rc.get("originalLine"),
                "diff_hunk": rc.get("diffHunk"),
                "created_at": rc.get("createdAt"),
                "updated_at": rc.get("updatedAt"),
            })

    for cn in (pr.get("commits") or {}).get("nodes") or []:
        c = cn.get("commit") or {}
        c_author = (c.get("author") or {})
        c_committer = (c.get("committer") or {})
        result["commits"].append({
            **base,
            "sha": c.get("oid"),
            "node_id": c.get("oid"),
            "author": {"login": (c_author.get("user") or {}).get("login")},
            "committer": {"login": (c_committer.get("user") or {}).get("login")},
            "commit": {
                "message": c.get("message"),
                "author": {"date": c.get("authoredDate")},
                "committer": {"date": c.get("committedDate")},
            },
            "html_url": c.get("url"),
        })

    return result


def _detect_overflow(pr: dict[str, Any]) -> dict[str, bool]:
    """Check which nested connections were truncated at their first-page limit."""
    overflow: dict[str, bool] = {}
    reviews = pr.get("reviews") or {}
    fetched_reviews = len(reviews.get("nodes") or [])
    overflow["reviews"] = (reviews.get("totalCount") or 0) > fetched_reviews and fetched_reviews > 0

    comments = pr.get("comments") or {}
    fetched_comments = len(comments.get("nodes") or [])
    overflow["issue_comments"] = (comments.get("totalCount") or 0) > fetched_comments and fetched_comments > 0

    for rv in reviews.get("nodes") or []:
        rv_comments = rv.get("comments") or {}
        fetched_rc = len(rv_comments.get("nodes") or [])
        if (rv_comments.get("totalCount") or 0) > fetched_rc and fetched_rc > 0:
            overflow["review_comments"] = True
            break

    return overflow


class Mathlib4Extractor:
    def __init__(self, config: ScraperConfig, client: GitHubClient, state_file: Path | None = None):
        self.config = config
        self.client = client
        self.repo_ref = RepoRef(owner=config.repo.owner, name=config.repo.name)
        self.raw_root = config.paths.raw_root
        self.run_logs_dir = config.paths.run_logs_dir
        self.progress_every_prs = max(1, config.extraction.progress_every_prs)
        self._last_graphql_remaining: int | None = None
        self._last_graphql_reset_at: str | None = None
        self._state_file = state_file

    def _raw_path(self, entity: str, filename: str) -> Path:
        return self.raw_root / entity / f"dt={utc_date_str()}" / filename

    def _write_raw_rows(self, entity: str, filename: str, rows: list[dict[str, Any]]) -> None:
        if not rows:
            return
        write_jsonl(self._raw_path(entity, filename), rows)

    def _init_buckets(self) -> tuple[dict[str, list[dict[str, Any]]], dict[str, int]]:
        entities = [
            "pull_requests",
            "pr_labels",
            "pr_files",
            "issue_comments",
            "reviews",
            "review_comments",
            "commits",
            "timeline_events",
        ]
        rows_by_entity = {entity: [] for entity in entities}
        counts_by_entity = {entity: 0 for entity in entities}
        return rows_by_entity, counts_by_entity

    def _empty_rows(self) -> dict[str, list[dict[str, Any]]]:
        rows_by_entity, _ = self._init_buckets()
        return rows_by_entity

    def _pace_graphql(self, rate_limit: dict[str, Any] | None) -> None:
        """Sleep if needed to stay within GraphQL rate budget."""
        if not rate_limit:
            return
        remaining = rate_limit.get("remaining", 5000)
        reset_at = rate_limit.get("resetAt")
        self._last_graphql_remaining = remaining
        self._last_graphql_reset_at = reset_at

        if remaining > 200:
            return
        if not reset_at:
            time.sleep(5)
            return
        try:
            reset_dt = datetime.fromisoformat(reset_at.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            wait = (reset_dt - now).total_seconds() + 2
            if wait > 0:
                print(f"[rate-limit] remaining={remaining}, sleeping {wait:.0f}s until reset", flush=True)
                time.sleep(min(wait, 600))
        except (ValueError, TypeError):
            time.sleep(10)

    def _graphql_with_pacing(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        """Execute a GraphQL query and handle rate-limit pacing."""
        data = self.client.graphql(query, variables)
        self._pace_graphql(data.pop("rateLimit", None))
        return data

    def _iter_pull_requests(
        self, start_cursor: str | None = None, states: list[str] | None = None
    ) -> Iterator[tuple[list[dict[str, Any]], str | None, bool]]:
        after = start_cursor
        page_num = 0
        while page_num < self.config.pagination.max_pages_per_entity:
            data = self._graphql_with_pacing(
                PULL_REQUESTS_QUERY,
                {
                    "owner": self.repo_ref.owner,
                    "name": self.repo_ref.name,
                    "first": self.config.pagination.graphql_page_size,
                    "after": after,
                    "states": states,
                },
            )
            pr_conn = data["repository"]["pullRequests"]
            nodes = pr_conn["nodes"]
            page_info = pr_conn["pageInfo"]
            page_num += 1
            yield nodes, page_info["endCursor"], page_info["hasNextPage"]
            if not page_info["hasNextPage"]:
                break
            after = page_info["endCursor"]

    def _fetch_overflow_reviews(self, pr_number: int, initial_nodes: list[dict]) -> list[dict]:
        """Paginate remaining reviews for a PR that had >30 reviews."""
        all_nodes = list(initial_nodes)
        after = None
        for _ in range(100):
            data = self._graphql_with_pacing(
                OVERFLOW_REVIEWS_QUERY,
                {
                    "owner": self.repo_ref.owner,
                    "name": self.repo_ref.name,
                    "prNumber": pr_number,
                    "after": after,
                },
            )
            conn = data["repository"]["pullRequest"]["reviews"]
            page_nodes = conn.get("nodes") or []
            all_nodes.extend(page_nodes)
            pi = conn.get("pageInfo") or {}
            if not pi.get("hasNextPage"):
                break
            after = pi.get("endCursor")
        return all_nodes

    def _fetch_overflow_issue_comments(self, pr_number: int, initial_nodes: list[dict]) -> list[dict]:
        """Paginate remaining issue comments for a PR that had >30 comments."""
        all_nodes = list(initial_nodes)
        after = None
        for _ in range(100):
            data = self._graphql_with_pacing(
                OVERFLOW_ISSUE_COMMENTS_QUERY,
                {
                    "owner": self.repo_ref.owner,
                    "name": self.repo_ref.name,
                    "prNumber": pr_number,
                    "after": after,
                },
            )
            conn = data["repository"]["pullRequest"]["comments"]
            page_nodes = conn.get("nodes") or []
            all_nodes.extend(page_nodes)
            pi = conn.get("pageInfo") or {}
            if not pi.get("hasNextPage"):
                break
            after = pi.get("endCursor")
        return all_nodes

    def _resolve_overflow(self, pr: dict[str, Any]) -> None:
        """Fetch truncated nested data in-place for a single PR node."""
        overflow = _detect_overflow(pr)
        pr_number = int(pr["number"])

        if overflow.get("reviews"):
            initial = (pr.get("reviews") or {}).get("nodes") or []
            all_reviews = self._fetch_overflow_reviews(pr_number, initial)
            pr["reviews"]["nodes"] = all_reviews

        if overflow.get("issue_comments"):
            initial = (pr.get("comments") or {}).get("nodes") or []
            all_comments = self._fetch_overflow_issue_comments(pr_number, initial)
            pr["comments"]["nodes"] = all_comments

    def _process_pr_batch(
        self,
        pr_nodes: list[dict[str, Any]],
        run_id: str,
        counts_by_entity: dict[str, int],
        rows_by_entity: dict[str, list[dict[str, Any]]],
        buffer_rows: dict[str, list[dict[str, Any]]],
        collect_rows: bool,
        page_index: int,
        state_name: str,
    ) -> None:
        """Process a batch of PR nodes from GraphQL, extracting all entity rows."""
        stamped_prs: list[dict[str, Any]] = []
        stamped_labels: list[dict[str, Any]] = []

        for pr in pr_nodes:
            stamped_prs.append({"scraped_at": utc_now_iso(), "run_id": run_id, **pr})
            for label in (pr.get("labels") or {}).get("nodes") or []:
                stamped_labels.append({
                    "scraped_at": utc_now_iso(),
                    "run_id": run_id,
                    "pr_number": pr["number"],
                    "pr_node_id": pr["id"],
                    **label,
                })

        self._write_raw_rows(
            "pull_requests",
            f"{run_id}_{state_name.lower()}_page_{page_index:05d}.jsonl",
            stamped_prs,
        )
        self._write_raw_rows(
            "pr_labels",
            f"{run_id}_{state_name.lower()}_page_{page_index:05d}.jsonl",
            stamped_labels,
        )

        self._ingest_rows("pull_requests", stamped_prs, counts_by_entity, rows_by_entity, buffer_rows, collect_rows)
        self._ingest_rows("pr_labels", stamped_labels, counts_by_entity, rows_by_entity, buffer_rows, collect_rows)

        for pr in pr_nodes:
            pr_number = int(pr["number"])
            self._resolve_overflow(pr)
            child_payloads = _flatten_graphql_pr(pr, run_id)
            for entity, child_rows in child_payloads.items():
                self._write_raw_rows(entity, f"{run_id}_pr_{pr_number}.jsonl", child_rows)
                self._ingest_rows(entity, child_rows, counts_by_entity, rows_by_entity, buffer_rows, collect_rows)

    def run_backfill(
        self,
        state: ScraperState,
        max_prs: int | None = None,
        on_flush: Callable[[dict[str, list[dict[str, Any]]], bool], None] | None = None,
        flush_every_prs: int | None = None,
        collect_rows: bool = True,
    ) -> ExtractResult:
        rows_by_entity, counts_by_entity = self._init_buckets()
        buffer_rows = self._empty_rows()
        if not collect_rows:
            rows_by_entity = self._empty_rows()
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        total_prs = 0
        page_index = 0

        for state_name in self.config.extraction.backfill_states:
            cursor_key = self._cursor_key("backfill", state_name)
            start_cursor = state.graphql_cursors.get(cursor_key)
            for page_index, (pr_nodes, end_cursor, has_next) in enumerate(
                self._iter_pull_requests(start_cursor=start_cursor, states=[state_name]), start=1
            ):
                if max_prs is not None and total_prs >= max_prs:
                    break

                batch_limit = max_prs - total_prs if max_prs is not None else len(pr_nodes)
                selected = pr_nodes[:batch_limit]
                if not selected:
                    state.graphql_cursors[cursor_key] = end_cursor
                    if not has_next:
                        break
                    continue

                self._process_pr_batch(
                    selected, run_id, counts_by_entity, rows_by_entity,
                    buffer_rows, collect_rows, page_index, state_name,
                )
                total_prs += len(selected)

                if on_flush and flush_every_prs and flush_every_prs > 0 and total_prs % flush_every_prs == 0:
                    on_flush(buffer_rows, False)
                    buffer_rows = self._empty_rows()

                if self._should_report_progress(total_prs, max_prs):
                    self._emit_progress(
                        run_id=run_id, mode="backfill", page_index=page_index,
                        total_prs=total_prs, counts_by_entity=counts_by_entity,
                        last_pr_number=int(selected[-1]["number"]),
                        state_name=state_name,
                    )

                truncated = len(selected) < len(pr_nodes)
                if not truncated:
                    state.graphql_cursors[cursor_key] = end_cursor
                self._save_state_checkpoint(state)
                if truncated or (max_prs is not None and total_prs >= max_prs):
                    break
                if not has_next:
                    break
            if max_prs is not None and total_prs >= max_prs:
                break

        if on_flush and self._has_any_rows(buffer_rows):
            on_flush(buffer_rows, True)

        state.updated_at_watermarks["pull_requests_latest"] = utc_now_iso()
        self._save_state_checkpoint(state)
        self._write_run_log(run_id, "backfill", counts_by_entity)
        self._emit_progress(
            run_id=run_id, mode="backfill", page_index=page_index,
            total_prs=total_prs, counts_by_entity=counts_by_entity,
            last_pr_number=None, final=True,
        )
        return ExtractResult(run_id=run_id, rows_by_entity=rows_by_entity, counts_by_entity=counts_by_entity)

    def run_sync(
        self,
        state: ScraperState,
        max_prs: int | None = None,
        on_flush: Callable[[dict[str, list[dict[str, Any]]], bool], None] | None = None,
        flush_every_prs: int | None = None,
        collect_rows: bool = True,
    ) -> ExtractResult:
        rows_by_entity, counts_by_entity = self._init_buckets()
        buffer_rows = self._empty_rows()
        if not collect_rows:
            rows_by_entity = self._empty_rows()
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

        last_watermark = _parse_ts(state.updated_at_watermarks.get("pull_requests_latest"))
        if last_watermark is None:
            last_watermark = datetime.now(timezone.utc) - timedelta(days=self.config.sync.requery_recent_days)
        cutoff = last_watermark - timedelta(days=self.config.sync.requery_recent_days)

        total_prs = 0
        page_index = 0
        for state_name in self.config.extraction.sync_states:
            cursor_key = self._cursor_key("sync", state_name)
            start_cursor = state.graphql_cursors.get(cursor_key)
            for page_index, (pr_nodes, end_cursor, has_next) in enumerate(
                self._iter_pull_requests(start_cursor=start_cursor, states=[state_name]), start=1
            ):
                if max_prs is not None and total_prs >= max_prs:
                    break

                candidate_nodes = [
                    pr for pr in pr_nodes
                    if not (pr_updated := _parse_ts(pr.get("updatedAt"))) or pr_updated >= cutoff
                ]

                batch_limit = max_prs - total_prs if max_prs is not None else len(candidate_nodes)
                selected = candidate_nodes[:batch_limit]
                if not selected:
                    state.graphql_cursors[cursor_key] = end_cursor
                    if not has_next:
                        break
                    continue

                self._process_pr_batch(
                    selected, run_id, counts_by_entity, rows_by_entity,
                    buffer_rows, collect_rows, page_index, state_name,
                )
                total_prs += len(selected)

                if on_flush and flush_every_prs and flush_every_prs > 0 and total_prs % flush_every_prs == 0:
                    on_flush(buffer_rows, False)
                    buffer_rows = self._empty_rows()

                if self._should_report_progress(total_prs, max_prs):
                    self._emit_progress(
                        run_id=run_id, mode="sync", page_index=page_index,
                        total_prs=total_prs, counts_by_entity=counts_by_entity,
                        last_pr_number=int(selected[-1]["number"]),
                        state_name=state_name,
                    )

                truncated = len(selected) < len(candidate_nodes)
                if not truncated:
                    state.graphql_cursors[cursor_key] = end_cursor
                self._save_state_checkpoint(state)
                if truncated or (max_prs is not None and total_prs >= max_prs):
                    break
                if not has_next:
                    break
            if max_prs is not None and total_prs >= max_prs:
                break

        if on_flush and self._has_any_rows(buffer_rows):
            on_flush(buffer_rows, True)
        state.updated_at_watermarks["pull_requests_latest"] = utc_now_iso()
        self._save_state_checkpoint(state)
        self._write_run_log(run_id, "sync", counts_by_entity)
        self._emit_progress(
            run_id=run_id, mode="sync", page_index=page_index,
            total_prs=total_prs, counts_by_entity=counts_by_entity,
            last_pr_number=None, final=True,
        )
        return ExtractResult(run_id=run_id, rows_by_entity=rows_by_entity, counts_by_entity=counts_by_entity)

    def run_hydrate_pr(self, pr_number: int) -> ExtractResult:
        rows_by_entity, counts_by_entity = self._init_buckets()
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

        pr_payload = self.client.rest_get(
            f"repos/{self.repo_ref.owner}/{self.repo_ref.name}/pulls/{pr_number}",
            params={},
        )
        if not isinstance(pr_payload, dict):
            raise RuntimeError(f"Unexpected PR payload type for {pr_number}")

        stamped_pr = {"scraped_at": utc_now_iso(), "run_id": run_id, **pr_payload}
        self._write_raw_rows("pull_requests", f"{run_id}_pr_{pr_number}.jsonl", [stamped_pr])
        rows_by_entity["pull_requests"].append(stamped_pr)
        counts_by_entity["pull_requests"] += 1

        labels = pr_payload.get("labels", [])
        label_rows = [
            {
                "scraped_at": utc_now_iso(),
                "run_id": run_id,
                "pr_number": pr_number,
                "pr_node_id": pr_payload.get("node_id"),
                "id": label.get("id"),
                "name": label.get("name"),
                "color": label.get("color"),
                "description": label.get("description"),
            }
            for label in labels
        ]
        self._write_raw_rows("pr_labels", f"{run_id}_pr_{pr_number}.jsonl", label_rows)
        rows_by_entity["pr_labels"].extend(label_rows)
        counts_by_entity["pr_labels"] += len(label_rows)

        per_page = self.config.pagination.rest_page_size
        child_payloads = {
            "pr_files": self.client.fetch_pr_files(self.repo_ref, pr_number, per_page=per_page),
            "issue_comments": self.client.fetch_issue_comments(self.repo_ref, pr_number, per_page=per_page),
            "reviews": self.client.fetch_reviews(self.repo_ref, pr_number, per_page=per_page),
            "review_comments": self.client.fetch_review_comments(self.repo_ref, pr_number, per_page=per_page),
            "commits": self.client.fetch_commits(self.repo_ref, pr_number, per_page=per_page),
            "timeline_events": self.client.fetch_timeline_events(self.repo_ref, pr_number, per_page=per_page),
        }
        for entity, child_rows in child_payloads.items():
            stamped_rows = [
                {"scraped_at": utc_now_iso(), "run_id": run_id, "pr_number": pr_number, **row}
                for row in child_rows
            ]
            self._write_raw_rows(entity, f"{run_id}_pr_{pr_number}.jsonl", stamped_rows)
            rows_by_entity[entity].extend(stamped_rows)
            counts_by_entity[entity] += len(stamped_rows)

        self._write_run_log(run_id, "hydrate-pr", counts_by_entity)
        return ExtractResult(run_id=run_id, rows_by_entity=rows_by_entity, counts_by_entity=counts_by_entity)

    def _save_state_checkpoint(self, state: ScraperState) -> None:
        if self._state_file:
            state.save(self._state_file)

    def _write_run_log(self, run_id: str, mode: str, counts_by_entity: dict[str, int]) -> None:
        append_json(
            self.run_logs_dir / f"{utc_date_str()}.jsonl",
            {"run_id": run_id, "mode": mode, "counts_by_entity": counts_by_entity, "ts": utc_now_iso()},
        )

    def _should_report_progress(self, total_prs: int, max_prs: int | None) -> bool:
        _ = max_prs
        if total_prs <= 0:
            return False
        return total_prs % self.progress_every_prs == 0

    def _emit_progress(
        self,
        run_id: str,
        mode: str,
        page_index: int,
        total_prs: int,
        counts_by_entity: dict[str, int],
        last_pr_number: int | None,
        state_name: str | None = None,
        final: bool = False,
    ) -> None:
        payload = {
            "type": "progress",
            "run_id": run_id,
            "mode": mode,
            "state": state_name,
            "page_index": page_index,
            "processed_prs": total_prs,
            "last_pr_number": last_pr_number,
            "counts_by_entity": counts_by_entity,
            "final": final,
            "ts": utc_now_iso(),
        }
        print(json.dumps(payload), flush=True)
        append_json(self.run_logs_dir / f"{utc_date_str()}_progress.jsonl", payload)

    def _cursor_key(self, mode: str, state_name: str) -> str:
        return f"pull_requests_{mode}_{state_name.lower()}"

    def _has_any_rows(self, rows_by_entity: dict[str, list[dict[str, Any]]]) -> bool:
        return any(bool(rows) for rows in rows_by_entity.values())

    def _ingest_rows(
        self,
        entity: str,
        rows: list[dict[str, Any]],
        counts_by_entity: dict[str, int],
        rows_by_entity: dict[str, list[dict[str, Any]]],
        buffer_rows: dict[str, list[dict[str, Any]]],
        collect_rows: bool,
    ) -> None:
        if not rows:
            return
        counts_by_entity[entity] += len(rows)
        buffer_rows[entity].extend(rows)
        if collect_rows:
            rows_by_entity[entity].extend(rows)
