# DeepLearning.AI course, Appendix and robot repo: summary (2026-10-14)

Course: *Building AI Assistants with On-Device Memory* (DeepLearning.AI × Qdrant, taught by Dylan Couzon). The notebooks and data are course material and are **not redistributed** here.

Companion repo: https://github.com/https-deeplearning-ai/sc-on-device-ai-memory. It holds the Qdrant Edge Memory Robot under **Apache-2.0**, and we may reuse its code with attribution.

## Notebooks
**L3: Store / Find / Forget.**
- A shard with named vectors `text` (768-d, Nomic) and `image` (512-d, CLIP), cosine distance.
- Payload filters: `category` (keyword) and `price` (float).
- CLIP text→image search.
- Delete, and a latency curve.

**L4: Voice assistant.**
- A day of text, voice and photo memories.
- Whisper transcripts go into the same text space as typed notes.
- Recall per modality with thresholds: text 0.6, photo 0.23.
- A new note is retrievable immediately.

**L5: Learning through memory.**
- Teach an object from two photos, then recognize it.
- Threshold **0.80**: the highest non-match scored 0.74 and the lowest match 0.86.
- `freshness_ranking` with a 7-day half-life and weight 0.2.
- Persist and reload.

**Local check:** all notebooks run locally on our setup and reproduce the saved scores exactly (60/60 values).

## Appendix: hybrid on-device + cloud
1. Build a local `sync_shard` from a day of notes and photos.
2. Set `QDRANT_URL` and `QDRANT_API_KEY` from a free cluster. The key is shown only once. If either is empty, nothing is uploaded.
3. **Push.** `cloud_client("assistant_memory")` creates the collection (text 768 + image 512, cosine) **only if it does not exist**. `cloud_points` scrolls the shard with vectors, then `client.upsert` uploads them.
4. **Device B, full snapshot.** `GET /collections/{c}/shards/0/snapshot` → `EdgeShard.unpack_snapshot` → load. Device B can now search a day it did not record.
5. **Only what changed.** `push_note` to the cloud → `device_b.snapshot_manifest()` → `POST .../snapshot/partial/create` → `update_from_snapshot`. The download is small.
6. **Write locally, answer from both.** A local shard plus a push to the cloud. `recall_both` keeps the best score per id.

## Robot repo vs notebooks
**The robot adds:**
- YOLOE detection with BoT-SORT tracking
- masked crops
- sightings (when and where an object was seen), ignoring clutter, rename, forget a single view
- an HTTPS web UI for phones, and Jetson deployment

**The robot drops:**
- CLIP text→image search (measured as not useful on live crops)
- freshness weighting
- general notes
- cloud sync

**Thresholds:** the robot uses 0.90 on live crops with a 0.05 "maybe" margin. The notebooks use 0.80 on photos.

## Local environment notes
- `qdrant-edge-py 0.7.2`, `fastembed 0.8.0`, `onnxruntime-gpu 1.27.0` (CUDA 13), `torch 2.13.0+cu130`.
- CPU and GPU encoders give identical scores to three decimals.
- The Qdrant Cloud REST API answers on the default HTTPS port as well as on `:6333`.
- Use **project-prefixed collection names**, and never delete a collection this project did not create.
