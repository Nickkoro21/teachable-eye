# Qdrant Edge: documentation notes (read 2026-10-14)

Sources: https://qdrant.tech/documentation/edge/ and its sub-pages:
- edge-vs-qdrant-cluster
- edge-api/{shard-lifecycle, configuration, updating-data, reading-data, snapshots}
- edge-quickstart, edge-fastembed-embeddings, edge-bm25
- edge-data-synchronization-patterns, edge-synchronization-guide

Also used: PyPI `qdrant-edge-py`, the Python examples in `qdrant/qdrant` (`lib/edge/python/examples`), and the cloud/authentication, guides/security, pricing and cloud/create-cluster pages.

## What it is
An embedded, in-process vector engine (~11 MB). The docs describe it as "SQLite for vector search".

- **Unit:** one `EdgeShard` is one directory.
- **Single shard only:** no collections, aliases or replication.
- **Manual indexing:** you run `optimize()` yourself to build the HNSW index.
- **Snapshots:** it can **restore** them but not **create** them.
- **API:** its own API. Not REST/gRPC, and not `QdrantClient(path=...)`.

- **Status:** beta. The API may change.
- **Licence:** Apache-2.0 (per PyPI).
- **Cost and account:** none needed to use Edge. An account is needed only for sync.
- **Versions:** this project pins **0.7.2** (June 2026). The latest is 0.8.0 (August 2026).
- **Check before relying on these in 0.7.2:** TurboQuant, `facet`, `Mmr`/`Sample`, `update_mode`, `prevent_unoptimized`, `Bm25Config`.

## API (Python)
**Lifecycle.**
- `EdgeShard.create(path, config)`, `EdgeShard.load(path, config=None)`.
- `info()`, `flush()`, `close()`.
- **Only one open `EdgeShard` per directory.** Shards in different directories can be open together.

**Configuration.**
- `EdgeConfig(vectors={...}, sparse_vectors={...}, on_disk_payload, hnsw_config, quantization_config, optimizers, max_search_threads, search_pool_core)`.
- In Python it can only be set at create or load time.

**Vectors and IDs.**
- Dense vectors: size and distance are immutable. Multivector (ColBERT style) is supported.
- Sparse vectors: `Modifier.Idf` for BM25.
- Distances: Cosine, Dot, Euclid, Manhattan.
- IDs: int or UUID.
- Quantization: scalar, product, binary, TurboQuant.

**Writes.** All go through `shard.update(UpdateOperation.X)` and are logged to the WAL first.
- Upsert (with `update_mode`), delete by ids or by filter.
- Update or delete vectors.
- Set, overwrite, delete or clear payload.
- Create or delete field indexes.
- Create or delete named vectors. Existing points are not backfilled.

**Reads.**
- `query(QueryRequest(query, prefetches, filter, limit, offset, score_threshold, params, with_payload, with_vector, using))`.
- Query kinds:
  - Nearest, recommend, discover, context
  - Fusion (RRF/DBSF)
  - OrderBy
  - **Formula** (score boosting, e.g. decay)
  - **Mmr**
  - Sample
- Also `scroll`, `retrieve`, `count`, `facet`.

**No background optimizer.** Until `optimize()` runs, search is brute force.

**Embeddings.**
- BM25 is built in: `Bm25(Bm25Config(language, tokenizer="multilingual"...))`. Use `embed_document` for documents and `embed_query` for queries.
- FastEmbed: set `cache_dir` and use `local_files_only=True` for offline use.

## Sync (implemented by the application)
1. **Seed:** `GET {QDRANT_URL}/collections/{C}/shards/0/snapshot` with the `api-key` header → `EdgeShard.unpack_snapshot(file, dir)` → `load`.
2. **Incremental:** `manifest = shard.snapshot_manifest()` → `POST .../shards/0/snapshot/partial/create` with `json=manifest` → `shard.update_from_snapshot(path)`. Pause local writes first.
3. **Push (dual write):** upsert locally and also enqueue a `PointStruct` → a worker calls `QdrantClient.upsert`. Use the same vector name, size and distance on both sides.

**Recommended layout:**
- A **mutable** shard for local writes, each stamped with `sync_timestamp`.
- An **immutable** shard that mirrors the server.
- After each refresh, `delete_points_by_filter(RangeFloat(lte=T))` on the mutable shard.
- Query both shards, merge, and dedup by id.

**Gaps and errors in the docs:**
- No conflict resolution or ID strategy is given. Use UUIDs, or UUIDv5 namespaced by device.
- Bug: the Python sync-guide snippet points `IMMUTABLE_SHARD_DIR` at the mutable path and then calls `rmtree` on it.

## Qdrant Cloud: what is needed
| Use | Needs |
|---|---|
| Edge only (local) | Nothing |
| Seed / partial snapshot (pull) | `QDRANT_URL` + `QDRANT_API_KEY`. A read-only key can download; check whether it can also create partial snapshots |
| Push (upsert), create collection | A key with **manage** or **collection read-write** |
| Management API key / account id | **Not needed** |

**Database API keys:**
- Created on Cluster Detail → API Keys, and shown only once.
- They **expire after 90 days by default**.
- Granular (JWT) keys can be scoped to specific collections.

**Free tier:**
- 1 node, 1 GB RAM, 0.5 vCPU, 4 GB disk (about 1M 768-d vectors).
- The cluster is **suspended after 1 week of inactivity and deleted 4 weeks after that**.

## Platforms
- **Python wheels:** Windows x64, macOS x64/arm64, Linux glibc/musl x64/arm64 (Jetson works). abi3 for CPython ≥ 3.10.
- **Mobile:** no Android or iOS wheels. An unofficial Dart/Flutter package exists.
- **Bindings:** Python and Rust.
- **GPU:** **none**. Search runs on the CPU; the GPU only speeds up the encoders.
- **Disk:** the WAL pre-allocates 32 MiB.

## Gotchas
- Beta: pin the version.
- Run `optimize()`, or search stays brute force.
- One open shard per directory.
- `info()` counts are approximate.
- `retrieve` silently drops ids that do not exist.
- Applying a snapshot rewrites the directory.
- Seeding from a full snapshot wipes the directory.
- No built-in retry, queue or conflict resolution.
