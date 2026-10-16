"""Faces: YuNet detection, a small IoU tracker, SFace embeddings.

Both models come from the OpenCV Model Zoo (Apache-2.0) and run through
OpenCV's DNN module; they are small enough that the CPU keeps up:
    YuNet  face_detection_yunet_2023mar.onnx    ~230 KB  boxes + 5 landmarks
    SFace  face_recognition_sface_2021dec.onnx  ~37 MB   128-d identity vector
SFace's published cosine match threshold is 0.363 (on LFW).

Faces are aligned with the 5 landmarks before embedding, which is what
makes the identity vector stable when the head turns or tilts.
"""
import threading
import time
import urllib.request

import cv2
import numpy as np

from teachable_eye.detect import STABLE_FRAMES, DEAD_SECONDS, Track
from teachable_eye.encoders import model_dir

ZOO = "https://github.com/opencv/opencv_zoo/raw/main/models"
YUNET = ("face_detection_yunet_2023mar.onnx",
         f"{ZOO}/face_detection_yunet/face_detection_yunet_2023mar.onnx")
SFACE = ("face_recognition_sface_2021dec.onnx",
         f"{ZOO}/face_recognition_sface/face_recognition_sface_2021dec.onnx")
SFACE_DIM = 128

SCORE = 0.80        # YuNet confidence floor
MIN_FACE = 0.0008   # smallest face kept, as a fraction of the frame area
IOU_MATCH = 0.3     # box overlap that continues a track
DETECT_SIDE = 640   # faces are detected on a frame scaled to this long side


def _model(name_url):
    name, url = name_url
    path = model_dir("opencv") / name
    if not path.exists():
        print(f"downloading {name} (OpenCV Model Zoo, Apache-2.0)...")
        tmp = path.with_suffix(".part")
        urllib.request.urlretrieve(url, tmp)
        tmp.replace(path)
    return str(path)


_lock = threading.Lock()
_recognizer = None


def _sface():
    global _recognizer
    if _recognizer is None:
        _recognizer = cv2.FaceRecognizerSF.create(_model(SFACE), "")
    return _recognizer


def embed_faces(aligned):
    """Aligned 112x112 BGR faces -> list of L2-normalised 128-d lists."""
    out = []
    with _lock:
        rec = _sface()
        for face in aligned:
            v = rec.feature(face).reshape(-1).astype(np.float32)
            n = float(np.linalg.norm(v))
            out.append((v / n if n else v).tolist())
    return out


def _iou(a, b):
    ix1, iy1 = max(a[0], b[0]), max(a[1], b[1])
    ix2, iy2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


_guard = None
GUARD_SCORE = 0.5   # lower than SCORE: when in doubt, it is a face


def has_face(img):
    """True when `img` (BGR) shows a face. Used before any picture may leave
    the device (assist.py): a crop with a face is never sent."""
    h, w = img.shape[:2]
    if h < 10 or w < 10:
        return False
    scale = min(1.0, DETECT_SIDE / max(h, w))
    small = img if scale == 1.0 else cv2.resize(
        img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    # small crops: faces may fill them, upscale so YuNet can see them
    if max(small.shape[:2]) < 320:
        f = 320 / max(small.shape[:2])
        small = cv2.resize(small, None, fx=f, fy=f, interpolation=cv2.INTER_LINEAR)
    return len(_guard_detect(small)) > 0


def _guard_detect(img):
    """YuNet at the lower GUARD_SCORE: rows of [x, y, w, h, 5 landmarks, score]."""
    global _guard
    with _lock:
        if _guard is None:
            _guard = cv2.FaceDetectorYN.create(_model(YUNET), "", (320, 320),
                                               GUARD_SCORE, 0.3, 5000)
        _guard.setInputSize((img.shape[1], img.shape[0]))
        _, found = _guard.detect(img)
    return [] if found is None else list(found)


def find_face(frame, nbox, pad=0.3):
    """Look for a face inside a box the user drew (normalised x1, y1, x2, y2).

    The region (plus a margin) is scaled to ~640 px so small or turned faces
    the live detector missed can be found, with a lower confidence floor: the
    user has already said there is a face there. Returns (normalised face
    box, aligned 112x112 face) for the largest face, or None.
    """
    h, w = frame.shape[:2]
    x1, y1, x2, y2 = nbox
    bw, bh = (x2 - x1) * w, (y2 - y1) * h
    X1, Y1 = max(0, int(x1 * w - pad * bw)), max(0, int(y1 * h - pad * bh))
    X2, Y2 = min(w, int(x2 * w + pad * bw)), min(h, int(y2 * h + pad * bh))
    region = frame[Y1:Y2, X1:X2]
    if region.size == 0 or min(region.shape[:2]) < 8:
        return None
    scale = DETECT_SIDE / max(region.shape[:2])
    view = cv2.resize(region, None, fx=scale, fy=scale,
                      interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR)
    rows = _guard_detect(view)
    if not rows:
        return None
    row = max(rows, key=lambda r: r[2] * r[3]).copy()
    row[:14] /= scale                        # back to region pixels
    # ... and to frame pixels: positions only (x, y and the 5 landmarks),
    # never the width and height at indices 2 and 3
    row[[0, 4, 6, 8, 10, 12]] += X1
    row[[1, 5, 7, 9, 11, 13]] += Y1
    with _lock:
        aligned = _sface().alignCrop(frame, row)
    fx, fy, fw, fh = (float(v) for v in row[:4])
    box = [max(0.0, fx / w), max(0.0, fy / h), min(1.0, (fx + fw) / w), min(1.0, (fy + fh) / h)]
    return [round(v, 4) for v in box], aligned


class FaceTracker:
    """Detect faces, follow them with greedy IoU matching, keep aligned crops."""

    def __init__(self, score=SCORE):
        self.detector = cv2.FaceDetectorYN.create(
            _model(YUNET), "", (320, 320), score, 0.3, 5000)
        _sface()                          # load (and download) up front
        self.tracks = {}
        self._next = 1

    def reset(self):
        self.tracks.clear()

    def _faces(self, frame):
        """[(pixel box, aligned crop, quality)] for one frame."""
        h, w = frame.shape[:2]
        scale = min(1.0, DETECT_SIDE / max(h, w))
        small = frame if scale == 1.0 else cv2.resize(
            frame, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
        self.detector.setInputSize((small.shape[1], small.shape[0]))
        _, faces = self.detector.detect(small)
        out = []
        if faces is None:
            return out
        rec = _sface()
        for f in faces:
            row = f.copy()
            row[:14] /= scale                    # back to full-frame pixels
            x, y, fw, fh = row[:4]
            if fw * fh / (w * h) < MIN_FACE:
                continue
            with _lock:
                aligned = rec.alignCrop(frame, row)
            # plain floats: numpy float32 is not JSON serialisable
            box = [float(max(0.0, x)), float(max(0.0, y)),
                   float(min(w, x + fw)), float(min(h, y + fh))]
            out.append((box, aligned, float(row[14]) * (fw * fh) ** 0.5))
        return out

    def process(self, frame, now=None):
        now = now or time.time()
        h, w = frame.shape[:2]
        found = self._faces(frame)
        unmatched = set(self.tracks)
        for box, aligned, quality in sorted(found, key=lambda f: -f[2]):
            best, best_iou = None, IOU_MATCH
            for tid in unmatched:
                iou = _iou(self.tracks[tid].box, box)
                if iou >= best_iou:
                    best, best_iou = tid, iou
            if best is None:
                best = self._next
                self._next += 1
                self.tracks[best] = Track(best)
            else:
                unmatched.discard(best)
            t = self.tracks[best]
            t.frames = min(t.frames + 1, STABLE_FRAMES + 1)
            t.last_seen = now
            t.box, t.frame_wh = box, (w, h)
            t.salience = quality
            if quality >= t.crop_q or t.crop is None:
                t.crop, t.crop_q = aligned, quality
        for tid in list(unmatched):
            t = self.tracks[tid]
            if now - t.last_seen > DEAD_SECONDS:
                del self.tracks[tid]
            else:
                t.frames = max(0, t.frames - 1)
        return [t for t in self.tracks.values() if t.stable]

    def detect_once(self, frame):
        h, w = frame.shape[:2]
        return [([round(b[0] / w, 4), round(b[1] / h, 4),
                  round(b[2] / w, 4), round(b[3] / h, 4)], aligned)
                for b, aligned, _ in self._faces(frame)]
