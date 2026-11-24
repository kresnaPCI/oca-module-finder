from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .cast import cast_service
from .config import PORT, VIDEO_DIR, media_base_url
from .media import ensure_video_dir, list_videos, resolve_video

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("cast-hub")

STATIC_DIR = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    ensure_video_dir()
    log.info("Video library: %s", VIDEO_DIR)
    log.info("Open on your iPhone: %s", media_base_url())
    try:
        yield
    finally:
        cast_service.close()


app = FastAPI(title="Cast Hub", lifespan=lifespan)


class CastRequest(BaseModel):
    video_id: str = Field(..., description="Relative path under the videos folder")
    device_uuid: str


class VolumeRequest(BaseModel):
    device_uuid: str
    level: float = Field(..., ge=0.0, le=1.0)


class DeviceRequest(BaseModel):
    device_uuid: str


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "video_dir": str(VIDEO_DIR),
        "media_base_url": media_base_url(),
        "port": PORT,
    }


@app.get("/api/videos")
def videos():
    return {"videos": [v.to_dict() for v in list_videos()]}


@app.get("/api/devices")
def devices(refresh: bool = Query(False)):
    try:
        found = cast_service.scan(force=refresh)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Discovery failed: {exc}") from exc
    return {"devices": [d.to_dict() for d in found]}


@app.get("/api/status")
def status(device_uuid: str | None = None):
    return cast_service.status(device_uuid)


@app.post("/api/cast")
def cast(body: CastRequest):
    video = resolve_video(body.video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="Video not found")

    # Chromecast must fetch from the Mac's LAN IP, not localhost.
    url = f"{media_base_url()}/media/{video.id}"
    try:
        result = cast_service.play(
            uuid=body.device_uuid,
            media_url=url,
            content_type=video.content_type,
            title=video.name,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Cast failed: {exc}") from exc
    return {"ok": True, "media_url": url, "status": result}


@app.post("/api/pause")
def pause(body: DeviceRequest):
    try:
        return {"ok": True, "status": cast_service.pause(body.device_uuid)}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/resume")
def resume(body: DeviceRequest):
    try:
        return {"ok": True, "status": cast_service.resume(body.device_uuid)}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/stop")
def stop(body: DeviceRequest):
    try:
        return {"ok": True, "status": cast_service.stop(body.device_uuid)}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/volume")
def volume(body: VolumeRequest):
    try:
        return {"ok": True, "status": cast_service.set_volume(body.device_uuid, body.level)}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/media/{video_path:path}")
def media_file(video_path: str):
    video = resolve_video(video_path)
    if video is None:
        raise HTTPException(status_code=404, detail="Video not found")
    return FileResponse(
        video.path,
        media_type=video.content_type,
        filename=video.name,
        headers={"Accept-Ranges": "bytes"},
    )


app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
