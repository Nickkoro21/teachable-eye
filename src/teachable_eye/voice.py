"""Voice teach (R21): a short spoken sentence -> a label, on the PC.

The phone records while the user holds the 🎤 button and sends a 16 kHz
mono WAV. Whisper (onnx-asr, ONNX Runtime on the GPU) transcribes it in the
app's language (en or el) and labels.parse_label turns "this is my hat" /
«αυτό είναι το καπέλο μου» into "hat" / "καπέλο". Nothing is saved here:
the label only pre-fills the name sheet, the user confirms with Save.

Model: onnx-community/whisper-large-v3-turbo (fp16, ~1.6 GB, MIT licence),
downloaded once to data/models/whisper/. Audio is never stored.
"""
import io
import os
import threading
import time
import wave

import numpy as np

from teachable_eye import config
from teachable_eye.labels import parse_label

MODEL = os.environ.get("VOICE_MODEL", "onnx-community/whisper-large-v3-turbo").strip()
QUANT = os.environ.get("VOICE_QUANT", "fp16").strip() or None
RATE = 16_000
MIN_SECONDS, MAX_SECONDS = 0.4, 15.0
SILENCE_RMS = 0.004        # below this the recording is treated as silence

_model = None
_lock = threading.Lock()


def load():
    """Load (and download once) the Whisper model."""
    global _model
    with _lock:
        if _model is None:
            import onnx_asr
            from teachable_eye.encoders import model_dir, onnx_providers
            # onnx-asr treats an existing folder as "offline": create only the
            # parent, and drop an empty leftover so the download can happen
            path = model_dir("whisper") / MODEL.rsplit("/", 1)[-1]
            if path.is_dir() and not (path / "config.json").exists() and not any(path.iterdir()):
                path.rmdir()
            print(f"loading voice model {MODEL} ({QUANT or 'fp32'})...")
            _model = onnx_asr.load_model(MODEL, path, quantization=QUANT,
                                         providers=onnx_providers())
    return _model


def warm():
    """Load in the background at start-up, so the first 🎤 is not slow."""
    try:
        load().recognize(np.zeros(RATE, np.float32), sample_rate=RATE, language="en")
    except Exception as exc:             # voice is optional; the rest still works
        print(f"voice model not available: {exc}")


def read_wav(data):
    """WAV bytes (PCM 16-bit, any rate, mono or stereo) -> float32 mono 16 kHz."""
    try:
        with wave.open(io.BytesIO(data)) as w:
            if w.getsampwidth() != 2:
                raise ValueError("expected 16-bit PCM audio")
            rate, channels = w.getframerate(), w.getnchannels()
            # check the length BEFORE resampling: a tiny declared rate would
            # otherwise blow a small file up to gigabytes
            if not 8_000 <= rate <= 48_000 or not 1 <= channels <= 2:
                raise ValueError("expected 8-48 kHz mono or stereo audio")
            if w.getnframes() / rate > MAX_SECONDS:
                raise ValueError("too long: say just the name, e.g. “this is my hat”")
            pcm = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2")
    except (wave.Error, EOFError):
        raise ValueError("not a WAV recording") from None
    audio = pcm.astype(np.float32) / 32768.0
    if channels > 1:
        audio = audio.reshape(-1, channels).mean(axis=1)
    if rate != RATE and len(audio):
        n = int(round(len(audio) * RATE / rate))
        audio = np.interp(np.linspace(0, len(audio) - 1, n), np.arange(len(audio)),
                          audio).astype(np.float32)
    return audio


def check(audio):
    """Reject what cannot be a naming sentence before running the model."""
    seconds = len(audio) / RATE
    if seconds < MIN_SECONDS:
        raise ValueError("too short: hold the button while you speak")
    if seconds > MAX_SECONDS:
        raise ValueError("too long: say just the name, e.g. “this is my hat”")
    if float(np.sqrt(np.mean(audio ** 2))) < SILENCE_RMS:
        raise ValueError("no speech heard")
    return seconds


def transcribe(data, lang="en"):
    """WAV bytes -> {"text", "label", "lang", "seconds", "ms"}."""
    lang = lang if lang in ("en", "el") else config.VOICE_LANGUAGE
    audio = read_wav(data)
    seconds = check(audio)
    started = time.perf_counter()
    text = str(load().recognize(audio, sample_rate=RATE, language=lang)).strip()
    return {"text": text, "label": parse_label(text), "lang": lang,
            "seconds": round(seconds, 2),
            "ms": round((time.perf_counter() - started) * 1000)}
