# qdrant/qdrant-edge-demo: analysis (2026-10-14)

Source: https://github.com/qdrant/qdrant-edge-demo (commit 1afc374). **No LICENSE**, so we use it as a reference for patterns only.

## Purpose
"Smart Glasses × Qdrant Edge". Simulated glasses keep a visual memory of a video (`input.mp4` at 1 fps), and you search it in natural language ("where are my keys?") offline.

It demonstrates:
- an embedded shard
- offline-first ingest through a durable queue
- **indexing on the server**, returned as full and partial snapshots
- the two-shard pattern

```
 DEVICE (Streamlit app.py)                                   SERVER
 bg thread: VideoCapture @1fps -> SSIM dedup (>0.75 skip) -> JPEG -> CLIP vision 512
   -> [Mutable EdgeShard] + [SQLiteAckQueue] --(5 s)--> POST /api/upsert (FastAPI proxy :8000, X-API-Key) --> Qdrant :6333 "smart_glasses" (HNSW)
   [Immutable EdgeShard] <-- unpack/update -- /api/snapshots/full | /api/snapshots/partial (manifest) <-- shard 0 snapshot
 UI: text -> CLIP text -> MMR(lambda=0.8) on BOTH shards -> merge by score -> dedup id -> top 3
```

## Stack
- **Runtime:** Python 3.11 (<3.14), managed with uv.
- **Vector store:** qdrant-edge-py 0.5.0 on the device. The server is the Docker image `qdrant/qdrant:latest`, reached with qdrant-client 1.16.2.
- **Models:** fastembed 0.8.0 with CLIP ViT-B-32 vision and text, on onnxruntime CPU.
- **Vision:** opencv, scikit-image for SSIM.
- **UI and backend:** a Streamlit UI and a FastAPI proxy.
- **Queue:** persist-queue (`SQLiteAckQueue`).
- No tests.

## Sync
- **IDs and payload:** IDs are uuid4, generated on the device. The payload is `{image_path, sync_timestamp}`; images are never uploaded.
- **Push:** each write is upserted into the mutable shard and put on a SQLite ack queue. A worker drains the queue every 5 s with ack/nack, giving at-least-once delivery. Upserts are idempotent.
- **Full sync:** shard 0 snapshot → `EdgeShard.unpack_snapshot` → reopen.
- **Partial sync:** `snapshot_manifest()` → proxy → `update_from_snapshot()`.
- **After a sync:** `delete_points_by_filter(sync_timestamp <= T)` on the mutable shard. The server wins conflicts.

## Configuration
None. Everything is hardcoded (`localhost:6333`, `demo-api-key`). Using Qdrant Cloud would need code changes: pass the API key and header, and stop recreating the collection on startup.

## Patterns worth re-implementing
- **Storage and sync:**
  - two-shard initialisation
  - local upsert and durable queue in one call
  - ack/nack upload loop
  - full and partial sync with range-delete cleanup
- **Retrieval:** MMR for diverse results.
- **Server side:** a thin proxy that keeps the API key off the devices.
- **Capture:** an **SSIM gate** that cheaply drops near-identical frames before embedding.

## Bugs and gaps
- **Frame skip:** `frame_count % frames_to_skip == 1` is never true when skip is 1.
- **Sync race:** there is a race between `force_sync` and taking the timestamp T.
- **MMR:** MMR merged across shards is not a global MMR.
- **Indexing:** `sync_timestamp` has no payload index.
- **Batching:** batches are unbounded.
- **Security:** demo-grade only.
