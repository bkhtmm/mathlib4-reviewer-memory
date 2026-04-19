#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from pipeline.build_review_events import build_review_events
from pipeline.config import load_config
from pipeline.export_ml_views import export_classifier_examples, export_rag_documents
from pipeline.extract_mathlib4 import Mathlib4Extractor
from pipeline.github_client import GitHubClient
from pipeline.http import GithubHttpClient, HttpSettings
from pipeline.normalize_mathlib4 import normalize_rows
from pipeline.state import ScraperState, utc_now_iso


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape mathlib4 PR lifecycle data.")
    parser.add_argument("--config", default="config/scraper.yaml", help="Path to scraper config.")
    parser.add_argument(
        "--mode",
        choices=["backfill", "sync", "hydrate-pr"],
        required=True,
        help="Extraction mode.",
    )
    parser.add_argument("--pr-number", type=int, default=None, help="PR number for hydrate-pr mode.")
    parser.add_argument(
        "--max-prs",
        type=int,
        default=None,
        help="Optional limit on PRs processed in this run (useful for dry-runs).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not os.getenv("GITHUB_TOKEN"):
        raise RuntimeError("GITHUB_TOKEN is required for reliable GitHub API scraping.")
    config = load_config(REPO_ROOT / args.config)
    state = ScraperState.load(REPO_ROOT / config.paths.state_file)

    http_client = GithubHttpClient(
        HttpSettings(
            timeout_seconds=config.api.timeout_seconds,
            max_retries=config.api.max_retries,
            backoff_seconds=config.api.backoff_seconds,
            user_agent=config.api.user_agent,
        )
    )
    gh_client = GitHubClient(
        http_client=http_client,
        api_base_url=config.api.base_url,
        graphql_url=config.api.graphql_url,
    )
    state_file_path = REPO_ROOT / config.paths.state_file
    extractor = Mathlib4Extractor(config=config, client=gh_client, state_file=state_file_path)

    run_started = datetime.now(timezone.utc)
    normalize_result = None

    def flush_batch(rows_by_entity: dict[str, list[dict]], _is_final: bool) -> None:
        nonlocal normalize_result
        if not any(rows_by_entity.values()):
            return
        normalize_result = normalize_rows(
            rows_by_entity=rows_by_entity,
            curated_root=REPO_ROOT / config.paths.curated_root,
            bot_patterns=config.filters.infra_bot_patterns,
        )

    if args.mode == "backfill":
        extract_result = extractor.run_backfill(
            state=state,
            max_prs=args.max_prs,
            on_flush=flush_batch,
            flush_every_prs=config.extraction.normalize_flush_every_prs,
            collect_rows=False,
        )
    elif args.mode == "sync":
        extract_result = extractor.run_sync(
            state=state,
            max_prs=args.max_prs,
            on_flush=flush_batch,
            flush_every_prs=config.extraction.normalize_flush_every_prs,
            collect_rows=False,
        )
    else:
        if args.pr_number is None:
            raise ValueError("--pr-number is required for hydrate-pr mode.")
        extract_result = extractor.run_hydrate_pr(pr_number=args.pr_number)
        normalize_result = normalize_rows(
            rows_by_entity=extract_result.rows_by_entity,
            curated_root=REPO_ROOT / config.paths.curated_root,
            bot_patterns=config.filters.infra_bot_patterns,
        )

    if normalize_result is None:
        normalize_result = normalize_rows(
            rows_by_entity={},
            curated_root=REPO_ROOT / config.paths.curated_root,
            bot_patterns=config.filters.infra_bot_patterns,
        )

    review_events_df = build_review_events(REPO_ROOT / config.paths.curated_root)
    rag_path = export_rag_documents(
        curated_root=REPO_ROOT / config.paths.curated_root,
        exports_root=REPO_ROOT / config.paths.exports_root,
    )
    classifier_path = export_classifier_examples(
        curated_root=REPO_ROOT / config.paths.curated_root,
        exports_root=REPO_ROOT / config.paths.exports_root,
    )

    run_summary = {
        "mode": args.mode,
        "run_id": extract_result.run_id,
        "started_at": run_started.isoformat(),
        "finished_at": utc_now_iso(),
        "extract_counts": extract_result.counts_by_entity,
        "normalized_counts": normalize_result.row_counts,
        "review_events_count": int(len(review_events_df)),
        "rag_export_path": str(rag_path),
        "classifier_export_path": str(classifier_path),
    }
    state.append_run(run_summary)
    state.save(REPO_ROOT / config.paths.state_file)

    print(json.dumps(run_summary, indent=2))


if __name__ == "__main__":
    main()
