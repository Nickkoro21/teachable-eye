"""Optional help from Claude (Anthropic API) — off unless ASSIST=on (R36-R40).

The app works fully without it. When it is on, the user asks for help one
action at a time; Claude never decides anything on its own:

    suggest_names   names for the boxes of a photo (Label all); the user
                    still reviews and saves every label
    second_opinion  is this the same object as the nearest taught ones?
                    (shown next to the memory's own answer, never instead)
    write_summary   an evaluation report rewritten for non-specialists
    ask_memory      questions answered from memory *metadata* (no pictures)

Privacy rules, enforced here and tested:
  * objects only — the people task is refused;
  * a crop is checked for faces (YuNet) and never sent if it shows one;
  * pictures are sent as small JPEGs (<= 384 px), nothing is stored remotely
    by this app; the key comes only from ANTHROPIC_API_KEY.
Every call is logged locally (tokens only) to data/reports/assist-usage.jsonl.
"""
import base64
import json
import os
import time

import cv2

from teachable_eye import config

FALLBACK_BETA = "server-side-fallback-2026-07-01"
SEND_SIDE = 384
LANGS = {"en": "English", "el": "Greek"}


class AssistError(RuntimeError):
    """A user-facing reason why Claude's help is not available right now."""


_client = None


def set_client(client):
    """Use this client instead of anthropic.Anthropic() (tests)."""
    global _client
    _client = client


def _get_client():
    global _client
    if _client is None:
        import anthropic
        _client = anthropic.Anthropic(timeout=90.0, max_retries=2)
    return _client


def status():
    key = bool(os.environ.get("ANTHROPIC_API_KEY")) or _client is not None
    return {"enabled": config.ASSIST, "key": key,
            "ready": config.ASSIST and key, "model": config.ASSIST_MODEL}


def _check(task="objects"):
    if not config.ASSIST:
        raise AssistError("Claude help is off on the PC (set ASSIST=on in .env)")
    if not status()["key"]:
        raise AssistError("no Anthropic API key on the PC (ANTHROPIC_API_KEY)")
    if task != "objects":
        raise AssistError("Claude help is for objects only; faces never leave the device")


def _image(img):
    h, w = img.shape[:2]
    s = min(1.0, SEND_SIDE / max(h, w))
    if s < 1.0:
        img = cv2.resize(img, (max(1, int(w * s)), max(1, int(h * s))),
                         interpolation=cv2.INTER_AREA)
    data = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])[1].tobytes()
    return {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                        "data": base64.standard_b64encode(data).decode()}}


def _sendable(img):
    """A picture may leave the device only without a face in it."""
    from teachable_eye.faces import has_face
    return img is not None and img.size > 0 and not has_face(img)


def _log(kind, resp):
    try:
        u = resp.usage
        row = {"ts": time.time(), "kind": kind, "model": getattr(resp, "model", None),
               "input_tokens": getattr(u, "input_tokens", None),
               "output_tokens": getattr(u, "output_tokens", None)}
        folder = config.DATA_DIR / "reports"
        folder.mkdir(parents=True, exist_ok=True)
        with open(folder / "assist-usage.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
    except Exception:                       # logging must never break a call
        pass


def _call(kind, system, content, schema=None, effort="low", max_tokens=8000):
    import anthropic
    output_config = {"effort": effort}
    if schema:
        output_config["format"] = {"type": "json_schema", "schema": schema}
    try:
        resp = _get_client().beta.messages.create(
            model=config.ASSIST_MODEL, max_tokens=max_tokens, system=system,
            messages=[{"role": "user", "content": content}],
            output_config=output_config,
            # a declined request is retried server-side on the recommended model
            betas=[FALLBACK_BETA], fallbacks="default",
        )
    except anthropic.AuthenticationError:
        raise AssistError("the Anthropic API key was rejected") from None
    except anthropic.RateLimitError:
        raise AssistError("too many requests to Claude; try again in a minute") from None
    except anthropic.APIConnectionError:
        raise AssistError("cannot reach the Anthropic API (internet?)") from None
    except anthropic.APIStatusError as exc:
        raise AssistError(f"Anthropic API error {exc.status_code}") from None
    _log(kind, resp)
    if resp.stop_reason == "refusal":
        raise AssistError("Claude declined this request")
    if resp.stop_reason == "max_tokens":
        raise AssistError("Claude's answer was cut off")
    text = "".join(b.text for b in resp.content if b.type == "text").strip()
    if not schema:
        return text
    try:
        return json.loads(text)
    except ValueError:
        raise AssistError("Claude's answer could not be read") from None


# -- name suggestions (Label all) ------------------------------------------------

NAMES_SCHEMA = {
    "type": "object",
    "properties": {"items": {"type": "array", "items": {
        "type": "object",
        "properties": {"index": {"type": "integer"}, "name": {"type": "string"},
                       "confident": {"type": "boolean"}},
        "required": ["index", "name", "confident"], "additionalProperties": False}}},
    "required": ["items"], "additionalProperties": False,
}


# System prompts follow Anthropic's prompting guidance for Claude Opus 5.5 /
# Sonnet 5.5: say who it is for and *why* (the person confirms everything, a
# confident wrong answer costs more than "unsure"), describe the data in XML
# tags, ask for what to do rather than lists of don'ts, and let effort (not
# "think less" wording) control depth. Output shape comes from a JSON schema.
NAMES_SYSTEM = """\
You suggest names for objects in a person's private visual memory app. The app \
runs on their own PC; they photograph things at home, at work and outdoors, and \
teach the app a name for each one so it can recognise them later. You see crops \
of the boxes found in one photo, in <crop> tags. Your names only pre-fill a form: \
the person reviews every one before saving, so a clear "not sure" helps them more \
than a confident guess that is wrong.

For each crop, give the everyday name a person would say for that thing: 1-3 \
words, lower case, without an article (for example "coffee mug", "car keys", \
"κούπα", "κλειδιά"). Name the kind of thing you can see; owners, brands or \
contents belong in the name only when they are clearly visible.

<existing_labels> lists what this person has already taught. When a crop shows \
the same kind of thing, reuse their wording, so the memory stays consistent (if \
they say "κούπα", do not answer "φλιτζάνι"). It may still be a different item \
of that kind, so drop personal parts of a label such as an owner's name.

Set confident to false when the crop is blurred, cut off or ambiguous. When a \
crop shows only background (a wall, a floor, a table top), give that surface's \
name with confident false. Return exactly one item per crop, with index equal \
to the crop's index."""


def suggest_names(crops, known_labels=(), lang="en", task="objects"):
    """One suggestion per crop: {"name", "confident", "skipped"}.

    `skipped` crops (a face in them, or empty) were not sent; their name is "".
    """
    _check(task)
    send = [i for i, c in enumerate(crops) if _sendable(c)]
    out = [{"name": "", "confident": False, "skipped": i not in send}
           for i in range(len(crops))]
    if not send:
        return out
    language = LANGS.get(lang, "English")
    # pictures first, then the instructions (Anthropic's guidance for vision)
    content = []
    for n, i in enumerate(send, 1):
        content += [{"type": "text", "text": f"<crop index=\"{n}\">"}, _image(crops[i]),
                    {"type": "text", "text": "</crop>"}]
    known = "\n".join(sorted(set(known_labels))[:200]) or "(none yet)"
    content.append({"type": "text", "text":
                    f"<existing_labels>\n{known}\n</existing_labels>\n\n"
                    f"Suggest a name in {language} for each of the {len(send)} crops."})
    system = NAMES_SYSTEM
    data = _call("names", system, content, NAMES_SCHEMA, effort="low")
    for item in data.get("items", []):
        n = item.get("index")
        if isinstance(n, int) and 1 <= n <= len(send):
            out[send[n - 1]].update(name=str(item.get("name", "")).strip()[:60],
                                    confident=bool(item.get("confident")))
    return out


# -- second opinion -----------------------------------------------------------------

OPINION_SCHEMA = {
    "type": "object",
    "properties": {
        "match": {"type": "string"},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "reason": {"type": "string"},
    },
    "required": ["match", "confidence", "reason"], "additionalProperties": False,
}


OPINION_SYSTEM = """\
You give a second opinion to a private object-recognition app. The app's own \
memory compared the picture in <query> with the items the person has taught, and \
was not sure. Each <candidate> shows one or two taught pictures of one of the \
nearest items, under its label.

These are personal items, so the question is whether the query shows the same \
physical item, not just the same kind of thing: compare colour, markings, text, \
shape and wear, and allow for different light, angle and distance. Set match to \
the candidate's label exactly when you think it is that item; set it to an empty \
string when it is none of them or the pictures do not let you tell. Your answer \
is shown next to the app's own, and the person decides, so state your confidence \
honestly: "low" whenever the pictures are too small, blurred or alike to be sure. \
Give the reason in one or two short sentences, naming what you compared."""


def second_opinion(query, candidates, lang="en", task="objects"):
    """Is `query` the same physical object as one of the candidates?

    `candidates`: [(label, [example crops])], nearest first. Returns
    {"match": label or "", "confidence", "reason"}. Advice only.
    """
    _check(task)
    if not _sendable(query):
        raise AssistError("this picture shows a face, so it stays on the device")
    content = [{"type": "text", "text": "<query>"}, _image(query),
               {"type": "text", "text": "</query>"}]
    labels = []
    for label, examples in candidates:
        pics = [e for e in examples if _sendable(e)][:2]
        if not pics:
            continue
        labels.append(label)
        content.append({"type": "text", "text": f"<candidate label={json.dumps(label, ensure_ascii=False)}>"})
        content += [_image(p) for p in pics]
        content.append({"type": "text", "text": "</candidate>"})
    if not labels:
        raise AssistError("no taught examples to compare with")
    language = LANGS.get(lang, "English")
    content.append({"type": "text", "text":
                    "Is the object in <query> the same physical item as one of the "
                    f"candidates? Write the reason in {language}."})
    data = _call("opinion", OPINION_SYSTEM, content, OPINION_SCHEMA, effort="low")
    match = data.get("match", "")
    return {"match": match if match in labels else "",
            "confidence": data.get("confidence", "low"),
            "reason": str(data.get("reason", ""))[:400]}


# -- evaluation summary ----------------------------------------------------------------

def write_summary(report, lang="en"):
    """Rewrite an evaluation report (dict) for people who are not CV specialists."""
    _check(report.get("task", "objects"))
    slim = {k: v for k, v in report.items() if k not in ("items", "sweep")}
    language = LANGS.get(lang, "English")
    text = _call("summary", SUMMARY_SYSTEM, [{"type": "text", "text":
                 f"<report>\n{json.dumps(slim, ensure_ascii=False)}\n</report>\n\n"
                 f"Write the summary in {language}."}],
                 effort="medium", max_tokens=16000)
    return text


SUMMARY_SYSTEM = """\
You turn the evaluation report of a teachable object-recognition app into a short \
summary for managers who decide whether the project continues. They are not \
computer-vision specialists, so use plain words and explain any term you need.

The report (JSON in <report>) tests the app on pictures it was never taught. Key \
fields: "current" and "recommended" give results at two decision thresholds; \
"correct" counts test views of taught items named right; "dangerous" counts \
confident wrong names (a wrong label, or a never-taught item taken for a taught \
one); "rejected" counts never-taught items correctly called unknown; "uncertain" \
means the app said it was unsure, which is safe. Dangerous errors matter most: \
the goal is zero, even at the cost of more "unsure" answers.

Cover, in this order: what was tested (how many items and views); how often it \
was right and how many dangerous errors it made; what the recommended threshold \
would change; how much to trust the numbers given the test size; one or two next \
steps. Use only figures that appear in the report, quoted exactly. Markdown with \
a short title and a few bullet points, about 200 words."""


# -- questions about memory --------------------------------------------------------------

def ask_memory(question, labels, evalset=None, lang="en"):
    """Answer a question from memory metadata only (labels, counts, dates).

    `labels`: memory.labels() of the objects task. No pictures are sent.
    """
    _check("objects")
    question = (question or "").strip()[:500]
    if not question:
        raise AssistError("empty question")
    rows = []
    for g in labels:
        times = sorted(e.get("ts") or 0 for e in g["examples"])
        rows.append({
            "label": g["label"], "views": g["count"],
            # the day is enough to answer "when"; times of day stay on the PC
            "first_taught": time.strftime("%Y-%m-%d", time.localtime(times[0])) if times else None,
            "last_taught": time.strftime("%Y-%m-%d", time.localtime(times[-1])) if times else None,
        })
    meta = {"today": time.strftime("%Y-%m-%d"), "objects_memory": rows,
            "test_set": evalset or {}}
    language = LANGS.get(lang, "English")
    return _call("ask", ASK_SYSTEM, [{"type": "text", "text":
                 f"<metadata>\n{json.dumps(meta, ensure_ascii=False)}\n</metadata>\n\n"
                 f"<question>{question}</question>\n\nAnswer in {language}."}], effort="low")


ASK_SYSTEM = """\
You answer a person's questions about their private object memory app. <metadata> \
holds everything you know: each taught label with its number of views and the \
first and last time it was taught, plus how many test pictures each label has. \
You cannot see any pictures. Answer from the metadata in two or three sentences; \
when it cannot answer the question, say what it does show instead. Point out \
anything that looks like a mistake the person would want to fix, such as two \
labels that differ only by accents or spelling."""
