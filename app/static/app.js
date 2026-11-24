const state = {
  devices: [],
  videos: [],
  selectedDevice: null,
  selectedVideo: null,
  casting: false,
};

const el = {
  devices: document.getElementById("devices"),
  videos: document.getElementById("videos"),
  deviceHint: document.getElementById("device-hint"),
  videoHint: document.getElementById("video-hint"),
  status: document.getElementById("status"),
  now: document.getElementById("now-playing"),
  nowTitle: document.getElementById("now-title"),
  nowMeta: document.getElementById("now-meta"),
  volume: document.getElementById("volume"),
};

function setStatus(message, kind = "") {
  el.status.textContent = message || "";
  el.status.className = `status${kind ? ` ${kind}` : ""}`;
}

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || data.message || `Request failed (${res.status})`);
  }
  return data;
}

function renderDevices() {
  el.devices.innerHTML = "";
  if (!state.devices.length) {
    el.deviceHint.hidden = false;
    el.deviceHint.textContent =
      "No Cast devices found. Same Wi‑Fi as the Mac? Try Scan again.";
    return;
  }
  el.deviceHint.hidden = true;
  for (const device of state.devices) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = `device${state.selectedDevice === device.uuid ? " selected" : ""}`;
    btn.setAttribute("role", "option");
    btn.setAttribute("aria-selected", state.selectedDevice === device.uuid ? "true" : "false");
    btn.innerHTML = `
      <span class="device-name">${escapeHtml(device.name)}</span>
      <span class="device-meta">${escapeHtml(device.model || "Cast device")} · ${escapeHtml(device.host || "")}</span>
    `;
    btn.addEventListener("click", () => {
      state.selectedDevice = device.uuid;
      renderDevices();
      maybeCast();
    });
    el.devices.appendChild(btn);
  }
}

function renderVideos() {
  el.videos.innerHTML = "";
  if (!state.videos.length) {
    el.videoHint.hidden = false;
    el.videoHint.innerHTML =
      'No videos yet. Drop files into the <code>videos</code> folder on your Mac, then Reload.';
    return;
  }
  el.videoHint.hidden = true;
  for (const video of state.videos) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = `video${state.selectedVideo === video.id ? " selected" : ""}`;
    btn.setAttribute("role", "option");
    btn.setAttribute("aria-selected", state.selectedVideo === video.id ? "true" : "false");
    btn.innerHTML = `
      <span class="video-name">${escapeHtml(video.name)}</span>
      <span class="video-meta">${escapeHtml(video.size_label)} · tap to cast</span>
    `;
    btn.addEventListener("click", () => {
      state.selectedVideo = video.id;
      renderVideos();
      maybeCast();
    });
    el.videos.appendChild(btn);
  }
}

async function loadDevices(refresh = false) {
  el.deviceHint.hidden = false;
  el.deviceHint.textContent = "Scanning your Wi‑Fi for Cast devices…";
  try {
    const data = await api(`/api/devices?refresh=${refresh ? "true" : "false"}`);
    state.devices = data.devices || [];
    if (
      state.selectedDevice &&
      !state.devices.some((d) => d.uuid === state.selectedDevice)
    ) {
      state.selectedDevice = null;
    }
    if (!state.selectedDevice && state.devices.length === 1) {
      state.selectedDevice = state.devices[0].uuid;
    }
    renderDevices();
  } catch (err) {
    el.deviceHint.textContent = err.message;
    setStatus(err.message, "error");
  }
}

async function loadVideos() {
  el.videoHint.hidden = false;
  el.videoHint.textContent = "Loading videos from this Mac…";
  try {
    const data = await api("/api/videos");
    state.videos = data.videos || [];
    renderVideos();
  } catch (err) {
    el.videoHint.textContent = err.message;
    setStatus(err.message, "error");
  }
}

async function maybeCast() {
  if (!state.selectedDevice || !state.selectedVideo || state.casting) return;
  state.casting = true;
  const video = state.videos.find((v) => v.id === state.selectedVideo);
  setStatus(`Casting “${video?.name || "video"}”…`);
  try {
    const data = await api("/api/cast", {
      method: "POST",
      body: JSON.stringify({
        video_id: state.selectedVideo,
        device_uuid: state.selectedDevice,
      }),
    });
    showNowPlaying(video, data.status);
    setStatus("Playing on TV", "ok");
  } catch (err) {
    setStatus(err.message, "error");
  } finally {
    state.casting = false;
  }
}

function showNowPlaying(video, status) {
  el.now.hidden = false;
  el.nowTitle.textContent = video?.name || status?.title || "Playing";
  const device = state.devices.find((d) => d.uuid === state.selectedDevice);
  el.nowMeta.textContent = device ? `on ${device.name}` : "";
  if (typeof status?.volume === "number") {
    el.volume.value = Math.round(status.volume * 100);
  }
}

async function control(path) {
  if (!state.selectedDevice) return;
  try {
    const data = await api(path, {
      method: "POST",
      body: JSON.stringify({ device_uuid: state.selectedDevice }),
    });
    if (path === "/api/stop") {
      el.now.hidden = true;
      setStatus("Stopped");
    } else {
      setStatus(data.status?.player_state || "OK", "ok");
    }
  } catch (err) {
    setStatus(err.message, "error");
  }
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

document.getElementById("refresh-devices").addEventListener("click", () => loadDevices(true));
document.getElementById("refresh-videos").addEventListener("click", () => loadVideos());
document.getElementById("btn-pause").addEventListener("click", () => control("/api/pause"));
document.getElementById("btn-resume").addEventListener("click", () => control("/api/resume"));
document.getElementById("btn-stop").addEventListener("click", () => control("/api/stop"));

let volumeTimer = null;
el.volume.addEventListener("input", () => {
  if (!state.selectedDevice) return;
  clearTimeout(volumeTimer);
  volumeTimer = setTimeout(async () => {
    try {
      await api("/api/volume", {
        method: "POST",
        body: JSON.stringify({
          device_uuid: state.selectedDevice,
          level: Number(el.volume.value) / 100,
        }),
      });
    } catch (err) {
      setStatus(err.message, "error");
    }
  }, 150);
});

loadDevices(true);
loadVideos();
