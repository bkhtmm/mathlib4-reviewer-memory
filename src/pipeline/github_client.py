from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterator

from .http import GithubHttpClient


@dataclass(frozen=True)
class RepoRef:
    owner: str
    name: str


class GitHubClient:
    def __init__(self, http_client: GithubHttpClient, api_base_url: str, graphql_url: str):
        self.http_client = http_client
        self.api_base_url = api_base_url.rstrip("/")
        self.graphql_url = graphql_url

    def graphql(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        resp = self.http_client.request(
            "POST",
            self.graphql_url,
            json={"query": query, "variables": variables},
        )
        payload = resp.json()
        if payload.get("errors"):
            raise RuntimeError(f"GraphQL errors: {payload['errors']}")
        result = dict(payload["data"])
        if "rateLimit" in result:
            result["rateLimit"] = result["rateLimit"]
        return result

    def rest_get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any] | list[Any]:
        url = f"{self.api_base_url}/{endpoint.lstrip('/')}"
        resp = self.http_client.request("GET", url, params=params)
        return resp.json()

    def rest_paginate(self, endpoint: str, per_page: int = 100, extra_params: dict[str, Any] | None = None) -> Iterator[list[dict[str, Any]]]:
        page = 1
        while True:
            params = {"per_page": per_page, "page": page}
            if extra_params:
                params.update(extra_params)
            payload = self.rest_get(endpoint, params=params)
            if not isinstance(payload, list) or not payload:
                break
            yield payload
            if len(payload) < per_page:
                break
            page += 1

    def fetch_pr_files(self, repo: RepoRef, pr_number: int, per_page: int = 100) -> list[dict[str, Any]]:
        endpoint = f"repos/{repo.owner}/{repo.name}/pulls/{pr_number}/files"
        rows: list[dict[str, Any]] = []
        for page_rows in self.rest_paginate(endpoint, per_page=per_page):
            rows.extend(page_rows)
        return rows

    def fetch_issue_comments(self, repo: RepoRef, pr_number: int, per_page: int = 100) -> list[dict[str, Any]]:
        endpoint = f"repos/{repo.owner}/{repo.name}/issues/{pr_number}/comments"
        rows: list[dict[str, Any]] = []
        for page_rows in self.rest_paginate(endpoint, per_page=per_page):
            rows.extend(page_rows)
        return rows

    def fetch_reviews(self, repo: RepoRef, pr_number: int, per_page: int = 100) -> list[dict[str, Any]]:
        endpoint = f"repos/{repo.owner}/{repo.name}/pulls/{pr_number}/reviews"
        rows: list[dict[str, Any]] = []
        for page_rows in self.rest_paginate(endpoint, per_page=per_page):
            rows.extend(page_rows)
        return rows

    def fetch_review_comments(self, repo: RepoRef, pr_number: int, per_page: int = 100) -> list[dict[str, Any]]:
        endpoint = f"repos/{repo.owner}/{repo.name}/pulls/{pr_number}/comments"
        rows: list[dict[str, Any]] = []
        for page_rows in self.rest_paginate(endpoint, per_page=per_page):
            rows.extend(page_rows)
        return rows

    def fetch_commits(self, repo: RepoRef, pr_number: int, per_page: int = 100) -> list[dict[str, Any]]:
        endpoint = f"repos/{repo.owner}/{repo.name}/pulls/{pr_number}/commits"
        rows: list[dict[str, Any]] = []
        for page_rows in self.rest_paginate(endpoint, per_page=per_page):
            rows.extend(page_rows)
        return rows

    def fetch_timeline_events(self, repo: RepoRef, pr_number: int, per_page: int = 100) -> list[dict[str, Any]]:
        endpoint = f"repos/{repo.owner}/{repo.name}/issues/{pr_number}/timeline"
        rows: list[dict[str, Any]] = []
        for page_rows in self.rest_paginate(endpoint, per_page=per_page):
            rows.extend(page_rows)
        return rows
