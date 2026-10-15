"""One task's memory: a Qdrant Edge shard of taught examples.

The core knows nothing about cameras, detectors or encoders. A task hands it
vectors and labels; it stores them, finds nearest neighbours and applies the
decision policy. One shard per task keeps vector spaces apart (CLIP 512-d vs
SFace 128-d) and lets a whole task be wiped at once (e.g. "forget everyone").

Patterns follow the DeepLearning.AI course (L3 store/find/forget, L5 teach +
threshold) and https-deeplearning-ai/sc-on-device-ai-memory robot/brain/memory.py
(Apache-2.0): named vector, flush after every write, RLock around the shard.
"""
import shutil
import threading
import time
import uuid
from pathlib import Path

from qdrant_edge import (
    CountRequest,
    Distance,
    EdgeConfig,
    EdgeShard,
    EdgeVectorParams,
    FieldCondition,
    Filter,
    MatchValue,
    PayloadSchemaType,
    Point,
    Query,
    QueryRequest,
    ScrollRequest,
    UpdateOperation,
)

from teachable_eye.labels import norm_label
from teachable_eye.policy import Neighbour, decide

VECTOR = "v"
SCAN_LIMIT = 100_000   # full scans are fine at personal scale
TAUGHT = "taught"


class TaskMemory:
    def __init__(self, directory, dim, task, thresholds):
        self.dir = Path(directory)
        self.dim = dim
        self.task = task
        self.thresholds = thresholds
        self._lock = threading.RLock()
        self.shard = self._open()

    # -- lifecycle -------------------------------------------------------------

    def _open(self):
        if (self.dir / "edge_config.json").exists():
            try:
                return EdgeShard.load(str(self.dir))
            except Exception as exc:
                if "WouldBlock" in str(exc):
                    # Qdrant Edge allows one open shard per directory.
                    raise SystemExit(
                        f"memory {self.dir} is already open in another "
                        "teachable-eye process; stop it first or set "
                        "TEYE_DATA_DIR to a different folder") from None
                raise
        self.dir.mkdir(parents=True, exist_ok=True)
        shard = EdgeShard.create(str(self.dir), EdgeConfig(vectors={
            VECTOR: EdgeVectorParams(size=self.dim, distance=Distance.Cosine),
        }))
        for key in ("label", "kind", "parent"):
            shard.update(UpdateOperation.create_field_index(
                key, PayloadSchemaType.Keyword))
        return shard

    def close(self):
        with self._lock:
            self.shard.close()

    def wipe(self):
        """Delete every example of this task, files included."""
        with self._lock:
            self.shard.close()
            shutil.rmtree(self.dir, ignore_errors=True)
            self.shard = self._open()

    # -- writes ----------------------------------------------------------------

    def teach(self, vector, label, **payload):
        """Add one example. Re-teaching a label adds a view, never overwrites."""
        label = norm_label(label)
        if not label:
            raise ValueError("empty label")
        pid = str(uuid.uuid4())
        body = {"label": label, "task": self.task, "kind": TAUGHT,
                "ts": time.time(), **payload}
        with self._lock:
            self.shard.update(UpdateOperation.upsert_points([
                Point(id=pid, vector={VECTOR: list(map(float, vector))},
                      payload=body)]))
            self.shard.flush()
        return pid

    def forget_label(self, label):
        """Delete every example of a label. Returns how many were deleted."""
        ids = self._ids_of(norm_label(label))
        if ids:
            with self._lock:
                self.shard.update(UpdateOperation.delete_points(ids))
                self.shard.flush()
        return len(ids)

    def forget_example(self, pid):
        """Delete one taught view and the augmented variants made from it."""
        with self._lock:
            records, _ = self.shard.scroll(ScrollRequest(
                limit=SCAN_LIMIT, with_payload=True))
            ids = [str(r.id) for r in records
                   if str(r.id) == pid or r.payload.get("parent") == pid]
            if ids:
                self.shard.update(UpdateOperation.delete_points(ids))
                self.shard.flush()
            return sum(1 for i in ids if i == pid)

    def rename(self, label, new_label):
        """Rename a label; renaming onto an existing label merges the two."""
        new_label = norm_label(new_label)
        if not new_label:
            raise ValueError("empty label")
        ids = self._ids_of(norm_label(label))
        if ids:
            with self._lock:
                self.shard.update(UpdateOperation.set_payload(
                    ids, {"label": new_label}))
                self.shard.flush()
        return len(ids)

    # -- reads -----------------------------------------------------------------

    def recognize(self, vector, k=3):
        """Nearest taught examples -> Decision (see policy.decide).

        An augmented variant counts as its original view: the evidence shows
        each taught view once, with the best score among it and its variants.
        """
        with self._lock:
            hits = self.shard.query(QueryRequest(
                query=Query.Nearest(list(map(float, vector)), using=VECTOR),
                filter=Filter(must=[FieldCondition(
                    key="kind", match=MatchValue(value=TAUGHT))]),
                limit=k * 6,
                with_payload=True,
            ))
        neighbours, seen = [], set()
        for h in hits:                      # best-first
            root = h.payload.get("parent") or str(h.id)
            if root in seen:
                continue
            seen.add(root)
            neighbours.append(Neighbour(root, h.payload.get("label", ""),
                                        float(h.score), h.payload.get("thumb")))
            if len(neighbours) == k:
                break
        return decide(neighbours, self.thresholds)

    def count(self):
        with self._lock:
            return self.shard.count(CountRequest(exact=True))

    def examples(self):
        """Every taught view as {id, label, ts, thumb, ...}, newest first.

        Augmented variants are internal and not listed (they go with their view).
        """
        with self._lock:
            records, _ = self.shard.scroll(ScrollRequest(
                limit=SCAN_LIMIT, with_payload=True))
        rows = [dict(r.payload, id=str(r.id)) for r in records
                if not r.payload.get("parent")]
        rows.sort(key=lambda r: r.get("ts") or 0, reverse=True)
        return rows

    def labels(self):
        """Labels with their examples, most recently taught first."""
        groups = {}
        for row in self.examples():
            groups.setdefault(row["label"], []).append(row)
        return [{"label": label, "count": len(rows), "examples": rows}
                for label, rows in groups.items()]

    def _ids_of(self, label):
        with self._lock:
            records, _ = self.shard.scroll(ScrollRequest(
                limit=SCAN_LIMIT, with_payload=False,
                filter=Filter(must=[FieldCondition(
                    key="label", match=MatchValue(value=label))])))
        return [str(r.id) for r in records]
