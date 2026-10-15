"""Per-track smoothing so a live label does not flicker (R8).

Each stable track is re-queried every couple of seconds. One borderline
query should not flip a label the previous ones agreed on, so the displayed
decision is the majority of the last `window` decisions. With no majority the
previous display is kept.
"""
from collections import Counter, deque

from teachable_eye.policy import KNOWN, UNCERTAIN, UNKNOWN


class LabelVote:
    def __init__(self, window=3):
        self.window = window
        self.history = deque(maxlen=window)
        self.shown = None   # the last Decision displayed

    def add(self, decision):
        """Record one Decision; return the Decision to display."""
        self.history.append(decision)
        if self.shown is None:
            self.shown = decision
            return decision
        keys = Counter(self._key(d) for d in self.history)
        best, count = keys.most_common(1)[0]
        if count * 2 > len(self.history):
            # newest decision carrying the winning key (fresh score/neighbours)
            for d in reversed(self.history):
                if self._key(d) == best:
                    self.shown = d
                    break
        return self.shown

    @staticmethod
    def _key(d):
        if d.decision == KNOWN:
            return (KNOWN, d.label)
        if d.decision == UNCERTAIN:
            return (UNCERTAIN, d.guess)
        return (UNKNOWN, None)
