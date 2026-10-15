"""A6: label parsing for typed names and spoken sentences (EN + EL)."""
import pytest

from teachable_eye.labels import norm_label, parse_label


@pytest.mark.parametrize("said, label", [
    ("This is my hat", "hat"),
    ("this is a red microphone, I bought it yesterday", "red microphone"),
    ("That's the coffee mug", "coffee mug"),
    ("Αυτό είναι το καπέλο μου", "καπέλο"),
    ("αυτό είναι ένα μικρόφωνο", "μικρόφωνο"),
    ("Αυτή είναι η κούπα που αγόρασα", "κούπα"),
    ("water bottle", "water bottle"),
])
def test_parse(said, label):
    assert parse_label(said) == label


@pytest.mark.parametrize("silence", ["", "   ", None])
def test_silence_is_not_a_label(silence):
    assert parse_label(silence) is None


def test_norm_label():
    assert norm_label("  Water   Bottle ") == "water bottle"
