# 06 — Face pipeline review (people task)

> Background note, not normative (2026-10-19). A frank review of the people/face pipeline as it is
> after R57 ("faces from further away"), written by the sub-agent that implemented R57. Every claim is
> tagged: **[M]** measured on this PC during R57 (numbers in `specs/tech-stack.md`, "Faces from further
> away"), **[E]** an estimate or a judgement, **[C]** cited from a linked source. Names of people never
> appear; the author's local crops were read only to compute numbers.

## 1. The pipeline as built

```
phone camera 1920×1080 stream (getUserMedia)                        [the sensor is 4K+; the browser stream is 1080p]
  → canvas downscale to 960 px long side (bilinear), JPEG q 0.7     app.js MAX_SIDE (now ?side=1280 optional)
  → WebSocket → decode (OpenCV)                                      server.py /ws
  → YuNet 2023mar on the frame as received (≤ 1280 px)              faces.py DETECT_SIDE   (before R57: scaled again to 640)
  → size floor: score ≥ 0.80 if box ≥ 56 px, else ≥ 0.60; box ≥ 16 px
  → greedy IoU tracker (IOU_MATCH 0.3), STABLE_FRAMES 3, DEAD_SECONDS 5
  → identity band: far < 40 px (no crop) · weak < 56 px · ok
  → alignCrop (5 landmarks → 112×112, warpAffine)                   SFace's own aligner
  → SFace 2021dec → 128-d, L2-normalised
  → every 2 s: k-NN in Qdrant Edge (views + hidden variants), policy 0.40 / 0.06, vote over 3
  → row {box, far, decision, label/guess, score, candidates}         weak: known → uncertain
teach: the best crop so far (score × √area) → 112 px aligned crop + 7 variants (strong profile)
photo: 1920 px → detected at 1280 px, same bands; user box → find_face at 640 px (floor 0.5), same bands
privacy: has_face (floor 0.5, no size floor, ≤ 1280 px) before any object crop goes to Claude
```

## 2. Pixel budget end to end — the thing that actually limits range

| stage | a face at 2 m | at 4 m | at 6 m | note |
|---|---|---|---|---|
| sensor (12-50 MP) | plenty | plenty | plenty | never reaches us |
| 1080p stream | ~112 px | ~56 px | ~37 px | [E] ~29 px/° on the main camera; a 14 cm face ≈ 8°·m / d |
| 960 px frame on the PC | **~56 px** | **~28 px** | **~19 px** | [E] 14 px/°; this is all the detector and the recogniser ever see |
| YuNet at 960 | found 90 % / 95 % (≥ 0.8 / ≥ 0.6) | 75 % / 95 % | 35 % / 60 % | [M] composites; the 640 path gave 75/90, 45/70, 0/30 |
| aligned 112 px crop | 2× upsampled | 4× upsampled | 6× | [E] from the crop/box ratio ≈ 1.4 [M] |
| SFace self-match (p10) | ≈ 0.96 | ≈ 0.85 | ≈ 0.64 | [M] the 112 crop shrunk to the crop size and blown back |

Reading: R57 moved the detector from "sees 2/3 fewer pixels than it could" to "sees everything the
phone sends", which is the free win. The remaining loss is on the phone: 1080p → 960 is 2× linear, and
the stream is itself a downscale of the sensor. Nothing on the PC can recover that. JPEG q 0.7 is a
smaller loss, but note its chroma is 4:2:0 [C, JPEG default in browsers]: colour lives at 480×270.

Consequences:
- A **name needs ≥ 40 px** (sure ≥ 56 px) → at 960 px that is ~2.8 m (sure ~2 m) [E]. A "far" box
  continues to ~5-6 m. These are estimates until H16.
- `?side=1280` moves every number by ×1.33 at ~1.8× the YuNet cost (26 → 49 ms [M]) and ~1.8× bytes.
- The **right fix for identity at 3-6 m is on the phone**, not the PC: crop the face region from the
  1080p stream at full resolution and send it next to the 960 px frame (a "far pass" where the pixels
  are). A server-side tiled pass over the received 960 px frame has nothing more to look at, so it was
  deliberately not built.
- Face **super-resolution** (GFPGAN & co.) is the wrong tool here: it invents identity-bearing detail,
  which is exactly the "confident wrong answer" this project must never give [E].

## 3. Models

### 3.1 In use

| model | what | licence | strengths | weaknesses |
|---|---|---|---|---|
| **YuNet 2023mar** (OpenCV Zoo) | anchor-free detector, ~75 k params, 5 landmarks | Apache-2.0 [C: zoo README] | 26 ms at 960 px on CPU [M]; stable; built into OpenCV | WIDER Face *hard* AP ≈ 0.71 vs easy ≈ 0.83 [C: zoo README, numbers at 640 scale; verify before quoting] — small/turned faces are where it is weakest; no quality score; frontal bias in the training set |
| **SFace 2021dec** (OpenCV Zoo) | 112 px → 128-d embedding, MobileFaceNet-class backbone | Apache-2.0 [C] | 7 ms/face [M]; the only clean-licence recogniser we found; the published cosine threshold 0.363 [C: OpenCV docs `FaceRecognizerSF`] | 128-d, 2021-era accuracy; sensitive to alignment and to upsampled crops [M]; no built-in quality/"unknown" notion |

YuNet paper: Wu et al., *YuNet: A Tiny Millisecond-level Face Detector*, Machine Intelligence Research
2023 — <https://link.springer.com/article/10.1007/s11633-023-1423-y>. SFace paper: Zhong et al.,
*SFace: Sigmoid-Constrained Hypersphere Loss for Robust Face Recognition*, IEEE TIP 2021 —
<https://arxiv.org/abs/2205.12010>. Zoo pages: <https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet>,
<https://github.com/opencv/opencv_zoo/tree/main/models/face_recognition_sface>.

### 3.2 Realistic alternatives, with licences (the deciding factor here)

Detectors
- **SCRFD** (InsightFace) — <https://arxiv.org/abs/2105.04714>. Much stronger on WIDER *hard*
  (SCRFD-2.5GF ≈ 0.78, 10GF ≈ 0.83 at 640 [C: paper]). **Licence: InsightFace code is MIT but the
  pretrained weights are "for non-commercial research purposes only"** [C: <https://github.com/deepinsight/insightface> README].
  Excluded by `tech-stack.md` for that reason; still the best technical reference point.
- **RetinaFace** — <https://arxiv.org/abs/1905.00641>. Official weights: InsightFace terms as above.
  Third-party PyTorch re-implementations (e.g. biubug6) are MIT for the *code*; their weights are
  trained on WIDER Face, whose terms are research-oriented [E: check before shipping].
- **MediaPipe Face Detector** (BlazeFace short/full-range) — Apache-2.0 [C: <https://ai.google.dev/edge/mediapipe/solutions/vision/face_detector>].
  The full-range model targets ~5 m; accuracy on small faces is below SCRFD and roughly YuNet-class
  [E]. A possible second opinion, not an upgrade.
- **libfacedetection** (Shiqi Yu, BSD-3) — <https://github.com/ShiqiYu/libfacedetection>: the same
  author's C++ library; the same YuNet family. No gain.
- **YOLO-face variants** on Ultralytics — AGPL-3.0; same problem the objects side already carries.

Recognisers
- **ArcFace / InsightFace** (glint360k, MS1MV3 weights, "buffalo_l" packs, and most ONNX copies on
  Hugging Face) — **non-commercial** [C: InsightFace README]. Excluded.
- **AdaFace** — <https://github.com/mkminchul/AdaFace>: code MIT, but the released weights were
  trained on MS1MV2/WebFace4M, which carry research-only dataset terms [E: check the model card].
- **EdgeFace** (Idiap, 2023) — <https://github.com/otroshi/edgeface>: small, strong for its size;
  the weights are under Idiap's own licence (check whether it is the non-commercial one) [E].
- **FaceNet** (davidsandberg, MIT, VGGFace2-trained) — old, and VGGFace2 terms are research [E].
- **DeepFace** (MIT wrapper) — only wraps the above; licences are inherited.
- **SFace (OpenCV Zoo)** — the one option we found that is Apache-2.0 end to end. That is why it is
  here. Alternatives that keep the licence clean: train nothing, feed SFace better pixels (section 2),
  and build the "unknown" behaviour in the policy (which is what the k-NN + bands do).

Judgement [E]: the model choice is right for an Apache-2.0 repo with the "no non-commercial weights"
rule. The pipeline loses far more to resolution and to association than to SFace's age.

## 4. Every hyperparameter, with a verdict

| where | value | verdict |
|---|---|---|
| `MAX_SIDE` (phone) | 960, `?side=1280` optional | Fine as default; 1280 should become the default only if H16 shows the PC keeps up at ~6 fps with other work (49 ms YuNet + 7 ms/face [M] is within M2) |
| `DETECT_SIDE` | 1280 cap (live 960 as received) | Right. 1920 would cost 150 ms [M] and the phone does not send it |
| `SCORE` / `SCORE_FAR` | 0.80 ≥ 56 px / 0.60 below | [M] on composites: 0.60 lifts a 28 px face from 45 % to 75 % of frames; 0 false boxes on 100 synthetic frames at 0.60 — weak evidence, real rooms (posters, patterns, hands) are H16's job. If H16 shows ghost boxes, 0.65 is the next step, not 0.80 |
| YuNet NMS 0.3, top_k 5000 | zoo defaults | NMS 0.3 is strict (two faces whose boxes overlap > 30 % lose one: a child in front of a parent); 0.4 is common. top_k only bounds candidates; no cost |
| `MIN_FACE_PX` | 16 | Below it YuNet finds 0-15 % [M]; a 16 px box is useless for anything but "someone is there" |
| `NAME_PX` / `SURE_PX` | 40 / 56 | From the self-match curve (p10 0.94 / 0.96 at the matching crop sizes [M]) plus room for real blur. The self-match test is lenient (same picture); H16 must show no name at 4 m |
| `IOU_MATCH` | 0.3, plain IoU, no motion model | **The weakest link for far faces [E].** Two equal boxes of side s keep IoU ≥ 0.3 only while the shift is ≤ ~0.37 s: 21 px for a 56 px face, 10 px for a 28 px one. At ~6 fps a hand-held pan or a walking person exceeds that, so the track restarts, never reaches 3 stable frames, and the far box flickers — the exact symptom the author reported. Fix: match on IoU of boxes grown ×2 (or centre distance ≤ one box side), with a two-pass association (ByteTrack idea: high-score boxes first, then low-score ones only to existing tracks, <https://arxiv.org/abs/2110.06864>) |
| `STABLE_FRAMES` | 3 | ≈ 0.5 s at 6 fps; right for suppressing the lower floor's flicker |
| `DEAD_SECONDS` | 5 (shared with objects) | Long for faces: a person who steps into the spot another left < 5 s ago inherits the track, and the vote needs 2 more queries (≈ 4 s) to flip. 2 s for faces, and a vote reset after any gap > 1 s [E] |
| `REQUERY_SECONDS` 2 + vote 3 | | A wrong name needs ~4 s to disappear; acceptable. Note the vote window is in *queries*, so it is 6 s of wall time |
| crop quality | `score × √area` | No sharpness, no frontal-ness. Objects use a Laplacian term; faces should too, plus a frontal score from the landmarks (eye distance / box width, nose between the eyes). Blurry or turned templates are the main way a memory goes bad [E] |
| `PEOPLE_THRESHOLD` / `MARGIN` | 0.40 / 0.06 | **Provisional and never calibrated**: `data/eval/people` is empty, M4 is not recorded. SFace's 0.363 [C] is an LFW number on clean pairs; live phone crops score lower for the same person and higher for similar strangers [E]. This is the single most important open measurement |
| people augmentation (strong) | mirror, darker, brighter, tilt ±8°, blur, chin hidden (7) | Reasonable. `blur` is the one that helps far faces. Missing: a **"small face" variant** (shrink the aligned crop to ~40 px and blow it back), which is precisely the degradation a 40-56 px face suffers; cheap and specific. Mirror is harmless for SFace [E] |
| `CROP_SIZE` 384 | kept crop per view | Meaningless for faces: the crop *is* the 112 px aligned face. A later recogniser cannot be re-run on it. Keep the native-resolution face region (≈ 1.5 × box, ≤ 256 px) as well [E] |
| `GUARD_SCORE` 0.5, no size floor | `has_face` | Right direction (when in doubt, it is a face). Residual risk: YuNet's frontal bias — a strong profile or a half-hidden face can pass the guard and go to Claude. Cheap mitigation: run the guard on the crop and on its mirror/2× (it already upsamples < 320 px) [E] |

## 5. Architecture

- **Detect every frame + greedy IoU** is the right simplicity at 6 fps; the association rule is what
  needs work (section 4). A Kalman filter is not needed; a scale-aware match and a two-pass
  association are.
- **Which crop is taught**: the best-quality crop since the last query, one per view. With Video teach
  (15 most different of a recording) this is good; with TEACH it is one frame, chosen by a quality that
  ignores blur. Teaching from the *weak* band (40-56 px) is allowed on purpose: a template with the same
  degradation matches the same person at that distance better [E]; but the UI should say "closer is
  better" when the held face is < 56 px.
- **k-NN memory**: best score over views and hidden variants. Variants make the memory denser, which
  raises the score of *similar strangers* too; the recommended bands from the evaluation (R35/R56)
  are the only guard, and they do not exist for people yet.
- **The name is now dropped when a face walks away** (R57) and re-asked when it returns. Before, a
  track kept its last name at any size — a confident label on a 15 px face.
- **Consent** is asked once per person per session on the phone and not written anywhere. A
  `consent_ts` payload field would make it auditable at no cost [E].
- **Liveness** (research/05): a photo of a person is the person. Known gap, separate spike; it does not
  bear on the aircraft goal.
- **Privacy**: faces never leave the device; the guard is the only cloud boundary and it is tested.
- **Threads**: OpenCV DNN uses all 16 threads for a 26 ms call while the GPU encoder and uvicorn run in
  the same process; no measured problem, but `cv2.setNumThreads(8)` is a one-line knob if the PC gets
  busy [E].

## 6. The objects side, briefly

- The same "second downscale" exists: live frames are 960 px, YOLOE runs at `IMGSZ = 640` (photos at
  1280). Small objects lose pixels exactly like far faces did. The GPU has headroom (~63 ms per frame
  with DINOv2-large [tech-stack]); try 960 and measure [E].
- `DETECT_MIN_AREA = 0.0003` is ~12 px at 640 letterbox — below what YOLOE can see; harmless.
- Object bands (0.45 / 0.10 for dinov2-large) are also provisional; M3 is pending like M4.
- `crop_quality` has the Laplacian term faces lack; share it.

## 7. Recommendations (impact / effort / risk)

**Do now**
1. **H16 and a people test set, then run the evaluation (M4)** — calibrate 0.40 / 0.06 on the phone;
   nothing else is as valuable. High / low / none.
2. **Scale-aware association for faces** (IoU on boxes grown ×2 or centre distance ≤ one box side;
   low-score boxes only continue existing tracks) — fixes far-box flicker. High for far faces / low /
   low (far and weak faces carry no confident name, so a wrong association cannot name anyone).
3. **"Small face" augmentation variant** (shrink to ~40 px and back) for the people profile; Update
   variants rebuilds. Medium / tiny / low.
4. **Face crop quality = score × √area × sharpness × frontal-ness**; hint "closer is better" when a
   held face is < 56 px. Medium / low / low.
5. **Faces: `DEAD_SECONDS` 2 s and vote reset after a gap** > 1 s. Medium / tiny / low.

**Later**
6. **Phone-side far pass**: send the face region cropped from the 1080p stream at full resolution
   (or make 1280 the default after H16). The only route to names at 3-6 m. High / medium / low.
7. Keep the native-resolution face region next to the 112 px crop, so a future recogniser or a better
   aligner can be re-run without re-teaching. Medium / low / none.
8. Liveness spike as written in research/05. Medium / medium / low.
9. `consent_ts` in the payload. Low / tiny / none.
10. Guard hardening (mirror / 2× pass; or a person-ness check) before pictures go to Claude. Medium /
    low / none.
11. NMS 0.3 → 0.4 if H16 or real use shows overlapping faces losing one. Low / tiny / low.

**Not worth it**
- Switching to InsightFace / ArcFace / SCRFD weights: licence excludes them.
- A tiled "far pass" on the server: the received frame has no more pixels to find.
- YuNet at 1920 px (150 ms) or on the GPU (26 ms on CPU is fine).
- Face super-resolution before SFace: invents identity.
- A Kalman tracker: the association rule, not prediction, is the gap at 6 fps.
