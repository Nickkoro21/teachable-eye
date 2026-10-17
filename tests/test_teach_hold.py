"""TEACH holds the crop at press time (feedback from the second phone test:
the object was lost while the user typed its name, so Save failed)."""
import pathlib

import numpy as np
import pytest

from teachable_eye import config
from teachable_eye.detect import Track
from teachable_eye.memory import TaskMemory
from teachable_eye.policy import KNOWN
from teachable_eye.tasks import ObjectsTask


class FakeDetector:
    """One object with id 7 while `visible`, nothing otherwise."""

    def __init__(self):
        self.tracks = {}
        self.visible = True

    def reset(self):
        self.tracks.clear()

    def process(self, frame, now):
        if not self.visible:
            self.tracks.clear()
            return []
        t = self.tracks.setdefault(7, Track(7))
        t.frames, t.last_seen = 4, now
        t.box, t.frame_wh = [10, 10, 30, 30], (100, 100)
        t.crop = np.full((20, 20, 3), 200, np.uint8)
        return [t]

    def detect_once(self, frame):
        return [([0.1, 0.1, 0.3, 0.3], np.full((20, 20, 3), 50, np.uint8))]


def fake_embed(crops):
    return [[float(c.mean() / 255), 1.0, 0.0, 0.0] for c in crops]


@pytest.fixture
def task(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    mem = TaskMemory(tmp_path / "m", 4, "objects", config.TaskThresholds(0.9, 0.05))
    t = ObjectsTask(detector=FakeDetector(), embed=fake_embed, memory=mem)
    yield t
    mem.close()


def test_hold_survives_losing_the_object(task):
    task.process(np.zeros((100, 100, 3), np.uint8), now=1.0)
    hid = task.hold(7)
    task.detector.visible = False                  # phone moved while typing
    task.process(np.zeros((100, 100, 3), np.uint8), now=9.0)
    assert task.teach_held(hid, "cup")
    assert task.memory.recognize(fake_embed([np.full((2, 2, 3), 200, np.uint8)])[0]).decision == KNOWN


def test_hold_is_single_use_and_bad_name_keeps_it(task):
    task.process(np.zeros((100, 100, 3), np.uint8), now=1.0)
    hid = task.hold(7)
    with pytest.raises(ValueError):
        task.teach_held(hid, "   ")                 # empty name: hold kept
    task.teach_held(hid, "cup")
    with pytest.raises(LookupError):
        task.teach_held(hid, "cup")                 # already used


def test_hold_unknown_track(task):
    with pytest.raises(LookupError):
        task.hold(99)


def test_teach_from_photo(task):
    rows = task.still(np.zeros((100, 100, 3), np.uint8))
    hid = task.hold(rows[0]["id"], from_still=True)
    assert task.teach_held(hid, "mug")
    assert task.memory.labels()[0]["label"] == "mug"


class MovingDetector(FakeDetector):
    """Track 7 whose look changes every frame (the user walks around it)."""

    def __init__(self):
        super().__init__()
        self.shade = 0

    def process(self, frame, now):
        rows = super().process(frame, now)
        self.shade = (self.shade + 40) % 256
        self.tracks[7].crop = np.full((20, 20, 3), self.shade, np.uint8)
        return rows


def angle_embed(crops):
    # each shade maps to a different direction, so views are distinct
    out = []
    for c in crops:
        a = float(c.mean()) / 255 * 3.0
        out.append([float(np.cos(a)), float(np.sin(a)), 0.0, 0.0])
    return out


def test_burst_collects_distinct_views(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    mem = TaskMemory(tmp_path / "m", 4, "objects", config.TaskThresholds(0.9, 0.05))
    task = ObjectsTask(detector=MovingDetector(), embed=angle_embed, memory=mem)
    frame = np.zeros((100, 100, 3), np.uint8)
    task.process(frame, now=1.0)
    bid = task.start_burst(7, seconds=30)
    for i in range(12):
        task.process(frame, now=2.0 + i * 0.2)
    assert task.burst_status(bid)["views"] >= 3
    hid, views = task.finish_burst(bid)
    assert len(task.hold_preview(hid)) == views
    task.teach_held(hid, "teapot")
    assert task.memory.labels()[0]["count"] == views
    mem.close()


def test_burst_still_view_is_one_view(task):
    frame = np.zeros((100, 100, 3), np.uint8)
    task.process(frame, now=1.0)
    bid = task.start_burst(7, seconds=30)
    for i in range(8):                        # identical crops every frame
        task.process(frame, now=2.0 + i * 0.2)
    _, views = task.finish_burst(bid)
    assert views == 1


def test_user_drawn_region_on_a_photo(task):
    """Small things the detector misses (a gum on grass) can be marked."""
    frame = np.full((200, 200, 3), 90, np.uint8)
    frame[95:105, 95:105] = 220
    with pytest.raises(LookupError):
        task.region([0.4, 0.4, 0.6, 0.6])           # no photo yet
    task.still(frame)
    row = task.region([0.45, 0.45, 0.55, 0.55])
    assert row["manual"] and row["decision"] == "unknown"
    hid = task.hold(row["id"], from_still=True)
    task.teach_held(hid, "gum")
    assert task.memory.labels()[0]["label"] == "gum"


VIT = (pathlib.Path(__file__).resolve().parents[1] / "data" / "models" / "opencv"
       / "object_tracking_vittrack_2023sep.onnx")


@pytest.mark.skipif(not VIT.exists(), reason="VitTrack model not downloaded")
def test_follow_a_user_box_after_pause(task, monkeypatch):
    """Pause, fix the box, resume: the tracker follows the user's box."""
    from teachable_eye import follow
    monkeypatch.setattr(follow, "_model", lambda: str(VIT))
    task.detector.visible = False                 # the detector sees nothing
    rng = np.random.default_rng(1)
    bg = rng.integers(0, 60, (240, 320, 3), dtype=np.uint8)

    def frame(x):
        f = bg.copy()
        f[100:130, x:x + 30] = (40, 200, 240)
        return f

    task.process(frame(50), now=1.0)              # live, sets the live size
    task.still(frame(50))                         # pause
    tid = task.follow([50 / 320, 100 / 240, 80 / 320, 130 / 240])
    rows = []
    for i in range(1, 8):                         # resume: it moves right
        rows = task.process(frame(50 + i * 6), now=1.0 + i * 0.2)
    row = next(r for r in rows if r["id"] == tid)
    assert row["manual"]
    assert abs(row["box"][0] - (50 + 7 * 6) / 320) < 0.04
    hid = task.hold(tid)
    assert task.teach_held(hid, "gum")


def test_variants_have_own_thumbs_and_go_with_their_view(task):
    """Augmented variants are visible per view; deleting a view deletes them
    and their thumbnail files (people must be forgettable completely)."""
    task.process(np.zeros((100, 100, 3), np.uint8), now=1.0)
    task.teach_held(task.hold(7), "bag")
    view = task.memory.labels()[0]["examples"][0]
    names = sorted(v["aug"] for v in view["variants"])
    assert names == ["darker", "flip", "zoom_center"]
    thumbs = {view["thumb"]} | {v["thumb"] for v in view["variants"]}
    assert len(thumbs) == 4                                  # each has its own
    assert all((task.thumbs / name).exists() for name in thumbs)
    # one variant can go on its own
    task.memory.forget_example(view["variants"][0]["id"])
    task.gc_thumbs()
    assert len(task.memory.labels()[0]["examples"][0]["variants"]) == 2
    # the main view takes the rest with it, files included
    task.memory.forget_example(view["id"])
    assert task.gc_thumbs() >= 3
    assert task.memory.count() == 0
    assert not any(task.thumbs.glob("*.jpg"))


def test_gc_keeps_pictures_another_encoders_memory_uses(tmp_path, monkeypatch):
    """Switching encoders keeps one memory per encoder; they share thumbnails.
    Forgetting in one must not delete files the other still refers to."""
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    from teachable_eye.tasks import object_memory_dir
    monkeypatch.setattr(config, "OBJECT_ENCODER", "dinov2-large")
    other = TaskMemory(object_memory_dir("clip-b32"), 4, "objects",
                       config.TaskThresholds(0.9, 0.05))
    mem = TaskMemory(object_memory_dir("dinov2-large"), 4, "objects",
                     config.TaskThresholds(0.9, 0.05))
    task = ObjectsTask(detector=FakeDetector(), embed=fake_embed, memory=mem)
    shared = task.thumbs / ("a" * 32 + ".jpg")
    shared.write_bytes(b"x")
    other.teach([1, 0, 0, 0], "bag", thumb=shared.name)
    other.close()
    pid = mem.teach([1, 0, 0, 0], "bag", thumb=shared.name)
    mem.forget_example(pid)
    task.gc_thumbs()
    assert shared.exists()              # still used by the clip-b32 memory
    mem.close()


def test_encoder_registry_dims():
    from teachable_eye.encoders import ENCODERS, encoder_dim
    assert encoder_dim("dinov2-large") == 2048 and encoder_dim("clip-b32") == 512
    assert set(config.DEFAULT_OBJECT_BANDS) == set(ENCODERS)


def test_people_box_drawn_on_a_photo_snaps_to_a_face(tmp_path, monkeypatch):
    """A box drawn on a face is searched for a face (aligned from its
    landmarks); with no face in it the user is told so."""
    from teachable_eye import faces
    from teachable_eye.tasks import PeopleTask
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    mem = TaskMemory(tmp_path / "p", 4, "people", config.TaskThresholds(0.4, 0.06))
    task = PeopleTask(detector=FakeDetector(), embed=fake_embed, memory=mem)
    with pytest.raises(LookupError, match="photo"):
        task.region([0.1, 0.1, 0.5, 0.5])
    task.still(np.zeros((100, 100, 3), np.uint8))
    monkeypatch.setattr(faces, "find_face", lambda frame, box: None)
    with pytest.raises(LookupError, match="no face"):
        task.region([0.1, 0.1, 0.5, 0.5])
    face = np.full((112, 112, 3), 120, np.uint8)
    monkeypatch.setattr(faces, "find_face", lambda frame, box: ([0.2, 0.2, 0.4, 0.45], face))
    row = task.region([0.1, 0.1, 0.5, 0.5])
    assert row["box"] == [0.2, 0.2, 0.4, 0.45] and row["manual"]
    assert task.teach_held(task.hold(row["id"], from_still=True), "person-a")
    assert mem.count() == 3                       # the face + mirror + darker
    with pytest.raises(LookupError):
        task.follow([0.1, 0.1, 0.5, 0.5])
    mem.close()


def test_burst_records_the_whole_time_and_keeps_the_most_different_views():
    """A turning face gives many distinct views: the burst must not stop at
    the first ten, and the kept views must span the whole turn."""
    from teachable_eye.tasks import BURST_KEEP, Burst
    crop = np.full((20, 20, 3), 128, np.uint8)
    b = Burst(7, seconds=30)
    for i in range(40):                      # a head turning 180 degrees
        a = np.pi * i / 39
        b.offer(crop, [np.cos(a), np.sin(a), 0.0, 0.0])
    assert not b.done                        # no early stop any more
    kept = b.select()
    frames = b.status()["frames"]            # near-copies of the last frame are skipped
    assert 15 <= frames <= 40
    assert len(kept) >= 8
    assert kept[0] == 0 and kept[-1] == frames - 1   # both ends of the turn are kept
    rng = np.random.default_rng(0)           # many very different views:
    b = Burst(7, seconds=30)                 # the cap is BURST_KEEP, not 10
    for _ in range(40):
        b.offer(crop, rng.normal(size=64))
    assert len(b.select()) == BURST_KEEP


def test_long_burst_is_thinned_evenly_not_cut(monkeypatch):
    """A long recording keeps covering its whole length when the pool fills."""
    from teachable_eye import tasks
    monkeypatch.setattr(tasks, "BURST_POOL", 20)
    b = tasks.Burst(7, seconds=30)
    rng = np.random.default_rng(1)
    big = np.full((800, 600, 3), 90, np.uint8)
    for _ in range(100):
        b.offer(big, rng.normal(size=32))
    assert len(b.crops) <= 20
    assert max(b.crops[0].shape[:2]) <= tasks.CROP_SIZE    # stored small
    assert b.offered == 100
