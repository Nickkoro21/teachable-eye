# Feature 01: Memory core + objects & people from the phone

> Roadmap: Phase 1 · Branch: `feature/01-memory-core-objects-people` · Status: **PLAN, under review**

## Goal

The author points an Android phone at a hat, a microphone, `person-a` or `person-b`, teaches each one once or a few times, and sees the label appear live over the camera view. Anything untaught is shown as `unknown`, and borderline matches are shown as `uncertain`.

Everything runs on the author's PC (RTX 4060 Ti). The phone is the camera and the screen, connected over the local Wi-Fi.

## Approach

Build a small, generic **memory core** that later phases reuse for aircraft. Plug two **tasks** into it:

| Task | Region of interest | Encoder | Shard |
|---|---|---|---|
| `objects` | YOLOE (prompt-free) + BoT-SORT tracking, stability gate, masked crop | CLIP ViT-B/32 (512-d), GPU | `data/memory/objects` |
| `people` | YuNet face detector | SFace (128-d), Apache-2.0 | `data/memory/people` |

The core does not know about cameras or tasks. It stores examples (vector + payload), runs k-NN, applies the decision policy (`known` / `uncertain` / `unknown`) and returns the nearest examples as the explanation.

The **phone** runs a PWA in Chrome:
1. `getUserMedia` shows the live camera.
2. Downscaled JPEG frames go over a **WebSocket** to the PC.
3. The PC returns JSON results with normalised boxes.
4. The page draws the overlay on the local video, so there is no lag from a round-tripped video stream.

**Reuse.** Detection, cropping, label parsing, HTTPS certificate and WAV helpers are adapted from `https-deeplearning-ai/sc-on-device-ai-memory` (Apache-2.0), with attribution at the point of use. The robot's camera loop, MJPEG stream, laptop microphone, watchdog and appliance code are **not** reused.

## Task groups (in order)

1. **TG1 Scaffold**
   - `pyproject.toml` with uv: the pinned stack from `tech-stack.md`, CUDA torch, onnxruntime-gpu.
   - Package layout and settings from `.env`.
   - `pytest` runs.
2. **TG2 Memory core**
   - `TaskMemory` over one Qdrant Edge shard: teach, recognize (k-NN), forget a label, forget one example, rename, list.
   - Decision policy with threshold and `uncertain` margin.
   - Explanation through the top-k neighbours.
   - Persists across restarts.
3. **TG3 Objects pipeline**
   - Detector and tracker adapted from the robot.
   - CLIP encoder on GPU.
   - Per-track recognition: re-query every ~2 s, and a short vote over recent frames so the label does not flicker.
4. **TG4 Server + phone PWA** (**milestone A: objects on the phone**)
   - FastAPI over HTTPS on the LAN.
   - `/ws` frame ingest with a single active source.
   - Overlay on the phone.
   - TEACH: tap a box and type a label.
   - Memory tab: list, rename, forget a label, forget one view.
   - Photo mode: capture one still and get a result.
   - EN/EL UI.
5. **TG5 Evaluation tool** *(revised 2026-10-16: collection method A, see R34-R35)*
   - Test views are collected **in the app** (🧪 Test set switch in TEACH / Label all), kept in `data/eval/`, never taught.
   - Run from the phone against the live memory; `tools/evaluate.py --encoders` compares encoders on the same data.
   - ~~`tools/evaluate.py` on a local folder of `<label>_<n>.jpg`, split into teach and eval.~~
   - Outputs: confusion matrix, threshold sweep, and the `uncertain` rate.
   - Compares memory k-NN against a logistic-regression baseline on the same embeddings.
   - Writes a Markdown/JSON report to `data/reports/`.
   - Used to calibrate thresholds for the phone camera.
6. **TG6 People task** (**milestone B: people on the phone**)
   - YuNet + SFace pipeline and an Objects/People mode switch.
   - Consent confirmation on the first teach of a new person.
   - Face data stays only in `data/`.
7. **TG8 Optional Claude help** *(added 2026-10-16, R36-R41)* — opt-in on the PC and on the phone; objects only; faces never sent.
   - Name suggestions (Label all), second opinion (uncertain/unknown), evaluation summary for managers, questions about memory metadata.
8. **TG7 Voice teach (EN/EL)**
   - Hold-to-talk on the phone and local Whisper.
   - "this is my hat" / «αυτό είναι το καπέλο μου» becomes the label.
   - English is the default, Greek is selectable.

## Decisions taken (defaults, change in review if needed)

- **Live first, photo second.** Live mode is the main experience. Photo mode reuses the same pipeline on one frame.
- **Typed TEACH first, voice later** (TG7).
- **People in this feature**, as their own task group after objects work.
- **WebSocket over per-frame HTTP.** The robot's HTTP/1.0 server would open a new TLS connection for every frame.
- **One shard per task.** It avoids mixing 512-d CLIP and 128-d SFace spaces and keeps people data separable, so it can be wiped as a whole.
- **No "ask" (text recall) in this feature.** It belongs to a later phase.

## Out of scope

Aircraft, video files and clip tooling (Phase 2+), cloud sync, on-device inference on the phone, multi-user/auth, notifications.

## Risks

| Risk | Mitigation |
|---|---|
| Thresholds calibrated on the robot's webcam do not fit the phone camera | TG5 calibrates on phone photos before trusting live results |
| Portrait phone frames, different aspect ratio | Normalised boxes; YOLO letterboxes any aspect |
| Chrome needs HTTPS for the camera, and the certificate warning confuses users | Self-signed certificate plus the `/cert.crt` install path (from the robot docs) |
| Windows Firewall blocks the LAN port | The author allows Python on **private** networks once |
| Wi-Fi latency | ~6 fps uplink at 960 px max side; the overlay is drawn locally |

## Changes from phone testing (2026-10-15)

Recorded here so the spec matches the build (no drift):

| Feedback | Change |
|---|---|
| Too many boxes, no visible selection | All boxes shown; tap selects, tapping the same spot again cycles through overlapping boxes; the target gets corners. Boxes touching two frame edges are "background" (thin, never the default target) |
| Save failed: "object no longer in view" | TEACH creates a server-side **hold** of the crop; live frames pause while naming; TEACH also works on photos |
| Re-typing names for new views | The name sheet lists existing labels (thumbnail + count), the most likely one starred and pre-selected |
| Header and hint overflowed on a narrow phone | Compact icon header, wrapping hint, landing page with how-to, privacy note and language switch |
| "How do I teach from video?" | **Teach from video (burst):** for 5 s, distinct views of the chosen track are collected (a view is kept only when cosine < 0.95 to all kept views, max 10), then named at once |
| Phone connection | Tailscale Serve on :8443 (trusted certificate, works away from home); server bound to 127.0.0.1 |
| A bag taught from afar was not recognized up close | Close-ups kept (max area 0.90); teach-time augmentation: hidden zoom/mirror/darker variants per view (faces: mirror/darker only) |
| A gum on grass was not detected | Min area 0.0003; photos detected at 1280 px; on a photo, tap or drag anywhere to mark your own box |
| "Pause, fix the box, and keep following it" | ⏸ Photo pauses; drag a box's corners to fix it; ▶ Live starts **VitTrack** (OpenCV Zoo, Apache-2.0) from that exact box; a detector box on the same object (IoU ≥ 0.5) is hidden; the track ends after 8 unsure frames |
| Selfie camera, "is it working?" | ⟲ switches front/back camera (front is mirrored like a selfie camera); 3-2-1 countdown before a photo or a video teach |

## Changes on 2026-10-16

| Request / finding | Change |
|---|---|
| Server stopped overnight in People mode (`float32 is not JSON serializable`) | Face boxes and all track boxes are converted to plain floats before they are sent |
| Evaluation data: collect in the app (method A) or name files (method B)? | **A**: a sticky 🧪 Test set switch; views go to `data/eval/`, never to memory; Memory → Test set tab with Run evaluation |
| "Where could the Anthropic API help?" — implement the proposals | TG8: four opt-in actions (names, second opinion, summary, questions); faces are filtered out with YuNet before any picture is sent |
| Landing page appeared unstyled with dead buttons on the phone (4G, Tailscale off on the phone, so the PC was unreachable): the service worker served the cached page but had no CSS/JS for the new `?v=` version | Offline, cached assets match any version (`ignoreSearch`) and are pre-cached; the landing page shows "The PC is not answering" with what to check (Tailscale on the phone, PC awake), disables Start and re-checks every 4 s |
| Server should come up with the PC | Local helper `teye-autostart.ps1` (outside the repo) starts it hidden at sign-in, logs to `logs/`, restarts it after a crash |
| The evidence card for an unknown object listed "nearest" examples at 0.13: noise | For `unknown` the card (and its neighbours) is hidden; it appears only to offer Claude's opinion when enabled |
| Save after a Video teach looked dead (people: 6 views took ~10 s, button greyed) | Each point was flushed to the hard disk on its own (~2 s each); a teach now writes all views and variants in one batch with one flush (18 points: 35 s → 0.5 s). The button reads "Saving…" meanwhile; the people sheet no longer mentions a zoom variant |
| "I don't want the nearest-examples card at all: it hides the picture" | The live view has no evidence card; the box caption says known / maybe / unknown. The card appears only to offer or show Claude's opinion. Evidence stays in Memory |
| TG7 voice teach | 🎤 Say (hold) on the live view and 🎤 beside the name field; Whisper large-v3-turbo fp16 on the GPU (~0.15-0.3 s per sentence after loading in the background at start-up); speak in the app's language |
