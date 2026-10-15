"""Tasks: what to look at, how to embed it, and which memory to ask.

A task turns a camera frame into results the page can draw:
    {"id": track id, "box": [x1, y1, x2, y2] in 0..1, "focus": bool,
     "background": bool, **Decision.to_json()}
and stores examples when the user teaches. Each task owns one TaskMemory.

`VisualTask` holds everything the tasks share (vote, hold, photo mode,
teach-from-video bursts, thumbnails). A concrete task only chooses its
detector/tracker, its encoder and its memory:

    objects  YOLOE + BoT-SORT  -> masked crop   -> CLIP ViT-B/32 (512-d)
    people   YuNet + IoU track -> aligned face  -> SFace (128-d)

A tracker must offer: tracks (dict id -> detect.Track), process(frame, now),
detect_once(frame) -> [(norm box, crop)], reset().
"""
import threading
import time
import uuid

import cv2
import numpy as np

from teachable_eye import config
from teachable_eye.memory import TaskMemory
from teachable_eye.vote import LabelVote

THUMB_SIZE = 160
HOLD_SECONDS = 300     # how long a TEACH selection waits for its name
EDGE = 0.02            # a box this close to a frame edge "touches" it

BURST_SECONDS = 5.0    # teach-from-video: how long views are collected
BURST_MAX_VIEWS = 10
BURST_DISTINCT = 0.95  # keep a view only if cosine < this to every kept view


def is_background(box):
    """Tables, walls, floors: boxes touching two or more frame edges.

    A phone is held close to what it looks at, so a real target rarely
    reaches two edges at once, while the surfaces around it nearly always do.
    """
    x1, y1, x2, y2 = box
    touches = (x1 <= EDGE) + (y1 <= EDGE) + (x2 >= 1 - EDGE) + (y2 >= 1 - EDGE)
    return touches >= 2


def pick_focus(boxes, aim=(0.5, 0.5)):
    """The default target: the smallest non-background box under the aim
    point, else the non-background box whose centre is nearest the aim.
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


def _unit(v):
    v = np.asarray(v, dtype=np.float32)
    n = float(np.linalg.norm(v))
    return v / n if n else v


class Burst:
    """Teach from video: collect distinct views of one track for a few seconds.

    Every processed frame offers the track's newest crop; a view is kept only
    when it differs enough from those already kept, so standing still adds
    nothing and walking around the object adds its other sides.
    """

    def __init__(self, tid, seconds=BURST_SECONDS, max_views=BURST_MAX_VIEWS):
        self.tid = tid
        self.until = time.time() + seconds
        self.max_views = max_views
        self.crops, self.vectors = [], []
        self.offered = 0

    @property
    def done(self):
        return time.time() >= self.until or len(self.crops) >= self.max_views

    def offer(self, crop, vector):
        self.offered += 1
        v = _unit(vector)
        if all(float(v @ k) < BURST_DISTINCT for k in self.vectors):
            self.crops.append(crop.copy())
            self.vectors.append(v)

    def status(self):
        return {"views": len(self.crops), "offered": self.offered,
                "left": max(0.0, round(self.until - time.time(), 1)),
                "done": self.done}


class VisualTask:
    name = "task"
    needs_consent = False

    def __init__(self, detector, embed, memory, source="phone"):
        self.detector = detector
        self.embed = embed
        self.memory = memory
        self.source = source
        self.thumbs = config.DATA_DIR / "thumbs" / self.name
        self.thumbs.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._votes = {}        # tid -> LabelVote
        self._shown = {}        # tid -> Decision currently displayed
        self._crops = {}        # tid -> last crop sent to memory
        self._holds = {}        # hold id -> ([crops], tid or None, time)
        self._still_crops = {}  # photo-mode row id -> crop (last photo only)
        self._bursts = {}       # burst id -> Burst

    # -- live ------------------------------------------------------------------

    def reset(self):
        with self._lock:
            self.detector.reset()
            self._votes.clear()
            self._shown.clear()
            self._crops.clear()
            self._bursts.clear()

    def process(self, frame, now=None):
        now = now or time.time()
        with self._lock:
            tracks = self.detector.process(frame, now)
            bursting = {b.tid: b for b in self._bursts.values() if not b.done}
            # one batched embedding call: due recognitions + burst views
            due = [t for t in tracks if t.crop is not None
                   and (t.tid in bursting or t.due_for_query(now))]
            if due:
                vectors = self.embed([t.crop for t in due])
                for t, vec in zip(due, vectors):
                    if t.tid in bursting:
                        bursting[t.tid].offer(t.crop, vec)
                    if t.due_for_query(now):
                        vote = self._votes.setdefault(t.tid, LabelVote())
                        self._shown[t.tid] = vote.add(self.memory.recognize(vec))
                        t.last_query = now
                    self._crops[t.tid] = t.crop
                    t.crop, t.crop_q = None, 0.0
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

    # -- teaching ----------------------------------------------------------------

    def hold(self, tid, from_still=False):
        """Freeze what will be taught, at the moment TEACH is pressed.

        The user may move the phone while typing the name and the tracker
        can lose the object meanwhile; the held crop survives that.
        """
        with self._lock:
            if from_still:
                crop = self._still_crops.get(tid)
            else:
                track = self.detector.tracks.get(tid)
                crop = track.crop if track is not None else None
                if crop is None:
                    crop = self._crops.get(tid)
            if crop is None:
                raise LookupError("that object is no longer in view")
            return self._new_hold([crop], None if from_still else tid)

    def start_burst(self, tid, seconds=BURST_SECONDS):
        """Teach from video: start collecting views of track `tid`."""
        with self._lock:
            if tid not in self.detector.tracks:
                raise LookupError("that object is no longer in view")
            bid = uuid.uuid4().hex
            self._bursts[bid] = Burst(tid, seconds)
            return bid

    def burst_status(self, bid):
        b = self._bursts.get(bid)
        if b is None:
            raise LookupError("no such video teach")
        return b.status()

    def finish_burst(self, bid):
        """Stop collecting; turn the distinct views into a hold."""
        with self._lock:
            b = self._bursts.pop(bid, None)
            if b is None:
                raise LookupError("no such video teach")
            crops = b.crops or ([self._crops[b.tid]] if b.tid in self._crops else [])
            if not crops:
                raise LookupError("no views captured; keep the object in view")
            return self._new_hold(crops, b.tid), len(crops)

    def _new_hold(self, crops, tid):
        now = time.time()
        self._holds = {k: v for k, v in self._holds.items()
                       if now - v[2] < HOLD_SECONDS}
        hid = uuid.uuid4().hex
        self._holds[hid] = ([c.copy() for c in crops], tid, now)
        return hid

    def hold_preview(self, hid):
        """Thumbnails (JPEG bytes) of a hold, for the name sheet."""
        held = self._holds.get(hid)
        if held is None:
            raise LookupError("the selection expired; press TEACH again")
        return [self._thumb_bytes(c) for c in held[0]]

    def teach_held(self, hid, label):
        """Store every view of a hold under `label`. Returns the first id."""
        with self._lock:
            held = self._holds.pop(hid, None)
            if held is None:
                raise LookupError("the selection expired; press TEACH again")
            crops, tid, _ = held
            try:
                vectors = self.embed(crops)
                ids = [self.memory.teach(vec, label, thumb=self._save_thumb(c),
                                         source=self.source)
                       for c, vec in zip(crops, vectors)]
            except ValueError:
                self._holds[hid] = held          # let the user fix the name
                raise
            if tid is not None:                  # show the label at once
                self._votes.pop(tid, None)
                self._shown.pop(tid, None)
                track = self.detector.tracks.get(tid)
                if track is not None:
                    track.requery_now()
                    if track.crop is None:
                        track.crop = crops[0]
            return ids[0]

    def teach(self, tid, label):
        """Hold and teach in one step (used by tests and tools)."""
        return self.teach_held(self.hold(tid), label)

    # -- photo mode --------------------------------------------------------------

    def still(self, frame):
        """Every detection in one photo with its decision (R14), no tracking."""
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

    # -- thumbnails --------------------------------------------------------------

    @staticmethod
    def _small(crop):
        h, w = crop.shape[:2]
        scale = THUMB_SIZE / max(h, w)
        return cv2.resize(crop, (max(1, int(w * scale)), max(1, int(h * scale))),
                          interpolation=cv2.INTER_AREA)

    def _thumb_bytes(self, crop):
        return cv2.imencode(".jpg", self._small(crop),
                            [cv2.IMWRITE_JPEG_QUALITY, 80])[1].tobytes()

    def _save_thumb(self, crop):
        name = f"{uuid.uuid4().hex}.jpg"
        cv2.imwrite(str(self.thumbs / name), self._small(crop),
                    [cv2.IMWRITE_JPEG_QUALITY, 85])
        return name


class ObjectsTask(VisualTask):
    """YOLOE + tracking → masked crop → CLIP → memory (R7, R8)."""

    name = "objects"

    def __init__(self, detector=None, embed=None, memory=None):
        from teachable_eye import encoders
        if detector is None:
            from teachable_eye.detect import Detector
            detector = Detector()
        super().__init__(
            detector, embed or encoders.embed_crops,
            memory or TaskMemory(config.DATA_DIR / "memory" / self.name,
                                 encoders.CLIP_DIM, self.name, config.OBJECTS))


class PeopleTask(VisualTask):
    """YuNet face detection + IoU tracking → aligned face → SFace (R18-R20).

    Face data (memory, thumbnails) stays under data/ on this device only.
    """

    name = "people"
    needs_consent = True

    def __init__(self, detector=None, embed=None, memory=None):
        from teachable_eye import faces
        super().__init__(
            detector or faces.FaceTracker(), embed or faces.embed_faces,
            memory or TaskMemory(config.DATA_DIR / "memory" / self.name,
                                 faces.SFACE_DIM, self.name, config.PEOPLE))
