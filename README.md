# teachable-eye

**A teachable visual memory that runs on the device.** Show it a few examples, give each one a label, and it recognizes new views by similarity — no retraining. When the evidence is weak it says **"uncertain"** instead of guessing.

Built on [Qdrant Edge](https://qdrant.tech/documentation/edge/) as an application and extension of the DeepLearning.AI × Qdrant course *Building AI Assistants with On-Device Memory*.

> **Status (2026-10-18):** Phase 1 (feature 01: objects and people from the phone) is built and reviewed on its branch; it waits for the author's test-set measurements and phone checks before merging. Next: feature 02 (parts and their state), then Phase 2 (aircraft video).

## Goal

Three tests of increasing difficulty, all on the same memory core:

1. **Objects** — teach "hat", "microphone" from a phone camera and recognize them again.
2. **People** — recognize consenting people with a face-specific encoder (face data never leaves the device).
3. **Training-aircraft approach check** — from a ground camera at the runway end, assist the human observer with two calls on short final:
   - **Configuration:** `secured` (gear down *and* landing light on) / `possibly-unsecured` / `uncertain`
   - **Glide path:** `on` / `low` / `high` / `uncertain`

The system **assists** an observer; it never replaces one. The dangerous error (`unsecured → secured`) is driven toward zero by design.

## What works today (phone + PC)

| | |
|---|---|
| **Recognition** | Live boxes (YOLOE + tracking) with *known* / *maybe X?* / *unknown*; tap the label of the active box to see the runner-up labels and how close they are |
| **Teaching** | TEACH (typed or spoken: hold 🎤 and say "this is my hat" / «αυτό είναι το καπέλο μου»), **Video** (record until Stop; the 15 most different views are kept), **Label all** on a paused photo |
| **Boxes** | One active box at a time; move it, resize it by its corners, ✕ to drop it; pinch to zoom a paused photo; draw your own box (on a face it snaps to the face) |
| **Memory** | Per label and per view, with the stored variants (augmentation: zoom, mirror, light, turns, pieces, hidden parts, blur); rename, forget a view or a label |
| **Pictures & video files** | Label pictures or frames of a video from the phone or the PC (drag and drop) without the camera |
| **Evaluation** | A 🧪 test set that is never taught; Run evaluation → correct / *dangerous* / uncertain, recommended thresholds, augmentation profiles compared, views needed, k-NN vs logistic regression |
| **People** | Separate face memory (YuNet + SFace), consent required, "Forget everyone" removes faces, test views and reports |
| **Optional Claude help** | Off unless enabled: name suggestions, a second opinion, a summary for managers, questions about memory — objects only, pictures with a face are never sent |

## Principles

- **On-device first** — works offline; cloud help and sync are optional.
- **No training media in any repository** — images, video, audio, face data, embeddings and flight tracks never go into git. A pre-commit hook enforces it.
- **Measured, not assumed** — every task has a held-out evaluation and a documented threshold; models are chosen by measurement.
- **Explainable** — every decision can show what else it could have been.
- **English first, Greek second.**

## Specs (Spec-Driven Development)

| File | Purpose |
|---|---|
| [`specs/mission.md`](specs/mission.md) | Why, users, principles, how the course maps to this project |
| [`specs/tech-stack.md`](specs/tech-stack.md) | Technologies, models, data model, hardware, licences; "As built" |
| [`specs/roadmap.md`](specs/roadmap.md) | Phases, status log, next steps, backlog |
| [`specs/features/01-memory-core-objects-people/`](specs/features/01-memory-core-objects-people/) | Feature 01: plan, requirements (R1-R53, N1-N11), validation |
| [`research/`](research/) | Notes on Qdrant Edge, the course, reference projects, face liveness |

Each feature is delivered as `specs/features/NN-name/{feature-plan,requirements,validation}.md` → implementation on a feature branch → validation.

## Run it (PC + Android phone)

Requirements: Windows/Linux PC with an NVIDIA GPU (CPU works, slower), [uv](https://docs.astral.sh/uv/), an Android phone with Chrome. Models are downloaded on first use into `data/models/` and checked by SHA-256.

**Recommended: Tailscale** (works away from home, trusted certificate, nothing exposed on the Wi-Fi). With Tailscale on the PC and the phone:

```powershell
uv sync
copy .env.example .env      # then set TEYE_PUBLIC_HOST=<pc-name>.<tailnet>.ts.net
uv run teachable-eye --host 127.0.0.1 --no-https
tailscale serve --bg --https=8443 http://127.0.0.1:8765   # once; persists. Undo: tailscale serve --https=8443 off
```

Then open `https://<pc-name>.<tailnet>.ts.net:8443` on the phone. The server answers only to its own names (`127.0.0.1`, `localhost` and `TEYE_PUBLIC_HOST`), which protects it from other web pages open on the PC.

**Same Wi-Fi instead:** `uv run teachable-eye --host 0.0.0.0` (add `--advertise <PC-LAN-IP>` if the printed IP is wrong), open the printed `https://<pc-ip>:8765` and accept the certificate warning (or install `/cert.crt` once). The Windows firewall must allow Python on that network.

On the phone: allow the camera, point at an object, tap its box, press **TEACH** and give it a name; show it again from another angle — the label appears. Everything the app learns stays in `data/` on the PC (git-ignored). Settings and their defaults are in [`.env.example`](.env.example).

## Development

```powershell
git config core.hooksPath .githooks   # enable the no-media pre-commit check
uv run pytest                         # fast tests (no models, no network)
uv run python tools/evaluate.py --encoders dinov2-large,clip-b32   # compare encoders on your test set
```

The no-media check can also be run by hand: `python tools/check_no_media.py --all`.

## Licences

Project: [Apache-2.0](LICENSE). Note: the detector (Ultralytics YOLOE, BoT-SORT) is **AGPL-3.0** — fine for this open-source project; switch to an Apache-2.0 detector before any closed use (see `specs/tech-stack.md`).

## Acknowledgements

- [DeepLearning.AI — Building AI Assistants with On-Device Memory](https://learn.deeplearning.ai/courses/building-ai-assistants-with-on-device-memory) (Qdrant, Dylan Couzon)
- [https-deeplearning-ai/sc-on-device-ai-memory](https://github.com/https-deeplearning-ai/sc-on-device-ai-memory) — Qdrant Edge Memory Robot (Apache-2.0); code reused from it is marked at the point of use.
