"""RAG retrieval over the mathlib4 reviewer-comment index.

Loads the corpus (metadata) and the aligned L2-normalized vectors produced by
scripts/embed_rag_corpus.py and exposes a Retriever that supports:

  - Query by raw text (embeds with voyage-code-3, input_type="query"); requires
    VOYAGE_API_KEY.
  - Query by an existing corpus record_id (reuses the stored document vector);
    useful for offline evaluation without any API calls.
  - Filters:
      * exclude_pr       : drop hits from one PR (avoids same-PR leakage in
                           leave-one-out eval; simulates "fresh" retrieval on
                           open PRs that already have review activity).
      * date_before      : drop hits whose created_at >= cutoff (temporal
                           hold-out: filters the index at query time instead of
                           rebuilding it).
      * topic_whitelist  : keep only hits whose topic_labels intersect the set.
      * max_per_pr       : cap hits from any single PR (k=20 can otherwise turn
                           into 15 near-duplicates from one chatty PR).
      * mmr_lambda       : Maximal Marginal Relevance re-ranking for diversity.

All vectors are assumed L2-normalized, so cosine == dot product.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CORPUS = REPO_ROOT / "data" / "index" / "rag_corpus.parquet"
DEFAULT_VECTORS = REPO_ROOT / "data" / "index" / "rag_vectors.npz"

VOYAGE_MODEL = "voyage-code-3"
VOYAGE_DIMS = 1024
MAX_HUNK_CHARS = 30000


@dataclass
class Hit:
    rank: int
    sim: float
    record_id: str
    pr_number: int
    pr_title: str
    file_path: str
    line: float | None
    reviewer: str
    topic_labels: str
    has_suggestion: bool
    comment_text: str
    embedding_text: str
    created_at: str

    def as_dict(self) -> dict:
        return {
            "rank": self.rank,
            "sim": self.sim,
            "record_id": self.record_id,
            "pr_number": self.pr_number,
            "pr_title": self.pr_title,
            "file_path": self.file_path,
            "line": self.line,
            "reviewer": self.reviewer,
            "topic_labels": self.topic_labels,
            "has_suggestion": self.has_suggestion,
            "comment_text": self.comment_text,
            "embedding_text": self.embedding_text,
            "created_at": self.created_at,
        }


class Retriever:
    def __init__(
        self,
        corpus_path: Path | str = DEFAULT_CORPUS,
        vectors_path: Path | str = DEFAULT_VECTORS,
    ) -> None:
        self.df = pd.read_parquet(corpus_path).reset_index(drop=True)
        data = np.load(vectors_path, allow_pickle=True)
        self.vectors: np.ndarray = data["vectors"].astype(np.float32, copy=False)
        record_ids = data["record_ids"]

        corpus_rids = self.df["record_id"].to_numpy()
        if len(record_ids) != len(corpus_rids) or not np.array_equal(record_ids, corpus_rids):
            raise ValueError("record_ids in vectors file do not match corpus parquet row order")

        self.rid_to_row = {str(rid): i for i, rid in enumerate(corpus_rids)}
        self.pr_number = self.df["pr_number"].astype("int64").to_numpy()
        self.created_at = self.df["created_at"].astype(str).to_numpy()
        self._topic_sets = [
            frozenset(s.split(",")) if s else frozenset()
            for s in self.df["topic_labels"].astype(str).tolist()
        ]
        self._voyage_client = None

    @property
    def size(self) -> int:
        return len(self.df)

    def embed_text(self, text: str) -> np.ndarray:
        if self._voyage_client is None:
            import os
            import voyageai

            api_key = os.getenv("VOYAGE_API_KEY")
            if not api_key:
                raise RuntimeError("VOYAGE_API_KEY is not set")
            self._voyage_client = voyageai.Client(api_key=api_key, max_retries=3)

        text = text[:MAX_HUNK_CHARS] if text else " "
        if not text.strip():
            text = " "
        result = self._voyage_client.embed([text], model=VOYAGE_MODEL, input_type="query")
        vec = np.asarray(result.embeddings[0], dtype=np.float32)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec

    def search(
        self,
        query_vec: np.ndarray,
        k: int = 20,
        exclude_pr: int | Iterable[int] | None = None,
        exclude_record_ids: Iterable[int] | None = None,
        date_before: str | None = None,
        topic_whitelist: Iterable[str] | None = None,
        max_per_pr: int | None = None,
        mmr_lambda: float | None = None,
        pool_multiplier: int = 10,
    ) -> list[Hit]:
        query_vec = query_vec.astype(np.float32, copy=False)
        with np.errstate(divide="ignore", over="ignore", invalid="ignore"):
            sims = self.vectors @ query_vec
        sims = np.nan_to_num(sims, nan=-np.inf, posinf=-np.inf, neginf=-np.inf)

        mask = np.ones(len(sims), dtype=bool)
        if exclude_pr is not None:
            if isinstance(exclude_pr, (int, np.integer)):
                mask &= self.pr_number != int(exclude_pr)
            else:
                excluded = set(int(x) for x in exclude_pr)
                mask &= ~np.isin(self.pr_number, list(excluded))
        if exclude_record_ids is not None:
            excluded_rids = {str(r) for r in exclude_record_ids}
            ex_rows = [self.rid_to_row[r] for r in excluded_rids if r in self.rid_to_row]
            if ex_rows:
                mask[np.array(ex_rows)] = False
        if date_before is not None:
            mask &= self.created_at < date_before
        if topic_whitelist is not None:
            want = frozenset(topic_whitelist)
            ok = np.array([bool(ts & want) for ts in self._topic_sets], dtype=bool)
            mask &= ok

        masked_sims = np.where(mask, sims, -np.inf)

        pool_size = min(mask.sum(), max(k * pool_multiplier, k))
        if pool_size <= 0:
            return []
        pool_idx = np.argpartition(-masked_sims, pool_size - 1)[:pool_size]
        pool_idx = pool_idx[np.argsort(-masked_sims[pool_idx])]

        if mmr_lambda is not None:
            selected = self._mmr_select(pool_idx, masked_sims, k, mmr_lambda)
        elif max_per_pr is not None:
            selected = self._cap_per_pr(pool_idx, masked_sims, k, max_per_pr)
        else:
            selected = pool_idx[:k].tolist()

        hits: list[Hit] = []
        for rank, idx in enumerate(selected, 1):
            if np.isinf(masked_sims[idx]):
                continue
            row = self.df.iloc[int(idx)]
            hits.append(
                Hit(
                    rank=rank,
                    sim=float(masked_sims[idx]),
                    record_id=str(row.record_id),
                    pr_number=int(row.pr_number),
                    pr_title=str(row.pr_title),
                    file_path=str(row.file_path),
                    line=float(row.line) if pd.notna(row.line) else None,
                    reviewer=str(row.reviewer),
                    topic_labels=str(row.topic_labels),
                    has_suggestion=bool(row.has_suggestion),
                    comment_text=str(row.comment_text),
                    embedding_text=str(row.embedding_text),
                    created_at=str(row.created_at),
                )
            )
        return hits

    def search_by_record_id(
        self,
        record_id: str,
        k: int = 20,
        auto_exclude_self: bool = True,
        auto_exclude_pr: bool = False,
        **kwargs,
    ) -> list[Hit]:
        record_id = str(record_id)
        if record_id not in self.rid_to_row:
            raise KeyError(f"record_id {record_id} not in corpus")
        row_idx = self.rid_to_row[record_id]
        q = self.vectors[row_idx]
        ex_rids = list(kwargs.pop("exclude_record_ids", []) or [])
        if auto_exclude_self:
            ex_rids.append(record_id)
        ex_pr = kwargs.pop("exclude_pr", None)
        if auto_exclude_pr and ex_pr is None:
            ex_pr = int(self.pr_number[row_idx])
        return self.search(
            q,
            k=k,
            exclude_record_ids=ex_rids,
            exclude_pr=ex_pr,
            **kwargs,
        )

    def search_text(
        self,
        text: str,
        k: int = 20,
        **kwargs,
    ) -> list[Hit]:
        return self.search(self.embed_text(text), k=k, **kwargs)

    def _cap_per_pr(
        self,
        pool_idx: np.ndarray,
        sims: np.ndarray,
        k: int,
        max_per_pr: int,
    ) -> list[int]:
        per_pr: dict[int, int] = {}
        picked: list[int] = []
        for idx in pool_idx:
            if np.isinf(sims[idx]):
                continue
            pr = int(self.pr_number[idx])
            if per_pr.get(pr, 0) >= max_per_pr:
                continue
            picked.append(int(idx))
            per_pr[pr] = per_pr.get(pr, 0) + 1
            if len(picked) >= k:
                break
        return picked

    def _mmr_select(
        self,
        pool_idx: np.ndarray,
        sims: np.ndarray,
        k: int,
        lam: float,
    ) -> list[int]:
        if len(pool_idx) == 0:
            return []
        selected: list[int] = [int(pool_idx[0])]
        candidates = [int(i) for i in pool_idx[1:]]
        while candidates and len(selected) < k:
            sel_mat = self.vectors[selected]
            best_score = -np.inf
            best_i = -1
            for i in candidates:
                if np.isinf(sims[i]):
                    continue
                dup = float((self.vectors[i] @ sel_mat.T).max())
                score = lam * float(sims[i]) - (1.0 - lam) * dup
                if score > best_score:
                    best_score = score
                    best_i = i
            if best_i < 0:
                break
            selected.append(best_i)
            candidates.remove(best_i)
        return selected
