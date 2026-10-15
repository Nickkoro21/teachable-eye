"""Image encoders: a small registry with one interface.

Every encoder turns OpenCV BGR crops into L2-normalised vectors:

    enc = get_encoder("dinov2-base")
    enc.dim, enc.embed([crop, ...]) -> [[float, ...], ...]

Which one the objects task uses is set by OBJECT_ENCODER (.env). Vectors of
different encoders are not comparable, so each encoder has its own memory
(see tasks.ObjectsTask) and thresholds are per encoder.

    clip-b32      CLIP ViT-B/32 (OpenAI), fastembed ONNX       512-d  course baseline
    unicom-b16    Unicom ViT-B/16 (retrieval), fastembed ONNX  768-d
    siglip2-base  SigLIP 2 base/16 (Google, Apache-2.0)        768-d
    dinov2-base   DINOv2 ViT-B/14 (Meta, Apache-2.0)           768-d
    dinov2-large  DINOv2 ViT-L/14 (Meta, Apache-2.0)          1024-d

CLIP and SigLIP learn what an image *means* (paired with text); DINOv2 is
self-supervised on images alone and keeps fine visual detail, which is what
"is this the same object?" needs. Torch models run in fp16 on CUDA.

On Windows the CUDA/cuDNN DLLs ship inside the torch cu130 wheel, so torch is
imported before ONNX Runtime creates a CUDA session.
"""
import os
import threading
from functools import lru_cache

import numpy as np

from teachable_eye import config

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


def _unit(rows):
    v = np.asarray(rows, dtype=np.float32)
    v /= np.maximum(np.linalg.norm(v, axis=1, keepdims=True), 1e-12)
    return v.tolist()


def _to_rgb_pil(bgr_crops):
    from PIL import Image
    return [Image.fromarray(np.ascontiguousarray(c[:, :, ::-1])) for c in bgr_crops]


class FastembedEncoder:
    """ONNX image models served by fastembed (CLIP, Unicom)."""

    def __init__(self, name, model, dim):
        from fastembed import ImageEmbedding
        self.name, self.dim = name, dim
        self._lock = threading.Lock()
        self._model = ImageEmbedding(model, threads=ENCODER_THREADS,
                                     cache_dir=fastembed_cache(),
                                     providers=onnx_providers())

    def embed(self, bgr_crops):
        if not bgr_crops:
            return []
        with self._lock:
            return _unit(list(self._model.embed(_to_rgb_pil(bgr_crops))))

    def close(self):
        pass


class TorchEncoder:
    """Hugging Face vision models (DINOv2, SigLIP 2) on the GPU in fp16."""

    def __init__(self, name, repo, dim, kind):
        import torch
        from transformers import AutoImageProcessor, AutoModel
        self.name, self.dim, self.kind = name, dim, kind
        self._lock = threading.Lock()
        self.device = ("cuda" if torch.cuda.is_available()
                       and config.ENCODER_DEVICE != "cpu" else "cpu")
        self.dtype = torch.float16 if self.device == "cuda" else torch.float32
        cache = str(model_dir("hf"))
        self.processor = AutoImageProcessor.from_pretrained(repo, cache_dir=cache)
        self.model = AutoModel.from_pretrained(repo, cache_dir=cache,
                                               dtype=self.dtype).to(self.device).eval()

    def embed(self, bgr_crops):
        if not bgr_crops:
            return []
        import torch
        with self._lock, torch.inference_mode():
            inputs = self.processor(images=_to_rgb_pil(bgr_crops), return_tensors="pt")
            pixels = inputs["pixel_values"].to(self.device, self.dtype)
            if self.kind == "siglip":
                feats = self.model.get_image_features(pixel_values=pixels)
                if hasattr(feats, "pooler_output"):
                    feats = feats.pooler_output
            else:                                   # DINOv2: CLS + mean patch
                out = self.model(pixel_values=pixels).last_hidden_state
                feats = torch.cat([out[:, 0], out[:, 1:].mean(dim=1)], dim=1)
            return _unit(feats.float().cpu().numpy())

    def close(self):
        pass


# name -> (factory, dim). DINOv2 vectors concatenate CLS and mean patch
# tokens (2 x hidden size): CLS carries the whole object, the patch mean keeps
# texture and local detail.
ENCODERS = {
    "clip-b32": (lambda: FastembedEncoder("clip-b32", "Qdrant/clip-ViT-B-32-vision", 512), 512),
    "unicom-b16": (lambda: FastembedEncoder("unicom-b16", "Qdrant/Unicom-ViT-B-16", 768), 768),
    "siglip2-base": (lambda: TorchEncoder("siglip2-base", "google/siglip2-base-patch16-224", 768, "siglip"), 768),
    "dinov2-base": (lambda: TorchEncoder("dinov2-base", "facebook/dinov2-base", 1536, "dino"), 1536),
    "dinov2-large": (lambda: TorchEncoder("dinov2-large", "facebook/dinov2-large", 2048, "dino"), 2048),
}

_cache = {}
_cache_lock = threading.Lock()


def get_encoder(name):
    if name not in ENCODERS:
        raise SystemExit(f"unknown encoder {name!r}; choose from {', '.join(ENCODERS)}")
    with _cache_lock:
        if name not in _cache:
            _cache[name] = ENCODERS[name][0]()
        return _cache[name]


def encoder_dim(name):
    return ENCODERS[name][1]


# -- the objects task's encoder (kept for callers of the old API) ------------

CLIP_DIM = 512


def embed_crops(bgr_crops):
    """Embed crops with the configured OBJECT_ENCODER."""
    return get_encoder(config.OBJECT_ENCODER).embed(bgr_crops)


def warm_clip():
    embed_crops([np.zeros((32, 32, 3), dtype=np.uint8)])
