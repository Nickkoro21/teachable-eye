"""A11-A13: test set, evaluation report and recommended bands (synthetic data)."""
import json

import numpy as np
import pytest
from fastapi.testclient import TestClient

from teachable_eye import config
from teachable_eye.config import TaskThresholds
from teachable_eye.evalset import EvalStore
from teachable_eye.evaluation import Memory, evaluate, outcome, score_items, to_markdown
from teachable_eye.memory import TaskMemory
from teachable_eye.server import create_app
from teachable_eye.tasks import ObjectsTask

from test_teach_hold import FakeDetector, fake_embed

DIM = 8


def axis(i):
    v = np.zeros(DIM, np.float32)
    v[i] = 1.0
    return v


def toward(i, j, cos):
    """Unit vector with cosine `cos` to axis i, leaning toward axis j."""
    return cos * axis(i) + np.sqrt(1 - cos * cos) * axis(j)


def points():
    pts = []
    for n, (label, i) in enumerate((("hat", 0), ("cup", 1))):
        for k in range(3):                         # 3 views per label
            vid = f"{label}{k}"
            pts.append({"id": vid, "label": label, "parent": None, "aug": None,
                        "vector": toward(i, 5 + k, 0.97)})
            pts.append({"id": vid + "z", "label": label, "parent": vid,
                        "aug": "flip", "vector": toward(i, 5 + k, 0.93)})
    return pts


def items():
    return [
        {"id": "1", "label": "hat", "vector": toward(0, 4, 0.9)},     # correct
        {"id": "2", "label": "cup", "vector": toward(1, 4, 0.85)},    # correct
        {"id": "3", "label": "hat", "vector": toward(1, 0, 0.8)},     # looks like the cup
        {"id": "4", "label": "bag", "vector": toward(2, 0, 0.95)},    # stranger
        {"id": "5", "label": "pen", "vector": toward(3, 1, 0.6)},     # stranger
    ]


def test_a11_outcomes_and_dangerous_errors():
    rows = score_items(Memory(points()), items())
    by_id = {r["id"]: r for r in rows}
    assert by_id["1"]["top_label"] == "hat" and by_id["1"]["enrolled"]
    assert not by_id["4"]["enrolled"]
    assert outcome(by_id["1"], 0.5, 0.1) == "correct"
    assert outcome(by_id["3"], 0.5, 0.1) == "wrong"          # confident wrong name
    assert outcome(by_id["4"], 0.5, 0.1) == "rejected"
    assert outcome(by_id["5"], 0.2, 0.1) == "false_accept"


def test_a12_recommended_threshold_has_no_dangerous_errors():
    r = evaluate(points(), items(), TaskThresholds(0.30, 0.10))
    assert r["current"]["dangerous"] > 0
    rec = r["recommended"]
    assert rec["dangerous"] == 0
    assert rec["correct"] == 2                     # both clean views still known
    assert r["separation"]["auc"] is not None
    assert r["augmentation"]["with_top1"] is not None
    assert r["views_curve"][0]["views"] == 1 and len(r["views_curve"]) == 3
    assert "logreg_top1" in r["classifier"]
    md = to_markdown(r)
    assert "Headline" in md and "stranger" in md


def test_a12_no_strangers_is_flagged():
    clean = [it for it in items() if it["label"] in ("hat", "cup") and it["id"] != "3"]
    r = evaluate(points(), clean, TaskThresholds(0.95, 0.05))
    assert any("strangers" in n.lower() for n in r["notes"])


def test_empty_evaluation_does_not_crash():
    r = evaluate([], [], TaskThresholds(0.5, 0.1))
    assert r["test"]["views"] == 0 and r["notes"]


# -- the test set and the task/server flow ------------------------------------------

@pytest.fixture
def task(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    mem = TaskMemory(tmp_path / "m", 4, "objects", TaskThresholds(0.9, 0.05))
    t = ObjectsTask(detector=FakeDetector(), embed=fake_embed, memory=mem)
    yield t
    mem.close()


def test_a11_test_views_never_reach_memory(task, tmp_path):
    task.process(np.zeros((100, 100, 3), np.uint8), now=1.0)
    assert task.eval_held(task.hold(7), "Cup") == 1
    assert task.memory.count() == 0
    items = task.evalset.items()
    assert [i["label"] for i in items] == ["cup"]
    assert (tmp_path / "eval" / "objects" / f"{items[0]['id']}.jpg").exists()
    assert task.evalset.delete(items[0]["id"]) and not task.evalset.items()


def test_evalstore_rejects_bad_ids(tmp_path):
    store = EvalStore("objects", root=tmp_path)
    with pytest.raises(LookupError):
        store.path("../../secret")


def test_a13_server_eval_flow(task, tmp_path):
    client = TestClient(create_app({"objects": task}))
    frame = np.zeros((100, 100, 3), np.uint8)
    task.process(frame, now=1.0)
    hid = client.post("/api/hold", json={"task": "objects", "id": 7}).json()["hold"]
    assert client.post("/api/teach", json={"task": "objects", "hold": hid,
                                           "label": "cup"}).status_code == 200
    hid = client.post("/api/hold", json={"task": "objects", "id": 7}).json()["hold"]
    res = client.post("/api/teach", json={"task": "objects", "hold": hid,
                                          "label": "cup", "eval": True}).json()
    assert res == {"eval": 1}
    listing = client.get("/api/eval?task=objects").json()
    assert listing["labels"] == {"cup": 1}
    iid = listing["items"][0]["id"]
    assert client.get(f"/api/eval/objects/{iid}.jpg").status_code == 200
    run = client.post("/api/eval/run", json={"task": "objects"}).json()
    assert run["current"]["correct"] == 1 and run["current"]["dangerous"] == 0
    assert set(run["profiles"]) == {"none", "basic", "strong"}      # compared on the same set
    assert run["profiles"]["strong"]["points"] > run["profiles"]["basic"]["points"]
    md = client.get(f"/api/reports/{run['report']}.md")
    assert md.status_code == 200 and "Evaluation" in md.text
    saved = json.loads((tmp_path / "reports" / f"{run['report']}.json").read_text("utf-8"))
    assert "vector" not in saved["items"][0]
    assert client.get("/api/reports/..%2Fsecret.md").status_code in (400, 404)
    assert client.post("/api/eval/forget", json={"task": "objects", "id": iid}).json()["deleted"]


def test_forgetting_a_label_removes_its_test_views_and_reports(task, tmp_path):
    """Forgetting someone is complete: test views and reports go too."""
    task.process(np.zeros((100, 100, 3), np.uint8), now=1.0)
    task.eval_held(task.hold(7), "person-a")
    task.eval_held(task.hold(7), "person-b")
    reports = tmp_path / "reports"
    reports.mkdir(exist_ok=True)
    (reports / "eval-objects-20261017-100000.json").write_text('{"label": "person-a"}')
    (reports / "eval-objects-20261017-100001.json").write_text('{"label": "person-b"}')
    task.forget_everywhere("person-a")
    assert [i["label"] for i in task.evalset.items()] == ["person-b"]
    assert sorted(p.name for p in reports.iterdir()) == ["eval-objects-20261017-100001.json"]
