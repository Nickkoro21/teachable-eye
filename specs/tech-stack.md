# Tech Stack

> Status: **v1.3** (2026-10-16: test set + evaluation, optional Claude help; v1.2: DINOv2-large) — choices marked *(decide by measurement)* are settled by a benchmark inside a feature, not up front.

## Core

| Concern | Choice | Notes |
|---|---|---|
| Language | Python 3.13 | Same interpreter as the reference robot env |
| Packaging | `uv` (standalone ≥ 0.13 in `.tools/uv`) | Lockfile committed; caches redirected to D: via `env.ps1` |
| Vector memory | **Qdrant Edge** `qdrant-edge-py==0.7.2` (pinned; beta) | One shard per task; upgrade to 0.8.x only in a dedicated feature |
| Optional sync | Qdrant Cloud via `qdrant-client` + REST shard snapshots | Two-shard pattern (mutable + immutable mirror); see `research/03` |
| Inference runtime | ONNX Runtime GPU 1.27 (CUDA 13) + PyTorch 2.13 cu130 | CUDA DLLs come from the torch wheel on Windows |
| Web server | FastAPI + uvicorn, HTTPS with self-generated cert (needed for phone camera/mic) | Local network only until the roles phase |
| UI | Server-rendered HTML + vanilla JS, installable as a **PWA** | No build step; works in Chrome on Android |
| Tests | `pytest`; evaluation scripts produce JSON + Markdown reports | Tests use only public, licence-compatible sample media or synthetic data |

## Models (per task)

| Task | Detector / ROI | Encoder | Decision |
|---|---|---|---|
| Objects | YOLOE-11L-seg prompt-free (Ultralytics, **AGPL-3.0**) + BoT-SORT; user boxes followed by **VitTrack** (OpenCV Zoo, Apache-2.0) | **DINOv2 ViT-L/14** (Meta, Apache-2.0; CLS + mean patch tokens, 2048-d, fp16 CUDA) — chosen by measurement; CLIP ViT-B/32, SigLIP 2, Unicom, DINOv2-base selectable (`OBJECT_ENCODER`) | k-NN over taught views + threshold + `uncertain` margin |
| People | **YuNet** face detector (OpenCV Zoo, Apache-2.0) | **SFace** (OpenCV Zoo, Apache-2.0) | k-NN + threshold; faces never leave the device |
| Approach — system | Aircraft detection + tracking | Crop embedding for gear (k-NN) + **landing-light detector** (brightness/saturation blob in the tracked box, temporal persistence) | Rule: `secured` iff gear-down ∧ light-on, else `possibly-unsecured`/`uncertain`; vote over N frames |
| Approach — glide path | Aircraft tracking (fixed ground camera) | Trajectory → fixed-length vector (resampled position/size over time) | k-NN against labelled approaches + `uncertain` |
| Voice (labels/queries) | — | Whisper (onnx-asr), `en` default, `el` supported | — |
| Optional cloud help (objects only) | YuNet face check before any picture leaves | **Claude** via the official `anthropic` SDK (`claude-opus-5-5`, structured JSON output, server-side refusal fallback) | Advice only: names, second opinion, summaries, metadata Q&A — never a decision |

Excluded: InsightFace/ArcFace pretrained weights (non-commercial licence).

## As built (feature 01, 2026-10-15)

**Modules** (`src/teachable_eye/`)

| Module | Role |
|---|---|
| `memory.py` | `TaskMemory`: one Qdrant Edge shard per task, named vector `v`, cosine; teach / recognize (k-NN, variants folded into their view) / forget label / forget view (+ its variants) / rename (merge) / list / wipe; indexes `label`, `kind`, `parent` |
| `policy.py` | `decide()`: `known` (≥ threshold) / `uncertain` (within margin, label only as a guess) / `unknown`; nearest neighbours as evidence |
| `vote.py` | Per-track majority vote over the last 3 recognitions (no flicker) |
| `tasks.py` | `VisualTask` shared by objects and people: live processing, hold (freeze TEACH selection), teach-from-video bursts, photo mode, user regions, follow, augmentation, thumbnail GC; `ObjectsTask`, `PeopleTask` |
| `detect.py` | YOLOE + BoT-SORT, stability gate (3 frames), masked padded crops, re-query every 2 s; photos at 1280 px |
| `faces.py` | YuNet + greedy IoU tracker + landmark-aligned SFace embeddings |
| `follow.py` | `FollowTrack`: VitTrack from a user box; replaces an overlapping detector box (IoU ≥ 0.5); ends after 8 unsure frames |
| `encoders.py` | Encoder registry, one interface (`embed`, `dim`): `clip-b32`, `unicom-b16` (fastembed ONNX), `siglip2-base`, `dinov2-base`, `dinov2-large` (transformers, fp16 CUDA) |
| `server.py` | FastAPI: `/ws` frames (one active camera), `/api/{hold,teach,burst,still,region,follow,unfollow,memory,rename,forget,forget_example,wipe,status}`, `/api/eval*`, `/api/reports/*.md`, `/api/assist*`, thumbnails; app shell served `no-cache` with content-hashed asset URLs |
| `evalset.py` | The test set: `data/eval/<task>/<id>.{jpg,json}`, never used for recognition |
| `evaluation.py` | Pure-array evaluation: outcomes (correct / wrong / uncertain / missed / rejected / false accept), recommended bands (zero dangerous errors), separation, augmentation and views-needed ablations, logistic-regression baseline, Markdown report |
| `assist.py` | Optional Claude help (off unless `ASSIST=on`): objects only, face check, small JPEGs, usage log |
| `web/` | Phone PWA (vanilla JS): landing page, live overlay, tap/cycle selection, photo pause with draw/resize, TEACH sheet with label chooser, Video burst, Memory with variants, EN/EL, front/back camera, 3-2-1, diagnostics |

**Encoder step-up (2026-10-15)** — `tools/bench_encoders.py` on two small local multi-view sets (author's phone thumbnails: 13 images / 3 labels; course objects: 16 / 6):

| encoder | phone AUC | phone margin | course margin | ms/img |
|---|---|---|---|---|
| clip-b32 | 0.902 | −0.137 | +0.141 | 3–12 |
| siglip2-base | 0.932 | −0.191 | +0.157 | 10–15 |
| unicom-b16 | 0.994 | −0.045 | +0.271 | 6–13 |
| dinov2-base | 1.000 | +0.033 | +0.326 | 10–22 |
| **dinov2-large** | **1.000** | **+0.057** | **+0.396** | 7–14 |

Only DINOv2 fully separates same-object from different-object pairs on the phone set. Live cost: ~63 ms per 960 px frame (vs ~55 ms with CLIP). Sets are small: indicative, to be confirmed by the evaluation tool on new phone data. Each encoder has its **own memory** (`data/memory/objects-<encoder>`; `clip-b32` keeps `data/memory/objects`) and its own **provisional** bands (`config.DEFAULT_OBJECT_BANDS`; dinov2-large 0.45/0.10). Taught **crops (384 px) are now kept** in `data/crops/` so `tools/reembed.py --from A --to B` rebuilds a memory for another encoder; the existing 13 views were migrated from their 160 px thumbnails. Thumbnail/crop clean-up checks every encoder's memory before deleting a shared file.

**Key parameters** (`.env`, defaults in `.env.example`): `OBJECT_ENCODER=dinov2-large`, objects bands per encoder,
`PEOPLE_THRESHOLD=0.40`, `PEOPLE_MARGIN=0.06`, `DETECT_CONF=0.30`, `DETECT_MIN_AREA=0.0003`,
`DETECT_MAX_AREA=0.90`, `AUGMENT=on`, `ENCODER_DEVICE=auto`. Boxes touching two frame edges are
flagged `background`. Bursts keep up to 10 views in 5 s, a view only if cosine < 0.95 to all kept views.

**Teach-time augmentation**: each taught view also stores hidden-by-default variants (objects: centre
zoom 70 %, mirror, darker; people: mirror, darker — faces are never cropped). Variants carry `parent`
and `aug`, have their own thumbnails, are listed under their view in Memory, and are deleted with it.

**Runtime**: `uv run teachable-eye --host 127.0.0.1 --no-https` (on the author's PC started at sign-in by a local helper script, hidden, with logs and crash restart) behind **Tailscale Serve** on port 8443
(trusted certificate, phone reachable away from home, nothing exposed on the Wi-Fi). Alternative:
`--host 0.0.0.0` with the self-signed certificate (`/cert.crt`). Only one process may open a shard
directory (Qdrant Edge); a second instance needs `TEYE_DATA_DIR`. Models live in `data/models/`
(YOLOE weights, OpenCV Zoo YuNet/SFace/VitTrack), downloaded on first use.

**Licence note**: Ultralytics (YOLOE, BoT-SORT) is **AGPL-3.0**. Fine for this open-source repo; before
any closed or commercial use, switch to an Apache-2.0 detector (RF-DETR, RT-DETR, OWLv2, Grounding DINO).

## Data model (Qdrant Edge)

- Shard per task, e.g. `objects`, `people`, `approach_system`, `approach_glidepath`.
- Point = one example view (or one approach for glide path); IDs are **UUIDs** (device-namespaced later for sync).
- Payload (indexed where filtered): `label`, `task`, `kind` (`taught`/`seen`/`eval`), `ts`, `source` (`webcam`/`phone`/`ground-cam`/`upload`), `aircraft_type`, `media_ref` (local path / hash — **never the media itself**), `split` (`train`/`eval`).
- Evaluation data is stored in a separate `eval` split and is **never** used for recognition.

## Data handling

- Media (images, video, audio, face crops) lives under a local `data/` directory **outside git tracking**; `.gitignore` denies media extensions repo-wide and a pre-commit check rejects them.
- Later: private, access-controlled store (private Hugging Face dataset or self-hosted) for backups and sharing.
- GPX files are used only by offline label-verification tools in `tools/`, never imported by the app.

## Hardware

| Role | Minimum | Recommended / current |
|---|---|---|
| Dev & inference PC | NVIDIA GPU ≥ 8 GB VRAM, 16 GB RAM, 4-core CPU | **Current:** i7-10700 (8C/16T), 32 GB RAM, RTX 4060 Ti 16 GB, NVMe (C:) + 2 TB HDD (D:) |
| Android (camera mode) | Android 10+, Chrome, same Wi-Fi as PC | Any recent phone; tripod mount for data collection |
| Android (on-device) | Chrome with WebGPU (Android 12+), 6 GB RAM | Snapdragon 8-series / recent Tensor or Dimensity *(decide by measurement)* |
| Ground camera (test 3) | 1080p, 25–30 fps, fixed mount, USB-UVC or RTSP | **4K** or optical zoom; see sizing note below |
| Field compute (test 3) | Laptop with NVIDIA GPU ≥ 8 GB | Or Jetson Orin NX/AGX (the reference robot already supports Jetson) |

**Demo v1 capture = the author's Android phone.** Record in 4K/30 fps, landscape, on a tripod, always at the same spot near the observer, with focus and exposure locked. Only the final approach matters, where the aircraft is visible to the eye. With the phone's main camera (~55 px/degree at 4K), an ~11 m aircraft is roughly 35 px across at 1 km, 70 px at 500 m and 115 px at 300 m. That is enough for the landing light everywhere and for the gear on short final. Zoom or a dedicated camera comes only after approval.

**Ground-camera sizing (post-approval, to be validated on site).** A trainer with ~11 m wingspan at 1.5 km subtends ~0.42°. ~60 px across the aircraft for gear checks needs ~140 px/degree → ~13° horizontal FOV at 1080p or ~27° at 4K. Glide-path tracking needs a **wide** view of the whole final approach, so either one 4K camera with digital crop, or two cameras (wide for trajectory, tele for gear/lights). The landing light is visible much farther away than the gear and gives the earliest cue.

## Environment & secrets

- `env.ps1` sets all caches under `D:\AI assistant on Device Memory\.cache` (keep C: untouched).
- Secrets come only from environment variables: `QDRANT_URL`, `QDRANT_API_KEY`, `HF_TOKEN`, `ANTHROPIC_API_KEY` (optional). Never written to files in the repo; `.env` is git-ignored.
- Anthropic API usage is per token and separate from any Claude subscription; every call's tokens are logged locally (`data/reports/assist-usage.jsonl`).
- Qdrant Cloud: use project-prefixed collection names; never delete collections we did not create (the cluster is shared).

## Licences

- Project licence: **Apache-2.0**.
- May reuse code from `https-deeplearning-ai/sc-on-device-ai-memory` (Apache-2.0) with attribution.
- `qdrant-labs/memory-fleet` and `qdrant/qdrant-edge-demo` have **no licence** → patterns only, no copied code.
- DeepLearning.AI course notebooks and `ro_shared_data` are **not** redistributed.
