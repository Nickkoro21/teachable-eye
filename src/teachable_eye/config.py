"""Settings, loaded from `.env` at the repository root.

Exported environment variables override `.env`; command-line flags override
both where they exist. Every value has a documented default in `.env.example`.
"""
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

REPO = Path(__file__).resolve().parents[2]
ENV_FILE = REPO / ".env"
load_dotenv(ENV_FILE, override=False)


def _num(name, default, cast=float):
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return cast(raw)
    except ValueError:
        raise SystemExit(f"{name} must be a number, got {raw!r}") from None


def _choice(name, default, allowed):
    raw = os.environ.get(name, "").strip().lower() or default
    if raw not in allowed:
        raise SystemExit(f"{name} must be one of {sorted(allowed)}, got {raw!r}")
    return raw


@dataclass(frozen=True)
class TaskThresholds:
    """Decision bands for one task (see policy.decide)."""
    threshold: float   # score >= threshold -> known
    margin: float      # threshold - margin <= score < threshold -> uncertain


# Data never leaves this directory (git-ignored, mission principle 4).
DATA_DIR = Path(os.environ.get("TEYE_DATA_DIR", "") or REPO / "data")

# Objects: CLIP ViT-B/32 on masked crops. The robot's live-crop calibration
# (0.90 / 0.05) is the starting point; re-calibrate with tools/evaluate.py.
OBJECTS = TaskThresholds(_num("OBJECTS_THRESHOLD", 0.90),
                         _num("OBJECTS_MARGIN", 0.05))

# People: SFace cosine similarity. OpenCV's published match threshold is 0.363.
PEOPLE = TaskThresholds(_num("PEOPLE_THRESHOLD", 0.40),
                        _num("PEOPLE_MARGIN", 0.06))

DETECT_CONF = _num("DETECT_CONF", 0.30)
DETECT_MIN_AREA = _num("DETECT_MIN_AREA", 0.002)
DETECT_MAX_AREA = _num("DETECT_MAX_AREA", 0.45)   # phones hold objects close

# Where the ONNX encoders run: auto (CUDA when available), cuda, or cpu.
ENCODER_DEVICE = _choice("ENCODER_DEVICE", "auto", {"auto", "cuda", "cpu"})

# Whisper language for voice teach: en (default) or el.
VOICE_LANGUAGE = _choice("VOICE_LANGUAGE", "en", {"en", "el"})

PORT = _num("TEYE_PORT", 8765, int)
