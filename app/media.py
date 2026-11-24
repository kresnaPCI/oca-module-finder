from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import CONTENT_TYPES, VIDEO_DIR, VIDEO_EXTENSIONS


@dataclass
class VideoItem:
    id: str
    name: str
    path: str
    size_bytes: int
    content_type: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "size_bytes": self.size_bytes,
            "size_label": _size_label(self.size_bytes),
            "content_type": self.content_type,
        }


def ensure_video_dir() -> Path:
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    return VIDEO_DIR


def list_videos() -> list[VideoItem]:
    ensure_video_dir()
    items: list[VideoItem] = []
    for path in sorted(VIDEO_DIR.rglob("*")):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix not in VIDEO_EXTENSIONS:
            continue
        rel = path.relative_to(VIDEO_DIR).as_posix()
        items.append(
            VideoItem(
                id=rel,
                name=path.name,
                path=str(path),
                size_bytes=path.stat().st_size,
                content_type=CONTENT_TYPES.get(suffix, "video/mp4"),
            )
        )
    return items


def resolve_video(video_id: str) -> VideoItem | None:
    # Prevent path traversal while allowing nested folders.
    candidate = (VIDEO_DIR / video_id).resolve()
    try:
        candidate.relative_to(VIDEO_DIR)
    except ValueError:
        return None
    if not candidate.is_file():
        return None
    suffix = candidate.suffix.lower()
    if suffix not in VIDEO_EXTENSIONS:
        return None
    rel = candidate.relative_to(VIDEO_DIR).as_posix()
    return VideoItem(
        id=rel,
        name=candidate.name,
        path=str(candidate),
        size_bytes=candidate.stat().st_size,
        content_type=CONTENT_TYPES.get(suffix, "video/mp4"),
    )


def _size_label(n: int) -> str:
    value = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{n} B"
