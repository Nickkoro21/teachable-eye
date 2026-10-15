"""Tasks: what to look at, how to embed it, and which memory to ask.

A task turns a camera frame into results the page can draw:
    {"id": track id, "box": [x1, y1, x2, y2] in 0..1, "focus": bool,
     **Decision.to_json()}
and stores examples when the user teaches. Each task owns one TaskMemory.
"""
import threading
import time
import uuid

import cv2

from teachable_eye import config
from teachable_eye.memory import TaskMemory
from teachable_eye.vote import LabelVote

THUMB_SIZE = 160


class ObjectsTask:
    """YOLOE + tracking → masked crop → CLIP → memory (R7, R8)."""

    name = "objects"

    def __init__(self, detector=None, embed=None, memory=None):
        from teachable_eye import encoders
        if detector is None:
            from teachable_eye.detect import Detector
            detector = Detector()
        self.detector = detector
        self.embed = embed or encoders.embed_crops
        self.memory = memory or TaskMemory(
            config.DATA_DIR / "memory" / self.name, encoders.CLIP_DIM,
            self.name, config.OBJECTS)
        self.thumbs = config.DATA_DIR / "thumbs" / self.name
        self.thumbs.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._votes = {}       # tid -> LabelVote
        self._shown = {}       # tid -> Decision currently displayed
        self._crops = {}       # tid -> last crop sent to memory (for teach)

    def reset(self):
        with self._lock:
            self.detector.reset()
            self._votes.clear()
            self._shown.clear()
            self._crops.clear()

    def process(self, frame, now=None):
        now = now or time.time()
        with self._lock:
            tracks = self.detector.process(frame, now)
            due = [t for t in tracks if t.due_for_query(now) and t.crop is not None]
            if due:
                vectors = self.embed([t.crop for t in due])
                for t, vec in zip(due, vectors):
                    decision = self.memory.recognize(vec)
                    vote = self._votes.setdefault(t.tid, LabelVote())
                    self._shown[t.tid] = vote.add(decision)
                    self._crops[t.tid] = t.crop
                    t.last_query, t.crop, t.crop_q = now, None, 0.0
            for store in (self._votes, self._shown, self._crops):
                for tid in [k for k in store if k not in self.detector.tracks]:
                    del store[tid]
            focus = max(tracks, key=lambda t: t.salience).tid if tracks else None
            out = []
            for t in tracks:
                shown = self._shown.get(t.tid)
                row = {"id": t.tid, "box": t.norm_box(), "focus": t.tid == focus}
                row.update(shown.to_json() if shown else
                           {"decision": "pending", "label": None, "guess": None,
                            "score": 0.0, "neighbours": []})
                out.append(row)
            return out

    def teach(self, tid, label):
        """Store the crop of track `tid` under `label`. Returns the example id."""
        with self._lock:
            track = self.detector.tracks.get(tid)
            crop = self._crops.get(tid)
            if crop is None and track is not None:
                crop = track.crop
            if crop is None:
                raise LookupError("that object is no longer in view")
            vec = self.embed([crop])[0]
            thumb = self._save_thumb(crop)
            pid = self.memory.teach(vec, label, thumb=thumb, source="phone")
            # show the new label on the very next frame
            self._votes.pop(tid, None)
            self._shown.pop(tid, None)
            if track is not None:
                track.requery_now()
                if track.crop is None:
                    track.crop = crop
            return pid

    def still(self, frame):
        """Photo mode (R14): every detection with its decision, no tracking."""
        with self._lock:
            found = self.detector.detect_once(frame)
            if not found:
                return []
            vectors = self.embed([crop for _, crop in found])
            return [dict({"id": i, "box": box, "focus": False},
                         **self.memory.recognize(vec).to_json())
                    for i, ((box, _), vec) in enumerate(zip(found, vectors))]

    def _save_thumb(self, crop):
        h, w = crop.shape[:2]
        scale = THUMB_SIZE / max(h, w)
        small = cv2.resize(crop, (max(1, int(w * scale)), max(1, int(h * scale))),
                           interpolation=cv2.INTER_AREA)
        name = f"{uuid.uuid4().hex}.jpg"
        cv2.imwrite(str(self.thumbs / name), small,
                    [cv2.IMWRITE_JPEG_QUALITY, 85])
        return name
