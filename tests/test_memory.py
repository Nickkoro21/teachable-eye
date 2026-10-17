"""A1-A5: memory core, decision policy and per-track vote (synthetic vectors)."""
import numpy as np
import pytest

from teachable_eye.config import TaskThresholds
from teachable_eye.memory import TaskMemory
from teachable_eye.policy import KNOWN, UNCERTAIN, UNKNOWN, Decision
from teachable_eye.vote import LabelVote

BANDS = TaskThresholds(threshold=0.90, margin=0.05)
DIM = 16


def unit(v):
    v = np.asarray(v, dtype=np.float32)
    return v / np.linalg.norm(v)


def axis(i):
    v = np.zeros(DIM, np.float32)
    v[i] = 1.0
    return v


def toward(base, other, cos):
    """A unit vector with cosine `cos` to unit `base`, rotated toward `other`."""
    o = other - base * float(base @ other)
    o = o / np.linalg.norm(o)
    return unit(cos * base + np.sqrt(1 - cos * cos) * o)


@pytest.fixture
def mem(tmp_path):
    m = TaskMemory(tmp_path / "shard", DIM, "objects", BANDS)
    yield m
    m.close()


def test_a1_teach_and_recognize_known(mem):
    mem.teach(axis(0), "Hat")
    mem.teach(axis(1), "microphone")
    d = mem.recognize(toward(axis(0), axis(5), 0.97))
    assert d.decision == KNOWN and d.label == "hat"
    assert d.neighbours[0].label == "hat"
    d = mem.recognize(toward(axis(1), axis(6), 0.95))
    assert d.decision == KNOWN and d.label == "microphone"


def test_a2_uncertain_unknown_and_empty(mem):
    assert mem.recognize(axis(0)).decision == UNKNOWN          # empty memory
    mem.teach(axis(0), "hat")
    d = mem.recognize(toward(axis(0), axis(5), 0.87))
    assert d.decision == UNCERTAIN and d.guess == "hat" and d.label is None
    d = mem.recognize(toward(axis(0), axis(5), 0.30))
    assert d.decision == UNKNOWN and d.label is None and d.guess is None


def test_a3_forget_and_rename(mem):
    a = mem.teach(axis(0), "hat")
    mem.teach(axis(2), "hat")
    mem.teach(axis(1), "mic")
    assert mem.forget_example(a) == 1
    assert mem.count() == 2
    assert mem.rename("mic", "HAT") == 1                       # merge
    assert [g["label"] for g in mem.labels()] == ["hat"]
    assert mem.forget_label("hat") == 2
    assert mem.count() == 0
    assert mem.recognize(axis(0)).decision == UNKNOWN


def test_a4_persists_across_reopen(tmp_path):
    m = TaskMemory(tmp_path / "s", DIM, "objects", BANDS)
    m.teach(axis(3), "cap", thumb="t1.jpg")
    m.close()
    m = TaskMemory(tmp_path / "s", DIM, "objects", BANDS)
    d = m.recognize(axis(3))
    assert d.decision == KNOWN and d.label == "cap"
    assert d.neighbours[0].thumb == "t1.jpg"
    m.close()


def test_a4_wipe(mem):
    mem.teach(axis(0), "person-a")
    mem.wipe()
    assert mem.count() == 0


def _d(kind, label=None):
    if kind == KNOWN:
        return Decision(KNOWN, label, None, 0.95)
    if kind == UNCERTAIN:
        return Decision(UNCERTAIN, None, label, 0.87)
    return Decision(UNKNOWN, None, None, 0.2)


def test_a5_vote_does_not_flicker():
    v = LabelVote(window=3)
    assert v.add(_d(KNOWN, "hat")).label == "hat"
    assert v.add(_d(KNOWN, "hat")).label == "hat"
    # one stray answer cannot flip a 2-of-3 majority
    assert v.add(_d(KNOWN, "mic")).label == "hat"
    assert v.add(_d(UNKNOWN)).label == "hat"          # hat, mic, unknown -> no majority, keep
    assert v.add(_d(UNKNOWN)).decision == UNKNOWN     # mic, unknown, unknown -> unknown


def test_augmented_variants_are_hidden_and_go_with_their_view(mem):
    view = mem.teach(axis(0), "bag", thumb="t.jpg")
    for i, name in ((5, "zoom_center"), (6, "flip")):
        mem.teach(toward(axis(0), axis(i), 0.95), "bag", thumb="t.jpg",
                  parent=view, aug=name)
    assert mem.labels()[0]["count"] == 1                 # variants not listed
    d = mem.recognize(toward(axis(0), axis(5), 0.97), k=3)
    assert d.label == "bag"
    assert [n.id for n in d.neighbours] == [view]        # one view, best score
    assert mem.forget_example(view) == 1
    assert mem.count() == 0                              # variants deleted too


def test_teach_many_is_one_write_with_variants(mem):
    ids = mem.teach_many([
        {"id": "00000000-0000-0000-0000-000000000001", "vector": axis(0), "label": "Hat"},
        {"vector": axis(1), "label": "hat", "parent": "00000000-0000-0000-0000-000000000001",
         "aug": "flip"},
        {"vector": axis(2), "label": "cup"},
    ])
    assert ids[0] == "00000000-0000-0000-0000-000000000001" and len(ids) == 3
    assert mem.count() == 3
    view = [e for e in mem.examples() if e["label"] == "hat"][0]
    assert [v["aug"] for v in view["variants"]] == ["flip"]
    assert mem.recognize(axis(1)).label == "hat"            # the variant counts
    assert mem.forget_example(ids[0]) == 1 and mem.count() == 1
    with pytest.raises(ValueError):
        mem.teach_many([{"vector": axis(0), "label": "  "}])


def test_recognize_lists_the_runner_up_labels(mem):
    """Tapping a label shows what else it could be, best score per label."""
    mem.teach(axis(0), "koro")
    mem.teach(toward(axis(0), axis(1), 0.97), "koro")
    mem.teach(toward(axis(0), axis(2), 0.80), "georgia")
    mem.teach(axis(3), "roumi")
    d = mem.recognize(toward(axis(0), axis(4), 0.95))
    labels = [c[0] for c in d.candidates]
    assert labels[:2] == ["koro", "georgia"]           # best first, one per label
    assert len(labels) == len(set(labels))
    assert d.candidates[0][1] >= d.candidates[1][1]
    out = d.to_json()["candidates"]
    assert out[0]["label"] == "koro" and "score" in out[0]
