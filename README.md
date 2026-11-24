# Cast Hub

Local web app for a **Mac Mini** (or any Mac on your Wi‑Fi): open it on your iPhone, pick a video from a folder on the Mac, and cast it to a **Chromecast / Google Cast TV**.

> Not a Cursor-hosted app — it must run on your Mac so the TV can pull video from your home network.

## What you need

- Mac and TV on the **same Wi‑Fi**
- A Cast device: Chromecast, Android TV, Google TV, or a smart TV with Google Cast
- Videos on the Mac (best: **MP4 H.264 + AAC**)

Apple TV / AirPlay-only sets are not supported yet.

## Quick start (Mac)

```bash
cd /path/to/oca-module-finder   # or wherever you cloned this
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Put videos here (or set VIDEO_DIR to another folder)
mkdir -p videos
# open videos && drop files in

uvicorn app.main:app --host 0.0.0.0 --port 8765
```

On the Mac, note the LAN IP (System Settings → Network), e.g. `192.168.1.20`.

On your iPhone (same Wi‑Fi), open:

```text
http://192.168.1.20:8765
```

1. Tap **Scan** if no TV appears  
2. Select the TV  
3. Tap a video — it casts  

## Power-cut friendly Mac setup

So the hub comes back after blackouts:

1. **Energy → Start up automatically after a power failure**
2. **Users & Groups → Automatic login** (requires FileVault off)
3. **Login Items** → add a way to start Cast Hub (Terminal script, Automator, or `launchd`)

Example `launchd` label idea: run `uvicorn` at login; keep the Mac awake while casting.

## Environment

| Variable | Default | Meaning |
|---|---|---|
| `VIDEO_DIR` | `./videos` | Folder of videos to list |
| `CAST_PORT` | `8765` | HTTP port |
| `CAST_PUBLIC_HOST` | (auto LAN IP) | IP/hostname Chromecast uses to fetch video. Set if auto-detect is wrong. |

Example:

```bash
VIDEO_DIR="$HOME/Movies/Cast" CAST_PUBLIC_HOST=192.168.1.20 uvicorn app.main:app --host 0.0.0.0 --port 8765
```

## How it works

```text
iPhone Safari  →  Cast Hub on Mac  →  tells Chromecast to play
                         ↑                    │
                         └──── TV pulls MP4 ───┘
```

The phone only talks to the Mac. The **TV streams from the Mac’s LAN address**, so both must be on the home network.

## API (optional)

- `GET /api/videos` — library  
- `GET /api/devices?refresh=true` — Cast discovery  
- `POST /api/cast` — `{ "video_id", "device_uuid" }`  
- `POST /api/pause` / `resume` / `stop` / `volume`

## Tips

- Prefer `.mp4` (H.264). Some `.mkv` files won’t play on Chromecast.
- macOS firewall: allow Python/uvicorn for incoming LAN connections.
- If cast starts but TV shows an error, set `CAST_PUBLIC_HOST` to your Mac’s Wi‑Fi IP and retry.
