# Feature 01: Requirements

## Functional

**Memory core (TG2)**
- **R1**: The core stores examples as points in a Qdrant Edge shard (`qdrant-edge-py==0.7.2`), one shard per task. Points use UUID ids. The payload holds at least `label`, `task`, `kind` (`taught`), `ts`, `source` and `thumb` (a local file name only).
- **R2**: `teach(vector, label, ...)` adds one example. Teaching the same label again adds another view; it never overwrites.
- **R3**: `recognize(vector)` returns `{decision, label, score, neighbours[k]}`, where `decision` is one of:
  - `known`: score ≥ `threshold`
  - `uncertain`: `threshold − margin` ≤ score < `threshold`. The best label is shown only as a guess.
  - `unknown`: score below that range, or an empty memory
- **R4**: Forget a whole label, forget one example by id, rename a label (merging into an existing label is allowed), and list labels with their examples. Forget really deletes the points.
- **R5**: Memory survives an application restart. The shard is flushed after every write.
- **R6**: Thresholds and margins are set per task in `.env`, with documented defaults. The defaults for objects start from the robot's 0.90 / 0.05 and are re-calibrated with the TG5 tool.

**Objects (TG3)**
- **R7**: The objects task detects with YOLOE plus BoT-SORT tracking. It applies a stability gate of at least 3 consecutive detections and embeds the sharpest masked crop with CLIP ViT-B/32 on the GPU (CPU fallback).
- **R8**: Each stable track is re-queried at most every 2 s. The displayed label comes from a vote over that track's last 3 recognitions, so it does not flicker.

**Server + phone (TG4)**
- **R9**: A FastAPI server over HTTPS (self-signed certificate generated on first run, installable from `/cert.crt`). It binds to the LAN address chosen by `--host` and `--advertise`, port 8765 by default.
- **R10**: The phone page (an installable PWA in Chrome on Android) shows the rear camera full-screen. It sends JPEG frames (max side 960 px, about 6 fps) over `/ws` and draws boxes and labels from the JSON replies on the local video.
- **R11**: Only one camera source is active at a time. A new connection replaces the old one and resets the tracker.
- **R12**: TEACH: tap a box, type a label, confirm. The example is stored, and the next recognition of that track shows the label.
- **R13**: The Memory tab lists labels with thumbnails and counts and supports rename, forget label and forget one view.
- **R14**: Photo mode sends one full-resolution still and shows every detection with its decision and its top-3 neighbours.
- **R15**: UI strings exist in English (default) and Greek, switchable in the page and remembered on the phone.

**Evaluation (TG5)**
- **R16**: `tools/evaluate.py --task objects|people --source DIR` reads `<label>_<n>.<ext>` images from a local folder and splits each label into teach and eval sets (default: first 2 teach, rest eval). It reports:
  - a confusion matrix including `uncertain` and `unknown`
  - a threshold sweep
  - an open-set check: labels held out entirely must come back `unknown`/`uncertain`
  - a comparison with logistic regression on the same embeddings
- **R17**: Reports are written to `data/reports/<timestamp>-<task>.{md,json}` and are never committed.

**People (TG6)**
- **R18**: The people task detects faces with YuNet and embeds them with SFace (OpenCV Zoo, Apache-2.0). Model files are downloaded into `data/models/` on first use.
- **R19**: The first time a new person label is taught, the page asks the user to confirm that this person consented. If the user declines, nothing is stored.
- **R20**: Mode switch between Objects and People. The two use separate shards, and "Forget everyone" wipes the people shard.

**Voice (TG7)**
- **R21**: Hold-to-talk on the phone sends a WAV to the PC. Local Whisper (`onnx-asr`, language `en` by default, `el` selectable) transcribes it, and the label is parsed from "this is (my) X" / «αυτό είναι (ο/η/το) X». Silence is rejected.

## Non-functional

- **N1 Privacy:** media, thumbnails, face crops, embeddings, shards, models and reports live only under `data/` (git-ignored). The pre-commit no-media check stays green.
- **N2 Latency (PC, RTX 4060 Ti):** server processing is ≤ 150 ms per frame for objects and ≤ 60 ms for people. The first box appears within 1 s of an object entering the view on a normal home Wi-Fi.
- **N3 Robustness:** losing the phone (tab hidden, Wi-Fi drop) never crashes the server. Reconnecting resumes.
- **N4 Portability:** runs on Windows 11 with the repository's `uv` environment, with caches on D: through `env.ps1`. GPU is optional with a CPU fallback, slower but correct.
- **N5 Attribution:** every adapted file or function from the robot repo carries a header comment naming the source and the Apache-2.0 licence.
- **N6 Language:** code, comments and docs are in English. Greek appears only in UI strings and voice parsing.
- **N7 No secrets:** no credentials are needed for this feature; Qdrant Cloud is not used.

## Added during implementation

- **R22**: TEACH holds the selected crop on the server at press time; naming may take up to 5 min and survives the object leaving view.
- **R23**: Teach from video collects up to 10 distinct views of one track over 5 s (cosine < 0.95 to every kept view) and teaches them under one label.
- **R24**: The teach sheet offers existing labels as one-tap choices, the most likely first.
- **R25**: A landing page explains the four steps, shows whether the PC is reachable, and starts Objects or People mode.
