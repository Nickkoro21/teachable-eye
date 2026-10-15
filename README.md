# teachable-eye

**A teachable visual memory that runs on the device.** Show it a few examples, give each one a label, and it recognizes new views by similarity — no retraining. When the evidence is weak it says **"uncertain"** instead of guessing.

Built on [Qdrant Edge](https://qdrant.tech/documentation/edge/) as an application and extension of the DeepLearning.AI × Qdrant course *Building AI Assistants with On-Device Memory*.

> **Status:** Phase 0 — constitution and repository setup. No application code yet.

## Goal

Three tests of increasing difficulty, all on the same memory core:

1. **Objects** — teach "hat", "microphone" from a phone camera and recognize them again.
2. **People** — recognize consenting people with a face-specific encoder (face data never leaves the device).
3. **Training-aircraft approach check** — from a ground camera at the runway end, assist the human observer with two calls on short final:
   - **Configuration:** `secured` (gear down *and* landing light on) / `possibly-unsecured` / `uncertain`
   - **Glide path:** `on` / `low` / `high` / `uncertain`

The system **assists** an observer; it never replaces one. The dangerous error (`unsecured → secured`) is driven toward zero by design.

## Principles

- **On-device first** — works offline; cloud sync is optional.
- **No training media in any repository** — images, video, audio, face data, embeddings and flight tracks never go into git. A pre-commit hook enforces it.
- **Measured, not assumed** — every task has a held-out evaluation and a documented threshold.
- **Explainable** — every decision shows its nearest examples.
- **English first, Greek second.**

## Specs (Spec-Driven Development)

| File | Purpose |
|---|---|
| [`specs/mission.md`](specs/mission.md) | Why, users, principles, how the course maps to this project |
| [`specs/tech-stack.md`](specs/tech-stack.md) | Technologies, models, data model, hardware, licences |
| [`specs/roadmap.md`](specs/roadmap.md) | Phases and open questions |
| [`research/`](research/) | Notes on Qdrant Edge, the course, and reference projects |

Each feature is delivered as `specs/features/NN-name/{feature-plan,requirements,validation}.md` → implementation on a feature branch → validation.

## Development setup

```powershell
git config core.hooksPath .githooks   # enable the no-media pre-commit check
```

The check can also be run by hand: `python tools/check_no_media.py --all`.

## Acknowledgements

- [DeepLearning.AI — Building AI Assistants with On-Device Memory](https://learn.deeplearning.ai/courses/building-ai-assistants-with-on-device-memory) (Qdrant, Dylan Couzon)
- [https-deeplearning-ai/sc-on-device-ai-memory](https://github.com/https-deeplearning-ai/sc-on-device-ai-memory) — Qdrant Edge Memory Robot (Apache-2.0); code reused from it is marked at the point of use.

## Licence

[Apache-2.0](LICENSE)
