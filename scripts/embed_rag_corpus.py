"""Embed the RAG corpus using Voyage code-3 and save vectors to disk.

Reads:  data/index/rag_corpus.parquet
Writes: data/index/rag_vectors.npz  (vectors + record_ids)

Supports resuming: if rag_vectors.npz already exists with partial results,
it picks up from where it left off.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import shutil

import numpy as np
import pandas as pd
import voyageai


REPO_ROOT = Path(__file__).resolve().parent.parent
CORPUS_PATH = REPO_ROOT / "data" / "index" / "rag_corpus.parquet"
OUTPUT_PATH = REPO_ROOT / "data" / "index" / "rag_vectors.npz"

MODEL = "voyage-code-3"
DIMS = 1024
MAX_BATCH_TOKENS = 50000
MAX_BATCH_TEXTS = 64
MAX_RETRIES = 8
CHARS_PER_TOKEN = 2
MAX_HUNK_CHARS = 30000


def _make_batches(texts, start_idx):
    """Split texts into batches that respect the token limit."""
    batches = []
    i = start_idx
    while i < len(texts):
        batch = []
        batch_tokens = 0
        while i < len(texts) and len(batch) < MAX_BATCH_TEXTS:
            est_tokens = len(texts[i]) // CHARS_PER_TOKEN + 1
            if batch and batch_tokens + est_tokens > MAX_BATCH_TOKENS:
                break
            batch.append(i)
            batch_tokens += est_tokens
            i += 1
        if batch:
            batches.append(batch)
    return batches


def embed_corpus():
    api_key = os.getenv("VOYAGE_API_KEY")
    if not api_key:
        print("ERROR: VOYAGE_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    vo = voyageai.Client(api_key=api_key, max_retries=3)
    df = pd.read_parquet(CORPUS_PATH)
    df["embedding_text"] = df["embedding_text"].str[:MAX_HUNK_CHARS]
    texts = df["embedding_text"].tolist()
    record_ids = df["record_id"].tolist()
    total = len(texts)

    start_idx = 0
    vectors = np.zeros((total, DIMS), dtype=np.float32)

    if OUTPUT_PATH.exists():
        checkpoint = np.load(OUTPUT_PATH, allow_pickle=True)
        saved_ids = checkpoint["record_ids"].tolist()
        saved_vecs = checkpoint["vectors"]
        if len(saved_ids) == total and list(saved_ids) == record_ids:
            print("Already fully embedded. Nothing to do.")
            return
        start_idx = len(saved_ids)
        vectors[:start_idx] = saved_vecs[:start_idx]
        print("Resuming from row {:,} / {:,}".format(start_idx, total))

    batches = _make_batches(texts, start_idx)
    print("Total: {:,} texts in {:,} batches".format(total - start_idx, len(batches)), flush=True)

    total_tokens = 0
    t0 = time.time()
    embedded_count = start_idx

    for batch_num, batch_indices in enumerate(batches, 1):
        batch_texts = [texts[i] if texts[i].strip() else " " for i in batch_indices]

        for attempt in range(MAX_RETRIES):
            try:
                result = vo.embed(batch_texts, model=MODEL, input_type="document")
                break
            except Exception as exc:
                if attempt < MAX_RETRIES - 1:
                    wait = 2 ** (attempt + 1)
                    print("  Retry {} after error: {} (waiting {}s)".format(
                        attempt + 1, str(exc)[:120], wait))
                    time.sleep(wait)
                else:
                    raise

        for i, vec in zip(batch_indices, result.embeddings):
            vectors[i] = vec
        total_tokens += result.total_tokens
        embedded_count += len(batch_indices)

        elapsed = time.time() - t0
        done = embedded_count - start_idx
        total_todo = total - start_idx
        rate = done / elapsed if elapsed > 0 else 0
        eta = (total_todo - done) / rate if rate > 0 else 0

        if batch_num % 20 == 0 or batch_num <= 3 or embedded_count == total:
            print("[{:>6,} / {:,}]  batch {}/{}  tokens: {:,}  elapsed: {:.0f}s  ETA: {:.0f}s ({:.1f}min)".format(
                embedded_count, total, batch_num, len(batches),
                total_tokens, elapsed, eta, eta / 60), flush=True)

            _atomic_save(vectors[:embedded_count], record_ids[:embedded_count])

    _atomic_save(vectors, record_ids)


def _atomic_save(vectors, record_ids):
    tmp = OUTPUT_PATH.with_suffix(".tmp.npz")
    np.savez(tmp, vectors=vectors, record_ids=np.array(record_ids))
    shutil.move(str(tmp), str(OUTPUT_PATH))

    elapsed = time.time() - t0
    print()
    print("Done! {:,} vectors embedded in {:.0f}s ({:.1f}min)".format(
        total, elapsed, elapsed / 60))
    print("Total tokens: {:,}".format(total_tokens))
    print("Output: {}".format(OUTPUT_PATH))
    print("File size: {:.1f} MB".format(OUTPUT_PATH.stat().st_size / 1024 / 1024))


if __name__ == "__main__":
    embed_corpus()
