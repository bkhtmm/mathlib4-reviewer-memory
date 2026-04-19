from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class RepoConfig:
    owner: str
    name: str


@dataclass(frozen=True)
class ApiConfig:
    base_url: str
    graphql_url: str
    timeout_seconds: int
    max_retries: int
    backoff_seconds: float
    user_agent: str


@dataclass(frozen=True)
class PaginationConfig:
    graphql_page_size: int
    rest_page_size: int
    max_pages_per_entity: int


@dataclass(frozen=True)
class SyncConfig:
    requery_recent_days: int


@dataclass(frozen=True)
class ExtractionConfig:
    backfill_states: list[str]
    sync_states: list[str]
    normalize_flush_every_prs: int
    progress_every_prs: int


@dataclass(frozen=True)
class PathsConfig:
    raw_root: Path
    curated_root: Path
    exports_root: Path
    state_file: Path
    run_logs_dir: Path


@dataclass(frozen=True)
class FiltersConfig:
    infra_bot_patterns: list[str]


@dataclass(frozen=True)
class ScraperConfig:
    repo: RepoConfig
    api: ApiConfig
    pagination: PaginationConfig
    sync: SyncConfig
    extraction: ExtractionConfig
    paths: PathsConfig
    filters: FiltersConfig


def _expand_path(path_like: str) -> Path:
    return Path(path_like).expanduser()


def load_config(config_path: str | Path) -> ScraperConfig:
    with Path(config_path).open("r", encoding="utf-8") as f:
        raw: dict[str, Any] = yaml.safe_load(f)

    return ScraperConfig(
        repo=RepoConfig(**raw["repo"]),
        api=ApiConfig(**raw["api"]),
        pagination=PaginationConfig(**raw["pagination"]),
        sync=SyncConfig(**raw["sync"]),
        extraction=ExtractionConfig(
            backfill_states=raw.get("extraction", {}).get("backfill_states", ["CLOSED", "OPEN"]),
            sync_states=raw.get("extraction", {}).get("sync_states", ["CLOSED", "OPEN"]),
            normalize_flush_every_prs=int(raw.get("extraction", {}).get("normalize_flush_every_prs", 25)),
            progress_every_prs=int(raw.get("extraction", {}).get("progress_every_prs", 5)),
        ),
        paths=PathsConfig(
            raw_root=_expand_path(raw["paths"]["raw_root"]),
            curated_root=_expand_path(raw["paths"]["curated_root"]),
            exports_root=_expand_path(raw["paths"]["exports_root"]),
            state_file=_expand_path(raw["paths"]["state_file"]),
            run_logs_dir=_expand_path(raw["paths"]["run_logs_dir"]),
        ),
        filters=FiltersConfig(**raw["filters"]),
    )
