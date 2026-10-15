"""Aim-to-teach target selection (feedback from the first phone test)."""
from teachable_eye.tasks import is_background, pick_focus

TABLE = [0.0, 0.25, 1.0, 0.55]     # a plank strip spanning the frame
LIGHTER = [0.42, 0.20, 0.56, 0.40]
WALL = [0.0, 0.0, 0.6, 0.3]        # touches top + left


def test_background_touches_two_edges():
    assert is_background(TABLE)
    assert is_background(WALL)
    assert not is_background(LIGHTER)


def test_smallest_box_under_reticle_wins():
    boxes = {1: TABLE, 2: LIGHTER, 3: [0.3, 0.1, 0.7, 0.6]}
    assert pick_focus(boxes, aim=(0.5, 0.3)) == 2


def test_background_never_focus():
    assert pick_focus({1: TABLE, 2: WALL}) is None


def test_nearest_when_nothing_under_aim():
    boxes = {1: TABLE, 2: [0.05, 0.6, 0.2, 0.8], 3: [0.55, 0.55, 0.7, 0.7]}
    assert pick_focus(boxes, aim=(0.5, 0.5)) == 3
