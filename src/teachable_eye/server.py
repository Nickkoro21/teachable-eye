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


def asset_version():
    """Short hash of the web assets; changes whenever any of them changes."""
    import hashlib
    h = hashlib.sha1()
    for name in ("index.html", "style.css", "app.js"):
        path = WEB / name
        if path.exists():
            h.update(path.read_bytes())
    return h.hexdigest()[:10]


def decode_jpeg(data):
    frame = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        raise ValueError("not a JPEG/PNG image")
    return frame


class HoldBody(BaseModel):
    task: str
    id: int
    still: bool = False      # the id refers to the last photo, not a live track


class RegionBody(BaseModel):
    task: str
    box: list[float]


class BurstBody(BaseModel):
    task: str
    id: int
    seconds: float = 5.0


class TeachBody(BaseModel):
    task: str
    label: str
    hold: str | None = None  # from /api/hold (preferred)
    id: int | None = None    # live track id (hold + teach in one step)
    consent: bool = False


class LabelBody(BaseModel):
    task: str
    label: str
    to: str | None = None


class ExampleBody(BaseModel):
    task: str
    id: str


class TaskBody(BaseModel):
    task: str


def create_app(tasks, cert_path=None, info=None):
    """`tasks`: {name: task}. Each task has process/teach/still/reset/memory."""
    app = FastAPI(title="teachable-eye", docs_url=None, redoc_url=None)
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
            "tasks": {name: {"threshold": t.memory.thresholds.threshold,
                             "margin": t.memory.thresholds.margin,
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
            try:
                await previous.close(code=4000, reason="replaced by a new camera")
            except RuntimeError:
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
                await socket.send_json({
                    "task": task, "rows": rows,
                    "w": int(frame.shape[1]), "h": int(frame.shape[0]),
                    "ms": round((time.perf_counter() - started) * 1000, 1),
                })
        except WebSocketDisconnect:
            pass
        finally:
            if state["active"] is socket:
                state["active"] = None

    @app.post("/api/hold")
    async def hold(body: HoldBody):
        """TEACH pressed: freeze the selected crop until it gets a name."""
        try:
            hid = await run(task_of(body.task).hold, body.id, body.still)
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
        if getattr(task, "needs_consent", False) and not body.consent:
            raise HTTPException(428, "consent required for a person")
        try:
            if body.hold:
                pid = await run(task.teach_held, body.hold, body.label)
            elif body.id is not None:
                pid = await run(task.teach, body.id, body.label)
            else:
                raise HTTPException(400, "missing hold or id")
        except (LookupError, ValueError) as exc:
            raise HTTPException(409, str(exc)) from None
        return {"id": pid}

    @app.post("/api/still")
    async def still(request: Request, task: str = "objects"):
        current = task_of(task)
        try:
            frame = decode_jpeg(await request.body())
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from None
        rows = await run(current.still, frame)
        return {"task": task, "rows": rows,
                "w": int(frame.shape[1]), "h": int(frame.shape[0])}

    @app.post("/api/region")
    async def region(body: RegionBody):
        """Photo mode: recognize a box the user drew where nothing was found."""
        if len(body.box) != 4:
            raise HTTPException(400, "box needs 4 numbers")
        x1, y1, x2, y2 = body.box
        if not (0 <= x1 < x2 <= 1 and 0 <= y1 < y2 <= 1):
            raise HTTPException(400, "box must be normalised x1<x2, y1<y2 in 0..1")
        try:
            row = await run(task_of(body.task).region, body.box)
        except LookupError as exc:
            raise HTTPException(409, str(exc)) from None
        return {"row": row}

    @app.post("/api/follow")
    async def follow(body: RegionBody):
        """Resume live view tracking a box chosen or drawn on the paused photo."""
        if len(body.box) != 4:
            raise HTTPException(400, "box needs 4 numbers")
        try:
            tid = await run(task_of(body.task).follow, body.box)
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
        try:
            n = task_of(body.task).memory.rename(body.label, body.to)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from None
        return {"changed": n}

    @app.post("/api/forget")
    async def forget(body: LabelBody):
        return {"deleted": task_of(body.task).memory.forget_label(body.label)}

    @app.post("/api/forget_example")
    async def forget_example(body: ExampleBody):
        return {"deleted": task_of(body.task).memory.forget_example(body.id)}

    @app.post("/api/wipe")
    async def wipe(body: TaskBody):
        await run(task_of(body.task).memory.wipe)
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

    @app.exception_handler(HTTPException)
    async def http_error(_, exc):
        return JSONResponse({"error": exc.detail}, status_code=exc.status_code)

    @app.get("/favicon.ico")
    async def favicon():
        return Response(status_code=204)

    return app
