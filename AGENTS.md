# Instructions for coding agents

Read before doing anything in this repository.

## Source of truth
- `specs/mission.md`, `specs/tech-stack.md`, `specs/roadmap.md` form the **constitution**. Follow them; when a change is needed, update the specs in the same change (no spec drift).
- Work one roadmap phase at a time. Each feature lives in `specs/features/NN-name/` with `feature-plan.md`, `requirements.md`, `validation.md`, on its own branch `feature/NN-name`.
- `research/` holds background notes; it is not normative.

## Hard rules
1. **Never commit media or derived personal data**: images, video, audio, face crops, embeddings, GPX/KML, datasets, model weights, shards. They live under `data/` (git-ignored) or outside the repo. The pre-commit hook (`tools/check_no_media.py`) must stay enabled and passing.
2. **Never commit secrets.** Credentials come only from environment variables (`QDRANT_URL`, `QDRANT_API_KEY`, `HF_TOKEN`, `ANTHROPIC_API_KEY`).
3. **Real people's names** do not appear in the repo; use `person-a`, `person-b` in docs and tests.
4. **Qdrant Cloud:** use project-prefixed collection names (`teye_*`); never delete or overwrite a collection this project did not create.
5. **Safety asymmetry:** for the approach check, never trade a `unsecured → secured` error for accuracy elsewhere. When in doubt, output `uncertain`.
6. Code from `qdrant-labs/memory-fleet` and `qdrant/qdrant-edge-demo` (no licence) must **not** be copied; re-implement patterns. Code from `https-deeplearning-ai/sc-on-device-ai-memory` (Apache-2.0) may be reused with an attribution comment.
7. **Cloud help (Anthropic API) is optional and objects-only**: never send faces, people's names or approach decisions; every picture passes the face check in `assist.py` first.

## Conventions
- English for code, comments, specs, commit messages and UI strings (Greek is a second UI language).
- Python 3.13, `uv`, `pytest`. Tests use synthetic data or licence-compatible public samples only.
- Claims in docs (accuracy, latency, thresholds) must come from a recorded measurement.

## Local environment (author's machine)
- Load `D:\AI assistant on Device Memory\env.ps1` before running anything: it keeps all caches on D: and puts the project's `uv` first on PATH.
