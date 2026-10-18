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
- **R16** *(superseded 2026-10-16 by R34-R35: the author chose in-app collection, method A)*: `tools/evaluate.py --task objects|people --source DIR` reads `<label>_<n>.<ext>` images from a local folder and splits each label into teach and eval sets (default: first 2 teach, rest eval). It reports:
  - a confusion matrix including `uncertain` and `unknown`
  - a threshold sweep
  - an open-set check: labels held out entirely must come back `unknown`/`uncertain`
  - a comparison with logistic regression on the same embeddings
- **R17**: Reports are written to `data/reports/` as `.md` + `.json` and are never committed.

**People (TG6)**
- **R18**: The people task detects faces with YuNet and embeds them with SFace (OpenCV Zoo, Apache-2.0). Model files are downloaded into `data/models/` on first use.
- **R19**: The first time a new person label is taught, the page asks the user to confirm that this person consented. If the user declines, nothing is stored.
- **R20**: Mode switch between Objects and People. The two use separate shards, and "Forget everyone" wipes the people shard.

**Voice (TG7)**
- **R21** *(built 2026-10-16)*: Hold-to-talk on the phone (🎤 in the bottom bar, and next to the name field) records 16 kHz mono PCM and sends a WAV to the PC. Local Whisper (`onnx-asr`, `onnx-community/whisper-large-v3-turbo` fp16 on the GPU) transcribes it **in the app's language** (en/el, the landing-page switch), and the label is parsed from "this is (my) X" / «αυτό είναι (ο/η/το) X». The 🎤 in the bottom bar freezes the chosen box at press time (like TEACH) and opens the name sheet pre-filled; nothing is saved until Save (and consent for people). Recordings shorter than 0.4 s, longer than 15 s or silent are rejected before the model runs; audio is never stored. `VOICE=off` disables it.

## Non-functional

- **N1 Privacy:** media, thumbnails, face crops, embeddings, shards, models and reports live only under `data/` (git-ignored). The pre-commit no-media check stays green.
- **N2 Latency (PC, RTX 4060 Ti):** server processing is ≤ 150 ms per frame for objects and ≤ 60 ms for people. The first box appears within 1 s of an object entering the view on a normal home Wi-Fi.
- **N3 Robustness:** losing the phone (tab hidden, Wi-Fi drop) never crashes the server. Reconnecting resumes.
- **N4 Portability:** runs on Windows 11 with the repository's `uv` environment, with caches on D: through `env.ps1`. GPU is optional with a CPU fallback, slower but correct.
- **N5 Attribution:** every adapted file or function from the robot repo carries a header comment naming the source and the Apache-2.0 licence.
- **N6 Language:** code, comments and docs are in English. Greek appears only in UI strings and voice parsing.
- **N7 No secrets:** Qdrant Cloud is not used. The only credential is the optional `ANTHROPIC_API_KEY` (R36), read from the environment, never written to a file.

## Added during implementation

- **R22**: TEACH holds the selected crop on the server at press time; naming may take up to 5 min and survives the object leaving view.
- **R23**: Teach from video collects up to 10 distinct views of one track over 5 s (cosine < 0.95 to every kept view) and teaches them under one label.
- **R24**: The teach sheet offers existing labels as one-tap choices, the most likely first.
- **R25**: A landing page explains the four steps, shows whether the PC is reachable, and starts Objects or People mode.
- **R26**: Each taught view stores hidden augmented variants (objects: centre zoom 70%, mirror, darker; people: mirror, darker), deleted with their view; `AUGMENT=off` disables them.
- **R27**: On a paused photo the user can mark a box (tap or drag) or resize a box by its corners; the box is recognized and can be taught.
- **R28**: Resuming live view follows the chosen/fixed box with a single-object tracker (VitTrack) started from that box; it replaces an overlapping detector box and ends after 8 low-confidence frames.
- **R29**: Front/back camera switch; 3-2-1 countdown before a photo or a video teach.
- **R30**: Every variant has its own thumbnail and is listed under its view in Memory; deleting a view deletes its variants, a single variant can be deleted alone, and forgetting removes thumbnail files from disk too.
- **R31**: The teach sheet matches existing labels ignoring case and accents (ποτήρι = ποτηρι).
- **R32** *(done 2026-10-15)*: On a paused photo, label several boxes at once: a list of every box with its own label field (existing-label chooser, pre-filled from memory, empty = skip) and a single Save that teaches them all, each with its variants.
- **R33**: In "Label all" the photo stays touchable: selecting a row highlights its box, whose corners can be dragged to fix it (the row keeps its number and typed name); dragging on empty space adds a new box as the next numbered row.

**Test set and evaluation (TG5, method A — 2026-10-16)**
- **R34**: TEACH and Label all have a sticky **🧪 Test set** switch. When on, the held views are saved to `data/eval/<task>/` (crop JPEG + JSON label) and **never** to memory; a badge shows the mode. People views still need consent. A test label that memory does not know is a *stranger* (its right answer is `unknown`). Memory has a **Test set** tab listing test views per label (taught / never taught), each deletable.
- **R35**: **Run evaluation** (phone, Test set tab) embeds every test view with the live encoder and scores it against the live memory (variants count as their view). It reports, at the current bands and at the **recommended** bands: correct, **dangerous** (confident wrong name, or a stranger taken for something taught), uncertain, missed, strangers rejected; a confusion table; same/different separation (AUC, gap); nearest-label accuracy; with/without augmentation; accuracy vs number of views per label; k-NN vs logistic regression. The recommended threshold is the lowest with zero dangerous errors on the test set; the margin puts 90 % of strangers below the uncertain band (0.02-0.15). Reports: `data/reports/eval-<task>-<time>-<encoder>.{json,md}`; the phone links the Markdown. Thresholds are changed by the author in `.env`, never automatically.
- **R35b**: `tools/evaluate.py --encoders a,b,c` compares object encoders on the same taught views (kept crops, else thumbnails, plus variants) and the same test set; it reads the taught views from the running server, so the server can keep running.

**Optional help from Claude (TG8 — 2026-10-16)**
- **R36**: Off unless `ASSIST=on` on the PC **and** the user ticks "Claude help" on the phone's landing page (default off). The key comes only from `ANTHROPIC_API_KEY`. Objects only: the people task is refused, and every picture is checked with YuNet first; a picture with a face is never sent. Pictures go as JPEG ≤ 384 px. Every call's token usage is logged locally to `data/reports/assist-usage.jsonl`. The app works fully without it.
- **R37**: **Suggest names** in Label all: the empty rows' crops (no faces) are sent once; the suggestions only pre-fill the fields (marked), the user reviews and presses Save. Existing labels are sent so their wording is reused.
- **R38**: **Ask Claude** on an `uncertain`/`unknown` object: the crop and up to 2 kept pictures of each of the nearest taught labels are sent; Claude answers which label (or none), how sure, and why. Shown under the memory's own answer, never instead of it; "Teach as …" opens the name sheet pre-filled, the user confirms.
- **R39**: **Summary for managers** under an evaluation result: the report numbers (no pictures, no per-view rows) are rewritten in the UI language; saved next to the report.
- **R40**: **Ask about memory** (Memory tab): answered from objects metadata only (labels, view counts, first/last taught dates, test-set counts); no pictures, nothing about people.
- **R41**: Requests use `claude-opus-5-5` by default (`ASSIST_MODEL`; `claude-sonnet-5-5` is the cheaper alternative) with structured JSON output where an answer is parsed, explicit effort (low for names/opinions/questions, medium for summaries), adaptive thinking, and the server-side refusal fallback. System prompts follow Anthropic's guidance for these models: who it is for and why (the person confirms; a confident wrong answer costs more than "unsure"), data in XML tags, pictures before the question, positive instructions. A refusal, a missing key or a network error gives a clear message and changes nothing.

**Box editing and zoom (2026-10-16, author's request)**
- **R42**: TEACH, 🎤, Video and "Ask Claude" act only on the **active** box, the one the user tapped (solid, thick, with corner handles and a ✕). With nothing active and exactly one candidate on screen, that one becomes active; with several, the app asks the user to tap one first. The automatic suggestion is drawn dashed.
- **R43**: The active box can be **moved** (drag inside it) and **resized** (drag a corner; the opposite corner stays). On a paused photo this happens directly; on the live view the first drag pauses the picture (a photo is taken at once and the same object is made active by overlap), because a moving box cannot be fixed. The fixed box is recognised again and keeps its row in Label all. People boxes are only chosen or dropped (faces are aligned from landmarks).
- **R44**: The ✕ under the active box **drops** it: on a photo the box (and its Label-all row) is removed; live, that track is neither drawn nor offered again until the camera restarts (a followed box also stops being followed).
- **R45**: **Pinch zoom** (two fingers): on a paused photo the picture and its boxes zoom together (1-6×, the point under the fingers stays put, "🔍 1×" resets) so a small part can be boxed precisely; on the live view the camera's own zoom is used when the phone offers it, otherwise the user is told to pause and zoom the photo.

**Pictures, video files, memory without a camera (2026-10-16, author's request)**
- **R46**: The landing page has **🗂 Memory & evaluation**: Memory and the Test set (with Run evaluation) open with an Objects/People switch and **no camera and no camera socket**, so a PC can look while the phone keeps the camera.
- **R47**: **🖼 Label pictures / video** (landing page; on the PC also drag-and-drop): pictures from the device open one by one like a paused photo, with every photo tool (active box, move/resize/✕, pinch zoom, TEACH, 🎤, Label all, 🧪 Test set) and **Next ▶**. A video plays in a player (±1 s steps); **Use this frame** turns the current frame into such a photo, and 🎞 returns to the player. Only the chosen picture or frame, scaled to ≤ 1920 px, is sent to the PC; files are never uploaded or stored by the app. No camera socket is opened (the phone's camera is not replaced). Switching Objects/People re-detects the same picture.
- **R48**: People boxes can be drawn or fixed on a photo too: the PC looks for a face inside the box (region + 30 % margin, scaled to 640 px, YuNet at a lower confidence floor of 0.5 because the user says a face is there), aligns it from its landmarks and snaps the box to it; with no face it answers "no face found in that box". Faces are not followed by VitTrack (the face detector tracks them).

**Video teach, runner-ups, stronger augmentation (2026-10-17, author's requests)**
- **R49** *(revises R23)*: Video teach runs until the user stops it (Stop or Video again; 60 s cap in the app, 120 s on the PC). Every frame of the track is a candidate (a near-copy of the previous one, cosine ≥ 0.995, is skipped; 200 candidates at most, thinned evenly, stored ≤ 384 px). At Stop the **15 most different views of the whole recording** are kept: farthest-point sampling from the sharpest view, a view only if cosine < 0.95 to every kept one. (Before: the first 10 distinct views, then stop — a turning face filled 10 in about a second.)
- **R50**: Every recognition also returns the best score of up to 5 nearby **labels**. Tapping the active box's label (marked ▾) opens "What else it could be": labels, scores, the gap to the next one, the bands, and a hint when two labels are close.
- **R51** *(revises R26)*: Augmentation **profiles**, `AUGMENT=strong|basic|off` (default strong).
  - Basic is R26.
  - Strong, objects: zoom, mirror, darker, brighter, turned ±15°, four ~56 % pieces (75 % of each side), a quarter hidden ×2, blurred — 13 variants. Pieces keep about half, not a quarter: a quarter of a mug looks like many things, and a confident wrong name is the costliest error.
  - Strong, people: mirror, darker, brighter, tilt ±8°, blur, chin hidden — 7 variants. Faces are never cropped (alignment).
  - **Memory → Update variants** rebuilds every view's variants with the configured profile from its kept crop (or thumbnail), so a profile change needs no re-teaching.
- **R52**: The evaluation also scores the same test set with the variants of each profile rebuilt from the taught views (none / basic / strong): correct with no dangerous error, strangers rejected, dangerous at the current bands. The profile is chosen from these numbers.

**Hardening after the deep review (2026-10-17, three review sub-agents: backend, phone app, security)**
- **N8 Same-site only:** the server answers only to its own host names (127.0.0.1, localhost, the LAN IP when served there, and `TEYE_PUBLIC_HOST` from the local `.env`, e.g. the Tailscale name); browser requests that change something (POST, the camera socket) must come from one of those origins. Blocks DNS rebinding and cross-site requests from any page open on the PC.
- **N9 Bounded inputs:** pictures ≤ 15 MB and ≤ 40 MP (size read from the header before decoding); voice 8–48 kHz, ≤ 15 s (checked before resampling); labels ≤ 60 characters; boxes 4 finite numbers inside 0..1; at most 50 waiting selections, 2 video teaches, 4 open photos, 300 boxes per photo, 64 crops per Claude request.
- **N10 Forgetting is complete:** forgetting a label (or Forget everyone) also deletes its test views and the evaluation reports of that task that name it.
- **N11 Pinned models:** OpenCV Zoo files are fetched from a fixed commit and every downloaded model (YuNet, SFace, VitTrack, YOLOE) is checked against its SHA-256 before use. The local HTTPS certificate is a CA limited to path length 0 and to this server's own names.
- **R53**: Each photo has an id (`/api/still` returns it); hold, region, follow and name suggestions name their photo, the PC keeping the last 4 — a phone and a PC can each have a photo open without their boxes mixing. Memory changes (rename, forget) run in the same worker as teaching, so they cannot interleave with Update variants.

**Ideas taken from the course repo (2026-10-18, author's go; Apache-2.0, attributed in code)**
- **R54** *(refines R21)*: Before Whisper, the quiet before and after the sentence is cut (100 ms blocks; speech = RMS ≥ 0.008 or ≥ 15 % of the loudest block; 0.2 s kept around it) — from `robot/device/mic.py` `trim_to_speech`.
- **R55**: On an `uncertain` active box, **✓ Yes, it is "X"** teaches the box as X in one tap. The PC checks the guess again before writing (live: the guess shown for that track is still X; photo: the crop still comes out nearest to X) and saves nothing if it moved. People need consent (asked once per person per session). Hidden while 🧪 Test set is on — from `robot/brain/core.py` `confirm`.
- **R56** *(refines R35)*: The recommended threshold is the lowest with zero dangerous errors **plus a 0.02 safety margin**, and the report says that separately taken pictures give only a floor: live scenes score closer, so test views should come through the live camera — from `testdata/verify_scores.py`.
