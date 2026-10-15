"""A7-A8: server smoke tests with a fake task (no models loaded)."""
import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from teachable_eye.config import TaskThresholds
from teachable_eye.memory import TaskMemory
from teachable_eye.server import create_app


class FakeTask:
    def __init__(self, tmp_path):
        self.memory = TaskMemory(tmp_path / "shard", 4, "objects",
                                 TaskThresholds(0.9, 0.05))
        self.resets = 0
        self.taught = []

    def reset(self):
        self.resets += 1

    def process(self, frame):
        return [{"id": 1, "box": [0.1, 0.2, 0.5, 0.6], "focus": True,
                 "decision": "unknown", "label": None, "guess": None,
                 "score": 0.1, "neighbours": []}]

    def still(self, frame):
        return self.process(frame)

    def teach(self, tid, label):
        if tid != 1:
            raise LookupError("that object is no longer in view")
        self.taught.append(label)
        return self.memory.teach([1, 0, 0, 0], label)


def jpeg(w=64, h=48):
    ok, buf = cv2.imencode(".jpg", np.full((h, w, 3), 127, np.uint8))
    assert ok
    return buf.tobytes()


@pytest.fixture
def setup(tmp_path):
    task = FakeTask(tmp_path)
    client = TestClient(create_app({"objects": task}))
    yield client, task
    task.memory.close()


def test_a7_ws_returns_normalised_boxes(setup):
    client, _ = setup
    with client.websocket_connect("/ws?task=objects") as ws:
        ws.send_bytes(jpeg())
        msg = ws.receive_json()
    assert msg["w"] == 64 and msg["h"] == 48
    for row in msg["rows"]:
        assert all(0.0 <= v <= 1.0 for v in row["box"])
        assert row["decision"] in {"known", "uncertain", "unknown", "pending"}


def test_a7_bad_frame_is_reported_not_fatal(setup):
    client, _ = setup
    with client.websocket_connect("/ws?task=objects") as ws:
        ws.send_bytes(b"not an image")
        assert "error" in ws.receive_json()
        ws.send_bytes(jpeg())
        assert "rows" in ws.receive_json()


def test_a8_second_camera_replaces_first(setup):
    client, task = setup
    with client.websocket_connect("/ws?task=objects") as first:
        first.send_bytes(jpeg())
        first.receive_json()
        with client.websocket_connect("/ws?task=objects") as second:
            with pytest.raises(WebSocketDisconnect) as closed:
                first.receive_json()
            assert closed.value.code == 4000
            second.send_bytes(jpeg())
            assert "rows" in second.receive_json()
    assert task.resets == 2


def test_teach_memory_rename_forget(setup):
    client, task = setup
    assert client.post("/api/teach", json={"task": "objects", "id": 1,
                                           "label": "Hat"}).status_code == 200
    assert client.post("/api/teach", json={"task": "objects", "id": 9,
                                           "label": "x"}).status_code == 409
    labels = client.get("/api/memory?task=objects").json()["labels"]
    assert labels[0]["label"] == "hat" and labels[0]["count"] == 1
    assert client.post("/api/rename", json={"task": "objects", "label": "hat",
                                            "to": "cap"}).json()["changed"] == 1
    assert client.post("/api/forget", json={"task": "objects",
                                            "label": "cap"}).json()["deleted"] == 1
    assert client.get("/api/memory?task=objects").json()["labels"] == []


def test_still_and_unknown_task(setup):
    client, _ = setup
    r = client.post("/api/still?task=objects", content=jpeg())
    assert r.status_code == 200 and r.json()["rows"]
    assert client.get("/api/memory?task=nope").status_code == 404


def test_thumb_path_is_sanitised(setup):
    client, _ = setup
    assert client.get("/thumb/objects/..%2F..%2Fsecret.txt").status_code in (400, 404)
    assert client.get("/thumb/objects/notahex.jpg").status_code == 400


def test_index_and_static(setup):
    client, _ = setup
    assert "teachable-eye" in client.get("/").text
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/manifest.webmanifest").status_code == 200
