"""Turning typed names and spoken sentences into labels (EN + EL).

Adapted from https-deeplearning-ai/sc-on-device-ai-memory, robot/brain/labels.py
(Apache-2.0). Changes: Greek phrases, Greek clause words, article stripping.
"""
import re

# ASR drops the punctuation that would end the naming clause, so the label
# also stops at words that start a new clause ("...my mug I bought it").
_CLAUSE_WORDS = {
    # en
    "i", "it", "and", "that", "which", "because", "she", "he", "they", "we",
    "you", "made", "bought", "got", "from", "at", "about", "in", "on",
    # el
    "και", "που", "το", "αγόρασα", "πήρα", "από", "στο", "στη", "στην",
    "γιατί", "επειδή", "μου", "έφτιαξε",
}
_LEADING = {
    "a", "an", "the", "my",                          # en
    "ο", "η", "το", "οι", "τα", "ένα", "ένας", "μια", "μία",  # el
}
_PATTERNS = [
    r"this is (.+?)(?:\s*[,.;!?—–-]|$)",
    r"that'?s (.+?)(?:\s*[,.;!?—–-]|$)",
    r"αυτ[όοήηάα]ς? (?:είναι|ειναι) (.+?)(?:\s*[,.;!;?·—–-]|$)",
    r"(?:είναι|ειναι) (.+?)(?:\s*[,.;!;?·—–-]|$)",
]
MAX_WORDS = 5


def norm_label(text):
    """A typed name: collapsed whitespace, lowercased. Labels are exact keys."""
    return " ".join((text or "").split()).lower()


def parse_label(transcript):
    """'This is my mug, Maria made it.' -> 'mug'; «Αυτό είναι το καπέλο μου» -> 'καπέλο'.

    Returns None when the transcript is empty, so silence never becomes a label.
    """
    text = (transcript or "").strip()
    if not text:
        return None
    phrase = text
    for pattern in _PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            phrase = m.group(1)
            break
    words = [w.strip(".,!?;·") for w in phrase.split()]
    while words and words[0].lower() in _LEADING:
        words = words[1:]
    kept = []
    for w in words:
        if w.lower() in _CLAUSE_WORDS:
            break
        kept.append(w)
    label = norm_label(" ".join(kept[:MAX_WORDS]))
    return label or None
