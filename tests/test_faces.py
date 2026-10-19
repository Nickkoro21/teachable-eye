"""A27: faces from further away (R57). Synthetic data only: the YuNet
detector is replaced by a fake that returns rows we choose, SFace by a fake
aligner, and the people task runs on a fake tracker."""
import numpy as np
import pytest

from teachable_eye import config, faces
from teachable_eye.detect import Track
from teachable_eye.memory import TaskMemory
from teachable_eye.policy import KNOWN, UNCERTAIN
from teachable_eye.tasks import PENDING, PeopleTask

YUNET_READY = (faces.model_dir("opencv") / faces.YUNET[0]).exists()


def row(x, y, w, h, score):
    """One YuNet row: box, 5 landmarks (eyes, nose, mouth corners), score."""
    r = np.zeros(15, np.float32)
    r[:4] = (x, y, w, h)
    r[4:14] = (x + w * 0.3, y + h * 0.4, x + w * 0.7, y + h * 0.4, x + w * 0.5, y + h * 0.6,
               x + w * 0.35, y + h * 0.8, x + w * 0.65, y + h * 0.8)
    r[14] = score
    return r


class FakeYuNet:
    """Returns the given rows for any image; remembers the input size."""

    def __init__(self, rows):
        self.rows, self.size = rows, None

    def setInputSize(self, size):
        self.size = size

    def detect(self, img):
        assert (img.shape[1], img.shape[0]) == self.size
        return 0, (np.stack(self.rows) if self.rows else None)


class FakeSFace:
    def __init__(self):
        self.aligned = []

    def alignCrop(self, frame, r):
        self.aligned.append(r.copy())
        return np.full((112, 112, 3), 90, np.uint8)


@pytest.fixture
def tracker(monkeypatch):
    if not YUNET_READY:
        pytest.skip("YuNet model not downloaded")
    sface = FakeSFace()
    monkeypatch.setattr(faces, "_sface", lambda: sface)
    t = faces.FaceTracker()
    t.sface = sface
    return t


# -- the rules themselves ------------------------------------------------------

def test_size_aware_score_floor():
    assert faces.score_floor(faces.SURE_PX) == faces.SCORE == 0.80
    assert faces.score_floor(faces.SURE_PX - 1) == faces.SCORE_FAR == 0.60
    assert faces.SCORE_FAR < faces.SCORE


def test_identity_band_boundaries():
    assert faces.identity_band(faces.NAME_PX - 0.5) == "far"
    assert faces.identity_band(faces.NAME_PX) == "weak"
    assert faces.identity_band(faces.SURE_PX - 0.5) == "weak"
    assert faces.identity_band(faces.SURE_PX) == "ok"
    assert faces.MIN_FACE_PX < faces.NAME_PX < faces.SURE_PX


def test_guard_is_not_weaker_than_the_live_detector(monkeypatch):
    """has_face: a lower floor than any live face needs, no size floor, and
    at least the live detector's resolution."""
    assert faces.GUARD_SCORE <= faces.SCORE_FAR
    seen = {}

    def guard(img):
        seen["size"] = img.shape[:2]
        return [row(5, 5, 6, 7, faces.GUARD_SCORE)]        # a 6 px face counts
    monkeypatch.setattr(faces, "_guard_detect", guard)
    assert faces.has_face(np.zeros((1080, 1920, 3), np.uint8)) is True
    assert max(seen["size"]) == faces.DETECT_SIDE >= 960    # no second downscale
    assert faces.has_face(np.zeros((300, 400, 3), np.uint8)) is True
    assert faces.REGION_SIDE == 640                           # R48 unchanged


# -- the detector path ---------------------------------------------------------

def test_small_faces_use_the_lower_floor_and_large_ones_the_high_one(tracker):
    tracker.detector = FakeYuNet([
        row(10, 10, 30, 36, 0.70),       # small, 0.70 >= 0.60: kept, far
        row(100, 10, 80, 90, 0.70),      # large, 0.70 < 0.80: dropped
        row(300, 10, 80, 90, 0.85),      # large, sure
        row(500, 10, 44, 52, 0.65),      # 44 px: kept, weak
        row(700, 10, 12, 14, 0.95),      # under MIN_FACE_PX: dropped
    ])
    found = tracker._faces(np.zeros((540, 960, 3), np.uint8))
    bands = sorted((round(b[0]), band) for b, _, _, band in found)
    assert bands == [(10, "far"), (300, "ok"), (500, "weak")]
    assert [a is None for b, a, _, _ in found if b[0] == 10] == [True]   # no crop when far
    assert len(tracker.sface.aligned) == 2                                # only the named ones


def test_live_frame_is_detected_as_received_and_photos_mapped_back(tracker):
    """960 px live frames are not resized; a 1920 px photo is detected at
    1280 px and boxes + landmarks come back in photo pixels."""
    tracker.detector = FakeYuNet([row(100, 50, 60, 70, 0.9)])
    found = tracker._faces(np.zeros((540, 960, 3), np.uint8))
    assert tracker.detector.size == (960, 540)
    assert found[0][0] == [100.0, 50.0, 160.0, 120.0]

    tracker.sface.aligned.clear()
    tracker.detector = FakeYuNet([row(100, 50, 60, 70, 0.9)])
    found = tracker._faces(np.zeros((1080, 1920, 3), np.uint8))
    assert tracker.detector.size == (1280, 720)
    assert found[0][0] == pytest.approx([150.0, 75.0, 240.0, 180.0])   # x1.5 back to photo pixels
    r = tracker.sface.aligned[0]
    assert (r[2], r[3]) == pytest.approx((90, 105))          # width/height scaled too
    assert r[4] == pytest.approx((100 + 60 * 0.3) * 1.5)    # a landmark, in photo pixels
    assert r[14] == pytest.approx(0.9)                       # the score is not scaled


def test_far_tracks_keep_no_crop_and_detect_once_flags(tracker):
    tracker.detector = FakeYuNet([row(10, 10, 30, 36, 0.7), row(300, 10, 80, 90, 0.9)])
    frame = np.zeros((540, 960, 3), np.uint8)
    for i in range(3):
        tracks = tracker.process(frame, now=100.0 + i)
    far = [t for t in tracks if t.far]
    assert len(tracks) == 2 and len(far) == 1 and far[0].crop is None
    assert [t.weak for t in tracks] == [False, False]
    once = tracker.detect_once(frame)
    assert {f["far"] for _, c, f in once} == {True, False}
    assert all((c is None) == f["far"] for _, c, f in once)


# -- the people task -----------------------------------------------------------

class SizedTracker:
    """One face track, id 7, whose size band is set by the test."""

    def __init__(self):
        self.tracks, self.band = {}, "ok"

    def reset(self):
        self.tracks.clear()

    def process(self, frame, now):
        t = self.tracks.setdefault(7, Track(7))
        t.frames, t.last_seen = 4, now
        t.box, t.frame_wh = [10, 10, 70, 80], (960, 540)
        t.far, t.weak = self.band == "far", self.band == "weak"
        t.crop = None if t.far else np.full((112, 112, 3), 200, np.uint8)
        return [t]

    def detect_once(self, frame):
        face = np.full((112, 112, 3), 200, np.uint8)
        return [([0.1, 0.1, 0.3, 0.3], None, {"far": True, "weak": False}),
                ([0.5, 0.1, 0.7, 0.3], face, {"far": False, "weak": True})]


def embed(crops):
    return [[float(c.mean() / 255), 1.0, 0.0, 0.0] for c in crops]


@pytest.fixture
def people(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    mem = TaskMemory(tmp_path / "p", 4, "people", config.TaskThresholds(0.4, 0.06))
    task = PeopleTask(detector=SizedTracker(), embed=embed, memory=mem)
    mem.teach(embed([np.full((112, 112, 3), 200, np.uint8)])[0], "person-a")
    yield task
    mem.close()


def test_far_face_gets_no_name_and_cannot_be_taught(people):
    frame = np.zeros((540, 960, 3), np.uint8)
    people.detector.band = "far"
    r = people.process(frame, now=10.0)[0]
    assert r["far"] is True and r["decision"] == "pending" and r["label"] is None
    with pytest.raises(LookupError, match="too far"):
        people.hold(7)
    with pytest.raises(LookupError, match="too far"):
        people.start_burst(7)
    assert people.confirm(7, "person-a") is None


def test_weak_face_is_uncertain_at_most_and_a_near_one_known(people):
    frame = np.zeros((540, 960, 3), np.uint8)
    people.detector.band = "weak"
    r = people.process(frame, now=10.0)[0]
    assert r["far"] is False and r["decision"] == UNCERTAIN
    assert r["label"] is None and r["guess"] == "person-a"
    people.detector.band = "ok"
    r = people.process(frame, now=10.1)[0]           # no new query: same evidence
    assert r["decision"] == KNOWN and r["label"] == "person-a"
    # walking away forgets the name; coming back asks memory again
    people.detector.band = "far"
    assert people.process(frame, now=10.2)[0]["decision"] == "pending"
    people.detector.band = "ok"
    assert people.process(frame, now=13.0)[0]["decision"] == KNOWN


def test_photo_rows_and_drawn_boxes_follow_the_same_rule(people, monkeypatch):
    rows = people.still(np.zeros((540, 960, 3), np.uint8))
    assert [r["far"] for r in rows] == [True, False]
    assert rows[0]["decision"] == "pending" and set(PENDING) <= set(rows[0])
    assert rows[1]["decision"] == UNCERTAIN and rows[1]["guess"] == "person-a"
    with pytest.raises(LookupError, match="too far"):
        people.hold(0, from_still=True)
    assert people.hold(1, from_still=True)
    # a box the user draws round a small face snaps to it but gets no name
    face = np.full((112, 112, 3), 200, np.uint8)
    monkeypatch.setattr(faces, "find_face", lambda frame, box: ([0.1, 0.1, 0.13, 0.16], face))
    r = people.region([0.05, 0.05, 0.2, 0.2])
    assert r["far"] is True and r["decision"] == "pending" and r["box"] == [0.1, 0.1, 0.13, 0.16]
    with pytest.raises(LookupError, match="too far"):
        people.hold(r["id"], from_still=True)
    monkeypatch.setattr(faces, "find_face", lambda frame, box: ([0.1, 0.1, 0.2, 0.3], face))
    r = people.region([0.05, 0.05, 0.3, 0.4])              # 96 px: the full policy
    assert r["far"] is False and r["decision"] == KNOWN
