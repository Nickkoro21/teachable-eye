# Tech Stack

> Status: **v1.0** — choices marked *(decide by measurement)* are settled by a benchmark inside a feature, not up front.

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
| Objects | YOLOE (prompt-free) + BoT-SORT tracking | CLIP ViT-B/32 (512-d) baseline; SigLIP / DINOv2 candidates *(decide by measurement)* | k-NN over taught views + threshold + `uncertain` margin |
| People | **YuNet** face detector (OpenCV Zoo, Apache-2.0) | **SFace** (OpenCV Zoo, Apache-2.0) | k-NN + threshold; faces never leave the device |
| Approach — system | Aircraft detection + tracking | Crop embedding for gear (k-NN) + **landing-light detector** (brightness/saturation blob in the tracked box, temporal persistence) | Rule: `secured` iff gear-down ∧ light-on, else `possibly-unsecured`/`uncertain`; vote over N frames |
| Approach — glide path | Aircraft tracking (fixed ground camera) | Trajectory → fixed-length vector (resampled position/size over time) | k-NN against labelled approaches + `uncertain` |
| Voice (labels/queries) | — | Whisper (onnx-asr), `en` default, `el` supported | — |

Excluded: InsightFace/ArcFace pretrained weights (non-commercial licence).

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
- Secrets come only from environment variables: `QDRANT_URL`, `QDRANT_API_KEY`, `HF_TOKEN`. Never written to files in the repo; `.env` is git-ignored.
- Qdrant Cloud: use project-prefixed collection names; never delete collections we did not create (the cluster is shared).

## Licences

- Project licence: **Apache-2.0**.
- May reuse code from `https-deeplearning-ai/sc-on-device-ai-memory` (Apache-2.0) with attribution.
- `qdrant-labs/memory-fleet` and `qdrant/qdrant-edge-demo` have **no licence** → patterns only, no copied code.
- DeepLearning.AI course notebooks and `ro_shared_data` are **not** redistributed.
