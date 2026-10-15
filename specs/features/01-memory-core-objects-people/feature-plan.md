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
5. **TG5 Evaluation tool**
   - `tools/evaluate.py` on a local folder of `<label>_<n>.jpg`, split into teach and eval.
   - Outputs: confusion matrix, threshold sweep, and the `uncertain` rate.
   - Compares memory k-NN against a logistic-regression baseline on the same embeddings.
   - Writes a Markdown/JSON report to `data/reports/`.
   - Used to calibrate thresholds for the phone camera.
6. **TG6 People task** (**milestone B: people on the phone**)
   - YuNet + SFace pipeline and an Objects/People mode switch.
   - Consent confirmation on the first teach of a new person.
   - Face data stays only in `data/`.
7. **TG7 Voice teach (EN/EL)**
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
