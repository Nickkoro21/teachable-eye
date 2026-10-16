"""Compare object encoders on the same taught views and the same test set.

    uv run python tools/evaluate.py --encoders dinov2-large,dinov2-base,clip-b32

The phone's Evaluate button scores the live memory with the live encoder.
This tool answers "would another encoder do better on MY data?": for each
encoder it re-embeds every taught view (its kept crop, else its thumbnail,
plus the same augmented variants) and every test view, then runs the same
evaluation (src/teachable_eye/evaluation.py) with that encoder's bands.

The list of taught views comes from the running server (/api/memory), so
the server may keep running; if it is not running, the memory is opened
directly. Reports go to data/reports/compare-objects-<time>.{json,md}.
"""
import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from teachable_eye import config  # noqa: E402
from teachable_eye.encoders import ENCODERS, encoder_dim, get_encoder  # noqa: E402
from teachable_eye.evalset import EvalStore  # noqa: E402
from teachable_eye.evaluation import evaluate  # noqa: E402
from teachable_eye.tasks import AUGMENT, object_memory_dir  # noqa: E402


def taught_views(server):
    """[{id, label, crop, thumb}] of the objects memory."""
    try:
        with urllib.request.urlopen(f"{server}/api/memory?task=objects", timeout=5) as r:
            labels = json.load(r)["labels"]
        print(f"taught views from the running server ({server})")
    except OSError:
        from teachable_eye.memory import TaskMemory
        mem = TaskMemory(object_memory_dir(config.OBJECT_ENCODER),
                         encoder_dim(config.OBJECT_ENCODER), "objects", config.OBJECTS)
        try:
            labels = mem.labels()
        finally:
            mem.close()
        print("taught views read from the memory folder (server not running)")
    return [e for g in labels for e in g["examples"]]


def picture(view):
    for folder, name in (("crops", view.get("crop")), ("thumbs", view.get("thumb"))):
        if name:
            img = cv2.imread(str(config.DATA_DIR / folder / "objects" / name))
            if img is not None:
                return img
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--encoders", default=",".join(ENCODERS),
                    help="comma-separated (default: all registered)")
    ap.add_argument("--server", default=f"http://127.0.0.1:{config.PORT}")
    args = ap.parse_args()

    views = [(v, picture(v)) for v in taught_views(args.server)]
    views = [(v, img) for v, img in views if img is not None]
    store = EvalStore("objects")
    items = store.items()
    tests = [store.image(it["id"]) for it in items]
    if not views or not items:
        raise SystemExit("need taught views and test views (🧪 Test set in the app)")
    print(f"{len(views)} taught views, {len(items)} test views")

    rows, reports = [], {}
    for name in [e.strip() for e in args.encoders.split(",") if e.strip()]:
        enc = get_encoder(name)
        enc.embed([views[0][1]])                          # load + warm up
        started = time.perf_counter()
        points = []
        for v, img in views:
            vec = enc.embed([img])[0]
            points.append({"id": v["id"], "label": v["label"], "parent": None,
                           "aug": None, "vector": vec})
            variants = [fn(img) for fn in AUGMENT["objects"]] if config.AUGMENT else []
            for fn, vv in zip(AUGMENT["objects"], enc.embed(variants) if variants else []):
                points.append({"id": f"{v['id']}-{fn.__name__}", "label": v["label"],
                               "parent": v["id"], "aug": fn.__name__, "vector": vv})
        test_items = [dict(it, vector=vec) for it, vec in zip(items, enc.embed(tests))]
        n_pics = len(views) * (1 + len(AUGMENT["objects"])) + len(tests)
        ms = 1000 * (time.perf_counter() - started) / n_pics
        t, m = config.DEFAULT_OBJECT_BANDS.get(name, (0.9, 0.05))
        r = evaluate(points, test_items, config.TaskThresholds(t, m),
                     encoder=name, extras=False)
        for it in r["items"]:
            it.pop("vector", None)
        reports[name] = r
        rec, sep = r["recommended"], r["separation"]
        rows.append({"encoder": name, "auc": sep["auc"], "gap": sep["gap"], "top1": r["top1"],
                     "safe_correct": rec["correct"], "taught_tests": rec["enrolled"],
                     "strangers_rejected": rec["rejected"], "strangers": rec["strangers"],
                     "threshold": rec["threshold"], "ms_per_image": round(ms, 1)})
        print(f"  {name:14s} AUC {sep['auc']}  gap {sep['gap']}  correct with no dangerous "
              f"error {rec['correct']}/{rec['enrolled']} at {rec['threshold']}  {ms:.1f} ms/img")

    stamp = time.strftime("%Y%m%d-%H%M%S")
    out = config.DATA_DIR / "reports"
    out.mkdir(parents=True, exist_ok=True)
    (out / f"compare-objects-{stamp}.json").write_text(
        json.dumps({"rows": rows, "reports": reports}, indent=1, ensure_ascii=False), encoding="utf-8")
    pct = lambda a, b: f"{100 * a / b:.0f}%" if b else "—"  # noqa: E731
    md = [f"# Encoder comparison — {time.strftime('%Y-%m-%d %H:%M')}", "",
          f"{len(views)} taught views (crops or thumbnails, + variants), {len(items)} test views.", "",
          "| encoder | AUC | gap | nearest-label acc. | correct, no dangerous error | strangers → unknown | threshold | ms/img |",
          "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        md.append(f"| {r['encoder']} | {r['auc']} | {r['gap']} | "
                  f"{pct(r['top1'] or 0, 1) if r['top1'] is not None else '—'} | "
                  f"{r['safe_correct']}/{r['taught_tests']} ({pct(r['safe_correct'], r['taught_tests'])}) | "
                  f"{r['strangers_rejected']}/{r['strangers']} | {r['threshold']} | {r['ms_per_image']} |")
    md += ["", "Correct = named right with the threshold set just above every dangerous "
           "score of that encoder. Small test sets make this optimistic."]
    (out / f"compare-objects-{stamp}.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"report: {out / f'compare-objects-{stamp}.md'}")


if __name__ == "__main__":
    main()
