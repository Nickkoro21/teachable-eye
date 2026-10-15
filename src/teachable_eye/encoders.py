"""Image encoders and where they run.

CLIP ViT-B/32 (fastembed, ONNX) embeds object crops into 512-d. The CUDA
provider is used when available; CPU and GPU give the same scores to three
decimals (measured on the reference robot's calibration set).

On Windows the CUDA/cuDNN DLLs ship inside the torch cu130 wheel, so torch is
imported before ONNX Runtime creates a CUDA session.
"""
import os
import threading
from functools import lru_cache

from teachable_eye import config

CLIP_VISION_MODEL = "Qdrant/clip-ViT-B-32-vision"
CLIP_DIM = 512
ENCODER_THREADS = 2


def model_dir(*parts):
    path = config.DATA_DIR.joinpath("models", *parts)
    path.mkdir(parents=True, exist_ok=True)
    return path


def fastembed_cache():
    return os.environ.get("FASTEMBED_CACHE_PATH") or str(model_dir("fastembed"))


@lru_cache(maxsize=1)
def onnx_providers():
    if config.ENCODER_DEVICE == "cpu":
        return ["CPUExecutionProvider"]
    try:
        import torch  # noqa: F401  (puts the CUDA DLLs on the search path)
        import onnxruntime as ort
        has_cuda = ("CUDAExecutionProvider" in ort.get_available_providers()
                    and torch.cuda.is_available())
    except ImportError:
        has_cuda = False
    if has_cuda:
        return ["CUDAExecutionProvider", "CPUExecutionProvider"]
    if config.ENCODER_DEVICE == "cuda":
        raise SystemExit("ENCODER_DEVICE=cuda but no CUDA provider is available")
    return ["CPUExecutionProvider"]


_clip_lock = threading.Lock()


@lru_cache(maxsize=1)
def _clip():
    from fastembed import ImageEmbedding
    return ImageEmbedding(CLIP_VISION_MODEL, threads=ENCODER_THREADS,
                          cache_dir=fastembed_cache(),
                          providers=onnx_providers())


def embed_crops(bgr_crops):
    """Embed OpenCV BGR crops with CLIP's vision tower -> list of 512-d lists."""
    if not bgr_crops:
        return []
    from PIL import Image
    images = [Image.fromarray(c[:, :, ::-1]) for c in bgr_crops]
    with _clip_lock:
        return [v.tolist() for v in _clip().embed(images)]


def warm_clip():
    import numpy as np
    embed_crops([np.zeros((32, 32, 3), dtype=np.uint8)])
