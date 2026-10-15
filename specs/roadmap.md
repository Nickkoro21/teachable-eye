# Roadmap

> Status: **v1.1** (2026-10-15: Phase 1 progress, status log, next steps, backlog). Each phase is delivered with the SDD feature loop: `specs/features/NN-name/{feature-plan,requirements,validation}.md` → implement on a feature branch → validate (human-in-the-loop) → replan.
> Phases 0–6 lead to **Demo v1** (approval). Phases 7+ follow once the project is approved and better equipment is available.

## Phase 0: Constitution & repo
- [x] Review and approve `mission.md`, `tech-stack.md`, `roadmap.md`
- [x] Choose the project name (teachable-eye)
- [x] Repo skeleton: `src/`, `tests/`, `tools/`, `data/` (ignored), `AGENTS.md`/`CLAUDE.md`, media-blocking `.gitignore` + pre-commit check, Apache-2.0 `LICENSE`
- [x] Translate the `research/` notes to English
- [x] Create the public GitHub repo

## Phase 1: Memory core + test 1 (objects, people) on PC and phone
Feature `01-memory-core-objects-people`, branch `feature/01-memory-core-objects-people` (not merged yet).
- [x] Teach, recognize, forget and list over Qdrant Edge (one shard per task, UUIDs, payload schema)
- [x] GPU encoders (CLIP baseline); YuNet + SFace for faces (local only, with consent)
- [x] Decision policy: threshold, `uncertain` margin, explanation (nearest examples)
- [x] Phone camera in Chrome (PWA, HTTPS) sends frames to the PC; EN/EL UI (reached via Tailscale Serve)
- [x] Added from phone testing (R22–R31): TEACH holds the crop; label chooser; teach from video (burst);
      landing page; close-ups; teach-time augmentation with visible variants; user-drawn boxes on photos;
      pause → fix box → follow it (VitTrack); front/back camera; 3-2-1 countdown; diagnostics line;
      cache-busting so phones never mix old/new files; forgetting also deletes thumbnail files
- [ ] **TG5 Evaluation tool**: held-out split, confusion matrix, threshold sweep, k-NN vs logistic-regression
      baseline, with/without augmentation — needed to calibrate thresholds for the author's phone
- [ ] **TG7 Voice teach** (Whisper `en`/`el`, "this is my hat" / «αυτό είναι το καπέλο μου»)
- [ ] Validation sign-off (validation.md Levels 1–3), SDD deep review with sub-agents, merge to `main`

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

## Status log

**2026-10-15** — Phase 0 done (public repo, constitution v1.0). Phase 1 milestones A (objects on the
phone) and B (people) reached on the feature branch; 40 tests passing. Measured on RTX 4060 Ti:
objects ~55 ms per 960 px frame (median), people ~8.5 ms per frame (CPU), VitTrack ~4 ms per frame.
Phone testing drove most changes since the spec (see the feature-plan "Changes from phone testing" table).

Observations from phone tests to carry forward:
- Thresholds (objects 0.90/0.05, people 0.40/0.06) are not yet calibrated for the phone: a vape pen
  scored 0.86 against a cup (correctly `uncertain`, but close) → TG5 first.
- Views taught before augmentation was enabled have no variants; re-teach with Video, or add an
  optional "create variants for old views" action (thumbnails are only 160 px, so lower quality).
- Labels differing only by accent (`ποτήρι` / `ποτηρι`) existed; merge by renaming one onto the other.

## Next steps (in order)
1. ~~**Multi-label a photo**~~ — done 2026-10-15 (R32): on a paused photo, "Label all" lists every box
   (detected and user-drawn) with a thumbnail and a label field each (existing-label chooser,
   pre-filled when memory already knows it, empty = skip); tapping a row highlights its box; one
   Save teaches all (each with its variants). Built on the existing per-box hold.
2. TG5 evaluation tool + calibrate thresholds on the author's phone photos (`<label>_<n>.jpg` in `data/`).
3. TG7 voice teach (EN/EL).
4. Validation sign-off, SDD deep review (sub-agents), merge feature 01 into `main`, changelog.
5. Replan: licence review of the detector (see tech-stack), then Phase 2 (video file import + aircraft
   detection/tracking spike on the first phone clips).

## Backlog / ideas (research before scheduling)
- **FOD (foreign object debris) detection** on runway/apron surfaces as a second demo: learn what the
  clean surface looks like, flag patches that differ (anomaly detection, Phase 7 technique). Came from
  a phone test where a chewing gum on grass was not a detector "object".
- **Video file import** (upload a whole phone video; offline tracking collects views across the file;
  automatic approach segmentation) — bridge to Phase 2.
- **AGPL-free detector**: Ultralytics (YOLOE, BoT-SORT) is AGPL-3.0; compare RF-DETR / RT-DETR /
  OWLv2 / Grounding DINO (Apache-2.0) before any non-open-source use.
- **OCR** (PaddleOCR / EasyOCR, Apache-2.0, Greek supported): aircraft registration on the fuselage
  as a payload field and filter; read text as searchable memory (course L4 pattern).
- **Motion cues**: background subtraction (MOG2/KNN) for small aircraft against a static sky; optical
  flow for speed/direction; camera-motion compensation; SSIM gate to skip identical frames.
- **Tracking upgrades for aircraft**: ByteTrack / OC-SORT + Kalman smoothing → trajectory vectors;
  SAM 2 for precise masks.
- Encoder comparison: SigLIP / DINOv2 vs CLIP ViT-B/32 (measured with the TG5 tool).

## Open questions
- Will the phone or camera always stand at the **same position**? (affects trajectory calibration)
- Android phone model (for the on-device phase)
- Permission to film at the airfield (to be obtained by the author)
