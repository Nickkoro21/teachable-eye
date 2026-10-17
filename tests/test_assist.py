"""A14-A16: optional Claude help — opt-in, objects only, no faces sent.

A fake client stands in for the Anthropic API: these tests make no network
calls and need no key.
"""
import json
from types import SimpleNamespace

import numpy as np
import pytest
from fastapi.testclient import TestClient

from teachable_eye import assist, config, faces
from teachable_eye.config import TaskThresholds
from teachable_eye.memory import TaskMemory
from teachable_eye.server import create_app


class FakeMessages:
    def __init__(self, answer, stop_reason="end_turn"):
        self.answer, self.stop_reason, self.calls = answer, stop_reason, []

    def create(self, **kw):
        self.calls.append(kw)
        text = self.answer if isinstance(self.answer, str) else json.dumps(self.answer)
        return SimpleNamespace(
            stop_reason=self.stop_reason, model=kw["model"],
            content=[SimpleNamespace(type="text", text=text)],
            usage=SimpleNamespace(input_tokens=10, output_tokens=5))


def fake_client(answer, stop_reason="end_turn"):
    msgs = FakeMessages(answer, stop_reason)
    return SimpleNamespace(beta=SimpleNamespace(messages=msgs)), msgs


@pytest.fixture
def on(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "ASSIST", True)
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    # a black crop stands for "a picture with a face"
    monkeypatch.setattr(faces, "has_face", lambda img: float(img.mean()) == 0.0)
    yield
    assist.set_client(None)


def gray(v=120):
    return np.full((40, 40, 3), v, np.uint8)


def images_in(call):
    return [b for b in call["messages"][0]["content"] if b["type"] == "image"]


def test_a14_off_by_default(monkeypatch):
    monkeypatch.setattr(config, "ASSIST", False)
    with pytest.raises(assist.AssistError, match="off"):
        assist.suggest_names([gray()])


def test_a14_people_are_refused(on):
    assist.set_client(fake_client({"items": []})[0])
    with pytest.raises(assist.AssistError, match="objects only"):
        assist.suggest_names([gray()], task="people")


def test_a15_suggest_names_skips_faces(on):
    client, msgs = fake_client({"items": [{"index": 1, "name": "mug", "confident": True},
                                          {"index": 2, "name": "lighter", "confident": False}]})
    assist.set_client(client)
    out = assist.suggest_names([gray(), gray(0), gray(200)], ["cup"], "en")
    assert [o["name"] for o in out] == ["mug", "", "lighter"]
    assert out[1]["skipped"] and not out[0]["skipped"]
    call = msgs.calls[0]
    assert len(images_in(call)) == 2                     # the face crop was not sent
    assert call["fallbacks"] == "default" and assist.FALLBACK_BETA in call["betas"]
    assert call["output_config"]["format"]["type"] == "json_schema"
    assert (config.DATA_DIR / "reports" / "assist-usage.jsonl").exists()


def test_a15_nothing_sendable_means_no_call(on):
    client, msgs = fake_client({"items": []})
    assist.set_client(client)
    out = assist.suggest_names([gray(0)])
    assert out[0]["skipped"] and not msgs.calls


def test_a16_second_opinion_only_returns_known_labels(on):
    client, msgs = fake_client({"match": "invented", "confidence": "high", "reason": "x"})
    assist.set_client(client)
    out = assist.second_opinion(gray(), [("cup", [gray(90)]), ("hat", [gray(0)])])
    assert out["match"] == ""                            # not one of the candidates
    text = " ".join(b.get("text", "") for b in msgs.calls[0]["messages"][0]["content"])
    assert "cup" in text and "hat" not in text           # hat's only example had a face
    client, _ = fake_client({"match": "cup", "confidence": "medium", "reason": "same logo"})
    assist.set_client(client)
    assert assist.second_opinion(gray(), [("cup", [gray(90)])])["match"] == "cup"


def test_a16_second_opinion_refuses_a_face(on):
    assist.set_client(fake_client({})[0])
    with pytest.raises(assist.AssistError, match="face"):
        assist.second_opinion(gray(0), [("cup", [gray()])])


def test_refusal_is_reported(on):
    assist.set_client(fake_client("", stop_reason="refusal")[0])
    with pytest.raises(assist.AssistError, match="declined"):
        assist.suggest_names([gray()])


def test_ask_and_summary_send_no_pictures(on):
    client, msgs = fake_client("You taught the cup twice.")
    assist.set_client(client)
    labels = [{"label": "cup", "count": 2, "examples": [{"ts": 1.0}, {"ts": 2.0}]}]
    assert "cup" in assist.ask_memory("how many cups?", labels, {"cup": 3})
    assert assist.write_summary({"task": "objects", "items": [{"id": "x"}], "current": {}})
    for call in msgs.calls:
        assert not images_in(call)
        assert '"items"' not in call["messages"][0]["content"][0]["text"]


def test_server_assist_status_and_errors(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "ASSIST", False)
    mem = TaskMemory(tmp_path / "m", 4, "objects", TaskThresholds(0.9, 0.05))

    class Task:
        memory = mem

        def still_crops(self, ids, still_id=None):
            return [gray() for _ in ids]

    client = TestClient(create_app({"objects": Task()}))
    st = client.get("/api/assist").json()
    assert st["enabled"] is False and st["ready"] is False
    res = client.post("/api/assist/names", json={"task": "objects", "ids": [1]})
    assert res.status_code == 503 and "off" in res.json()["error"]
    mem.close()


def test_has_face_on_a_blank_picture():
    path = faces.model_dir("opencv") / faces.YUNET[0]
    if not path.exists():
        pytest.skip("YuNet model not downloaded")
    assert faces.has_face(gray()) is False
