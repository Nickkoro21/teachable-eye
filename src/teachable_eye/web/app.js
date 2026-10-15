// teachable-eye phone client.
// The phone shows its own camera; frames go to the PC over /ws, one at a time
// (the next frame is sent only after the reply), and the replies are drawn as
// boxes over the local video.
"use strict";

const I18N = {
  en: {
    objects: "Objects", people: "People", memory: "Memory", photo: "Photo",
    live: "Live", teach: "TEACH", teachTitle: "Name this", save: "Save",
    cancel: "Cancel", labelObject: "e.g. hat", labelPerson: "e.g. person-a",
    consent: "This person agreed to be remembered on this device.",
    hintTap: "Tap a box to select it, then TEACH.",
    hintNone: "Point the camera at something.",
    known: "known", uncertain: "uncertain", unknown: "unknown", pending: "looking…",
    maybe: "maybe", views: "views", rename: "Rename", forget: "Forget",
    renamePrompt: "New name for “{0}”", forgetConfirm: "Forget “{0}” ({1} views)?",
    forgetEveryone: "Forget everyone", wipeConfirm: "Delete ALL people from this device?",
    empty: "Nothing taught yet.", taught: "Taught “{0}”.", connecting: "connecting",
    online: "live", offline: "offline", replaced: "Another camera took over.",
    cameraError: "Camera unavailable: {0}", nothingSelected: "Nothing to teach in view.",
    consentNeeded: "Please confirm consent first.", nearest: "nearest examples",
    peopleOff: "People mode is not available on the server yet.",
  },
  el: {
    objects: "Αντικείμενα", people: "Πρόσωπα", memory: "Μνήμη", photo: "Φωτό",
    live: "Ζωντανά", teach: "ΜΑΘΕ", teachTitle: "Δώσε όνομα", save: "Αποθήκευση",
    cancel: "Άκυρο", labelObject: "π.χ. καπέλο", labelPerson: "π.χ. person-a",
    consent: "Το πρόσωπο συμφώνησε να το θυμάται αυτή η συσκευή.",
    hintTap: "Πάτα ένα πλαίσιο και μετά ΜΑΘΕ.",
    hintNone: "Στόχευσε την κάμερα σε κάτι.",
    known: "γνωστό", uncertain: "αβέβαιο", unknown: "άγνωστο", pending: "κοιτάζω…",
    maybe: "ίσως", views: "όψεις", rename: "Μετονομασία", forget: "Ξέχνα",
    renamePrompt: "Νέο όνομα για «{0}»", forgetConfirm: "Να ξεχάσω το «{0}» ({1} όψεις);",
    forgetEveryone: "Ξέχνα όλα τα πρόσωπα", wipeConfirm: "Διαγραφή ΟΛΩΝ των προσώπων από τη συσκευή;",
    empty: "Δεν έχεις διδάξει τίποτα ακόμα.", taught: "Έμαθα «{0}».", connecting: "σύνδεση",
    online: "ζωντανά", offline: "εκτός", replaced: "Άλλη κάμερα πήρε τη θέση.",
    cameraError: "Η κάμερα δεν είναι διαθέσιμη: {0}", nothingSelected: "Δεν υπάρχει κάτι να μάθω.",
    consentNeeded: "Επιβεβαίωσε πρώτα τη συναίνεση.", nearest: "πιο κοντινά παραδείγματα",
    peopleOff: "Τα πρόσωπα δεν είναι ακόμα διαθέσιμα στον server.",
  },
};

const MAX_SIDE = 960;          // live frames sent to the PC
const STILL_SIDE = 1920;       // photo mode
const MIN_INTERVAL_MS = 150;   // ~6 fps ceiling
const COLORS = { known: "#14b8a6", uncertain: "#f59e0b", unknown: "#94a3b8", pending: "#e8eefc" };

const $ = (id) => document.getElementById(id);
const video = $("video"), overlay = $("overlay"), frozen = $("frozen");
const ctx = overlay.getContext("2d");
const grab = document.createElement("canvas");

const store = {
  get(k, d) { try { return localStorage.getItem(k) ?? d; } catch { return d; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch { /* private mode */ } },
};

const state = {
  lang: store.get("lang", "en"),
  task: "objects",
  tasks: ["objects"],
  ws: null, wsReady: false, waiting: false, lastSent: 0, retry: 0,
  rows: [], frameW: 1, frameH: 1, ms: 0,
  selected: null,        // track id the user tapped
  still: null,           // {rows, w, h} when photo mode is showing
  teachId: null,
};

// -- i18n ---------------------------------------------------------------------
function t(key, ...args) {
  let s = (I18N[state.lang] || I18N.en)[key] ?? I18N.en[key] ?? key;
  args.forEach((a, i) => { s = s.replace(`{${i}}`, a); });
  return s;
}
function applyLang() {
  document.documentElement.lang = state.lang;
  document.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n); });
  $("langBtn").textContent = state.lang === "en" ? "ΕΛ" : "EN";
  updateHint();
}

function toast(msg, ms = 2600) {
  const el = $("toast");
  el.textContent = msg; el.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => { el.hidden = true; }, ms);
}

// -- camera -------------------------------------------------------------------
async function startCamera() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: { ideal: "environment" }, width: { ideal: 1920 }, height: { ideal: 1080 } },
      audio: false,
    });
    video.srcObject = stream;
    await video.play();
  } catch (err) {
    toast(t("cameraError", err.message || err.name), 8000);
  }
  try { await navigator.wakeLock?.request("screen"); } catch { /* optional */ }
}

function snapshot(maxSide, quality) {
  const vw = video.videoWidth, vh = video.videoHeight;
  if (!vw || !vh) return null;
  const scale = Math.min(1, maxSide / Math.max(vw, vh));
  grab.width = Math.round(vw * scale);
  grab.height = Math.round(vh * scale);
  grab.getContext("2d").drawImage(video, 0, 0, grab.width, grab.height);
  return new Promise((resolve) => grab.toBlob(resolve, "image/jpeg", quality));
}

// -- live socket ----------------------------------------------------------------
function connect() {
  const scheme = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${scheme}://${location.host}/ws?task=${state.task}`);
  ws.binaryType = "arraybuffer";
  state.ws = ws; state.wsReady = false; state.waiting = false;
  setConn("connecting");
  ws.onopen = () => { state.wsReady = true; state.retry = 0; setConn("online"); };
  ws.onmessage = (ev) => {
    state.waiting = false;
    const msg = JSON.parse(ev.data);
    if (msg.error) return;
    if (msg.task !== state.task) return;
    state.rows = msg.rows; state.frameW = msg.w; state.frameH = msg.h; state.ms = msg.ms;
    if (state.selected != null && !state.rows.some((r) => r.id === state.selected)) state.selected = null;
    renderCard(); updateHint();
  };
  ws.onclose = (ev) => {
    if (state.ws !== ws) return;          // superseded by a task switch
    state.wsReady = false; state.waiting = false; state.rows = [];
    setConn("offline");
    if (ev.code === 4000) { toast(t("replaced"), 5000); return; }   // don't fight
    const delay = Math.min(8000, 500 * 2 ** state.retry++);
    setTimeout(() => { if (state.ws === ws) connect(); }, delay);
  };
}

function setConn(kind) {
  const el = $("conn");
  el.className = "pill " + (kind === "online" ? "ok" : kind === "offline" ? "bad" : "");
  el.textContent = kind === "online" && state.ms ? `${t("online")} · ${Math.round(state.ms)} ms` : t(kind);
}

async function pump() {
  const now = performance.now();
  if (state.wsReady && !state.waiting && !state.still && !document.hidden
      && now - state.lastSent >= MIN_INTERVAL_MS) {
    const blob = await snapshot(MAX_SIDE, 0.7);
    if (blob && state.ws && state.ws.readyState === WebSocket.OPEN) {
      state.waiting = true; state.lastSent = now;
      state.ws.send(await blob.arrayBuffer());
      setConn("online");
    }
  }
  draw();
  requestAnimationFrame(pump);
}

// -- drawing ------------------------------------------------------------------
// Map normalised frame coordinates to the screen, matching object-fit: cover.
function mapper(srcW, srcH) {
  const cw = overlay.clientWidth, ch = overlay.clientHeight;
  const scale = Math.max(cw / srcW, ch / srcH);
  const dx = (cw - srcW * scale) / 2, dy = (ch - srcH * scale) / 2;
  return ([x1, y1, x2, y2]) => [dx + x1 * srcW * scale, dy + y1 * srcH * scale,
                                (x2 - x1) * srcW * scale, (y2 - y1) * srcH * scale];
}

function caption(r) {
  if (r.decision === "known") return `${r.label} · ${r.score.toFixed(2)}`;
  if (r.decision === "uncertain") return `${t("maybe")} ${r.guess}? · ${r.score.toFixed(2)}`;
  if (r.decision === "pending") return t("pending");
  return t("unknown");
}

function draw() {
  const dpr = window.devicePixelRatio || 1;
  const cw = overlay.clientWidth, ch = overlay.clientHeight;
  if (overlay.width !== cw * dpr || overlay.height !== ch * dpr) {
    overlay.width = cw * dpr; overlay.height = ch * dpr;
  }
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, cw, ch);
  const src = state.still || { rows: state.rows, w: video.videoWidth || state.frameW, h: video.videoHeight || state.frameH };
  if (!src.rows.length) return;
  const map = mapper(src.w, src.h);
  ctx.font = "600 15px system-ui, sans-serif";
  ctx.textBaseline = "top";
  for (const r of src.rows) {
    const [x, y, w, h] = map(r.box);
    const color = COLORS[r.decision] || COLORS.unknown;
    const sel = r.id === state.selected || (state.selected == null && r.focus);
    ctx.lineWidth = sel ? 4 : 2;
    ctx.strokeStyle = color;
    ctx.setLineDash(r.decision === "pending" ? [6, 6] : []);
    ctx.strokeRect(x, y, w, h);
    ctx.setLineDash([]);
    const text = caption(r);
    const tw = ctx.measureText(text).width + 12;
    const ty = y > 26 ? y - 26 : y + 2;
    ctx.fillStyle = color;
    ctx.fillRect(x, ty, tw, 24);
    ctx.fillStyle = "#0b1220";
    ctx.fillText(text, x + 6, ty + 4);
  }
}

function hitTest(px, py) {
  const src = state.still || { rows: state.rows, w: video.videoWidth || state.frameW, h: video.videoHeight || state.frameH };
  const map = mapper(src.w, src.h);
  let best = null, bestArea = Infinity;
  for (const r of src.rows) {
    const [x, y, w, h] = map(r.box);
    if (px >= x && px <= x + w && py >= y && py <= y + h && w * h < bestArea) {
      best = r; bestArea = w * h;
    }
  }
  return best;
}

function currentTarget() {
  const rows = state.still ? state.still.rows : state.rows;
  return rows.find((r) => r.id === state.selected) || rows.find((r) => r.focus) || null;
}

function renderCard() {
  const card = $("card");
  const r = state.selected != null ? currentTarget() : null;
  if (!r || r.decision === "pending") { card.hidden = true; return; }
  const name = r.label || (r.guess ? `${t("maybe")} ${r.guess}?` : "—");
  const nbrs = (r.neighbours || []).map((n) => `
    <div class="nbr">${n.thumb ? `<img src="/thumb/${state.task}/${n.thumb}" alt="">` : ""}
      ${escapeHtml(n.label)}<br>${n.score.toFixed(2)}</div>`).join("");
  card.innerHTML = `<div class="head"><span class="dec" style="color:${COLORS[r.decision]}">
      ${escapeHtml(name)}</span><small>${t(r.decision)} · ${r.score.toFixed(2)}</small></div>
    ${nbrs ? `<small>${t("nearest")}</small><div class="nbrs">${nbrs}</div>` : ""}`;
  card.hidden = false;
}

function updateHint() {
  const rows = state.still ? state.still.rows : state.rows;
  $("hint").textContent = rows.length ? t("hintTap") : t("hintNone");
}

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

// -- actions ------------------------------------------------------------------
async function api(path, body) {
  const res = await fetch(path, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || res.statusText);
  return data;
}

function openTeach() {
  const r = currentTarget();
  if (!r || state.still) { toast(t("nothingSelected")); return; }
  state.teachId = r.id;
  $("labelInput").value = r.label || r.guess || "";
  $("labelInput").placeholder = state.task === "people" ? t("labelPerson") : t("labelObject");
  $("consentRow").hidden = state.task !== "people";
  $("consent").checked = false;
  $("teachThumb").removeAttribute("src");
  $("sheet").hidden = false;
  setTimeout(() => $("labelInput").focus(), 50);
}

async function submitTeach(ev) {
  ev.preventDefault();
  const label = $("labelInput").value.trim();
  if (!label) return;
  if (state.task === "people" && !$("consent").checked) { toast(t("consentNeeded")); return; }
  try {
    await api("/api/teach", { task: state.task, id: state.teachId, label, consent: $("consent").checked });
    toast(t("taught", label));
    $("sheet").hidden = true;
  } catch (err) { toast(err.message, 4000); }
}

async function takePhoto() {
  const blob = await snapshot(STILL_SIDE, 0.9);
  if (!blob) return;
  const res = await fetch(`/api/still?task=${state.task}`, { method: "POST", body: blob,
    headers: { "Content-Type": "image/jpeg" } });
  const data = await res.json();
  if (!res.ok) { toast(data.error || res.statusText, 4000); return; }
  frozen.width = grab.width; frozen.height = grab.height;
  frozen.getContext("2d").drawImage(grab, 0, 0);
  frozen.hidden = false;
  state.still = { rows: data.rows, w: data.w, h: data.h };
  state.selected = null;
  $("photoBtn").hidden = true; $("liveBtn").hidden = false; $("teachBtn").disabled = true;
  updateHint();
}

function backToLive() {
  state.still = null; frozen.hidden = true; state.selected = null;
  $("photoBtn").hidden = false; $("liveBtn").hidden = true; $("teachBtn").disabled = false;
  renderCard(); updateHint();
}

function switchTask(task) {
  if (task === state.task) return;
  if (!state.tasks.includes(task)) { toast(t("peopleOff")); return; }
  state.task = task; state.rows = []; state.selected = null;
  backToLive();
  document.querySelectorAll("#taskSeg button").forEach((b) => b.classList.toggle("on", b.dataset.task === task));
  const old = state.ws; state.ws = null; old?.close();
  connect();
}

// -- memory panel ---------------------------------------------------------------
async function openMemory() {
  $("memory").hidden = false;
  $("wipeBtn").hidden = state.task !== "people";
  await renderMemory();
}

async function renderMemory() {
  const list = $("memList");
  const res = await fetch(`/api/memory?task=${state.task}`);
  const data = await res.json();
  if (!data.labels || !data.labels.length) { list.innerHTML = `<p class="empty">${t("empty")}</p>`; return; }
  list.innerHTML = "";
  for (const g of data.labels) {
    const item = document.createElement("div");
    item.className = "mem-item";
    const first = g.examples.find((e) => e.thumb);
    item.innerHTML = `
      <div class="mem-row">
        ${first ? `<img src="/thumb/${state.task}/${first.thumb}" alt="">` : "<img alt=''>"}
        <div class="name"><b>${escapeHtml(g.label)}</b><small>${g.count} ${t("views")}</small></div>
        <div class="mem-actions">
          <button data-act="rename">${t("rename")}</button>
          <button data-act="forget">${t("forget")}</button>
        </div>
      </div>
      <div class="views">${g.examples.map((e) => `
        <div class="view">${e.thumb ? `<img src="/thumb/${state.task}/${e.thumb}" alt="">` : "<img alt=''>"}
          <button data-del="${e.id}" aria-label="delete view">✕</button></div>`).join("")}</div>`;
    item.querySelector('[data-act="rename"]').onclick = async () => {
      const to = prompt(t("renamePrompt", g.label), g.label);
      if (to && to.trim() && to.trim() !== g.label) {
        await api("/api/rename", { task: state.task, label: g.label, to: to.trim() }).catch((e) => toast(e.message));
        renderMemory();
      }
    };
    item.querySelector('[data-act="forget"]').onclick = async () => {
      if (confirm(t("forgetConfirm", g.label, g.count))) {
        await api("/api/forget", { task: state.task, label: g.label });
        renderMemory();
      }
    };
    item.querySelectorAll("[data-del]").forEach((b) => {
      b.onclick = async () => {
        await api("/api/forget_example", { task: state.task, id: b.dataset.del });
        renderMemory();
      };
    });
    list.appendChild(item);
  }
}

// -- wiring -------------------------------------------------------------------
overlay.addEventListener("click", (ev) => {
  const rect = overlay.getBoundingClientRect();
  const r = hitTest(ev.clientX - rect.left, ev.clientY - rect.top);
  state.selected = r ? r.id : null;
  renderCard();
});
$("teachBtn").onclick = openTeach;
$("cancelTeach").onclick = () => { $("sheet").hidden = true; };
$("teachForm").onsubmit = submitTeach;
$("photoBtn").onclick = takePhoto;
$("liveBtn").onclick = backToLive;
$("memBtn").onclick = openMemory;
$("closeMem").onclick = () => { $("memory").hidden = true; };
$("wipeBtn").onclick = async () => {
  if (confirm(t("wipeConfirm"))) { await api("/api/wipe", { task: "people" }); renderMemory(); }
};
$("langBtn").onclick = () => { state.lang = state.lang === "en" ? "el" : "en"; store.set("lang", state.lang); applyLang(); };
document.querySelectorAll("#taskSeg button").forEach((b) => { b.onclick = () => switchTask(b.dataset.task); });
document.addEventListener("visibilitychange", () => {
  if (!document.hidden && (!state.ws || state.ws.readyState > 1)) connect();
});

(async function init() {
  applyLang();
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {});
  try {
    const st = await (await fetch("/api/status")).json();
    state.tasks = Object.keys(st.tasks || { objects: 1 });
  } catch { /* server will tell us via the socket */ }
  document.querySelectorAll("#taskSeg button").forEach((b) => { b.disabled = !state.tasks.includes(b.dataset.task); });
  await startCamera();
  connect();
  requestAnimationFrame(pump);
})();
