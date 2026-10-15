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
HOLD_SECONDS = 300   # how long a TEACH selection waits for its name
EDGE = 0.02   # a box this close to a frame edge "touches" it


def is_background(box):
    """Tables, walls, floors: boxes touching two or more frame edges.

    A phone is held close to what it looks at, so a real target rarely
    reaches two edges at once, while the surfaces around it nearly always do.
    """
    x1, y1, x2, y2 = box
    touches = (x1 <= EDGE) + (y1 <= EDGE) + (x2 >= 1 - EDGE) + (y2 >= 1 - EDGE)
    return touches >= 2


def pick_focus(boxes, aim=(0.5, 0.5)):
    """The target: the smallest non-background box under the aim point.

    Falls back to the non-background box whose centre is nearest the aim.
    `boxes`: {id: [x1, y1, x2, y2]} normalised. Returns an id or None.
    """
    candidates = {k: b for k, b in boxes.items() if not is_background(b)}
    if not candidates:
        return None
    ax, ay = aim
    under = [(((b[2] - b[0]) * (b[3] - b[1])), k) for k, b in candidates.items()
             if b[0] <= ax <= b[2] and b[1] <= ay <= b[3]]
    if under:
        return min(under)[1]

    def dist(b):
        cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        return (cx - ax) ** 2 + (cy - ay) ** 2
    return min(candidates, key=lambda k: dist(candidates[k]))


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
        self._holds = {}       # hold id -> (crop, tid or None, time)
        self._still_crops = {} # photo-mode row id -> crop (last photo only)

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
            boxes = {t.tid: t.norm_box() for t in tracks}
            focus = pick_focus(boxes)
            out = []
            for t in tracks:
                shown = self._shown.get(t.tid)
                row = {"id": t.tid, "box": boxes[t.tid], "focus": t.tid == focus,
                       "background": is_background(boxes[t.tid])}
                row.update(shown.to_json() if shown else
                           {"decision": "pending", "label": None, "guess": None,
                            "score": 0.0, "neighbours": []})
                out.append(row)
            return out

    def hold(self, tid, from_still=False):
        """Freeze what will be taught, at the moment TEACH is pressed.

        The user may move the phone while typing the name; the tracker can
        lose the object meanwhile. The held crop survives that. Returns a
        hold id for `teach_held`.
        """
        with self._lock:
            now = time.time()
            self._holds = {k: v for k, v in self._holds.items()
                           if now - v[2] < HOLD_SECONDS}
            if from_still:
                crop = self._still_crops.get(tid)
            else:
                track = self.detector.tracks.get(tid)
                crop = track.crop if track is not None else None
                if crop is None:
                    crop = self._crops.get(tid)
            if crop is None:
                raise LookupError("that object is no longer in view")
            hid = uuid.uuid4().hex
            self._holds[hid] = (crop.copy(), None if from_still else tid, now)
            return hid

    def teach_held(self, hid, label):
        """Store a held crop under `label`. Returns the example id."""
        with self._lock:
            held = self._holds.pop(hid, None)
            if held is None:
                raise LookupError("the selection expired; press TEACH again")
            crop, tid, _ = held
            vec = self.embed([crop])[0]
            thumb = self._save_thumb(crop)
            try:
                pid = self.memory.teach(vec, label, thumb=thumb, source="phone")
            except ValueError:
                self._holds[hid] = held          # let the user fix the name
                raise
            # show the new label on the very next query of that track
            if tid is not None:
                self._votes.pop(tid, None)
                self._shown.pop(tid, None)
                track = self.detector.tracks.get(tid)
                if track is not None:
                    track.requery_now()
                    if track.crop is None:
                        track.crop = crop
            return pid

    def teach(self, tid, label):
        """Hold and teach in one step (used by tests and tools)."""
        return self.teach_held(self.hold(tid), label)

    def still(self, frame):
        """Photo mode (R14): every detection with its decision, no tracking."""
        with self._lock:
            found = self.detector.detect_once(frame)
            self._still_crops = {i: crop for i, (_, crop) in enumerate(found)}
            if not found:
                return []
            vectors = self.embed([crop for _, crop in found])
            return [dict({"id": i, "box": box, "focus": False,
                          "background": is_background(box)},
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
