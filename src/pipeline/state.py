from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ScraperState:
    graphql_cursors: dict[str, str | None] = field(default_factory=dict)
    updated_at_watermarks: dict[str, str | None] = field(default_factory=dict)
    last_runs: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def load(cls, path: Path) -> "ScraperState":
        if not path.exists():
            return cls()
        with path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
        return cls(
            graphql_cursors=payload.get("graphql_cursors", {}),
            updated_at_watermarks=payload.get("updated_at_watermarks", {}),
            last_runs=payload.get("last_runs", []),
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(
                {
                    "graphql_cursors": self.graphql_cursors,
                    "updated_at_watermarks": self.updated_at_watermarks,
                    "last_runs": self.last_runs[-100:],
                },
                f,
                indent=2,
                sort_keys=True,
            )

    def append_run(self, run_info: dict[str, Any]) -> None:
        payload = {"ts": utc_now_iso(), **run_info}
        self.last_runs.append(payload)
