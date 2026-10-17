"""Find and track objects before looking them up in memory.

Adapted from https-deeplearning-ai/sc-on-device-ai-memory, robot/brain/detect.py
(Apache-2.0). Kept: YOLOE prompt-free segmentation + BoT-SORT tracking, the
stability gate, masked padded crops, sharpest-crop selection, fp16 on CUDA.
Changed: settings from teachable_eye.config, weights under data/models,
a `detect_once` path for single stills, no ignore list, no macOS pool.

The detector's class names are never read: memory, not the detector, names
objects.
"""
import os
import time

import cv2
import numpy as np

from teachable_eye import config
from teachable_eye.encoders import model_dir

os.environ.setdefault("YOLO_AUTOINSTALL", "false")  # no pip calls at runtime

WEIGHTS = "yoloe-11l-seg-pf.pt"
IMGSZ = 640
IMGSZ_STILL = 1280   # photos: small things (a gum on grass) need resolution
MAX_DET = 64
STABLE_FRAMES = 3      # passes before a track is shown or teachable
REQUERY_SECONDS = 2.0  # how often a stable track re-asks memory
DEAD_SECONDS = 5.0     # forget a track this long after its last detection
PAD = 0.12             # crop margin; the mask removes the background anyway
FILL = (124, 124, 124)


def padded_crop(frame, box, mask=None):
    """12% margin, background outside the segmentation mask flattened to gray.

    Filling outside the mask is what makes recognition survive a changed
    background or a hand holding the object.
    """
    h, w = frame.shape[:2]
    x1, y1, x2, y2 = box
    px, py = (x2 - x1) * PAD, (y2 - y1) * PAD
    x1, y1 = max(0, int(x1 - px)), max(0, int(y1 - py))
    x2, y2 = min(w, int(x2 + px)), min(h, int(y2 + py))
    region = frame[y1:y2, x1:x2]
    if mask is not None and len(mask) >= 3 and region.size:
        full = np.zeros((h, w), np.uint8)
        cv2.fillPoly(full, [np.asarray(mask, dtype=np.int32)], 255)
        full = cv2.dilate(full, np.ones((7, 7), np.uint8), iterations=1)
        inside = full[y1:y2, x1:x2] > 0
        region = region.copy()
        region[~inside] = FILL
    return region


def box_crop(frame, nbox):
    """Plain padded crop of a normalised box (user-drawn regions, no mask)."""
    h, w = frame.shape[:2]
    x1, y1, x2, y2 = nbox
    return padded_crop(frame, [x1 * w, y1 * h, x2 * w, y2 * h])


def crop_quality(frame, box, conf):
    """Bigger, sharper, surer crops win."""
    h, w = frame.shape[:2]
    x1, y1, x2, y2 = (int(v) for v in box)
    if x2 - x1 < 8 or y2 - y1 < 8:
        return 0.0
    small = cv2.resize(frame[y1:y2, x1:x2], (96, 96),
                       interpolation=cv2.INTER_AREA)
    sharp = cv2.Laplacian(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY),
                          cv2.CV_32F).var()
    area = (x2 - x1) * (y2 - y1) / (w * h)
    return conf * (area ** 0.5) * min(sharp, 1200.0)


class Track:
    """One object being followed, and its best crop since the last query."""

    def __init__(self, tid):
        self.tid = tid
        self.frames = 0
        self.last_seen = 0.0
        self.last_query = 0.0
        self.box = None          # pixels in the frame it was seen in
        self.frame_wh = (1, 1)
        self.crop = None
        self.crop_q = 0.0
        self.salience = 0.0

    @property
    def stable(self):
        return self.frames >= STABLE_FRAMES

    def due_for_query(self, now):
        return self.stable and now - self.last_query >= REQUERY_SECONDS

    def requery_now(self):
        self.last_query = time.time() - REQUERY_SECONDS

    def norm_box(self):
        w, h = self.frame_wh
        x1, y1, x2, y2 = self.box
        return [round(float(x1) / w, 4), round(float(y1) / h, 4),
                round(float(x2) / w, 4), round(float(y2) / h, 4)]


# The YOLOE file is a pickle (loading runs code): only the known file is used.
WEIGHTS_SHA256 = "bf39e17c356f4b73977aa978bbdf6d19d0830e6bff46727d2d1f260414e41e0f"


def weights_path():
    path = model_dir() / WEIGHTS
    if not path.exists():
        from ultralytics.utils.downloads import attempt_download_asset
        attempt_download_asset(str(path))
        from teachable_eye.encoders import check_digest
        check_digest(path, WEIGHTS_SHA256)
    return str(path)


class Detector:
    """YOLOE + BoT-SORT tracking + the stability gate."""

    def __init__(self, conf=None, min_area=None, max_area=None):
        import torch
        from ultralytics import YOLO
        self.conf = config.DETECT_CONF if conf is None else conf
        self.min_area = config.DETECT_MIN_AREA if min_area is None else min_area
        self.max_area = config.DETECT_MAX_AREA if max_area is None else max_area
        self.model = YOLO(weights_path())
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.quantize = 16 if self.device == "cuda" else None  # fp16 on CUDA only
        self.tracks = {}

    def warm(self):
        self.model.predict(np.zeros((360, 640, 3), np.uint8), device=self.device,
                           imgsz=IMGSZ, quantize=self.quantize, verbose=False)

    def reset(self):
        """New camera source: drop every track and the tracker's state."""
        self.tracks.clear()
        predictor = getattr(self.model, "predictor", None)
        for tracker in getattr(predictor, "trackers", None) or []:
            tracker.reset()

    def _rows(self, results, w, h, with_ids):
        boxes = results.boxes
        if boxes is None or len(boxes) == 0:
            return
        if with_ids and boxes.id is None:
            return
        ids = boxes.id.int().tolist() if with_ids else [None] * len(boxes)
        polys = results.masks.xy if results.masks is not None else None
        for i, (tid, conf, box) in enumerate(zip(ids, boxes.conf.tolist(),
                                                 boxes.xyxy.tolist())):
            x1, y1, x2, y2 = box
            area = (x2 - x1) * (y2 - y1) / (w * h)
            if not self.min_area <= area <= self.max_area:
                continue
            mask = polys[i] if polys is not None and i < len(polys) else None
            yield tid, conf, box, mask

    def process(self, frame, now=None):
        """Track one live frame; returns the stable tracks."""
        now = now or time.time()
        results = self.model.track(
            frame, device=self.device, quantize=self.quantize, conf=self.conf,
            imgsz=IMGSZ, max_det=MAX_DET, agnostic_nms=True, persist=True,
            verbose=False, tracker="botsort.yaml")[0]
        h, w = frame.shape[:2]
        seen = set()
        for tid, conf, box, mask in self._rows(results, w, h, with_ids=True):
            t = self.tracks.setdefault(tid, Track(tid))
            t.frames = min(t.frames + 1, STABLE_FRAMES + 1)
            t.last_seen = now
            t.box, t.frame_wh = box, (w, h)
            x1, y1, x2, y2 = box
            cx, cy = (x1 + x2) / 2 / w - 0.5, (y1 + y2) / 2 / h - 0.5
            area = (x2 - x1) * (y2 - y1) / (w * h)
            t.salience = (area ** 0.5) * (1 - (cx * cx + cy * cy) ** 0.5)
            q = crop_quality(frame, box, conf)
            if q >= t.crop_q or t.crop is None:
                t.crop, t.crop_q = padded_crop(frame, box, mask), q
            seen.add(tid)
        for tid, t in list(self.tracks.items()):
            if tid not in seen:
                if now - t.last_seen > DEAD_SECONDS:
                    del self.tracks[tid]
                else:
                    t.frames = max(0, t.frames - 1)
        return [t for t in self.tracks.values() if t.stable]

    def detect_once(self, frame):
        """Detect on one still (no tracking state touched).

        Returns [(normalised box, crop)].
        """
        results = self.model.predict(
            frame, device=self.device, quantize=self.quantize, conf=self.conf,
            imgsz=IMGSZ_STILL, max_det=MAX_DET, agnostic_nms=True, verbose=False)[0]
        h, w = frame.shape[:2]
        out = []
        for _, _, box, mask in self._rows(results, w, h, with_ids=False):
            x1, y1, x2, y2 = box
            out.append(([round(x1 / w, 4), round(y1 / h, 4),
                         round(x2 / w, 4), round(y2 / h, 4)],
                        padded_crop(frame, box, mask)))
        return out
