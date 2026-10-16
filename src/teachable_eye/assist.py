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
    content = []
    for n, i in enumerate(send, 1):
        content += [{"type": "text", "text": f"Crop {n}:"}, _image(crops[i])]
    known = ", ".join(sorted(set(known_labels))[:200]) or "(none yet)"
    content.append({"type": "text", "text":
                    f"The person's existing labels: {known}\n"
                    f"Name each of the {len(send)} crops in {language}."})
    system = (
        "You help a person label objects for a personal visual memory that runs on "
        "their own device. You get numbered crops of objects from one photo. For each "
        "crop give a short everyday name: 1-3 words, lower case, no article. When a "
        "crop shows the same kind of thing as one of the person's existing labels, "
        "reuse their word for that kind of thing, but never assume it is the same "
        "personal item and leave out owners' names or details you cannot see. If a "
        "crop shows no clear object (a wall, a table top, a blur), give the surface or "
        "an empty name and set confident to false. Set confident to false whenever "
        "you are unsure. Return one item per crop, with index = the crop number.")
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


def second_opinion(query, candidates, lang="en", task="objects"):
    """Is `query` the same physical object as one of the candidates?

    `candidates`: [(label, [example crops])], nearest first. Returns
    {"match": label or "", "confidence", "reason"}. Advice only.
    """
    _check(task)
    if not _sendable(query):
        raise AssistError("this picture shows a face, so it stays on the device")
    content = [{"type": "text", "text": "The object to identify:"}, _image(query)]
    labels = []
    for label, examples in candidates:
        pics = [e for e in examples if _sendable(e)][:2]
        if not pics:
            continue
        labels.append(label)
        content.append({"type": "text", "text": f"Taught examples of \"{label}\":"})
        content += [_image(p) for p in pics]
    if not labels:
        raise AssistError("no taught examples to compare with")
    language = LANGS.get(lang, "English")
    content.append({"type": "text", "text":
                    "Is the object to identify the same physical item as one of the "
                    f"labels {', '.join(repr(x) for x in labels)}? "
                    f"Answer the reason in {language}, one or two short sentences."})
    system = (
        "You give a second opinion to a personal object-recognition app. Personal "
        "items matter: the same kind of object is not enough, it must look like the "
        "same physical item (colour, markings, shape, wear). Set match to the exact "
        "label if it is that item, or to an empty string if it is none of them or "
        "you cannot tell. Be conservative: when unsure, say so with low confidence.")
    data = _call("opinion", system, content, OPINION_SCHEMA, effort="low")
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
    system = (
        "You write short, plain summaries of evaluation results for managers who are "
        "not computer-vision specialists. Use only the numbers given; never invent or "
        "round them misleadingly. Explain: how often it named things correctly, the "
        "number of dangerous errors (a confident wrong name — the one that must stay "
        "at zero), how often it rightly said 'unknown' for never-taught things, what "
        "the recommended threshold changes, and what to do next. Say plainly when the "
        "test set is too small to be sure. Markdown, at most about 250 words.")
    text = _call("summary", system, [{"type": "text", "text":
                 f"Write the summary in {language}.\n\n" + json.dumps(slim, ensure_ascii=False)}],
                 effort="medium", max_tokens=16000)
    return text


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
            "first_taught": time.strftime("%Y-%m-%d %H:%M", time.localtime(times[0])) if times else None,
            "last_taught": time.strftime("%Y-%m-%d %H:%M", time.localtime(times[-1])) if times else None,
        })
    meta = {"today": time.strftime("%Y-%m-%d"), "objects_memory": rows,
            "test_set": evalset or {}}
    language = LANGS.get(lang, "English")
    system = (
        "You answer questions about a personal object memory using only the JSON "
        "metadata given (labels, number of taught views, dates; and the test set "
        "counts). You cannot see the pictures. If the metadata cannot answer the "
        "question, say so briefly. Be short.")
    return _call("ask", system, [{"type": "text", "text":
                 f"Metadata:\n{json.dumps(meta, ensure_ascii=False)}\n\n"
                 f"Question: {question}\nAnswer in {language}."}], effort="low")
