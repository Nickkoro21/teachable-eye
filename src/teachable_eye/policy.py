"""The decision policy: known / uncertain / unknown, with the evidence.

A memory always returns its nearest example, however poor the match (course
L5). The policy turns that score into a decision a person can trust:

    score >= threshold                       -> known      (label shown)
    threshold - margin <= score < threshold  -> uncertain  (label only as a guess)
    below, or nothing taught                 -> unknown
"""
from dataclasses import dataclass, field

KNOWN, UNCERTAIN, UNKNOWN = "known", "uncertain", "unknown"


@dataclass
class Neighbour:
    id: str
    label: str
    score: float
    thumb: str | None = None
    aug: str | None = None        # set when the best match was a variant


@dataclass
class Decision:
    decision: str                 # known | uncertain | unknown
    label: str | None             # set only when known
    guess: str | None             # nearest label when uncertain (display only)
    score: float                  # best similarity, 0.0 when memory is empty
    neighbours: list[Neighbour] = field(default_factory=list)
    # best score of each nearby LABEL, best first: what else it could be and
    # by how much, so the user sees what to teach to tell two things apart
    candidates: list[tuple[str, float]] = field(default_factory=list)

    def to_json(self):
        return {
            "decision": self.decision,
            "label": self.label,
            "guess": self.guess,
            "score": round(self.score, 4),
            "neighbours": [
                {"id": n.id, "label": n.label, "score": round(n.score, 4),
                 "thumb": n.thumb, "aug": n.aug} for n in self.neighbours
            ],
            "candidates": [{"label": lb, "score": round(sc, 4)}
                           for lb, sc in self.candidates],
        }


def at_most_uncertain(d):
    """The same evidence shown as a guess, never as a name: for a face too
    small to be sure of (R57). Everything but a `known` passes unchanged."""
    if d.decision != KNOWN:
        return d
    return Decision(UNCERTAIN, None, d.label, d.score, d.neighbours, d.candidates)


def decide(neighbours, thresholds):
    """Apply the bands to neighbours sorted best-first."""
    if not neighbours:
        return Decision(UNKNOWN, None, None, 0.0, [])
    top = neighbours[0]
    if top.score >= thresholds.threshold:
        return Decision(KNOWN, top.label, None, top.score, neighbours)
    if top.score >= thresholds.threshold - thresholds.margin:
        return Decision(UNCERTAIN, None, top.label, top.score, neighbours)
    return Decision(UNKNOWN, None, None, top.score, neighbours)
