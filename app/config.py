from __future__ import annotations

import os
import socket
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VIDEO_DIR = Path(os.environ.get("VIDEO_DIR", ROOT / "videos")).expanduser().resolve()
HOST = os.environ.get("CAST_HOST", "0.0.0.0")
PORT = int(os.environ.get("CAST_PORT", "8765"))
PUBLIC_HOST = os.environ.get("CAST_PUBLIC_HOST", "").strip()

VIDEO_EXTENSIONS = {
    ".mp4",
    ".m4v",
    ".mkv",
    ".webm",
    ".mov",
    ".avi",
}

CONTENT_TYPES = {
    ".mp4": "video/mp4",
    ".m4v": "video/mp4",
    ".webm": "video/webm",
    ".mov": "video/quicktime",
    ".mkv": "video/x-matroska",
    ".avi": "video/x-msvideo",
}


def lan_ip() -> str:
    if PUBLIC_HOST:
        return PUBLIC_HOST
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


def media_base_url() -> str:
    return f"http://{lan_ip()}:{PORT}"
