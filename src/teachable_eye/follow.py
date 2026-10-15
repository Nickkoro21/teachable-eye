"""Follow a box the user drew: single-object tracking with VitTrack.

The detector decides what is an object; sometimes the user knows better (a
gum on the grass, half of a bag, a corrected box). On a paused photo the user
draws or adjusts a box; when live view resumes, this tracker starts from that
exact box and follows it frame by frame.

VitTrack (OpenCV Model Zoo, Apache-2.0, ~700 KB) runs on the CPU in a few
milliseconds per frame and reports a confidence score; a track that stays
unsure for LOST_FRAMES frames is dropped.
"""
import time
import urllib.request

import cv2

from teachable_eye.detect import STABLE_FRAMES, Track, padded_crop
from teachable_eye.encoders import model_dir

VITTRACK = ("object_tracking_vittrack_2023sep.onnx",
            "https://github.com/opencv/opencv_zoo/raw/main/models/"
            "object_tracking_vittrack/object_tracking_vittrack_2023sep.onnx")
MIN_SCORE = 0.25     # below this a frame counts as "not sure where it is"
LOST_FRAMES = 8      # that many unsure frames in a row and the track ends
DUPLICATE_IOU = 0.5  # a detector box overlapping this much is the same thing


def _model():
    name, url = VITTRACK
    path = model_dir("opencv") / name
    if not path.exists():
        print(f"downloading {name} (OpenCV Model Zoo, Apache-2.0)...")
        tmp = path.with_suffix(".part")
        urllib.request.urlretrieve(url, tmp)
        tmp.replace(path)
    return str(path)


def iou(a, b):
    ix1, iy1 = max(a[0], b[0]), max(a[1], b[1])
    ix2, iy2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


class FollowTrack(Track):
    """A Track whose box comes from VitTrack instead of the detector."""

    manual = True

    def __init__(self, tid, frame, norm_box, now=None):
        super().__init__(tid)
        h, w = frame.shape[:2]
        x1, y1, x2, y2 = norm_box
        rect = (int(x1 * w), int(y1 * h),
                max(4, int((x2 - x1) * w)), max(4, int((y2 - y1) * h)))
        params = cv2.TrackerVit_Params()
        params.net = _model()
        self.tracker = cv2.TrackerVit_create(params)
        self.tracker.init(frame, rect)
        self.unsure = 0
        self.frames = STABLE_FRAMES + 1      # the user vouched for it
        self._set(frame, rect, now or time.time())

    def _set(self, frame, rect, now):
        h, w = frame.shape[:2]
        x, y, bw, bh = rect
        self.box = [float(max(0, x)), float(max(0, y)),
                    float(min(w, x + bw)), float(min(h, y + bh))]
        self.frame_wh = (w, h)
        self.last_seen = now
        crop = padded_crop(frame, self.box)
        if crop.size:
            self.crop, self.crop_q = crop, 1.0

    def update(self, frame, now):
        """Follow into `frame`. Returns False when the object is lost."""
        ok, rect = self.tracker.update(frame)
        score = float(self.tracker.getTrackingScore()) if ok else 0.0
        if ok and score >= MIN_SCORE:
            self.unsure = 0
            self._set(frame, rect, now)
        else:
            self.unsure += 1
        return self.unsure < LOST_FRAMES


def scaled(frame, size):
    """`frame` resized to `size` (w, h) if it differs (photo -> live scale)."""
    if size is None or (frame.shape[1], frame.shape[0]) == tuple(size):
        return frame
    return cv2.resize(frame, tuple(size), interpolation=cv2.INTER_AREA)

