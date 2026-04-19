from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Iterable, Mapping, Any

import pandas as pd


def utc_date_str() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=True))
            f.write("\n")
            count += 1
    return count


def append_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=True))
        f.write("\n")


def write_parquet(df: pd.DataFrame, path: Path, partition_cols: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if partition_cols:
        df.to_parquet(path, engine="pyarrow", index=False, partition_cols=partition_cols)
    else:
        df.to_parquet(path, engine="pyarrow", index=False)


def upsert_parquet(df_new: pd.DataFrame, path: Path, key_cols: list[str]) -> pd.DataFrame:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        df_existing = pd.read_parquet(path)
        df_all = pd.concat([df_existing, df_new], ignore_index=True)
    else:
        df_all = df_new.copy()

    if not len(df_all):
        return df_all

    df_all = df_all.drop_duplicates(subset=key_cols, keep="last")
    df_all.to_parquet(path, engine="pyarrow", index=False)
    return df_all
