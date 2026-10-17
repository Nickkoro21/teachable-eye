"""A6b: voice teach — WAV handling, silence rejection, label parsing, endpoint.

A fake model stands in for Whisper (no download, no GPU).
"""
import io
import wave

import numpy as np
import pytest
from fastapi.testclient import TestClient

from teachable_eye import config, voice
from teachable_eye.server import create_app


def wav(seconds=1.0, rate=48_000, loud=True, channels=1):
    n = int(seconds * rate)
    tone = np.sin(np.arange(n) * 2 * np.pi * 220 / rate) * (8000 if loud else 10)
    pcm = np.repeat(tone[:, None], channels, axis=1).astype("<i2")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(channels); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes(pcm.tobytes())
    return buf.getvalue()


class FakeWhisper:
    def __init__(self, text):
        self.text, self.calls = text, []

    def recognize(self, audio, sample_rate, language):
        self.calls.append((len(audio), sample_rate, language))
        return self.text


@pytest.fixture
def fake(monkeypatch):
    model = FakeWhisper("Αυτό είναι το καπέλο μου.")
    monkeypatch.setattr(voice, "_model", model)
    return model


def test_read_wav_resamples_to_16k_mono():
    audio = voice.read_wav(wav(1.0, rate=48_000, channels=2))
    assert audio.dtype == np.float32 and abs(len(audio) - 16_000) <= 1


def test_transcribe_gives_the_label_in_the_app_language(fake):
    out = voice.transcribe(wav(1.0), "el")
    assert out["label"] == "καπέλο" and out["lang"] == "el"
    assert fake.calls[0][1:] == (16_000, "el")


@pytest.mark.parametrize("data, reason", [
    (wav(0.1), "too short"), (wav(20), "too long"),
    (wav(1.0, loud=False), "no speech"), (b"not audio", "not a WAV")],
    ids=["short", "long", "silent", "not-wav"])
def test_bad_recordings_are_rejected_before_the_model(fake, data, reason):
    with pytest.raises(ValueError, match=reason):
        voice.transcribe(data, "en")
    assert not fake.calls


def test_voice_endpoint(fake, monkeypatch, tmp_path):
    monkeypatch.setattr(config, "VOICE", True)
    client = TestClient(create_app({}))
    res = client.post("/api/voice?lang=el", content=wav(1.0),
                      headers={"Content-Type": "audio/wav"})
    assert res.status_code == 200 and res.json()["label"] == "καπέλο"
    res = client.post("/api/voice?lang=el", content=wav(1.0, loud=False))
    assert res.status_code == 422 and "no speech" in res.json()["error"]
    monkeypatch.setattr(config, "VOICE", False)
    assert client.post("/api/voice", content=wav(1.0)).status_code == 503


def test_a_tiny_declared_rate_cannot_blow_up_memory(fake):
    """4 MB declaring 100 Hz would resample to ~6 GB (security review)."""
    with pytest.raises(ValueError, match="8-48 kHz"):
        voice.transcribe(wav(1.0, rate=4000), "en")
    assert not fake.calls
