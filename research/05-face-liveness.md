# 05 — Face liveness ("is it a live person or a photo?")

> Background note, not normative (2026-10-17). Question from the author: the app recognised him from a
> photo of himself — could it say "person X, but it looks like a photo"? Collected by a research
> sub-agent from primary sources; judgements are marked as such.

## Verified facts

**Passive single-frame CNNs**
- **minivision-ai Silent-Face-Anti-Spoofing** — <https://github.com/minivision-ai/Silent-Face-Anti-Spoofing>, licence **Apache-2.0**.
  - Two MiniFASNet models (`2.7_80x80_MiniFASNetV2`, `4_0_0_80x80_MiniFASNetV1SE`). Each takes an 80×80 crop of the face box enlarged ×2.7 / ×4.0, so it needs context around the face.
  - About 0.4 M parameters and 0.08 GFLOPs each, around 20 ms on phone SoCs.
  - 3 classes, and label 1 means real; the two models' outputs are summed.
  - Published TPR 97.8 % at FPR 1e-5, on their own unpublished data.
  - Weights are PyTorch only.
- **ONNX conversions**
  - <https://github.com/yakhyo/face-anti-spoofing> (Apache-2.0) releases `MiniFASNetV2.onnx` and `MiniFASNetV1SE.onnx`, about 4 MB together. It reports no accuracy of its own.
  - <https://github.com/SuriAI/face-antispoof-onnx> (Apache-2.0 code) offers a 128×128 MiniFASNetV2-SE as 1.8 MB FP32 or 0.6 MB INT8.
    - It reports 98.2 % on CelebA-Spoof, which is in-distribution.
    - **Licence flag:** the training data appears to be CelebA-Spoof, which is *non-commercial research only*. Do not bundle these weights.
- **OpenCV Zoo** has no anti-spoofing model.
- **Generalisation** across datasets is poor: surveys report >20 % HTER (<https://arxiv.org/pdf/2106.14948>). Per-frame scores are unstable, so aggregate over video (<https://arxiv.org/html/2406.12258v1>).
- **Geometric cue:** projective invariants of facial points while the head moves detect flat photos (De Marsico et al., ICB 2012).
- **Blink** needs eye contours (e.g. MediaPipe Face Landmarker, 478 points; check its licence). YuNet's 5 points cannot show a blink.

## Judgement (not verified)
- **First candidate: MiniFASNet V2 + V1SE from the yakhyo ONNX (Apache-2.0).**
  - Cost is negligible on the RTX 4060 Ti.
  - Expect a domain gap: YuNet boxes, 6 fps JPEG frames, home lighting. False "may be a photo" warnings are likely, so calibrate on our own clips.
- **Planar test from YuNet's 5 points.**
  - Fit a homography to the eyes and mouth corners, which are nearly coplanar, between two frames, then measure how far the nose tip is from where the homography puts it.
  - A flat photo gives ≈ 0. A live head turning 15–20° should give ≈ 0.05–0.1 of the eye distance.
  - It needs a head turn. **It does not catch a video replay of a moving head.**
- Screen moiré, colour and reflection cues are weak after JPEG; phone depth is not available to a browser.

## Proposed spike (when scheduled)
1. **Record** through the app, kept local and never committed:
   - 20 live clips of about 5 s: the author and 1–2 consenting people, 3 lighting conditions, near/far, small head turns.
   - 10 printed-photo clips: matte and glossy.
   - 10 photo-on-screen clips: phone and laptop.
   - 5 video-replay clips.
2. **Score** every frame with:
   - (a) the MiniFASNet ensemble,
   - (b) the nose-parallax residual.
   
   Aggregate each clip as the median over a 5-frame window.
3. **Measure** (ISO/IEC 30107-3 style):
   - APCER per attack type, reporting the worst type.
   - BPCER on live clips.
   - Choose the threshold for BPCER ≤ 5 % and report APCER there, plus the "unsure" share.
4. **UI:** advice next to the name — "looks live" / "may be a photo" / "unsure". It is never a security decision and never blocks.
