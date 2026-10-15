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
