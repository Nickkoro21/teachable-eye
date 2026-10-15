"""Block media, datasets and secrets from entering git (mission principle 4).

Usage:
    python tools/check_no_media.py          # check staged files (pre-commit)
    python tools/check_no_media.py --all    # check every tracked file
"""
import subprocess
import sys
from pathlib import PurePosixPath

BLOCKED_EXT = {
    # images
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tif", ".tiff",
    ".heic", ".heif", ".raw", ".dng",
    # video
    ".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v", ".3gp", ".h264", ".h265",
    # audio
    ".wav", ".mp3", ".m4a", ".ogg", ".flac", ".aac", ".opus",
    # flight tracks
    ".gpx", ".kml", ".igc",
    # vectors, weights, datasets
    ".npy", ".npz", ".pt", ".pth", ".onnx", ".safetensors", ".bin",
    ".parquet", ".h5", ".snapshot",
    # secrets
    ".pem", ".key",
}
BLOCKED_DIRS = {"data", "edge-data", "recordings", "captures", "snapshots", "cert"}
BLOCKED_NAMES = {".env"}
MAX_BYTES = 1_000_000  # anything this large is almost certainly not source


def git_lines(*args):
    out = subprocess.run(["git", *args], capture_output=True, text=True,
                         check=True).stdout
    return [line for line in out.splitlines() if line]


def problems(path, size):
    p = PurePosixPath(path)
    found = []
    if p.suffix.lower() in BLOCKED_EXT:
        found.append(f"blocked file type {p.suffix}")
    if p.name in BLOCKED_NAMES or (p.name.startswith(".env.")
                                   and p.name != ".env.example"):
        found.append("environment/secret file")
    if any(part in BLOCKED_DIRS or part.endswith("_shard")
           for part in p.parts[:-1]):
        found.append("inside a data/runtime directory")
    if size is not None and size > MAX_BYTES:
        found.append(f"larger than {MAX_BYTES // 1000} kB ({size // 1000} kB)")
    return found


def main():
    check_all = "--all" in sys.argv
    if check_all:
        paths = git_lines("ls-files")
    else:
        paths = git_lines("diff", "--cached", "--name-only",
                          "--diff-filter=ACMR")
    bad = []
    for path in paths:
        size = None
        try:
            obj = f"HEAD:{path}" if check_all else f":{path}"  # ":" = index
            size = int(git_lines("cat-file", "-s", obj)[0])
        except (subprocess.CalledProcessError, IndexError, ValueError):
            pass
        for reason in problems(path, size):
            bad.append(f"  {path}: {reason}")
    if bad:
        print("BLOCKED by tools/check_no_media.py (mission principle 4):")
        print("\n".join(bad))
        print("Keep media, datasets and secrets under data/ or outside the repo.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
