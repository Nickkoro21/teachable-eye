# Feature 01: Validation scorecard

Every item is scored **pass/fail**. The feature is done when all automated checks pass and the manual checks are signed off by the author.

## Level 1: Automated (`uv run pytest`)

| # | Check | Covers |
|---|---|---|
| A1 | Teach 2 labels with synthetic vectors, then recognize near vectors as `known` with the right label | R2, R3 |
| A2 | A vector between the bands gives `uncertain` with a guess; a far vector gives `unknown`; an empty memory gives `unknown` | R3 |
| A3 | Forget a label removes all its points; forget one view removes exactly one; rename merges correctly | R4 |
| A4 | Close and reopen the shard: the examples are still there | R5 |
| A5 | Per-track vote: alternating recognitions do not flip the displayed label until there is a majority | R8 |
| A6 | Label parsing: EN and EL phrases map to the expected labels; empty or silent input is rejected | R21 |
| A6b | Voice: WAV of any rate/channels becomes 16 kHz mono; short, long, silent and non-WAV input rejected before the model; `/api/voice` returns the label in the requested language, 422 on silence, 503 when off | R21 |
| A7 | Server smoke test: an HTTPS app starts; a synthetic JPEG over `/ws` returns valid JSON with normalised boxes in [0, 1] | R9, R10 |
| A8 | A second `/ws` connection replaces the first and resets the tracker | R11 |
| A9 | `tools/check_no_media.py --all` passes, and `git ls-files` contains no file under `data/` | N1 |
| A10 | ~~`evaluate.py` on a synthetic dataset~~ superseded by A11-A13 | R16, R17 |
| A11 | A view saved with 🧪 Test set lands in `data/eval/`, memory count unchanged; bad ids rejected; outcomes correct/wrong/rejected/false_accept computed right | R34 |
| A12 | Recommended bands have zero dangerous errors on a synthetic set where the current ones do not; missing strangers are flagged; empty sets do not crash | R35 |
| A13 | Server flow: teach, save a test view, run evaluation (JSON + Markdown written, no vectors in the JSON), report path sanitised, delete a test view | R34, R35, R17 |
| A14 | Claude help is refused when `ASSIST` is off and for the people task | R36 |
| A15 | Name suggestions: a face crop is not sent (and no call at all if nothing is sendable); the request uses structured output and the refusal fallback; usage is logged | R36, R37, R41 |
| A17 | A box drawn on a photo in People mode: no photo → error; no face → "no face found"; a face → snapped box, taught with its variants; faces are not followed | R48 |
| A16 | Second opinion returns only a candidate label (never an invented one), never sends a face; questions and summaries send no pictures and no per-view rows | R38-R40 |

## Level 2: Measured (recorded in the PR description)

| # | Measurement | Target |
|---|---|---|
| M1 | Server time per frame, objects (median and p95 over 200 frames) | median ≤ 150 ms |
| M2 | Server time per frame, people | median ≤ 60 ms |
| M3 | `evaluate.py --task objects` on the author's phone photos (≥ 4 labels × ≥ 5 views) | Known-label accuracy and `uncertain` rate reported. Held-out labels never `known` at the chosen threshold |
| M4 | `evaluate.py --task people` (person-a, person-b + strangers) | **No stranger is ever `known` as a taught person** at the chosen threshold |
| M5 | Memory k-NN vs logistic regression on the same embeddings | Both reported; neither claimed better without the numbers |
| M6 | `tools/evaluate.py --encoders` on the author's test set | Encoder choice confirmed or changed by the numbers |

## Level 3: Manual (author on the phone)

| # | Scenario | Pass when |
|---|---|---|
| H1 | Open `https://<pc-ip>:8765` on the Android phone, accept or install the certificate, allow the camera | Live view appears, boxes follow objects |
| H2 | Teach "hat" from 2 views, then show it from a new angle | "hat" appears in ≤ 1 s, stable (no flicker) |
| H3 | Teach "microphone"; show both objects together | Both are labelled correctly at the same time |
| H4 | Show an object that was never taught | `unknown` (or `uncertain`), never "hat" or "microphone" |
| H5 | Memory tab: rename "hat" to "cap", delete one view, forget "microphone" | The live view reflects each change immediately |
| H6 | Restart the server | Taught objects are still recognized |
| H7 | People mode: teach person-a and person-b (with the consent prompt); a third person appears | person-a and person-b are recognized; the third shows `unknown` |
| H8 | Switch the UI to Greek; teach by voice «αυτό είναι το μικρόφωνο» | The label "μικρόφωνο" is stored and recognized |
| H9 | Lock the phone for 1 minute, then unlock | Server still running; the live view resumes |
| H10 | Photo mode on a scene with 2 taught objects | Both listed with decision and top-3 neighbours |
| H11 | 🧪 Test set on: save views of taught objects and of never-taught ones; Memory → Test set → Run evaluation | Views listed per label, not in memory; result table and full report open |
| H12 | Claude help on: Suggest names on a photo with a person in it; Ask Claude on an uncertain object; Summary; Ask about memory | Names pre-filled except the person's box (🔒); every answer shown, nothing saved without Save |
| H13 | Two objects on screen, none tapped: TEACH asks to choose; tap one, drag it, drag a corner, ✕ the other; pinch-zoom a photo and box a small part (e.g. a button) | Only the active box is taught; the moved/resized box is the one taught; the dropped box does not come back; zoomed boxes line up with the picture |
| H14 | PC: 🗂 Memory & evaluation while the phone streams; 🖼 a few phone pictures and a short video: box, teach, Next, Use this frame; People: draw a box round a small or turned face | The phone keeps its camera; pictures and frames can be labelled like photos; the drawn face box snaps to the face (or says none was found) |

## Sign-off
- [ ] Level 1 all pass
- [ ] Level 2 numbers recorded (M3/M4 thresholds written back to `.env.example`)
- [ ] Level 3 all pass (author)
- [ ] Specs updated if anything changed during implementation (no drift)
