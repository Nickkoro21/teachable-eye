"""Tasks: what to look at, how to embed it, and which memory to ask.

A task turns a camera frame into results the page can draw:
    {"id": track id, "box": [x1, y1, x2, y2] in 0..1, "focus": bool,
     "background": bool, "far": bool, **Decision.to_json()}
and stores examples when the user teaches. Each task owns one TaskMemory.
A `far` row is a face too small for any identity (R57): its decision stays
`pending`, it cannot be taught; a face a little bigger is `uncertain` at most.

`VisualTask` holds everything the tasks share (vote, hold, photo mode,
teach-from-video bursts, thumbnails). A concrete task only chooses its
detector/tracker, its encoder and its memory:

    objects  YOLOE + BoT-SORT  -> masked crop   -> OBJECT_ENCODER (DINOv2-large)
    people   YuNet + IoU track -> aligned face  -> SFace (128-d)

A tracker must offer: tracks (dict id -> detect.Track), process(frame, now),
detect_once(frame) -> [(norm box, crop)] (faces: a third item, {"far", "weak"},
and crop None when far), reset().
"""
import threading
import time
import uuid

import cv2
import numpy as np

from teachable_eye import config
from teachable_eye.labels import norm_label
from teachable_eye.memory import TaskMemory
from teachable_eye.policy import at_most_uncertain
from teachable_eye.vote import LabelVote

# what a row says before (or instead of) a decision
PENDING = {"decision": "pending", "label": None, "guess": None,
           "score": 0.0, "neighbours": []}
TOO_FAR = "too far to teach; come closer"


def _found(item):
    """(box, crop, far, weak) from one detect_once item (objects: no flags)."""
    box, crop = item[0], item[1]
    flags = item[2] if len(item) > 2 else {}
    return box, crop, bool(flags.get("far")), bool(flags.get("weak"))

THUMB_SIZE = 160
CROP_SIZE = 384      # kept per taught view, so memory can be re-embedded
HOLD_SECONDS = 300     # how long a TEACH selection waits for its name
MAX_HOLDS = 50         # selections waiting for a name at most
MAX_STILLS = 4         # photos kept open at once (phone, PC, ...)
MAX_STILL_CROPS = 300  # boxes (detected + drawn) on one photo at most
EDGE = 0.02            # a box this close to a frame edge "touches" it

BURST_SECONDS = 60.0   # teach-from-video records until the user stops it; safety cap
BURST_MAX_SECONDS = 120.0
BURST_KEEP = 15        # views kept: the most different ones of the whole recording
BURST_DISTINCT = 0.95  # a kept view differs from every other (cosine < this)
BURST_SAME = 0.995     # a frame this close to the previous one is skipped (holding still)
BURST_POOL = 200       # candidate frames held at most (thinned evenly when full)


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


# -- teach-time augmentation ---------------------------------------------------
# A memory cannot generalise beyond what it stores, so a taught view also
# stores a few plausible variants of itself (hidden from the user, deleted
# with their view). Real views (Video) are still better than synthetic ones.

def zoom_center(crop, keep=0.7):
    """The middle of the crop: the same object seen from closer."""
    h, w = crop.shape[:2]
    dh, dw = int(h * (1 - keep) / 2), int(w * (1 - keep) / 2)
    return crop[dh:h - dh, dw:w - dw].copy() if h > 20 and w > 20 else crop


def flip(crop):
    """Mirror image: the other side of a roughly symmetric object."""
    return cv2.flip(crop, 1)


def darker(crop, gain=0.7):
    """Dimmer light (the room changes, the object does not)."""
    return cv2.convertScaleAbs(crop, alpha=gain, beta=0)


# -- the "strong" profile (2026-10-17, author's request: partial views and
# rotations, to make recognition more robust). Pieces keep about half of the
# object, not a quarter: a quarter of a mug looks like many things, and a
# confident wrong name is the error that matters most. Decided by the
# evaluation's basic-vs-strong comparison once there is a test set.

def brighter(crop, gain=1.3, bias=12):
    """Stronger light, e.g. near a window."""
    return cv2.convertScaleAbs(crop, alpha=gain, beta=bias)


def _rotate(crop, degrees):
    h, w = crop.shape[:2]
    m = cv2.getRotationMatrix2D((w / 2, h / 2), degrees, 1.0)
    return cv2.warpAffine(crop, m, (w, h), borderMode=cv2.BORDER_REPLICATE)


def rot_left(crop):
    """Turned 15° (the phone or the object held at an angle)."""
    return _rotate(crop, 15)


def rot_right(crop):
    return _rotate(crop, -15)


def tilt_left(crop):
    """A face tilted 8° (more would fight the eye alignment)."""
    return _rotate(crop, 8)


def tilt_right(crop):
    return _rotate(crop, -8)


def _corner(crop, corner, keep=0.75):
    """Keep 75 % of each side (~56 % of the area) from one corner."""
    h, w = crop.shape[:2]
    if h <= 20 or w <= 20:
        return crop
    kh, kw = int(h * keep), int(w * keep)
    y = 0 if corner[0] == "t" else h - kh
    x = 0 if corner[1] == "l" else w - kw
    return crop[y:y + kh, x:x + kw].copy()


def part_tl(crop):
    """Part of the object only: the rest out of frame or hidden."""
    return _corner(crop, "tl")


def part_tr(crop):
    return _corner(crop, "tr")


def part_bl(crop):
    return _corner(crop, "bl")


def part_br(crop):
    return _corner(crop, "br")


def _cover(crop, y0, y1, x0, x1):
    out = crop.copy()
    h, w = out.shape[:2]
    out[int(h * y0):int(h * y1), int(w * x0):int(w * x1)] = 127
    return out


def cover_tl(crop):
    """A quarter hidden (a hand, another object in front)."""
    return _cover(crop, 0, 0.5, 0, 0.5)


def cover_br(crop):
    return _cover(crop, 0.5, 1, 0.5, 1)


def cover_low(crop):
    """Lower third of a face hidden (a hand on the chin, a scarf)."""
    return _cover(crop, 0.68, 1, 0, 1)


def blur(crop):
    """Slightly out of focus or moving."""
    return cv2.GaussianBlur(crop, (5, 5), 0)


AUGMENT_PROFILES = {
    "basic": {
        "objects": (zoom_center, flip, darker),
        "people": (flip, darker),     # faces are aligned: never crop them
    },
    "strong": {
        "objects": (zoom_center, flip, darker, brighter, rot_left, rot_right,
                    part_tl, part_tr, part_bl, part_br, cover_tl, cover_br, blur),
        "people": (flip, darker, brighter, tilt_left, tilt_right, blur, cover_low),
    },
}


def augmentations(task, profile=None):
    """The variant functions for a task under a profile (default: the configured one)."""
    profile = profile or config.AUGMENT_PROFILE
    if not profile:
        return ()
    return AUGMENT_PROFILES[profile].get(task, ())


# kept for the tools: the configured profile per task
AUGMENT = {task: augmentations(task) for task in ("objects", "people")}


def _unit(v):
    v = np.asarray(v, dtype=np.float32)
    n = float(np.linalg.norm(v))
    return v / n if n else v


class Burst:
    """Teach from video: record one track for the whole time, keep the best views.

    Every processed frame offers the track's newest crop. All of them are
    candidates (except near-copies of the previous frame); at the end the
    most different views of the WHOLE recording are chosen (farthest-point
    sampling, sharpest view first), so turning around a face or an object
    covers all its sides. It used to keep the first 10 distinct views and
    stop: a turning face reached 10 in about a second and the later angles
    were lost (author's phone test, 2026-10-17).
    """

    def __init__(self, tid, seconds=BURST_SECONDS, keep=BURST_KEEP):
        self.tid = tid
        self.until = time.time() + seconds
        self.keep = keep
        self.crops, self.vectors, self.sharp = [], [], []
        self.offered = 0

    @property
    def done(self):
        return time.time() >= self.until

    def offer(self, crop, vector):
        self.offered += 1
        v = _unit(vector)
        if self.vectors and float(v @ self.vectors[-1]) >= BURST_SAME:
            return                                  # nothing changed
        if len(self.crops) >= BURST_POOL:
            # a long recording: thin out evenly, so the whole of it stays covered
            self.crops, self.vectors, self.sharp = (
                self.crops[::2], self.vectors[::2], self.sharp[::2])
        h, w = crop.shape[:2]
        if max(h, w) > CROP_SIZE:                   # bounded memory per candidate
            s = CROP_SIZE / max(h, w)
            crop = cv2.resize(crop, (max(1, int(w * s)), max(1, int(h * s))),
                              interpolation=cv2.INTER_AREA)
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if crop.ndim == 3 else crop
        self.crops.append(crop.copy())
        self.vectors.append(v)
        self.sharp.append(float(cv2.Laplacian(gray, cv2.CV_64F).var()))

    def select(self):
        """Indices (in time order) of up to `keep` views that differ most."""
        if not self.vectors:
            return []
        V = np.stack(self.vectors)
        chosen = [int(np.argmax(self.sharp))]       # start from the sharpest
        closest = V @ V[chosen[0]]                  # similarity to the chosen set
        while len(chosen) < self.keep:
            nxt = int(np.argmin(closest))           # the least like any chosen
            if closest[nxt] >= BURST_DISTINCT:
                break                               # the rest add nothing new
            chosen.append(nxt)
            closest = np.maximum(closest, V @ V[nxt])
        return sorted(chosen)

    def status(self):
        return {"views": len(self.select()), "frames": len(self.crops),
                "offered": self.offered,
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
        # the taught crops themselves: a new encoder can rebuild the memory
        # from them (tools/reembed.py) instead of the user re-teaching
        self.crops = config.DATA_DIR / "crops" / self.name
        self.crops.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._votes = {}        # tid -> LabelVote
        self._shown = {}        # tid -> Decision currently displayed
        self._crops = {}        # tid -> last crop sent to memory
        self._holds = {}        # hold id -> ([crops], tid or None, time)
        self._still_crops = {}  # photo-mode row id -> crop (last photo only)
        self._bursts = {}       # burst id -> Burst
        self._still_frame = None  # the photo being worked on (for user-drawn regions)
        self._stills = {}         # still id -> (frame, crops): the last few photos
        self.last_still_id = None
        self._live_wh = None      # size of the live frames (for follow)
        self._follow = {}         # tid -> follow.FollowTrack (user boxes)
        self._next_follow = 10_000

    def _track(self, tid):
        """A live track by id: user-followed boxes first, then the detector's."""
        return self._follow.get(tid) or self.detector.tracks.get(tid)

    # -- live ------------------------------------------------------------------

    def reset(self):
        with self._lock:
            self.detector.reset()
            self._votes.clear()
            self._shown.clear()
            self._crops.clear()
            self._bursts.clear()
            self._follow.clear()

    def process(self, frame, now=None):
        now = now or time.time()
        with self._lock:
            self._live_wh = (frame.shape[1], frame.shape[0])
            tracks = self.detector.process(frame, now)
            if self._follow:
                from teachable_eye.follow import DUPLICATE_IOU, iou
                for tid, ft in list(self._follow.items()):
                    if not ft.update(frame, now):
                        del self._follow[tid]          # lost it
                followed = [ft.box for ft in self._follow.values()]
                # the user's box wins over a detector box on the same thing
                tracks = [t for t in tracks
                          if all(iou(t.box, fb) < DUPLICATE_IOU for fb in followed)]
                tracks += list(self._follow.values())
            bursting = {b.tid: b for b in self._bursts.values() if not b.done}
            for t in tracks:
                if t.far:          # a face too small for a name: forget what
                    self._votes.pop(t.tid, None)   # it was called when nearer
                    self._shown.pop(t.tid, None)
            # one batched embedding call: due recognitions + burst views
            due = [t for t in tracks if t.crop is not None and not t.far
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
                for tid in [k for k in store if self._track(k) is None]:
                    del store[tid]
            boxes = {t.tid: t.norm_box() for t in tracks}
            focus = pick_focus({t.tid: boxes[t.tid] for t in tracks if not t.far})
            out = []
            for t in tracks:
                shown = self._shown.get(t.tid)
                if shown is not None and t.weak:     # a name needs a bigger face
                    shown = at_most_uncertain(shown)
                row = {"id": t.tid, "box": boxes[t.tid], "focus": t.tid == focus,
                       "background": is_background(boxes[t.tid]),
                       "manual": getattr(t, "manual", False), "far": t.far}
                row.update(shown.to_json() if shown else PENDING)
                out.append(row)
            return out

    # -- teaching ----------------------------------------------------------------

    def _use_still(self, still_id):
        """Work on photo `still_id` (None: the latest). The phone and the PC
        may each have a photo open: a box of one must never teach the other's
        crop (backend review 2026-10-17)."""
        if still_id is None:
            still_id = self.last_still_id       # the newest photo
            if still_id is None or still_id not in self._stills:
                return
        if still_id not in self._stills:
            raise LookupError("this photo has expired; take it again")
        self._still_frame, self._still_crops = self._stills[still_id]

    def hold(self, tid, from_still=False, still_id=None):
        """Freeze what will be taught, at the moment TEACH is pressed.

        The user may move the phone while typing the name and the tracker
        can lose the object meanwhile; the held crop survives that.
        """
        with self._lock:
            if from_still:
                self._use_still(still_id)
                crop = self._still_crops.get(tid)
                if crop is None and tid in self._still_crops:
                    raise LookupError(TOO_FAR)          # a far face (R57)
            else:
                track = self._track(tid)
                if track is not None and track.far:
                    raise LookupError(TOO_FAR)
                crop = track.crop if track is not None else None
                if crop is None:
                    crop = self._crops.get(tid)
            if crop is None:
                raise LookupError("that object is no longer in view")
            return self._new_hold([crop], None if from_still else tid)

    def start_burst(self, tid, seconds=BURST_SECONDS):
        """Teach from video: start collecting views of track `tid`."""
        with self._lock:
            track = self._track(tid)
            if track is None:
                raise LookupError("that object is no longer in view")
            if track.far:
                raise LookupError(TOO_FAR)
            bid = uuid.uuid4().hex
            seconds = min(max(1.0, float(seconds)), BURST_MAX_SECONDS)
            # forgotten recordings (the phone went away) must not pile up
            now = time.time()
            self._bursts = {k: b for k, b in self._bursts.items() if now < b.until + 60}
            if len(self._bursts) >= 2:
                self._bursts.pop(next(iter(self._bursts)))
            self._bursts[bid] = Burst(tid, seconds)
            return bid

    def burst_status(self, bid):
        with self._lock:                 # the worker may be thinning its lists
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
            crops = ([b.crops[i] for i in b.select()]
                     or ([self._crops[b.tid]] if b.tid in self._crops else []))
            if not crops:
                raise LookupError("no views captured; keep the object in view")
            return self._new_hold(crops, b.tid), len(crops)

    def _new_hold(self, crops, tid):
        now = time.time()
        self._holds = {k: v for k, v in self._holds.items()
                       if now - v[2] < HOLD_SECONDS}
        while len(self._holds) >= MAX_HOLDS:          # oldest first
            self._holds.pop(min(self._holds, key=lambda k: self._holds[k][2]))
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
            augs = augmentations(self.name)
            try:
                if not norm_label(label):
                    raise ValueError("empty label")
                vectors = self.embed(crops)
                points, ids = [], []
                for c, vec in zip(crops, vectors):
                    pid = str(uuid.uuid4())
                    ids.append(pid)
                    points.append({"id": pid, "vector": vec, "label": label,
                                   "thumb": self._save_thumb(c),
                                   "crop": self._save_crop(c), "source": self.source})
                    if augs:
                        variants = [fn(c) for fn in augs]
                        for fn, img, v in zip(augs, variants, self.embed(variants)):
                            points.append({"vector": v, "label": label,
                                           "thumb": self._save_thumb(img),
                                           "source": self.source, "parent": pid,
                                           "aug": fn.__name__})
                self.memory.teach_many(points)       # one write, one flush
            except Exception:
                # a bad name, or a GPU / disk error: the selection (maybe a
                # long video teach) stays, so Save can simply be pressed again
                self._holds[hid] = held
                raise
            if tid is not None:                  # show the label at once
                self._votes.pop(tid, None)
                self._shown.pop(tid, None)
                track = self._track(tid)
                if track is not None:
                    track.requery_now()
                    if track.crop is None:
                        track.crop = crops[0]
            return ids[0]

    def teach(self, tid, label):
        """Hold and teach in one step (used by tests and tools)."""
        return self.teach_held(self.hold(tid), label)

    def confirm(self, rid, label, from_still=False, still_id=None):
        """One tap on "maybe X?": teach the box's crop as X.

        The guess is checked again first, because the picture may have moved
        under a finger already on its way down: live, the guess on screen for
        that track must still be X; on a photo, the crop must still come out
        nearest to X. Returns the new view id, or None (nothing written).
        Adapted from https-deeplearning-ai/sc-on-device-ai-memory,
        robot/brain/core.py `confirm` (Apache-2.0).
        """
        with self._lock:              # check and freeze in one step (not re-entrant)
            if from_still:
                self._use_still(still_id)
                crop = self._still_crops.get(rid)
                if crop is None:
                    return None
                d = self.memory.recognize(self.embed([crop])[0])
                if (d.label or d.guess) != label:
                    return None
                hid = self._new_hold([crop], None)
            else:
                shown = self._shown.get(rid)
                if shown is None or (shown.label or shown.guess) != label:
                    return None
                track = self._track(rid)
                crop = track.crop if track is not None and track.crop is not None \
                    else self._crops.get(rid)
                if crop is None:
                    return None
                hid = self._new_hold([crop], rid)
        return self.teach_held(hid, label)

    def still_crops(self, rids, still_id=None):
        """Crops of rows of a photo (None where a row is unknown)."""
        with self._lock:
            self._use_still(still_id)
            return [self._still_crops.get(r) for r in rids]

    def example_images(self, label, n=2):
        """Up to `n` pictures of a taught label: kept crops, else thumbnails."""
        out = []
        for e in self.memory.examples():
            if e.get("label") != label:
                continue
            for folder, name in ((self.crops, e.get("crop")), (self.thumbs, e.get("thumb"))):
                img = cv2.imread(str(folder / name)) if name else None
                if img is not None:
                    out.append(img)
                    break
            if len(out) >= n:
                break
        return out

    def forget_everywhere(self, label):
        """After forgetting `label` (None: everything): delete its test views
        and the evaluation reports of this task that name it."""
        removed = 0
        for it in self.evalset.items():
            if label is None or it["label"] == label:
                removed += self.evalset.delete(it["id"])
        folder = config.DATA_DIR / "reports"
        for path in folder.glob(f"eval-{self.name}-*"):
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            if label is None or label in text:
                path.unlink(missing_ok=True)
                removed += 1
        return removed

    def held_crops(self, hid):
        """The crops of a hold, left in place (Claude's opinion reads them)."""
        held = self._holds.get(hid)
        if held is None:
            raise LookupError("the selection expired; press TEACH again")
        return held[0]

    # -- test set and evaluation (R34, R35) --------------------------------------

    @property
    def evalset(self):
        if getattr(self, "_evalset", None) is None:
            from teachable_eye.evalset import EvalStore
            self._evalset = EvalStore(self.name)
        return self._evalset

    def eval_held(self, hid, label):
        """Save the views of a hold to the test set, NOT to memory."""
        with self._lock:
            held = self._holds.pop(hid, None)
            if held is None:
                raise LookupError("the selection expired; press TEACH again")
            try:
                ids = [self.evalset.add(c, label, self.source) for c in held[0]]
            except ValueError:
                self._holds[hid] = held
                raise
            return len(ids)

    # -- variants of the views already taught ----------------------------------

    def _view_images(self):
        """[(view id, label, picture)] of every taught view: its kept crop, else
        its 160 px thumbnail (views taught before crops were kept)."""
        out = []
        for e in self.memory.examples():
            img = None
            for folder, name in ((self.crops, e.get("crop")), (self.thumbs, e.get("thumb"))):
                if name:
                    img = cv2.imread(str(folder / name))
                    if img is not None:
                        break
            if img is None:
                continue
            if self.name == "people" and img.shape[:2] != (112, 112):
                img = cv2.resize(img, (112, 112), interpolation=cv2.INTER_AREA)  # SFace input
            out.append((e["id"], e["label"], img))
        return out

    def _variant_points(self, views, profile=None, with_thumbs=False):
        points = []
        fns = augmentations(self.name, profile)
        if not fns:
            return points
        for vid, label, img in views:
            pics = [fn(img) for fn in fns]
            for fn, pic, vec in zip(fns, pics, self.embed(pics)):
                p = {"vector": vec, "label": label, "parent": vid, "aug": fn.__name__,
                     "source": self.source}
                if with_thumbs:
                    p["thumb"] = self._save_thumb(pic)
                points.append(p)
        return points

    def refresh_variants(self):
        """Rebuild the variants of every taught view with the current profile
        (e.g. after switching to "strong"), so nothing has to be re-taught."""
        with self._lock:
            views = self._view_images()
            points = self._variant_points(views, with_thumbs=True)
            removed = self.memory.forget_variants({vid for vid, _, _ in views})
            self.memory.teach_many(points)
        self.gc_thumbs()
        return {"views": len(views), "removed": removed, "added": len(points),
                "profile": config.AUGMENT_PROFILE}

    def run_eval(self, extras=True):
        """Score the test set against the live memory; save JSON + Markdown.

        With `extras`, the same test set is also scored with the variants of
        each augmentation profile rebuilt from the taught views (none, basic,
        strong), so the profile can be chosen by measurement.
        Returns the report (dict) and the file stem under data/reports/.
        """
        import json
        from teachable_eye.evaluation import evaluate, profile_summary, to_markdown
        with self._lock:
            items = self.evalset.items()
            images = [self.evalset.image(it["id"]) for it in items]
            vectors = self.embed(images) if images else []
            for it, vec in zip(items, vectors):
                it["vector"] = vec
            points = self.memory.points()
            report = evaluate(points, items, self.memory.thresholds,
                              task=self.name, encoder=getattr(self, "encoder", None),
                              extras=extras)
            if extras and items:
                views = self._view_images()
                roots = {p["id"]: p for p in points if not p.get("parent")}
                base = [roots[vid] for vid, _, _ in views if vid in roots]
                report["profiles"] = {}
                for name in ("none", *AUGMENT_PROFILES):
                    pts = base + (self._variant_points(views, name) if name != "none" else [])
                    r = evaluate(pts, items, self.memory.thresholds, extras=False)
                    report["profiles"][name] = profile_summary(r, len(pts))
        for it in report["items"]:
            it.pop("vector", None)
        folder = config.DATA_DIR / "reports"
        folder.mkdir(parents=True, exist_ok=True)
        stem = "eval-{}-{}{}".format(
            self.name, time.strftime("%Y%m%d-%H%M%S"),
            f"-{report['encoder']}" if report.get("encoder") else "")
        (folder / f"{stem}.json").write_text(json.dumps(report, indent=1, ensure_ascii=False),
                                             encoding="utf-8")
        (folder / f"{stem}.md").write_text(to_markdown(report), encoding="utf-8")
        return report, stem

    # -- photo mode --------------------------------------------------------------

    supports_regions = False   # user-drawn boxes (see region)

    def region(self, box, still_id=None):
        """Photo mode: the user marked `box` (normalised) where the detector
        found nothing. Recognize it and keep its crop so it can be taught."""
        if not self.supports_regions:
            raise LookupError("custom boxes are not available for this mode")
        with self._lock:
            self._use_still(still_id)
            if self._still_frame is None:
                raise LookupError("take a photo first")
            from teachable_eye.detect import box_crop
            crop = box_crop(self._still_frame, box)
            if crop.size == 0:
                raise LookupError("that box is empty")
            if len(self._still_crops) >= MAX_STILL_CROPS:
                raise LookupError("too many boxes on this photo; take a new one")
            rid = 1000 + len(self._still_crops)
            self._still_crops[rid] = crop
            vec = self.embed([crop])[0]
            return dict({"id": rid, "box": [round(float(v), 4) for v in box],
                         "focus": False, "background": False, "manual": True},
                        **self.memory.recognize(vec).to_json())

    def follow(self, box, still_id=None):
        """Resume live view following `box` (normalised) from a photo.

        The photo is scaled to the live frame size first, so the tracker
        starts in the same pixel space it will be updated in.
        """
        if not self.supports_regions:
            raise LookupError("following a box is not available for this mode")
        with self._lock:
            self._use_still(still_id)
            if self._still_frame is None:
                raise LookupError("take a photo first")
            from teachable_eye.follow import FollowTrack, scaled
            frame = scaled(self._still_frame, self._live_wh)
            tid = self._next_follow
            self._next_follow += 1
            self._follow[tid] = FollowTrack(tid, frame, box)
            self._follow[tid].requery_now()
            return tid

    def unfollow(self, tid):
        with self._lock:
            return self._follow.pop(tid, None) is not None

    def still(self, frame):
        """Every detection in one photo with its decision (R14), no tracking."""
        with self._lock:
            self._still_frame = frame
            found = [_found(item) for item in self.detector.detect_once(frame)]
            # a far face keeps its row but no crop: nothing to teach (R57)
            self._still_crops = {i: crop for i, (_, crop, _, _) in enumerate(found)}
            sid = uuid.uuid4().hex
            self._stills[sid] = (self._still_frame, self._still_crops)
            while len(self._stills) > MAX_STILLS:
                self._stills.pop(next(iter(self._stills)))
            self.last_still_id = sid
            near = [i for i, (_, crop, far, _) in enumerate(found) if not far]
            vectors = self.embed([found[i][1] for i in near]) if near else []
            decided = {i: self.memory.recognize(v) for i, v in zip(near, vectors)}
            out = []
            for i, (box, _, far, weak) in enumerate(found):
                d = decided.get(i)
                if d is not None and weak:
                    d = at_most_uncertain(d)
                out.append(dict({"id": i, "box": box, "focus": False,
                                 "background": is_background(box), "far": far},
                                **(d.to_json() if d else PENDING)))
            return out

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

    def gc_thumbs(self):
        """Delete thumbnail and crop files no memory point refers to any more.

        Forgetting must remove the pictures too, not only the vectors
        (mission principle 5: people can be forgotten completely).
        """
        in_use = self.memory.thumbs_in_use()
        # other encoders' memories of this task may share the same pictures
        for other in self.sibling_memory_dirs():
            try:
                mem = TaskMemory(other, 1, self.name, self.memory.thresholds)
            except (SystemExit, Exception):
                return 0      # cannot see what it uses: keep every file (safe side)
            try:
                in_use |= mem.thumbs_in_use()
            finally:
                mem.close()
        removed = 0
        for folder in (self.thumbs, self.crops):
            for path in folder.glob("*.jpg"):
                if path.name not in in_use:
                    path.unlink(missing_ok=True)
                    removed += 1
        return removed

    def sibling_memory_dirs(self):
        """Memories of this task kept for other encoders (objects only)."""
        return []

    def _save_crop(self, crop):
        h, w = crop.shape[:2]
        scale = min(1.0, CROP_SIZE / max(h, w))
        img = crop if scale == 1.0 else cv2.resize(
            crop, (max(1, int(w * scale)), max(1, int(h * scale))),
            interpolation=cv2.INTER_AREA)
        name = f"{uuid.uuid4().hex}.jpg"
        cv2.imwrite(str(self.crops / name), img, [cv2.IMWRITE_JPEG_QUALITY, 92])
        return name

    def _save_thumb(self, crop):
        name = f"{uuid.uuid4().hex}.jpg"
        cv2.imwrite(str(self.thumbs / name), self._small(crop),
                    [cv2.IMWRITE_JPEG_QUALITY, 85])
        return name


def object_memory_dir(encoder):
    """Each encoder has its own memory: vectors of different models are not
    comparable. clip-b32 keeps the original folder name."""
    base = config.DATA_DIR / "memory"
    return base / "objects" if encoder == "clip-b32" else base / f"objects-{encoder}"


class ObjectsTask(VisualTask):
    """YOLOE + tracking → masked crop → image encoder → memory (R7, R8)."""

    name = "objects"
    supports_regions = True

    def __init__(self, detector=None, embed=None, memory=None):
        from teachable_eye import encoders
        if detector is None:
            from teachable_eye.detect import Detector
            detector = Detector()
        self.encoder = config.OBJECT_ENCODER
        self._memory_dir = object_memory_dir(self.encoder)
        super().__init__(
            detector, embed or encoders.embed_crops,
            memory or TaskMemory(object_memory_dir(self.encoder),
                                 encoders.encoder_dim(self.encoder),
                                 self.name, config.OBJECTS))

    def sibling_memory_dirs(self):
        base = config.DATA_DIR / "memory"
        return [d for d in base.glob("objects*")
                if d.is_dir() and d.resolve() != self._memory_dir.resolve()
                and (d / "edge_config.json").exists()]


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

    # A box drawn on a photo means "there is a face here": look for one in it
    # (larger, more sensitive) and snap the box to it. Faces must be aligned
    # from their landmarks, so a plain crop of the box would not do.
    supports_regions = True

    def region(self, box, still_id=None):
        from teachable_eye.faces import find_face, identity_band
        with self._lock:
            self._use_still(still_id)
            if self._still_frame is None:
                raise LookupError("take a photo first")
            found = find_face(self._still_frame, box)
            if found is None:
                raise LookupError("no face found in that box")
            face_box, aligned = found
            if len(self._still_crops) >= MAX_STILL_CROPS:
                raise LookupError("too many boxes on this photo; take a new one")
            rid = 1000 + len(self._still_crops)
            # the same size rule as the live detector (R57): the user may say
            # "there is a face", not "I know who it is"
            h, w = self._still_frame.shape[:2]
            band = identity_band(min((face_box[2] - face_box[0]) * w,
                                     (face_box[3] - face_box[1]) * h))
            row = {"id": rid, "box": face_box, "focus": False,
                   "background": False, "manual": True, "far": band == "far"}
            if band == "far":
                self._still_crops[rid] = None
                return dict(row, **PENDING)
            self._still_crops[rid] = aligned
            d = self.memory.recognize(self.embed([aligned])[0])
            return dict(row, **(at_most_uncertain(d) if band == "weak" else d).to_json())

    def follow(self, box, still_id=None):
        raise LookupError("faces are followed by the face detector itself")
