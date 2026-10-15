"""Rebuild the objects memory for another encoder from what was taught.

    uv run python tools/reembed.py --from clip-b32 --to dinov2-large

Vectors of different encoders are not comparable, so switching OBJECT_ENCODER
starts from an empty memory. This copies every taught view (label, time,
source) from one encoder's memory into another's, re-embedding the stored
crop of each view (data/crops/objects). Views taught before crops were kept
fall back to their 160 px thumbnail — usable, but lower quality; re-teaching
those with Video is better. Augmented variants are regenerated.

The server must be stopped (one process per memory). The source memory is
only read, never changed.
"""
import argparse
import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from teachable_eye import config  # noqa: E402
from teachable_eye.encoders import encoder_dim, get_encoder  # noqa: E402
from teachable_eye.memory import TaskMemory  # noqa: E402
from teachable_eye.tasks import AUGMENT, CROP_SIZE, object_memory_dir  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from", dest="src", required=True)
    ap.add_argument("--to", dest="dst", required=True)
    ap.add_argument("--no-augment", action="store_true")
    args = ap.parse_args()
    if args.src == args.dst:
        raise SystemExit("--from and --to are the same encoder")

    src_dir, dst_dir = object_memory_dir(args.src), object_memory_dir(args.dst)
    if not src_dir.exists():
        raise SystemExit(f"no memory for {args.src} at {src_dir}")
    thumbs = config.DATA_DIR / "thumbs" / "objects"
    crops = config.DATA_DIR / "crops" / "objects"

    src = TaskMemory(src_dir, encoder_dim(args.src), "objects", config.OBJECTS)
    try:
        views = src.examples()
    finally:
        src.close()
    dst = TaskMemory(dst_dir, encoder_dim(args.dst), "objects", config.OBJECTS)
    have = {(e["label"], e.get("thumb")) for e in dst.examples()}
    enc = get_encoder(args.dst)
    augs = () if args.no_augment else AUGMENT["objects"]

    done = from_thumb = skipped = 0
    try:
        for v in views:
            if (v["label"], v.get("thumb")) in have:
                skipped += 1                      # already copied earlier
                continue
            img = None
            if v.get("crop"):
                img = cv2.imread(str(crops / v["crop"]))
            if img is None:
                img = cv2.imread(str(thumbs / (v.get("thumb") or "")))
                from_thumb += img is not None
            if img is None:
                print(f"  ! no picture for a view of {v['label']!r}, skipped")
                continue
            if max(img.shape[:2]) > CROP_SIZE:
                s = CROP_SIZE / max(img.shape[:2])
                img = cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
            keep = {k: v[k] for k in ("ts", "source", "crop") if v.get(k) is not None}
            pid = dst.teach(enc.embed([img])[0], v["label"], thumb=v.get("thumb"),
                            migrated_from=args.src, **keep)
            if augs:
                variants = [fn(img) for fn in augs]
                for fn, vec in zip(augs, enc.embed(variants)):
                    # variants share the view's thumbnail here (no new files)
                    dst.teach(vec, v["label"], thumb=v.get("thumb"),
                              parent=pid, aug=fn.__name__)
            done += 1
    finally:
        dst.close()
    print(f"{args.src} -> {args.dst}: {done} views copied "
          f"({from_thumb} from 160 px thumbnails), {skipped} already there")


if __name__ == "__main__":
    main()
