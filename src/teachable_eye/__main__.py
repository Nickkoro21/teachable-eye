"""Run the teachable-eye server.

    uv run teachable-eye --host 0.0.0.0            # phone on the same Wi-Fi
    uv run teachable-eye                           # this PC only (localhost)
"""
import argparse
import time

from teachable_eye import config


def main():
    ap = argparse.ArgumentParser(prog="teachable-eye")
    ap.add_argument("--host", default="127.0.0.1",
                    help="0.0.0.0 to serve the phone on the local network")
    ap.add_argument("--advertise", default=None,
                    help="LAN IP to put in the URL and certificate "
                         "(default: auto-detected)")
    ap.add_argument("--port", type=int, default=config.PORT)
    ap.add_argument("--no-https", action="store_true",
                    help="plain HTTP: use behind an HTTPS proxy such as "
                         "Tailscale Serve, or on localhost only (a phone "
                         "camera needs HTTPS)")
    ap.add_argument("--tasks", default="objects,people",
                    help="comma-separated tasks to load")
    args = ap.parse_args()

    import uvicorn

    from teachable_eye import encoders
    from teachable_eye.cert import ensure_cert, lan_ip
    from teachable_eye.server import create_app

    started = time.perf_counter()
    wanted = [t.strip() for t in args.tasks.split(",") if t.strip()]
    tasks = {}
    if "objects" in wanted:
        from teachable_eye.tasks import ObjectsTask
        print(f"loading objects task (YOLOE + {config.OBJECT_ENCODER})...")
        tasks["objects"] = ObjectsTask()
        tasks["objects"].detector.warm()
        encoders.warm_clip()
    if "people" in wanted:
        from teachable_eye.tasks import PeopleTask
        print("loading people task (YuNet + SFace)...")
        tasks["people"] = PeopleTask()
    if not tasks:
        raise SystemExit("no tasks loaded")
    if config.VOICE:
        # voice teach is optional: load Whisper in the background so the
        # server is ready at once and the first 🎤 is still quick
        import threading
        from teachable_eye import voice
        threading.Thread(target=voice.warm, daemon=True, name="voice-warm").start()

    lan = args.host not in ("127.0.0.1", "localhost")
    ip = args.advertise or (lan_ip() if lan else "127.0.0.1")
    cert = key = None
    if not args.no_https:
        cert, key = ensure_cert(ip)
    info = {"device": encoders.onnx_providers()[0], "ip": ip}
    app = create_app(tasks, cert_path=cert, info=info, hosts=[ip, args.advertise])
    scheme = "http" if args.no_https else "https"
    print(f"ready in {time.perf_counter() - started:.0f}s "
          f"(encoders: {info['device']}, tasks: {', '.join(tasks)})")
    print(f"open on the phone:  {scheme}://{ip}:{args.port}")
    if not args.no_https:
        print(f"install certificate: {scheme}://{ip}:{args.port}/cert.crt")
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning",
                ssl_certfile=str(cert) if cert else None,
                ssl_keyfile=str(key) if key else None)


if __name__ == "__main__":
    main()
