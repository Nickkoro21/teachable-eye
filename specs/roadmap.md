# Roadmap

> Status: **v1.0**. Each phase is delivered with the SDD feature loop: `specs/features/NN-name/{feature-plan,requirements,validation}.md` → implement on a feature branch → validate (human-in-the-loop) → replan.
> Phases 0–6 lead to **Demo v1** (approval). Phases 7+ follow once the project is approved and better equipment is available.

## Phase 0: Constitution & repo
- [x] Review and approve `mission.md`, `tech-stack.md`, `roadmap.md`
- [x] Choose the project name (teachable-eye)
- [x] Repo skeleton: `src/`, `tests/`, `tools/`, `data/` (ignored), `AGENTS.md`/`CLAUDE.md`, media-blocking `.gitignore` + pre-commit check, Apache-2.0 `LICENSE`
- [x] Translate the `research/` notes to English
- [x] Create the public GitHub repo

## Phase 1: Memory core + test 1 (objects, people) on PC and phone
- Teach, recognize, forget and list over Qdrant Edge (one shard per task, UUIDs, payload schema)
- GPU encoders (CLIP baseline); YuNet + SFace for faces (local only, with consent)
- Decision policy: threshold, `uncertain` margin, explanation (nearest examples)
- Phone camera in Chrome (PWA, HTTPS) sends frames to the PC on the local Wi-Fi; EN/EL UI
- Evaluation tool: held-out split, confusion matrix, threshold sweep, k-NN vs trained-classifier baseline

## Phase 2: Video import + aircraft detection & tracking
- Import phone videos (4K/30 fps, tripod, fixed position)
- Aircraft detection (pretrained `airplane` / YOLOE text prompt) + motion cue (static sky) + tracking
- Automatic approach segmentation (aircraft appears → disappears)
- Metrics: % of frames detected, first-detection point in the final approach, track losses
- Early spike: as soon as 3–5 phone clips exist, run a baseline detector to check that the distance and resolution are enough

## Phase 3: Observer labels
- Per-approach labels: configuration and glide path, as called by the observer
- Optional: Whisper transcription of the radio call from the clip audio to suggest labels
- Offline GPX label-verification tool (not part of the app)

## Phase 4: Configuration check
- Landing-light detector (brightness/saturation inside the tracked box, temporal persistence)
- Gear k-NN on aircraft crops
- Conservative rule: `secured` only if gear down and light on; otherwise `possibly-unsecured` or `uncertain`

## Phase 5: Glide-path check
- Trajectory (position and size over time) → fixed-length vector → k-NN against labelled approaches → `on` / `low` / `high` / `uncertain`

## Phase 6: Demo v1
- Report: agreement with the observer, `unsecured → secured` = 0, `uncertain` rate, k-NN vs classifier
- Annotated output videos (box, light/gear, trajectory vs reference, nearest examples)

## Phase 7+: After approval
- Neutral task packs (config-driven labels, encoders, ROI, decision rules)
- Anomaly detection + notifications (event interface: ntfy / Telegram / Android push)
- Real-time ground-camera assistance (dedicated camera, possibly wide + tele)
- On-device Android (WebGPU PWA vs native, decided by benchmark)
- Private data store, roles (who sees the app and the training data), Qdrant Cloud sync

## Open questions
- Will the phone or camera always stand at the **same position**? (affects trajectory calibration)
- Android phone model (for the on-device phase)
- Permission to film at the airfield (to be obtained by the author)
