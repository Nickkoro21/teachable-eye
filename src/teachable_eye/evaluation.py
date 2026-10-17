"""Evaluation: how well does memory recognise pictures it never saw (R35)?

Inputs are plain arrays, so the same code serves the server (vectors read
from the live memory) and tools/evaluate.py (vectors re-embedded with other
encoders):

    points  memory: [{"id", "label", "parent", "aug", "vector"}]  (variants
            have a parent; they count as their view, as in recognition)
    items   test set: [{"id", "label", "vector"}]

A test label that memory does not know is a *stranger*: the right answer
for it is `unknown`. Outcomes per test view, for bands (threshold, margin):

    taught label   correct | wrong (dangerous) | uncertain | missed
    stranger       rejected | false_accept (dangerous) | uncertain

"Dangerous" is any confident wrong name. The recommended threshold is the
lowest one with no dangerous errors on this test set (most correct answers
without a confident mistake); the margin is set so that most strangers fall
below the uncertain band. Small test sets make this optimistic: the report
says how many views it rests on.
"""
import math
import time

import numpy as np

KNOWN, UNCERTAIN, UNKNOWN = "known", "uncertain", "unknown"
STEP = 0.005               # threshold sweep resolution
MARGIN_RANGE = (0.02, 0.15)
CURVE_REPEATS = 20


def _unit(m):
    m = np.asarray(m, dtype=np.float32)
    if m.ndim == 1:
        m = m[None, :]
    n = np.linalg.norm(m, axis=1, keepdims=True)
    n[n == 0] = 1.0
    return m / n


class Memory:
    """Memory points grouped by taught view (a view + its variants)."""

    def __init__(self, points, with_variants=True):
        points = [p for p in points if with_variants or not p.get("parent")]
        roots = []
        index = {}
        for p in points:
            root = p.get("parent") or p["id"]
            if root not in index:
                index[root] = len(roots)
                roots.append(root)
        self.roots = roots
        self.owner = np.array([index[p.get("parent") or p["id"]] for p in points], dtype=int)
        self.vectors = _unit([p["vector"] for p in points]) if points else np.zeros((0, 1))
        label_of = {}
        for p in points:
            label_of.setdefault(p.get("parent") or p["id"], p["label"])
        self.root_labels = [label_of[r] for r in roots]
        self.labels = sorted(set(self.root_labels))
        self.points = points

    def subset(self, keep_roots):
        keep = set(keep_roots)
        return Memory([p for p in self.points if (p.get("parent") or p["id"]) in keep])

    def root_scores(self, queries):
        """(n_queries, n_roots): best cosine to each view or its variants."""
        q = _unit(queries)
        s = q @ self.vectors.T
        out = np.full((q.shape[0], len(self.roots)), -1.0, dtype=np.float32)
        for r in range(len(self.roots)):
            out[:, r] = s[:, self.owner == r].max(axis=1)
        return out


def score_items(memory, items):
    """Per test view: the nearest label and score, plus the best score of
    its own label (genuine) and of any other label (impostor)."""
    if not items or not memory.roots:
        return []
    rs = memory.root_scores([it["vector"] for it in items])
    labels = np.array(memory.root_labels)
    rows = []
    for it, scores in zip(items, rs):
        top = int(np.argmax(scores))
        own = labels == it["label"]
        rows.append({
            "id": it.get("id"), "label": it["label"],
            "enrolled": bool(own.any()),
            "top_label": str(labels[top]), "score": float(scores[top]),
            "genuine": float(scores[own].max()) if own.any() else None,
            "impostor": float(scores[~own].max()) if (~own).any() else None,
        })
    return rows


def outcome(row, threshold, margin):
    s = row["score"]
    decision = KNOWN if s >= threshold else UNCERTAIN if s >= threshold - margin else UNKNOWN
    if row["enrolled"]:
        if decision == KNOWN:
            return "correct" if row["top_label"] == row["label"] else "wrong"
        return "uncertain" if decision == UNCERTAIN else "missed"
    if decision == KNOWN:
        return "false_accept"
    return "uncertain" if decision == UNCERTAIN else "rejected"


OUTCOMES = ("correct", "wrong", "uncertain", "missed", "rejected", "false_accept")


def tally(rows, threshold, margin):
    counts = {k: 0 for k in OUTCOMES}
    for r in rows:
        counts[outcome(r, threshold, margin)] += 1
    enrolled = sum(r["enrolled"] for r in rows)
    strangers = len(rows) - enrolled
    counts.update(
        threshold=round(threshold, 3), margin=round(margin, 3),
        enrolled=enrolled, strangers=strangers,
        dangerous=counts["wrong"] + counts["false_accept"],
        correct_rate=_rate(counts["correct"], enrolled),
        reject_rate=_rate(counts["rejected"], strangers),
        dangerous_rate=_rate(counts["wrong"] + counts["false_accept"], len(rows)),
    )
    return counts


def _rate(n, d):
    return round(n / d, 4) if d else None


def confusion(rows, threshold, margin):
    """{true label: {predicted label | 'uncertain' | 'unknown': count}}."""
    table = {}
    for r in rows:
        s = r["score"]
        pred = r["top_label"] if s >= threshold else UNCERTAIN if s >= threshold - margin else UNKNOWN
        cell = table.setdefault(r["label"], {})
        cell[pred] = cell.get(pred, 0) + 1
    return table


def sweep(rows, lo=None, hi=None):
    scores = [r["score"] for r in rows]
    if not scores:
        return []
    lo = math.floor((min(scores) if lo is None else lo) * 100) / 100 - 0.05
    hi = math.ceil((max(scores) if hi is None else hi) * 100) / 100 + 0.02
    out = []
    for t in np.arange(lo, hi + 1e-9, STEP):
        c = tally(rows, float(t), 0.0)
        out.append({"t": round(float(t), 3), "correct": c["correct"], "wrong": c["wrong"],
                    "false_accept": c["false_accept"], "dangerous": c["dangerous"]})
    return out


def recommend(rows, current):
    """Lowest threshold with no confident mistake; margin from the strangers."""
    danger = [r["score"] for r in rows
              if (r["enrolled"] and r["top_label"] != r["label"]) or not r["enrolled"]]
    correct = [r["score"] for r in rows if r["enrolled"] and r["top_label"] == r["label"]]
    strangers = [r["score"] for r in rows if not r["enrolled"]]
    notes = []
    if danger:
        t = math.floor(max(danger) / STEP + 1) * STEP       # just above the worst
        basis = "lowest threshold with zero dangerous errors on the test set"
    elif correct:
        t = min(current.threshold, math.floor(min(correct) * 100) / 100)
        basis = "no wrong-label or stranger scores to stay above; kept at or below the current threshold"
        notes.append("No strangers and no confusions in the test set: the unknown side "
                     "is not calibrated. Add never-taught objects to the test set.")
    else:
        t = current.threshold
        basis = "nothing to calibrate on"
    if strangers:
        p90 = float(np.percentile(strangers, 90))
        m = min(max(t - p90, MARGIN_RANGE[0]), MARGIN_RANGE[1])
    else:
        m = current.margin
        notes.append("No strangers in the test set: margin kept as configured.")
    return round(t, 3), round(m, 3), basis, notes


def separation(rows):
    """How far apart same-object and different-object scores are."""
    genuine = [r["genuine"] for r in rows if r["genuine"] is not None]
    impostor = [r["impostor"] for r in rows if r["impostor"] is not None]
    if not genuine or not impostor:
        return {"auc": None, "genuine_min": None, "impostor_max": None, "gap": None}
    g, i = np.array(genuine), np.array(impostor)
    auc = float(((g[:, None] > i[None, :]).sum() + 0.5 * (g[:, None] == i[None, :]).sum())
                / (len(g) * len(i)))
    return {"auc": round(auc, 4), "genuine_min": round(float(g.min()), 4),
            "impostor_max": round(float(i.max()), 4),
            "gap": round(float(g.min() - i.max()), 4)}


def top1(rows):
    enrolled = [r for r in rows if r["enrolled"]]
    return _rate(sum(r["top_label"] == r["label"] for r in enrolled), len(enrolled))


def views_curve(memory, items, threshold, margin, seed=0):
    """Accuracy with only n taught views per label (n = 1, 2, ...)."""
    rng = np.random.default_rng(seed)
    by_label = {}
    for root, label in zip(memory.roots, memory.root_labels):
        by_label.setdefault(label, []).append(root)
    most = max((len(v) for v in by_label.values()), default=0)
    out = []
    for n in range(1, min(most, 10) + 1):
        accs, rates = [], []
        for _ in range(CURVE_REPEATS if most > 1 else 1):
            keep = []
            for roots in by_label.values():
                pick = rng.choice(len(roots), size=min(n, len(roots)), replace=False)
                keep += [roots[i] for i in pick]
            rows = score_items(memory.subset(keep), items)
            accs.append(top1(rows) or 0.0)
            rates.append(tally(rows, threshold, margin)["correct_rate"] or 0.0)
        out.append({"views": n, "top1": round(float(np.mean(accs)), 4),
                    "correct_rate": round(float(np.mean(rates)), 4)})
    return out


def classifier_baseline(memory, items, rows):
    """Logistic regression trained on the same memory, for comparison."""
    if len(memory.labels) < 2:
        return {"skipped": "needs at least two taught labels"}
    try:
        from sklearn.linear_model import LogisticRegression
    except ImportError:
        return {"skipped": "scikit-learn not installed"}
    y = np.array([memory.root_labels[o] for o in memory.owner])
    clf = LogisticRegression(max_iter=2000, C=10.0).fit(memory.vectors, y)
    q = _unit([it["vector"] for it in items])
    prob = clf.predict_proba(q)
    pred = clf.classes_[prob.argmax(1)]
    conf = prob.max(1)
    enrolled = np.array([r["enrolled"] for r in rows])
    truth = np.array([it["label"] for it in items])
    right = (pred == truth) & enrolled
    bad = (~enrolled) | (enrolled & (pred != truth))
    # the lowest confidence cut with no confident mistake, as for k-NN
    cut = float(conf[bad].max()) + 1e-6 if bad.any() else 0.0
    covered = right & (conf >= cut)
    knn_cut = recommend(rows, _Bands(1.0, 0.0))[0]
    return {
        "logreg_top1": _rate(int(right.sum()), int(enrolled.sum())),
        "knn_top1": top1(rows),
        "logreg_safe_correct_rate": _rate(int(covered.sum()), int(enrolled.sum())),
        "knn_safe_correct_rate": tally(rows, knn_cut, 0.0)["correct_rate"],
        "note": "Logistic regression must be retrained after every teach; "
                "k-NN memory learns from one example at once.",
    }


class _Bands:
    def __init__(self, threshold, margin):
        self.threshold, self.margin = threshold, margin


def evaluate(points, items, bands, task="objects", encoder=None, extras=True):
    """The full report as a dict (see to_markdown for its reading)."""
    started = time.perf_counter()
    memory = Memory(points)
    rows = score_items(memory, items)
    rec_t, rec_m, basis, notes = recommend(rows, bands)
    test_labels = {}
    for r in rows:
        e = test_labels.setdefault(r["label"], {"views": 0, "taught": r["enrolled"]})
        e["views"] += 1
    report = {
        "task": task, "encoder": encoder,
        "created": time.strftime("%Y-%m-%d %H:%M:%S"),
        "memory": {"labels": len(memory.labels), "views": len(memory.roots),
                   "points": len(memory.points)},
        "test": {"views": len(rows), "taught": sum(r["enrolled"] for r in rows),
                 "strangers": sum(not r["enrolled"] for r in rows), "labels": test_labels},
        "current": dict(tally(rows, bands.threshold, bands.margin),
                        confusion=confusion(rows, bands.threshold, bands.margin)),
        "recommended": dict(tally(rows, rec_t, rec_m), basis=basis,
                            confusion=confusion(rows, rec_t, rec_m)),
        "top1": top1(rows),
        "separation": separation(rows),
        "notes": notes,
        "items": [dict(r, outcome=outcome(r, bands.threshold, bands.margin)) for r in rows],
    }
    if not rows:
        report["notes"].append("Nothing to evaluate: teach some objects and save test views.")
        return report
    if extras:
        report["sweep"] = sweep(rows)
        if any(p.get("parent") for p in points):
            plain = score_items(Memory(points, with_variants=False), items)
            p_t = recommend(plain, bands)[0]
            report["augmentation"] = {
                "with_top1": top1(rows), "without_top1": top1(plain),
                "with_safe_correct_rate": report["recommended"]["correct_rate"],
                "without_safe_correct_rate": tally(plain, p_t, 0.0)["correct_rate"],
                "without_recommended_threshold": p_t,
            }
        report["views_curve"] = views_curve(memory, items, rec_t, rec_m)
        report["classifier"] = classifier_baseline(memory, items, rows)
    report["seconds"] = round(time.perf_counter() - started, 2)
    return report


def profile_summary(r, points):
    """The few numbers that decide between augmentation profiles."""
    rec = r["recommended"]
    return {"points": points, "top1": r["top1"], "auc": r["separation"]["auc"],
            "threshold": rec["threshold"], "correct": rec["correct"],
            "enrolled": rec["enrolled"], "correct_rate": rec["correct_rate"],
            "rejected": rec["rejected"], "strangers": rec["strangers"],
            "dangerous_at_current": r["current"]["dangerous"]}


def _pct(x):
    return "—" if x is None else f"{100 * x:.0f}%"


def to_markdown(r):
    """A plain report a person can read (English; Claude can translate)."""
    cur, rec = r["current"], r["recommended"]
    lines = [
        f"# Evaluation — {r['task']}" + (f" ({r['encoder']})" if r.get("encoder") else ""),
        "", f"{r['created']} · memory: {r['memory']['labels']} labels, "
        f"{r['memory']['views']} taught views · test set: {r['test']['views']} views "
        f"({r['test']['taught']} of taught things, {r['test']['strangers']} strangers)", "",
        "## Headline", "",
        "| bands | correct | dangerous | uncertain | missed | strangers rejected |",
        "|---|---|---|---|---|---|",
    ]
    for name, c in (("current", cur), ("recommended", rec)):
        lines.append(
            f"| {name} {c['threshold']:.2f} / {c['margin']:.2f} | {c['correct']}/{c['enrolled']} "
            f"({_pct(c['correct_rate'])}) | **{c['dangerous']}** | {c['uncertain']} | "
            f"{c['missed']} | {c['rejected']}/{c['strangers']} ({_pct(c['reject_rate'])}) |")
    lines += ["", f"Recommended threshold: {rec['basis']}.", "",
              "*Dangerous* = a confident wrong name (wrong label, or a stranger taken for "
              "something taught). It must stay at zero.", ""]
    sep = r["separation"]
    if sep["auc"] is not None:
        lines += ["## Separation", "",
                  f"AUC {sep['auc']:.3f} · lowest same-object score {sep['genuine_min']:.3f} · "
                  f"highest different-object score {sep['impostor_max']:.3f} · gap {sep['gap']:+.3f}",
                  ""]
    if r.get("top1") is not None:
        lines += [f"Nearest-label accuracy (no threshold): {_pct(r['top1'])}.", ""]
    if r.get("augmentation"):
        a = r["augmentation"]
        lines += ["## Teach-time augmentation", "",
                  "| | nearest-label accuracy | correct with no dangerous error |", "|---|---|---|",
                  f"| with variants | {_pct(a['with_top1'])} | {_pct(a['with_safe_correct_rate'])} |",
                  f"| without | {_pct(a['without_top1'])} | {_pct(a['without_safe_correct_rate'])} |", ""]
    if r.get("profiles"):
        lines += ["## Augmentation profiles (same views, same test set)", "",
                  "| profile | memory points | nearest-label acc. | AUC | correct, no dangerous error "
                  "| strangers → unknown | dangerous at current bands |",
                  "|---|---|---|---|---|---|---|"]
        for name, p in r["profiles"].items():
            lines.append(f"| {name} | {p['points']} | {_pct(p['top1'])} | "
                         f"{'—' if p['auc'] is None else f'{p['auc']:.3f}'} | "
                         f"{p['correct']}/{p['enrolled']} at {p['threshold']:.2f} | "
                         f"{p['rejected']}/{p['strangers']} | {p['dangerous_at_current']} |")
        lines += ["", "Choose the profile with more correct answers and no more dangerous "
                  "errors; set it with AUGMENT in .env, then Memory → Update variants.", ""]
    if r.get("views_curve"):
        lines += ["## Views needed", "", "| views per label | nearest-label accuracy | correct (recommended bands) |",
                  "|---|---|---|"]
        lines += [f"| {v['views']} | {_pct(v['top1'])} | {_pct(v['correct_rate'])} |"
                  for v in r["views_curve"]]
        lines.append("")
    c = r.get("classifier")
    if c and "skipped" not in c:
        lines += ["## Memory (k-NN) vs a trained classifier", "",
                  "| | accuracy | correct with no dangerous error |", "|---|---|---|",
                  f"| k-NN memory | {_pct(c['knn_top1'])} | {_pct(c['knn_safe_correct_rate'])} |",
                  f"| logistic regression | {_pct(c['logreg_top1'])} | {_pct(c['logreg_safe_correct_rate'])} |",
                  "", c["note"], ""]
    lines += ["## Per label (current bands)", "", "| label | taught | test views | answers |",
              "|---|---|---|---|"]
    for label, info in sorted(r["test"]["labels"].items()):
        answers = ", ".join(f"{k} {v}" for k, v in sorted(
            cur["confusion"].get(label, {}).items(), key=lambda kv: -kv[1]))
        lines.append(f"| {label} | {'yes' if info['taught'] else 'no (stranger)'} | "
                     f"{info['views']} | {answers} |")
    if r.get("notes"):
        lines += ["", "## Notes", ""] + [f"- {n}" for n in r["notes"]]
    lines += ["", f"Test views: {r['test']['views']}. With few views, rates are rough; "
              "collect more before changing thresholds for good."]
    return "\n".join(lines) + "\n"
