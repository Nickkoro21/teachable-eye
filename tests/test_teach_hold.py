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
    from teachable_eye.tasks import augmentations
    expected = sorted(fn.__name__ for fn in augmentations("objects"))
    view = task.memory.labels()[0]["examples"][0]
    names = sorted(v["aug"] for v in view["variants"])
    assert names == expected and {"darker", "flip", "zoom_center"} <= set(names)
    thumbs = {view["thumb"]} | {v["thumb"] for v in view["variants"]}
    assert len(thumbs) == len(expected) + 1                  # each has its own
    assert all((task.thumbs / name).exists() for name in thumbs)
    # one variant can go on its own
    task.memory.forget_example(view["variants"][0]["id"])
    task.gc_thumbs()
    assert len(task.memory.labels()[0]["examples"][0]["variants"]) == len(expected) - 1
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
    task.still(np.zeros((400, 400, 3), np.uint8))   # the face below is 80 px: a sure size (R57)
    monkeypatch.setattr(faces, "find_face", lambda frame, box: None)
    with pytest.raises(LookupError, match="no face"):
        task.region([0.1, 0.1, 0.5, 0.5])
    face = np.full((112, 112, 3), 120, np.uint8)
    monkeypatch.setattr(faces, "find_face", lambda frame, box: ([0.2, 0.2, 0.4, 0.45], face))
    row = task.region([0.1, 0.1, 0.5, 0.5])
    assert row["box"] == [0.2, 0.2, 0.4, 0.45] and row["manual"]
    assert task.teach_held(task.hold(row["id"], from_still=True), "person-a")
    from teachable_eye.tasks import augmentations
    assert mem.count() == 1 + len(augmentations("people"))   # the face + its variants
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


def test_augmentation_profiles_keep_shapes_sane():
    """Every variant is a valid picture; people never get crops of the face."""
    from teachable_eye.tasks import AUGMENT_PROFILES
    crop = np.random.default_rng(0).integers(0, 255, (120, 90, 3), dtype=np.uint8)
    for profile in AUGMENT_PROFILES.values():
        for task, fns in profile.items():
            for fn in fns:
                out = fn(crop)
                assert out.ndim == 3 and out.shape[2] == 3 and min(out.shape[:2]) >= 20, fn
                if task == "people":                 # aligned faces keep their size
                    assert out.shape == crop.shape, fn
    names = {fn.__name__ for fn in AUGMENT_PROFILES["strong"]["people"]}
    assert not names & {"zoom_center", "part_tl", "part_tr", "part_bl", "part_br"}


def test_refresh_variants_rebuilds_them_with_the_new_profile(task, monkeypatch):
    """Switching to the strong profile must not need any re-teaching."""
    from teachable_eye.tasks import augmentations
    monkeypatch.setattr(config, "AUGMENT_PROFILE", "basic")
    task.process(np.zeros((100, 100, 3), np.uint8), now=1.0)
    task.teach_held(task.hold(7), "bag")
    assert task.memory.count() == 1 + len(augmentations("objects", "basic"))
    old_thumbs = set(task.thumbs.glob("*.jpg"))
    monkeypatch.setattr(config, "AUGMENT_PROFILE", "strong")
    res = task.refresh_variants()
    strong = len(augmentations("objects", "strong"))
    assert res == {"views": 1, "removed": 3, "added": strong, "profile": "strong"}
    view = task.memory.labels()[0]["examples"][0]
    assert len(view["variants"]) == strong
    assert task.memory.count() == 1 + strong
    new_thumbs = set(task.thumbs.glob("*.jpg"))
    assert len(new_thumbs) == 1 + strong                 # old variant thumbs gone
    assert len(old_thumbs & new_thumbs) == 1             # only the view's own thumb


def test_two_photos_never_mix_their_boxes(task):
    """The phone and the PC may each have a photo open (review 2026-10-17)."""
    task.detector.detect_once = lambda frame: [([0.1, 0.1, 0.3, 0.3], frame[:20, :20].copy())]
    first = np.full((100, 100, 3), 30, np.uint8)
    task.still(first)
    sid_a = task.last_still_id
    task.still(np.full((100, 100, 3), 220, np.uint8))     # another client's photo
    hid = task.hold(0, from_still=True, still_id=sid_a)
    assert task.held_crops(hid)[0].mean() == 30              # photo A's crop, not B's
    assert task.held_crops(task.hold(0, from_still=True))[0].mean() == 220   # latest
    with pytest.raises(LookupError, match="expired"):
        task.hold(0, from_still=True, still_id="0" * 32)
    for _ in range(6):                                       # only the last few are kept
        task.still(first)
    with pytest.raises(LookupError, match="expired"):
        task.hold(0, from_still=True, still_id=sid_a)


def test_a_failed_save_keeps_the_selection(task, monkeypatch):
    """A GPU or disk error must not throw away a (long) video teach."""
    task.process(np.zeros((100, 100, 3), np.uint8), now=1.0)
    hid = task.hold(7)

    def broken(points):
        raise RuntimeError("CUDA out of memory")
    monkeypatch.setattr(task.memory, "teach_many", broken)
    with pytest.raises(RuntimeError):
        task.teach_held(hid, "cup")
    monkeypatch.undo()
    assert task.teach_held(hid, "cup")                       # Save again works


def test_runner_ups_survive_a_label_that_fills_the_pool(tmp_path, monkeypatch):
    """One video-taught label can fill all looked-at points (review #4)."""
    from teachable_eye import memory as memory_mod
    monkeypatch.setattr(memory_mod, "CANDIDATE_POOL", 5)
    mem = TaskMemory(tmp_path / "m2", 4, "objects", config.TaskThresholds(0.9, 0.05))
    for i in range(10):
        mem.teach([1.0, 0.01 * i, 0.0, 0.0], "mug")
    mem.teach([0.7, 0.7, 0.0, 0.0], "cup")
    mem.teach([0.0, 0.0, 1.0, 0.0], "hat")
    labels = [c[0] for c in mem.recognize([1.0, 0.0, 0.0, 0.0]).candidates]
    assert labels[:3] == ["mug", "cup", "hat"]
    mem.close()


def test_one_tap_confirm_teaches_only_the_guess_still_shown(task):
    """'Yes, it is X' re-checks the guess before writing anything."""
    from teachable_eye.policy import UNCERTAIN, Decision
    task.process(np.zeros((100, 100, 3), np.uint8), now=1.0)
    task._shown[7] = Decision(UNCERTAIN, None, "cup", 0.85, [])
    assert task.confirm(7, "hat") is None                     # the guess moved on
    assert task.memory.count() == 0
    assert task.confirm(7, "cup")                             # taught as the guess
    assert task.memory.labels()[0]["label"] == "cup"
    # on a photo: the crop must still come out nearest to the guess
    task.still(np.zeros((100, 100, 3), np.uint8))
    assert task.confirm(0, "cup", from_still=True)
    assert task.confirm(0, "hat", from_still=True) is None


def test_confirm_endpoint_reports_a_moved_guess(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from teachable_eye.server import create_app
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    mem = TaskMemory(tmp_path / "m3", 4, "objects", config.TaskThresholds(0.9, 0.05))
    t = ObjectsTask(detector=FakeDetector(), embed=fake_embed, memory=mem)
    client = TestClient(create_app({"objects": t}))
    t.process(np.zeros((100, 100, 3), np.uint8), now=1.0)
    res = client.post("/api/confirm", json={"task": "objects", "id": 7, "label": "cup"})
    assert res.status_code == 409 and "nothing was saved" in res.json()["error"]
    mem.close()
