"""TEACH holds the crop at press time (feedback from the second phone test:
the object was lost while the user typed its name, so Save failed)."""
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
