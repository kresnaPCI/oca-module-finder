from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import pychromecast
import zeroconf
from pychromecast.controllers.receiver import CastStatus
from pychromecast.error import ChromecastConnectionError

log = logging.getLogger("cast")


@dataclass
class CastDevice:
    uuid: str
    name: str
    model: str
    host: str
    cast_type: str

    def to_dict(self) -> dict:
        return {
            "uuid": self.uuid,
            "name": self.name,
            "model": self.model,
            "host": self.host,
            "cast_type": self.cast_type,
        }


class CastService:
    """Discover Chromecast / Cast-enabled TVs and control playback."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._zconf: zeroconf.Zeroconf | None = None
        self._browser: Any | None = None
        self._cast_info: dict[str, Any] = {}
        self._casts: dict[str, Any] = {}
        self._last_scan = 0.0
        self._active_uuid: str | None = None

    def scan(self, force: bool = False, timeout: float = 5.0) -> list[CastDevice]:
        with self._lock:
            now = time.time()
            if not force and self._cast_info and now - self._last_scan < 15:
                return self._devices()

            self._stop_browser()
            self._casts.clear()
            self._zconf = zeroconf.Zeroconf()
            discovered: dict[str, Any] = {}

            def add_cast(uuid: UUID, _service: str) -> None:
                info = self._browser.devices.get(uuid) if self._browser else None
                if info is not None:
                    discovered[str(uuid)] = info

            def update_cast(uuid: UUID, _service: str) -> None:
                add_cast(uuid, _service)

            def remove_cast(uuid: UUID, _service: str, cast_info: Any) -> None:
                discovered.pop(str(uuid), None)

            listener = pychromecast.SimpleCastListener(add_cast, remove_cast, update_cast)
            self._browser = pychromecast.CastBrowser(listener, self._zconf)
            self._browser.start_discovery()
            time.sleep(timeout)

            self._cast_info = dict(discovered)
            # Drop stale live connections for devices that disappeared.
            for uuid in list(self._casts):
                if uuid not in self._cast_info:
                    self._casts.pop(uuid, None)
            self._last_scan = now
            return self._devices()

    def _stop_browser(self) -> None:
        if self._browser is not None:
            try:
                self._browser.stop_discovery()
            except Exception:  # noqa: BLE001
                pass
            self._browser = None
        if self._zconf is not None:
            try:
                self._zconf.close()
            except Exception:  # noqa: BLE001
                pass
            self._zconf = None

    def _devices(self) -> list[CastDevice]:
        devices: list[CastDevice] = []
        for uuid, info in self._cast_info.items():
            devices.append(
                CastDevice(
                    uuid=uuid,
                    name=getattr(info, "friendly_name", None) or "Cast device",
                    model=getattr(info, "model_name", None) or "",
                    host=getattr(info, "host", None) or "",
                    cast_type=str(getattr(info, "cast_type", "") or ""),
                )
            )
        devices.sort(key=lambda d: d.name.lower())
        return devices

    def _get(self, uuid: str):
        if uuid in self._casts:
            cast = self._casts[uuid]
        else:
            info = self._cast_info.get(uuid)
            if info is None:
                self.scan(force=True)
                info = self._cast_info.get(uuid)
            if info is None:
                raise KeyError(f"Device not found: {uuid}")
            if self._zconf is None:
                self._zconf = zeroconf.Zeroconf()
            cast = pychromecast.get_chromecast_from_cast_info(info, self._zconf)
            self._casts[uuid] = cast

        try:
            cast.wait(timeout=5)
        except ChromecastConnectionError as exc:
            self._casts.pop(uuid, None)
            raise ConnectionError(str(exc)) from exc
        return cast

    def play(self, uuid: str, media_url: str, content_type: str, title: str) -> dict:
        with self._lock:
            cast = self._get(uuid)
            mc = cast.media_controller
            mc.play_media(
                media_url,
                content_type=content_type,
                title=title,
                thumb="",
                stream_type="BUFFERED",
            )
            mc.block_until_active(timeout=15)
            self._active_uuid = uuid
            return self.status(uuid)

    def pause(self, uuid: str) -> dict:
        with self._lock:
            cast = self._get(uuid)
            cast.media_controller.pause()
            time.sleep(0.3)
            return self.status(uuid)

    def resume(self, uuid: str) -> dict:
        with self._lock:
            cast = self._get(uuid)
            cast.media_controller.play()
            time.sleep(0.3)
            return self.status(uuid)

    def stop(self, uuid: str) -> dict:
        with self._lock:
            cast = self._get(uuid)
            cast.media_controller.stop()
            time.sleep(0.3)
            if self._active_uuid == uuid:
                self._active_uuid = None
            return self.status(uuid)

    def set_volume(self, uuid: str, level: float) -> dict:
        level = max(0.0, min(1.0, level))
        with self._lock:
            cast = self._get(uuid)
            cast.set_volume(level)
            time.sleep(0.2)
            return self.status(uuid)

    def status(self, uuid: str | None = None) -> dict:
        with self._lock:
            target = uuid or self._active_uuid
            if not target:
                return {"connected": False}
            try:
                cast = self._get(target)
            except (KeyError, ConnectionError) as exc:
                return {"connected": False, "error": str(exc)}

            mc = cast.media_controller
            status = mc.status
            cast_status: CastStatus | None = cast.status
            return {
                "connected": True,
                "uuid": target,
                "device_name": cast.name,
                "player_state": getattr(status, "player_state", None),
                "title": getattr(status, "title", None),
                "current_time": getattr(status, "current_time", None),
                "duration": getattr(status, "duration", None),
                "volume": cast_status.volume_level if cast_status else None,
                "muted": cast_status.volume_muted if cast_status else None,
            }

    def close(self) -> None:
        with self._lock:
            for cast in self._casts.values():
                try:
                    cast.disconnect(blocking=False)
                except Exception:  # noqa: BLE001
                    pass
            self._casts.clear()
            self._cast_info.clear()
            self._stop_browser()


cast_service = CastService()
