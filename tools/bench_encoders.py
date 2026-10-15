"""Compare image encoders for "is this the same object?" on local multi-view sets.

    uv run python tools/bench_encoders.py                 # all sets, all encoders
    uv run python tools/bench_encoders.py --encoders clip-b32,dinov2-large

Sets (local only, never committed):
  phone   taught thumbnails in data/thumbs/objects, labels read from the
          objects memory (the server must be stopped: one shard, one process)
  folder  any directory of <label>_<n>.jpg images (--folder DIR, repeatable)

Per encoder and set it reports:
  1-NN    leave-one-out nearest-neighbour accuracy (queries: labels with ≥2 views)
  AUC     how well same-object pairs out-score different-object pairs (1.0 = always)
  margin  worst same-object score minus best different-object score (> 0 = separable)
  gap     median(same) - median(different)
  ms      encode time per image (batch of 8, GPU when available)
Scores of different encoders are on different scales, so compare AUC, 1-NN and
margin — never raw thresholds.
"""
import argparse
import itertools
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from teachable_eye import config  # noqa: E402
from teachable_eye.encoders import ENCODERS, get_encoder  # noqa: E402


def load_folder(folder):
    items = []
    for p in sorted(Path(folder).iterdir()):
        if p.suffix.lower() not in (".jpg", ".jpeg", ".png", ".webp"):
            continue
        img = cv2.imread(str(p))
        if img is None:
            continue
        label = re.sub(r"[_-]?\d+$", "", p.stem) or p.stem
        items.append((label, img))
    return items


def load_phone():
    from teachable_eye.memory import TaskMemory
    shard = config.DATA_DIR / "memory" / "objects"
    if not shard.exists():
        return []
    mem = TaskMemory(shard, 512, "objects", config.OBJECTS)
    try:
        rows = mem.examples()
    finally:
        mem.close()
    thumbs = config.DATA_DIR / "thumbs" / "objects"
    items = []
    for row in rows:
        img = cv2.imread(str(thumbs / (row.get("thumb") or "")))
        if img is not None:
            label = re.sub(r"\s+", " ", row["label"].replace("ή", "η")).strip()
            items.append((label, img))
    return items


def auc(same, diff):
    same, diff = np.asarray(same), np.asarray(diff)
    if not len(same) or not len(diff):
        return float("nan")
    return float((same[:, None] > diff[None, :]).mean()
                 + 0.5 * (same[:, None] == diff[None, :]).mean())


def evaluate(vectors, labels):
    v = np.asarray(vectors, dtype=np.float32)
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    sims = v @ v.T
    same, diff = [], []
    for i, j in itertools.combinations(range(len(labels)), 2):
        (same if labels[i] == labels[j] else diff).append(float(sims[i, j]))
    counts = defaultdict(int)
    for lab in labels:
        counts[lab] += 1
    hits = total = 0
    for i, lab in enumerate(labels):
        if counts[lab] < 2:
            continue
        row = sims[i].copy()
        row[i] = -2
        hits += labels[int(row.argmax())] == lab
        total += 1
    return {
        "1nn": hits / total if total else float("nan"),
        "auc": auc(same, diff),
        "margin": (min(same) - max(diff)) if same and diff else float("nan"),
        "gap": (float(np.median(same)) - float(np.median(diff))) if same and diff else float("nan"),
        "same_med": float(np.median(same)) if same else float("nan"),
        "diff_max": max(diff) if diff else float("nan"),
        "pairs": (len(same), len(diff)),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--encoders", default=",".join(ENCODERS))
    ap.add_argument("--folder", action="append", default=[])
    ap.add_argument("--no-phone", action="store_true")
    args = ap.parse_args()

    sets = {}
    if not args.no_phone:
        phone = load_phone()
        if phone:
            sets["phone"] = phone
    for f in args.folder:
        sets[Path(f).name] = load_folder(f)
    if not sets:
        raise SystemExit("no data: teach some objects or pass --folder DIR")
    for name, items in sets.items():
        labs = defaultdict(int)
        for lab, _ in items:
            labs[lab] += 1
        print(f"set {name}: {len(items)} images, {len(labs)} labels {dict(labs)}")

    lines = ["| encoder | dim | set | 1-NN | AUC | margin | gap | same med | diff max | ms/img |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for key in args.encoders.split(","):
        enc = get_encoder(key)
        enc.embed([np.zeros((64, 64, 3), np.uint8)] * 2)          # warm up
        for name, items in sets.items():
            imgs = [img for _, img in items]
            labels = [lab for lab, _ in items]
            t0 = time.perf_counter()
            vecs = []
            for k in range(0, len(imgs), 8):
                vecs += enc.embed(imgs[k:k + 8])
            ms = (time.perf_counter() - t0) * 1000 / len(imgs)
            r = evaluate(vecs, labels)
            lines.append(f"| {key} | {enc.dim} | {name} | {r['1nn']:.2f} | {r['auc']:.3f} | "
                         f"{r['margin']:+.3f} | {r['gap']:.3f} | {r['same_med']:.3f} | "
                         f"{r['diff_max']:.3f} | {ms:.1f} |")
            print(lines[-1], flush=True)
        enc.close()
    report = "\n".join(lines)
    out = config.DATA_DIR / "reports"
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"encoders-{time.strftime('%Y%m%d-%H%M%S')}.md"
    path.write_text("# Encoder comparison\n\n" + report + "\n", encoding="utf-8")
    print(f"\nreport: {path}")


if __name__ == "__main__":
    main()
