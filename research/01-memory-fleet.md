# qdrant-labs/memory-fleet: analysis (2026-10-14)

Source: https://github.com/qdrant-labs/memory-fleet (commit 33f47b1, 2026-07-26). **No LICENSE**, so we use it as a reference for patterns only and copy no code.

## Purpose
"Fleet Memory": you show an object once to one device, by typing a name or saying "this is my mug". Every synced device then recognizes it.

- "Where did I leave my keys?" returns which device saw the object last, and when.
- No LLM at runtime. An optional local Ollama `gemma2:2b` only phrases the answer as a sentence.
- Offline-first. Cloud sync is opt-in.
- Author: Dylan Couzon (the course instructor).

## Architecture
Everything runs as one Python process with several threads.
```
 webcam -> grabber --frames--> Hub(WebSocket) <--> browser UI (vanilla JS)
              |                                    | teach/confirm/search/voice
          detect (YOLOE + BoT-SORT, ~8 Hz)          v
              | proposals                     FastAPI dispatch
          embed (Unicom 512-d) --Ingest-->  CORE (single thread, message queue)
                                             |        ^
                         +-------------------+        | ApplyPartialSnapshot
                         v                   v        |
                 mutable EdgeShard   immutable EdgeShard (fleet mirror)
                 (local teachings)   (read-only, snapshot-fed)
                                             ^
                       SyncManager thread ---+--- pull: partial snapshot (REST, ~30 s)
                              +-- push: qdrant-client upsert --> Qdrant Cloud "fleet" (+ "fleet-archive")
```

## Stack
- **Runtime:** Python 3.12 only, managed with uv.
- **Vector store:** `qdrant-edge-py==0.7.2`, pinned with the comment "beta, API drifts", plus qdrant-client 1.18.0.
- **Detection:** ultralytics 8.4.84 and torch 2.12.1, with YOLOE-11L on GPU or 11M on CPU.
- **Image embeddings:** fastembed 0.8.0 with **Qdrant/Unicom-ViT-B-32** (512-d, about 7.4 ms per crop on CPU).
- **Label search:** miniCOIL sparse plus bge-small-en-v1.5 dense (384-d), falling back to the built-in BM25.
- **Speech:** onnx-asr whisper-base.
- **Server and UI:** FastAPI with a vanilla JS front end.

## Qdrant Edge vs Cloud
**Shard config.**
- Named vector `exemplars`: 512-d cosine **multivector MaxSim**. One point is one object holding up to 24 views.
- Named vector `label_dense`: 384-d.
- Sparse vector `label` with the IDF modifier.
- Indexes: `kind` locally; `label_key` (keyword) and `t_seen` (float, used for decay) in the cloud.

**Two shards.** `mutable` holds local teachings and `immutable` is the fleet mirror. Recognition queries both, dedups by id, and the mutable copy wins.

**Pull.**
1. `snapshot_manifest()`
2. `POST /collections/fleet/shards/0/snapshot/partial/create` with an `api-key` header.
3. `update_from_snapshot()`

Edge 0.7.2 errors on an empty delta, so the code guards against it. A corrupted mirror is deleted and re-seeded.

**Push.** Opt-in, per object.
- Views are folded into an existing point when it has the same id, or the same label with MaxSim ≥ 0.80.
- Near-duplicate views (dot > 0.95) are dropped.
- Caps: 24 views and 8 negatives per object.

**IDs and conflicts.**
- IDs are UUID4.
- Local edits win: editing a fleet object is copy-on-write.
- After a pull, a local point is removed only if it carries `t_sync`.
- A fingerprint stops a push from stamping an object edited while the push was in flight.
- The server has no compare-and-set.

**Upkeep.**
- Heartbeat: `t_seen` and `last_seen_device` on recognized fleet points.
- **Fleet sleep:** merges same-label duplicates, then scores points with server-side `FormulaQuery` + `ExpDecayExpression` (30-day half-life). Points scoring below 0.05 move to `fleet-archive`.

**Hybrid search.** Sparse and dense legs fused with RRF **in the application**. Edge 0.7.2 exposes Prefetch/Fusion but does not apply them. Substring fallback and visual expansion add recall.

**Matcher.** Two thresholds (0.80 recognize, 0.55 suggest), a veto from negative exemplars, and a bonus for human-taught views.

## Configuration
- **Environment:** `QDRANT_URL`, `QDRANT_API_KEY` (unset means fully local), `DEVICE_NAME`, `EVENT_TAG`, `FM_PORT`, `FM_DATA_DIR`, `FM_CAMERA`, `FM_MODEL`, `FM_DEVICE`, `FM_PHRASE_MODEL`.
- **Not needed:** a management key or an account id.
- **Collections:** the app creates them itself.

## Running and platforms
- `make setup | run | run-b (second device on :8766) | demo-scale | fleet-sleep | reset`.
- Supported: macOS on Apple Silicon, and Linux with an NVIDIA GPU or CPU only.
- **Native Windows is unsupported.** It uses `stat().st_blocks` at startup, re-opens a `NamedTemporaryFile` in `/voice`, and uses `rm -rf`.

## Patterns worth re-implementing
- `memory/store.py`
  - two-shard store
  - multivector shard config
  - recognize fan-out
  - RRF text search
  - empty-delta guard
  - dedup after pull
- `sync/client.py`: collection and index bootstrap, partial snapshot download.
- `sync/manager.py`: SyncManager, `build_fold`.
- `sync/sleep.py`: decay and archive.
- `memory/core.py`: single-writer queue with an epoch guard, copy-on-write.
- `memory/matcher.py`: two thresholds with a negative veto.
- `perception/asr.py`: silence rejection by RMS.

## Gaps
- Visual objects only. There are no notes or episodic memory.
- No tests and no auth.
- Concurrent folds can race.
- No tombstones, so deleted views can return.
- Shard 0 is hardcoded.
- Thumbnails are stored as base64 in the cloud payload.
