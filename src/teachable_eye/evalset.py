"""The test set: labelled pictures kept apart from memory (R34).

A recognition score means little until it is measured on pictures the
memory never saw. While collecting, the user saves views "for test" instead
of teaching them; they land here, one JPEG + one JSON per view, and are
never used for recognition. A label that memory does not know is a
"stranger": the right answer for it is `unknown`.

    data/eval/<task>/<id>.jpg   the crop (objects) or aligned face (people)
    data/eval/<task>/<id>.json  {"label", "ts", "source"}

Everything stays under data/ (git-ignored, never committed).
"""
import json
import re
import time
import uuid

import cv2

from teachable_eye import config
from teachable_eye.labels import norm_label

CROP_SIZE = 384
_SAFE_ID = re.compile(r"^[0-9a-f]{32}$")


class EvalStore:
    def __init__(self, task, root=None):
        self.task = task
        self.dir = (root or config.DATA_DIR / "eval") / task
        self.dir.mkdir(parents=True, exist_ok=True)

    def add(self, crop, label, source="phone"):
        label = norm_label(label)
        if not label:
            raise ValueError("empty label")
        h, w = crop.shape[:2]
        scale = min(1.0, CROP_SIZE / max(h, w))
        img = crop if scale == 1.0 else cv2.resize(
            crop, (max(1, int(w * scale)), max(1, int(h * scale))),
            interpolation=cv2.INTER_AREA)
        iid = uuid.uuid4().hex
        cv2.imwrite(str(self.dir / f"{iid}.jpg"), img, [cv2.IMWRITE_JPEG_QUALITY, 92])
        (self.dir / f"{iid}.json").write_text(json.dumps(
            {"label": label, "ts": time.time(), "source": source}), encoding="utf-8")
        return iid

    def items(self):
        """Every test view as {id, label, ts, source}, newest first."""
        out = []
        for meta in self.dir.glob("*.json"):
            if not (self.dir / f"{meta.stem}.jpg").exists():
                continue
            try:
                data = json.loads(meta.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            out.append(dict(data, id=meta.stem))
        out.sort(key=lambda r: r.get("ts") or 0, reverse=True)
        return out

    def labels(self):
        """{label: count} of the test set."""
        counts = {}
        for it in self.items():
            counts[it["label"]] = counts.get(it["label"], 0) + 1
        return counts

    def path(self, iid):
        if not _SAFE_ID.match(iid or ""):
            raise LookupError("bad test view id")
        return self.dir / f"{iid}.jpg"

    def image(self, iid):
        img = cv2.imread(str(self.path(iid)))
        if img is None:
            raise LookupError("no such test view")
        return img

    def delete(self, iid):
        path = self.path(iid)
        existed = path.exists()
        path.unlink(missing_ok=True)
        path.with_suffix(".json").unlink(missing_ok=True)
        return existed
