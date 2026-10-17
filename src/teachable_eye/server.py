"""HTTP + WebSocket server for the phone PWA (R9-R15).

The phone keeps its own live video and only sends downscaled JPEG frames over
/ws; each reply carries normalised boxes and decisions that the page draws on
top of its video. The client waits for each reply before sending the next
frame, so frames never queue up behind a slow one.

Only one camera source is active: a new /ws connection replaces the previous
one and resets that task's tracker (R11).
"""
import asyncio
import re
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import cv2
import numpy as np
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from teachable_eye import config

WEB = Path(__file__).resolve().parent / "web"
_SAFE_NAME = re.compile(r"^[0-9a-f]{32}\.jpg$")
_SAFE_REPORT = re.compile(r"^eval-[a-z]+-[0-9]{8}-[0-9]{6}(-[a-z0-9.-]+)?$")


def asset_version():
    """Short hash of the web assets; changes whenever any of them changes."""
    import hashlib
    h = hashlib.sha1()
    for name in ("index.html", "style.css", "app.js"):
        path = WEB / name
        if path.exists():
            h.update(path.read_bytes())
    return h.hexdigest()[:10]


MAX_IMAGE_BYTES = 15_000_000
MAX_PIXELS = 40_000_000          # well above a 4K frame; a "decompression bomb" is refused


def decode_jpeg(data):
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError("picture too large")
    buf = np.frombuffer(data, np.uint8)
    # read the size from the header first: never decode a huge picture
    ok, size = _image_size(data)
    if ok and size[0] * size[1] > MAX_PIXELS:
        raise ValueError("picture too large")
    frame = cv2.imdecode(buf, cv2.IMREAD_COLOR)
    if frame is None:
        raise ValueError("not a JPEG/PNG image")
    if frame.shape[0] * frame.shape[1] > MAX_PIXELS:
        raise ValueError("picture too large")
    return frame


def _image_size(data):
    """(ok, (w, h)) from a JPEG or PNG header, without decoding the picture."""
    import struct
    if data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) >= 24:
        return True, struct.unpack(">II", data[16:24])
    if data[:2] == b"\xff\xd8":
        i = 2
        while i + 9 < len(data):
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                h, w = struct.unpack(">HH", data[i + 5:i + 9])
                return True, (w, h)
            seg = struct.unpack(">H", data[i + 2:i + 4])[0]
            i += 2 + seg
    return False, (0, 0)


def valid_box(box):
    """A normalised box: 4 finite numbers, 0 <= x1 < x2 <= 1, 0 <= y1 < y2 <= 1."""
    import math
    if len(box) != 4 or not all(isinstance(v, (int, float)) and math.isfinite(v) for v in box):
        return False
    x1, y1, x2, y2 = box
    return 0 <= x1 < x2 <= 1 and 0 <= y1 < y2 <= 1


class HoldBody(BaseModel):
    task: str
    id: int
    still: bool = False      # the id refers to a photo's row, not a live track
    still_id: str | None = None   # which photo (from /api/still); None: the latest


class RegionBody(BaseModel):
    task: str
    box: list[float]
    still_id: str | None = None


class BurstBody(BaseModel):
    task: str
    id: int
    seconds: float = 60.0   # runs until the user stops it; capped on the server


MAX_LABEL = 60


def check_label(label):
    if label is not None and len(label) > MAX_LABEL:
        raise HTTPException(400, f"label longer than {MAX_LABEL} characters")


class TeachBody(BaseModel):
    task: str
    label: str
    hold: str | None = None  # from /api/hold (preferred)
    id: int | None = None    # live track id (hold + teach in one step)
    consent: bool = False
    eval: bool = False       # save to the test set instead of memory (R34)


class LabelBody(BaseModel):
    task: str
    label: str
    to: str | None = None


class ExampleBody(BaseModel):
    task: str
    id: str


class TaskBody(BaseModel):
    task: str


class NamesBody(BaseModel):
    task: str
    ids: list[int]           # rows of a photo
    still_id: str | None = None
    lang: str = "en"


class OpinionBody(BaseModel):
    task: str
    hold: str
    lang: str = "en"


class SummaryBody(BaseModel):
    report: str
    lang: str = "en"


class AskBody(BaseModel):
    question: str
    lang: str = "en"


LOCAL_HOSTS = ("127.0.0.1", "localhost", "[::1]", "testserver")


def allowed_hosts(extra=()):
    """Host names this server answers to: this PC, plus TEYE_PUBLIC_HOST (the
    Tailscale name, kept in the local .env) and the LAN IP when served there."""
    hosts = set(LOCAL_HOSTS) | {h for h in extra if h}
    if config.PUBLIC_HOST:
        hosts.add(config.PUBLIC_HOST)
    return hosts


def create_app(tasks, cert_path=None, info=None, hosts=None):
    """`tasks`: {name: task}. Each task has process/teach/still/reset/memory."""
    app = FastAPI(title="teachable-eye", docs_url=None, redoc_url=None)
    hosts = allowed_hosts(hosts or ())

    # Security review 2026-10-17: any web page open on this PC could reach
    # 127.0.0.1 (DNS rebinding: an attacker's name resolving to 127.0.0.1) or
    # open the camera socket / send POSTs from its own origin. So the Host must
    # be one of ours, and a browser request must come from one of our origins.
    from urllib.parse import urlsplit
    from starlette.middleware.trustedhost import TrustedHostMiddleware

    class SameOrigin:
        def __init__(self, inner):
            self.inner = inner

        async def __call__(self, scope, receive, send):
            if scope["type"] in ("http", "websocket"):
                headers = dict(scope.get("headers") or [])
                origin = headers.get(b"origin", b"").decode("latin-1")
                unsafe = scope["type"] == "websocket" or scope.get("method") not in ("GET", "HEAD")
                if unsafe and origin and urlsplit(origin).hostname not in hosts:
                    if scope["type"] == "websocket":
                        await send({"type": "websocket.close", "code": 4403})
                    else:
                        await JSONResponse({"error": "cross-site request refused"},
                                           status_code=403)(scope, receive, send)
                    return
            await self.inner(scope, receive, send)

    app.add_middleware(SameOrigin)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=sorted(hosts))
    # one worker: models are not re-entrant and frames must stay in order
    pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="vision")
    state = {"active": None}   # the one live camera connection

    def task_of(name):
        task = tasks.get(name)
        if task is None:
            raise HTTPException(404, f"unknown task {name!r}")
        return task

    async def run(fn, *args):
        return await asyncio.get_running_loop().run_in_executor(pool, fn, *args)

    if WEB.exists():
        app.mount("/static", StaticFiles(directory=WEB), name="static")

    @app.middleware("http")
    async def no_stale_shell(request, call_next):
        # Always revalidate the app shell, so a phone never mixes an old page
        # with new scripts after an update (it did, during testing).
        response = await call_next(request)
        if request.url.path == "/" or request.url.path.startswith("/static/") \
                or request.url.path in ("/sw.js", "/manifest.webmanifest"):
            response.headers["Cache-Control"] = "no-cache"
        return response

    @app.get("/")
    async def index():
        # cache-busting: every asset URL carries a hash of the current files
        html = (WEB / "index.html").read_text(encoding="utf-8")
        for asset in ("style.css", "app.js"):
            html = html.replace(f"/static/{asset}\"",
                                f"/static/{asset}?v={asset_version()}\"")
        return Response(html, media_type="text/html; charset=utf-8")

    @app.get("/sw.js")
    async def service_worker():
        # served from the root so its scope covers the whole app
        return FileResponse(WEB / "sw.js", media_type="text/javascript")

    @app.get("/manifest.webmanifest")
    async def manifest():
        return FileResponse(WEB / "manifest.webmanifest",
                            media_type="application/manifest+json")

    @app.get("/cert.crt")
    async def cert():
        if not cert_path:
            raise HTTPException(404, "no certificate (plain HTTP)")
        return FileResponse(cert_path, media_type="application/x-x509-ca-cert",
                            filename="teachable-eye.crt")

    @app.get("/api/status")
    async def status():
        return {
            "augment": config.AUGMENT_PROFILE,
            "tasks": {name: {"threshold": t.memory.thresholds.threshold,
                             "margin": t.memory.thresholds.margin,
                             "encoder": getattr(t, "encoder", None),
                             "examples": t.memory.count()}
                      for name, t in tasks.items()},
            **(info or {}),
        }

    @app.websocket("/ws")
    async def ws(socket: WebSocket, task: str = "objects"):
        if task not in tasks:
            await socket.close(code=4404)
            return
        await socket.accept()
        previous = state["active"]
        state["active"] = socket
        if previous is not None:
            # The old phone connection may already be dead (Wi-Fi dropped,
            # screen locked): closing it then raises. That must never take
            # the NEW connection down with it — it did, in a loop, and the
            # phone's dot blinked white/red with no frames processed.
            try:
                await previous.close(code=4000, reason="replaced by a new camera")
            except (RuntimeError, WebSocketDisconnect, OSError):
                pass
            except Exception:                    # any other close failure
                pass
        current = tasks[task]
        await run(current.reset)
        try:
            while True:
                data = await socket.receive_bytes()
                if state["active"] is not socket:
                    break
                started = time.perf_counter()
                try:
                    frame = decode_jpeg(data)
                except ValueError as exc:
                    await socket.send_json({"error": str(exc)})
                    continue
                rows = await run(current.process, frame)
                if state["active"] is not socket:
                    break              # replaced while this frame was processed
                await socket.send_json({
                    "task": task, "rows": rows,
                    "w": int(frame.shape[1]), "h": int(frame.shape[0]),
                    "ms": round((time.perf_counter() - started) * 1000, 1),
                })
        except (WebSocketDisconnect, RuntimeError):
            # the phone went away, or this socket was closed by a newer one
            # (starlette raises a RuntimeError subclass on send-after-close)
            pass
        finally:
            if state["active"] is socket:
                state["active"] = None

    @app.post("/api/hold")
    async def hold(body: HoldBody):
        """TEACH pressed: freeze the selected crop until it gets a name."""
        try:
            task = task_of(body.task)
            hid = await run(lambda: task.hold(body.id, body.still, **(
                {"still_id": body.still_id} if body.still_id else {})))
        except LookupError as exc:
            raise HTTPException(409, str(exc)) from None
        return {"hold": hid}

    @app.post("/api/burst")
    async def burst(body: BurstBody):
        """Teach from video: collect distinct views of one tracked object."""
        try:
            bid = await run(task_of(body.task).start_burst, body.id, body.seconds)
        except LookupError as exc:
            raise HTTPException(409, str(exc)) from None
        return {"burst": bid}

    @app.get("/api/burst/{bid}")
    async def burst_status(bid: str, task: str = "objects"):
        try:
            return task_of(task).burst_status(bid)
        except LookupError as exc:
            raise HTTPException(404, str(exc)) from None

    @app.post("/api/burst/{bid}/finish")
    async def burst_finish(bid: str, task: str = "objects"):
        try:
            hid, views = await run(task_of(task).finish_burst, bid)
        except LookupError as exc:
            raise HTTPException(409, str(exc)) from None
        return {"hold": hid, "views": views}

    @app.get("/api/hold/{hid}/{index}.jpg")
    async def hold_thumb(hid: str, index: int, task: str = "objects"):
        try:
            thumbs = task_of(task).hold_preview(hid)
        except LookupError as exc:
            raise HTTPException(404, str(exc)) from None
        if not 0 <= index < len(thumbs):
            raise HTTPException(404, "no such view")
        return Response(thumbs[index], media_type="image/jpeg")

    @app.post("/api/teach")
    async def teach(body: TeachBody):
        task = task_of(body.task)
        check_label(body.label)
        if getattr(task, "needs_consent", False) and not body.consent:
            raise HTTPException(428, "consent required for a person")
        try:
            if body.eval:
                if not body.hold:
                    raise HTTPException(400, "missing hold")
                return {"eval": await run(task.eval_held, body.hold, body.label)}
            if body.hold:
                pid = await run(task.teach_held, body.hold, body.label)
            elif body.id is not None:
                pid = await run(task.teach, body.id, body.label)
            else:
                raise HTTPException(400, "missing hold or id")
        except (LookupError, ValueError) as exc:
            raise HTTPException(409, str(exc)) from None
        except HTTPException:
            raise
        except Exception as exc:          # GPU / disk: the selection is kept
            raise HTTPException(503, f"could not save, try again: {exc}") from None
        return {"id": pid}

    @app.post("/api/still")
    async def still(request: Request, task: str = "objects"):
        current = task_of(task)
        try:
            frame = decode_jpeg(await request.body())
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from None
        rows, sid = await run(lambda: (current.still(frame),
                                       getattr(current, "last_still_id", None)))
        return {"task": task, "rows": rows, "still_id": sid,
                "w": int(frame.shape[1]), "h": int(frame.shape[0])}

    @app.post("/api/region")
    async def region(body: RegionBody):
        """Photo mode: recognize a box the user drew where nothing was found."""
        if not valid_box(body.box):
            raise HTTPException(400, "box must be 4 numbers, x1<x2, y1<y2 in 0..1")
        try:
            task = task_of(body.task)
            row = await run(lambda: task.region(body.box, body.still_id))
        except LookupError as exc:
            raise HTTPException(409, str(exc)) from None
        return {"row": row}

    @app.post("/api/follow")
    async def follow(body: RegionBody):
        """Resume live view tracking a box chosen or drawn on the paused photo."""
        if not valid_box(body.box):
            raise HTTPException(400, "box must be 4 numbers, x1<x2, y1<y2 in 0..1")
        try:
            task = task_of(body.task)
            tid = await run(lambda: task.follow(body.box, body.still_id))
        except LookupError as exc:
            raise HTTPException(409, str(exc)) from None
        return {"id": tid}

    @app.post("/api/unfollow")
    async def unfollow(body: HoldBody):
        return {"stopped": await run(task_of(body.task).unfollow, body.id)}

    @app.get("/api/memory")
    async def memory(task: str = "objects"):
        return {"task": task, "labels": task_of(task).memory.labels()}

    @app.post("/api/rename")
    async def rename(body: LabelBody):
        if not body.to:
            raise HTTPException(400, "missing new label")
        check_label(body.to)
        try:
            mem = task_of(body.task).memory
            n = await run(mem.rename, body.label, body.to)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from None
        return {"changed": n}

    # Forgetting removes vectors AND thumbnail files (gc_thumbs).
    @app.post("/api/forget")
    async def forget(body: LabelBody):
        task = task_of(body.task)
        n = await run(task.memory.forget_label, body.label)
        await run(task.gc_thumbs)
        # forgetting is complete: test views and reports that name it go too
        if hasattr(task, "forget_everywhere"):
            await run(task.forget_everywhere, body.label)
        return {"deleted": n}

    @app.post("/api/forget_example")
    async def forget_example(body: ExampleBody):
        """Delete one view (with its variants) or one variant on its own."""
        task = task_of(body.task)
        n = await run(task.memory.forget_example, body.id)
        await run(task.gc_thumbs)
        return {"deleted": n}

    @app.post("/api/refresh_variants")
    async def refresh_variants(body: TaskBody):
        """Rebuild every view's variants with the configured profile."""
        return await run(task_of(body.task).refresh_variants)

    @app.post("/api/wipe")
    async def wipe(body: TaskBody):
        task = task_of(body.task)
        await run(task.memory.wipe)
        await run(task.gc_thumbs)
        if hasattr(task, "forget_everywhere"):
            await run(task.forget_everywhere, None)
        return {"ok": True}

    @app.get("/thumb/{task}/{name}")
    async def thumb(task: str, name: str):
        task_of(task)
        if not _SAFE_NAME.match(name):
            raise HTTPException(400, "bad name")
        path = config.DATA_DIR / "thumbs" / task / name
        if not path.exists():
            raise HTTPException(404, "no such thumbnail")
        return FileResponse(path, media_type="image/jpeg",
                            headers={"Cache-Control": "max-age=86400"})

    # -- voice teach (R21) ---------------------------------------------------------
    # Its own worker: transcribing must not hold up the live frames.
    voice_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="voice")

    @app.post("/api/voice")
    async def voice_label(request: Request, lang: str = "en"):
        """A WAV of "this is my hat" -> {"text", "label"}. Nothing is stored."""
        if not config.VOICE:
            raise HTTPException(503, "voice teach is off on the PC (VOICE=off)")
        from teachable_eye import voice
        data = await request.body()
        if len(data) > 4_000_000:
            raise HTTPException(413, "recording too long")
        try:
            return await asyncio.get_running_loop().run_in_executor(
                voice_pool, voice.transcribe, data, lang)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from None
        except Exception as exc:                 # model missing, GPU error, ...
            raise HTTPException(503, f"voice not available: {exc}") from None

    # -- test set and evaluation (R34, R35) -------------------------------------

    @app.get("/api/eval")
    async def eval_set(task: str = "objects"):
        store = task_of(task).evalset
        return {"task": task, "labels": store.labels(), "items": store.items()}

    @app.get("/api/eval/{task}/{iid}.jpg")
    async def eval_image(task: str, iid: str):
        try:
            path = task_of(task).evalset.path(iid)
        except LookupError as exc:
            raise HTTPException(400, str(exc)) from None
        if not path.exists():
            raise HTTPException(404, "no such test view")
        return FileResponse(path, media_type="image/jpeg")

    @app.post("/api/eval/forget")
    async def eval_forget(body: ExampleBody):
        try:
            return {"deleted": task_of(body.task).evalset.delete(body.id)}
        except LookupError as exc:
            raise HTTPException(400, str(exc)) from None

    @app.post("/api/eval/run")
    async def eval_run(body: TaskBody):
        report, stem = await run(task_of(body.task).run_eval)
        keep = ("task", "encoder", "created", "memory", "test", "current",
                "recommended", "top1", "separation", "augmentation", "views_curve",
                "classifier", "notes", "profiles")
        return {"report": stem, **{k: report.get(k) for k in keep}}

    @app.get("/api/reports/{stem}.md")
    async def report_md(stem: str):
        if not _SAFE_REPORT.match(stem):
            raise HTTPException(400, "bad report name")
        path = config.DATA_DIR / "reports" / f"{stem}.md"
        if not path.exists():
            raise HTTPException(404, "no such report")
        return Response(path.read_text(encoding="utf-8"),
                        media_type="text/markdown; charset=utf-8")

    # -- optional help from Claude (R36-R40) -------------------------------------

    def assist_error(exc):
        return HTTPException(503, str(exc))

    @app.get("/api/assist")
    async def assist_status():
        from teachable_eye import assist
        return assist.status()

    @app.post("/api/assist/names")
    async def assist_names(body: NamesBody):
        from teachable_eye import assist
        task = task_of(body.task)
        body.ids = list(dict.fromkeys(body.ids))[:64]      # unique, bounded cost
        try:
            crops = await run(lambda: task.still_crops(body.ids, body.still_id))
        except LookupError as exc:
            raise HTTPException(409, str(exc)) from None
        known = [g["label"] for g in task.memory.labels()]
        try:
            out = await asyncio.to_thread(
                assist.suggest_names, [c if c is not None else np.zeros((0, 0, 3), np.uint8)
                                       for c in crops], known, body.lang, body.task)
        except assist.AssistError as exc:
            raise assist_error(exc) from None
        return {"items": [dict(o, id=i) for i, o in zip(body.ids, out)]}

    @app.post("/api/assist/opinion")
    async def assist_opinion(body: OpinionBody):
        from teachable_eye import assist
        task = task_of(body.task)
        try:
            crop = task.held_crops(body.hold)[0]
        except LookupError as exc:
            raise HTTPException(409, str(exc)) from None

        def candidates():
            decision = task.memory.recognize(task.embed([crop])[0], k=3)
            labels = list(dict.fromkeys(n.label for n in decision.neighbours))
            return decision, [(lb, task.example_images(lb)) for lb in labels]
        decision, cands = await run(candidates)
        try:
            out = await asyncio.to_thread(assist.second_opinion, crop, cands,
                                          body.lang, body.task)
        except assist.AssistError as exc:
            raise assist_error(exc) from None
        return {**out, "memory": decision.to_json()}

    @app.post("/api/assist/summary")
    async def assist_summary(body: SummaryBody):
        import json
        from teachable_eye import assist
        if not _SAFE_REPORT.match(body.report):
            raise HTTPException(400, "bad report name")
        path = config.DATA_DIR / "reports" / f"{body.report}.json"
        if not path.exists():
            raise HTTPException(404, "no such report")
        report = json.loads(path.read_text(encoding="utf-8"))
        try:
            text = await asyncio.to_thread(assist.write_summary, report, body.lang)
        except assist.AssistError as exc:
            raise assist_error(exc) from None
        lang = "el" if body.lang == "el" else "en"
        path.with_name(f"{body.report}.summary-{lang}.md").write_text(text, encoding="utf-8")
        return {"text": text}

    @app.post("/api/assist/ask")
    async def assist_ask(body: AskBody):
        from teachable_eye import assist
        task = task_of("objects")
        labels = task.memory.labels()
        try:
            evalset = task.evalset.labels()
        except AttributeError:
            evalset = {}
        try:
            text = await asyncio.to_thread(assist.ask_memory, body.question, labels,
                                           evalset, body.lang)
        except assist.AssistError as exc:
            raise assist_error(exc) from None
        return {"text": text}

    @app.exception_handler(HTTPException)
    async def http_error(_, exc):
        return JSONResponse({"error": exc.detail}, status_code=exc.status_code)

    @app.get("/favicon.ico")
    async def favicon():
        return Response(status_code=204)

    return app
