from __future__ import annotations

from dataclasses import dataclass
import os
import random
import time
from typing import Any

import requests


@dataclass(frozen=True)
class HttpSettings:
    timeout_seconds: int
    max_retries: int
    backoff_seconds: float
    user_agent: str


class GithubHttpClient:
    def __init__(self, settings: HttpSettings):
        token = os.getenv("GITHUB_TOKEN", "").strip()
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": settings.user_agent,
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self.has_token = bool(token)

        self.settings = settings
        self.session = requests.Session()
        self.session.headers.update(headers)

    def request(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        timeout = kwargs.pop("timeout", self.settings.timeout_seconds)
        last_exc: Exception | None = None
        last_error: str | None = None

        for attempt in range(self.settings.max_retries):
            try:
                resp = self.session.request(method=method, url=url, timeout=timeout, **kwargs)
                if resp.status_code == 403 and "rate limit" in resp.text.lower():
                    last_error = f"403 rate-limited: {resp.text[:200]}"
                    self._backoff(attempt, rate_limited=True)
                    continue
                if resp.status_code in {429, 502, 503, 504}:
                    last_error = f"{resp.status_code} transient error: {resp.text[:200]}"
                    self._backoff(attempt)
                    continue
                resp.raise_for_status()
                self._maybe_pace_after_response(resp)
                return resp
            except requests.RequestException as exc:
                last_exc = exc
                last_error = str(exc)
                if getattr(exc, "response", None) is not None and exc.response.status_code in {401, 404}:
                    raise RuntimeError(f"GitHub API request failed: {exc}") from exc
                self._backoff(attempt)
            except Exception as exc:
                if "SSL" in type(exc).__name__ or "SSL" in str(exc):
                    last_exc = exc
                    last_error = f"SSL error: {exc}"
                    self._backoff(attempt)
                    continue
                raise

        details = last_error or str(last_exc) or "unknown error"
        raise RuntimeError(f"GitHub API request failed after retries: {details}")

    def _backoff(self, attempt: int, rate_limited: bool = False) -> None:
        base = self.settings.backoff_seconds * (2**attempt)
        jitter = random.uniform(0.0, 0.5)
        delay = min(base + jitter, 60.0 if rate_limited else 20.0)
        time.sleep(delay)

    def _maybe_pace_after_response(self, resp: requests.Response) -> None:
        remaining_raw = resp.headers.get("X-RateLimit-Remaining")
        reset_raw = resp.headers.get("X-RateLimit-Reset")
        if not remaining_raw or not reset_raw:
            return
        try:
            remaining = int(remaining_raw)
            reset_unix = int(reset_raw)
        except ValueError:
            return

        if remaining <= 5:
            sleep_for = max(0.0, reset_unix - time.time() + 1.0)
            if sleep_for > 0:
                time.sleep(min(sleep_for, 120.0))
