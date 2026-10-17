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

# Image encoder of the objects task (see encoders.ENCODERS). Each encoder has
# its own memory directory and its own score scale, so its own thresholds.
# dinov2-large won the 2026-10-15 comparison (tools/bench_encoders.py).
OBJECT_ENCODER = os.environ.get("OBJECT_ENCODER", "dinov2-large").strip() or "dinov2-large"

# PROVISIONAL bands per encoder until the evaluation tool calibrates them on
# the author's phone. clip-b32: the robot's live-crop calibration. Others: set
# between same-object and different-object scores of the encoder benchmark.
DEFAULT_OBJECT_BANDS = {
    "clip-b32": (0.90, 0.05),
    "siglip2-base": (0.88, 0.05),
    "unicom-b16": (0.30, 0.07),
    "dinov2-base": (0.45, 0.10),
    "dinov2-large": (0.45, 0.10),
}
_t, _m = DEFAULT_OBJECT_BANDS.get(OBJECT_ENCODER, (0.90, 0.05))
OBJECTS = TaskThresholds(_num("OBJECTS_THRESHOLD", _t), _num("OBJECTS_MARGIN", _m))

# People: SFace cosine similarity. OpenCV's published match threshold is 0.363.
PEOPLE = TaskThresholds(_num("PEOPLE_THRESHOLD", 0.40),
                        _num("PEOPLE_MARGIN", 0.06))

DETECT_CONF = _num("DETECT_CONF", 0.30)
DETECT_MIN_AREA = _num("DETECT_MIN_AREA", 0.0003)   # small things count too
# Close-ups fill the frame, so large boxes are kept; boxes touching two frame
# edges are flagged "background" (thin, never the default target) instead.
DETECT_MAX_AREA = _num("DETECT_MAX_AREA", 0.90)

# Teach-time augmentation: variants stored with each taught view.
#   strong (default; "on" means strong): crops, rotations, cover-ups, light, blur
#   basic: zoom, mirror, darker (the first version)   off: none
_aug = os.environ.get("AUGMENT", "strong").strip().lower() or "strong"
if _aug in ("on", "1", "true"):
    _aug = "strong"
if _aug in ("0", "false"):
    _aug = "off"
if _aug not in ("off", "basic", "strong"):
    raise SystemExit(f"AUGMENT must be off, basic or strong, got {_aug!r}")
AUGMENT = _aug != "off"
AUGMENT_PROFILE = _aug if AUGMENT else None

# Where the ONNX encoders run: auto (CUDA when available), cuda, or cpu.
ENCODER_DEVICE = _choice("ENCODER_DEVICE", "auto", {"auto", "cuda", "cpu"})

# Whisper language when the phone does not say (it sends the UI language).
VOICE_LANGUAGE = _choice("VOICE_LANGUAGE", "en", {"en", "el"})

# Voice teach (hold 🎤 and say "this is my hat"); Whisper runs on this PC.
VOICE = os.environ.get("VOICE", "on").strip().lower() not in ("off", "0", "false")

PORT = _num("TEYE_PORT", 8765, int)

# The public name the phone uses (e.g. the Tailscale Serve name). Kept in the
# local .env, never in the repo; requests for any other host name are refused.
PUBLIC_HOST = os.environ.get("TEYE_PUBLIC_HOST", "").strip().lower()

# Optional help from Claude (Anthropic API): name suggestions, a second
# opinion, report summaries, questions about memory. Off unless ASSIST=on;
# the key comes only from ANTHROPIC_API_KEY. Objects only: faces and
# people's names are never sent (mission: cloud help is optional).
ASSIST = os.environ.get("ASSIST", "off").strip().lower() in ("on", "1", "true")
ASSIST_MODEL = os.environ.get("ASSIST_MODEL", "claude-opus-5-5").strip() or "claude-opus-5-5"
