# Mission

> Status: **v1.1** — constitution approved 2026-10-15; working notes added the same day (end of file). Project name: **teachable-eye**.

## Problem

Visual checks that people repeat all day are slow to automate. Classic computer vision needs a large labelled dataset and a retraining cycle for every new object, person or condition. Cloud services need connectivity and send images off the device.

## What we are building

A **teachable visual memory that runs on the device**. You show it a few examples and give each one a label. It stores each example as a vector in a local [Qdrant Edge](https://qdrant.tech/documentation/edge/) shard and recognizes new views by similarity. It improves as you add examples, with **no retraining**.

It never has to guess. When the evidence is weak it answers **"uncertain — check visually"**.

The same core is validated on three tests of increasing difficulty:

| # | Test | Labels (examples) | Purpose |
|---|---|---|---|
| 1 | **Objects** | `hat`, `microphone`, … (open set) | Prove the teach → recognize loop (mirrors the DeepLearning.AI course) |
| 2 | **People** | `person-a`, `person-b`, … (real names stay local) | Identity with a face-specific encoder; consent and right to forget |
| 3 | **Training-aircraft approach check** | **System:** `secured` / `possibly-unsecured` / `uncertain` · **Glide path:** `on` / `low` / `high` / `uncertain` | The real goal: assist a ground observer watching final approaches |

### Test 3 in detail
- **Camera:** on the ground, watching training aircraft on final approach (one, at most two, aircraft types).
- **System secured** means the landing gear is down and locked. The landing light(s) come on with it.
  - `secured` **only if** gear is down **and** the landing light is on.
  - Gear down with the light off is a rare case, classified as `possibly-unsecured` (conservative by design).
  - Either cue not visible or not decidable gives `uncertain`.
- **Glide path:** the trajectory of the aircraft in the frame is compared with labelled past approaches.
  - Labels come from the observer's experience.
  - GPX flight tracks are used **only offline**, to verify sample labels. The application never reads them.
- **Phase order:**
  1. Post-landing review (upload a clip, get labels with the reasons).
  2. Real-time assistance and notifications during the approach.
- **Later:** anomaly detection. "Unlike any known normal approach" raises a notification, even with few examples of the abnormal case.

## First goal: a simple, convincing demo

The first deliverable is a working **demo for decision makers who are not computer-vision specialists**, to win approval for a funded project and better equipment.

- **Current practice:** a colleague sits at the runway end with a radio and calls configuration and glide path by eye. The system reproduces those two calls.
- **Data source:** all early images and video are recorded with the author's **Android phone** on a tripod and copied to the PC for analysis. No live streaming is needed for the first demo.
- **Headline result:** agreement with the human observer over N recorded approaches, **zero** `unsecured → secured`, and the `uncertain` rate. Each result is shown visually: aircraft box, light/gear state, trajectory against a reference, and nearest examples as the "why".
- **Pipeline order:** detect and track the aircraft first, then configuration and glide path. Both depend on the track.

## How the course maps to this project

This project applies and extends the DeepLearning.AI course *Building AI Assistants with On-Device Memory* (Qdrant).

| Course concept | Where it lives here |
|---|---|
| L3: store / find / forget, payload filters | One point per example or approach, with payload (aircraft type, date, observer label, light conditions). Filter by type. Forget bad samples |
| L4: multimodal recall, local Whisper | Search past approaches by text. Idea: transcribe the observer's radio call from the clip audio to suggest labels |
| L5: teach from few examples, threshold calibration, recency | **Core of the decision:** k-NN over gear crops and over trajectory vectors; a calibrated threshold gives `uncertain` |
| L5 inverted: distance to the nearest known example | Anomaly detection ("unlike any normal approach") |
| Appendix: Edge + Cloud hybrid | Phone ↔ PC ↔ cloud sync; later, several observers or runways share one memory |
| On-device, offline | Works at the runway without a network; media never leaves the device |

Detection and tracking (YOLO, motion, tracker) are the "eyes" and are **not** Qdrant. Qdrant Edge is the **memory and judgement**. The landing-light check is a simple brightness rule whose result is stored in memory.

**Why a memory and not only a trained classifier:** it works with few examples, learns in the field without retraining, explains itself through its nearest examples, and gives `uncertain` naturally. To keep this honest, evaluation always compares memory k-NN with a simple trained classifier on the **same** embeddings.

## Principles (non-negotiable)

1. **Assist, never replace.** Outputs support a human observer. They are not a certification or a control action.
2. **Asymmetric safety.** The dangerous error is `unsecured → secured`. Thresholds are calibrated to drive it toward zero. False alarms and `uncertain` are acceptable.
3. **On-device first.** Everything works offline. Cloud sync is optional and the local memory is always the source of truth.
4. **No training media in any repository.** No image, video, audio, face crop or embedding derived from people **ever** goes into git (public or private). Datasets live only on local disk, or later in an access-controlled private store. This is enforced by `.gitignore` and checks.
5. **Privacy and consent for people.** Face data is used only with the person's consent. It stays local and is deleted on request (`forget`).
6. **Measured, not assumed.** Every recognition task has a held-out evaluation set, a confusion matrix and a documented threshold. Claims in docs come from measurements.
7. **Explainable.** Every decision shows its nearest examples and scores ("why").
8. **English first, Greek second.** The code, specs and UI are in English. The UI and voice input also support Greek.

## Users

- **Now:** one user (the author). No login, local network only.
- **Later:** an instructor or observer team. Roles control who can view the application and who can view the training data.

## Platforms (in order)

1. **PC with an NVIDIA GPU**, using a webcam or uploaded media. This is the development and reference platform.
2. **Android phone as a camera** for the PC: a PWA in Chrome over the local Wi-Fi.
3. **Android on-device:** a PWA with WebGPU, or native if needed. Decided by measurement.
4. **Ground camera + PC (or Jetson-class box)** at the runway for test 3.

## Scope

**In scope:** teach/recognize/forget, evaluation tooling, clip collection and labelling, post-hoc and real-time approach checks, notifications, optional sync to Qdrant Cloud.

**Out of scope (for now):**
- Many aircraft types (at most two).
- Any flight-control or ATC integration.
- Using GPX data at runtime.
- Multi-user accounts before the roles phase.
- Commercial-only model licences.

## Success criteria

- **Test 1:** taught objects are recognized from new views at the calibrated threshold, and untaught objects return `unknown`/`uncertain`.
- **Test 2:** taught people are recognized, and an unknown face never maps to a taught name above the threshold.
- **Test 3:** on a held-out set of labelled approaches:
  - `unsecured → secured` errors = **0**
  - glide-path accuracy and the `uncertain` rate are reported per class
  - labels are cross-checked against GPX

## Working notes (2026-10-15, after the first phone tests)

What the phone tests taught us about the mission itself (details: `roadmap.md` status log,
`specs/features/01-memory-core-objects-people/feature-plan.md`):

- **The human stays in control of *what* is taught.** Users choose any box, cycle through
  overlapping ones, pause and fix a box by its corners, or draw their own; live view then follows
  exactly that box. The detector proposes, the user decides — the same assist-not-replace stance as
  the approach check.
- **Explainable includes the memory itself.** Augmented variants are stored to generalise (closer,
  mirrored, darker), but they are shown under their view and can be deleted; the evidence card says
  when the nearest match was a variant. Nothing the system "remembers" is hidden from the user.
- **Forgetting is complete.** Forgetting a label, a view or everyone removes vectors *and* the
  thumbnail files (principle 5).
- **Calibrate before trusting.** Thresholds came from another camera; on the phone some unrelated
  objects score close to the bar (correctly `uncertain`). Measured calibration (evaluation tool) comes
  before more features and before any aircraft claim (principle 6).
- **Some targets are not "objects".** Small debris on a surface was not detected as an object; that
  points to anomaly detection on a learned "clean surface" — a candidate second demo for aviation
  (FOD on runway/apron), kept in the roadmap backlog, not in scope yet.
