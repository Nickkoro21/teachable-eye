// teachable-eye phone client.
// The phone shows its own camera; frames go to the PC over /ws, one at a time
// (the next frame is sent only after the reply), and the replies are drawn as
// boxes over the local video.
"use strict";

const I18N = {
  en: {
    tagline: "Show it a few examples. It remembers — on your own device.",
    step1t: "Point", step1: "the camera at something; boxes appear around what it sees.",
    step2t: "Choose", step2: "a box (tap it; tap again for the next one under your finger).",
    step3t: "Teach", step3: "it a name — or use Video to capture several views while you move around it.",
    step4t: "Check", step4: "— green means known, orange means unsure, grey means unknown.",
    startObjects: "Start · Objects", startPeople: "Start · People",
    privacy: "Everything it learns stays on your PC. Faces are stored only with the person's consent and can be forgotten at any time.",
    serverOk: "PC connected · {0}", serverDown: "PC not reachable",
    objects: "Objects", people: "People", memory: "Memory", photo: "⏸ Photo", live: "▶ Live",
    video: "Video", teach: "TEACH", teachTitle: "Name this", save: "Save", cancel: "Cancel",
    labelObject: "e.g. hat", labelPerson: "e.g. person-a",
    consent: "This person agreed to be remembered on this device.",
    hintChoose: "Tap a box to choose it — tap again for the next one under your finger.",
    hintNone: "Point the camera at something.", hintPeopleNone: "Point the camera at a face.",
    hintPhoto: "Paused: tap a box, drag its corners to fix it, or drag anywhere for a new one. TEACH, or ▶ Live to follow it.",
    following: "Following your box.",
    deleteViewConfirm: "Delete this view and its {0} variants?",
    augNote: "Each view also stores variants: zoom, mirror, darker (see Memory).",
    aug_zoom_center: "zoom", aug_flip: "mirror", aug_darker: "darker", variant: "variant",
    liveTapHint: "Nothing there. Take a Photo to mark your own box.",
    known: "known", uncertain: "uncertain", unknown: "unknown", pending: "looking…",
    maybe: "maybe", views: "views", rename: "Rename", forget: "Forget",
    renamePrompt: "New name for “{0}”", forgetConfirm: "Forget “{0}” ({1} views)?",
    forgetEveryone: "Forget everyone", wipeConfirm: "Delete ALL people from this device?",
    empty: "Nothing taught yet.", taught: "Taught “{0}” ({1} views).",
    replaced: "Another camera took over.", cameraError: "Camera unavailable: {0}",
    nothingSelected: "Choose a box first.", consentNeeded: "Please confirm consent first.",
    nearest: "nearest examples", existing: "Add a view to an existing label",
    orNew: "…or type a new name", newLabel: "new", peopleOff: "People mode is not loaded on the PC.",
    recording: "Recording views…", recMove: "Move slowly around it.", stop: "Stop",
    recViews: "{0} views", noViews: "No views captured — keep it in view and try again.",
  },
  el: {
    tagline: "Δείξ' του λίγα παραδείγματα. Θυμάται — στη δική σου συσκευή.",
    step1t: "Στόχευσε", step1: "την κάμερα σε κάτι· εμφανίζονται πλαίσια γύρω από ό,τι βλέπει.",
    step2t: "Διάλεξε", step2: "ένα πλαίσιο (πάτα το· ξαναπάτα για το επόμενο κάτω από το δάχτυλο).",
    step3t: "Μάθε", step3: "του ένα όνομα — ή πάτα Βίντεο για πολλές όψεις καθώς κινείσαι γύρω του.",
    step4t: "Έλεγξε", step4: "— πράσινο: γνωστό, πορτοκαλί: αβέβαιο, γκρι: άγνωστο.",
    startObjects: "Έναρξη · Αντικείμενα", startPeople: "Έναρξη · Πρόσωπα",
    privacy: "Ό,τι μαθαίνει μένει στο PC σου. Τα πρόσωπα αποθηκεύονται μόνο με συναίνεση και διαγράφονται όποτε θέλεις.",
    serverOk: "PC συνδεδεμένο · {0}", serverDown: "Το PC δεν απαντά",
    objects: "Αντικείμενα", people: "Πρόσωπα", memory: "Μνήμη", photo: "⏸ Φωτό", live: "▶ Ζωντανά",
    video: "Βίντεο", teach: "ΜΑΘΕ", teachTitle: "Δώσε όνομα", save: "Αποθήκευση", cancel: "Άκυρο",
    labelObject: "π.χ. καπέλο", labelPerson: "π.χ. person-a",
    consent: "Το πρόσωπο συμφώνησε να το θυμάται αυτή η συσκευή.",
    hintChoose: "Πάτα ένα πλαίσιο για να το διαλέξεις — ξαναπάτα για το επόμενο.",
    hintNone: "Στόχευσε την κάμερα σε κάτι.", hintPeopleNone: "Στόχευσε την κάμερα σε ένα πρόσωπο.",
    hintPhoto: "Παύση: πάτα ένα πλαίσιο, σύρε τις γωνίες του για διόρθωση ή σύρε οπουδήποτε για νέο. ΜΑΘΕ, ή ▶ Ζωντανά για να το ακολουθήσει.",
    following: "Ακολουθώ το πλαίσιό σου.",
    deleteViewConfirm: "Διαγραφή αυτής της όψης και των {0} παραγώγων της;",
    augNote: "Κάθε όψη αποθηκεύει και παράγωγα: ζουμ, καθρέφτης, σκοτεινό (δες Μνήμη).",
    aug_zoom_center: "ζουμ", aug_flip: "καθρέφτης", aug_darker: "σκοτεινό", variant: "παράγωγο",
    liveTapHint: "Δεν υπάρχει κάτι εκεί. Πάτα Φωτό για να σημειώσεις δικό σου πλαίσιο.",
    known: "γνωστό", uncertain: "αβέβαιο", unknown: "άγνωστο", pending: "κοιτάζω…",
    maybe: "ίσως", views: "όψεις", rename: "Μετονομασία", forget: "Ξέχνα",
    renamePrompt: "Νέο όνομα για «{0}»", forgetConfirm: "Να ξεχάσω το «{0}» ({1} όψεις);",
    forgetEveryone: "Ξέχνα όλα τα πρόσωπα", wipeConfirm: "Διαγραφή ΟΛΩΝ των προσώπων από τη συσκευή;",
    empty: "Δεν έχεις διδάξει τίποτα ακόμα.", taught: "Έμαθα «{0}» ({1} όψεις).",
    replaced: "Άλλη κάμερα πήρε τη θέση.", cameraError: "Η κάμερα δεν είναι διαθέσιμη: {0}",
    nothingSelected: "Διάλεξε πρώτα ένα πλαίσιο.", consentNeeded: "Επιβεβαίωσε πρώτα τη συναίνεση.",
    nearest: "πιο κοντινά παραδείγματα", existing: "Πρόσθεσε όψη σε υπάρχουσα ετικέτα",
    orNew: "…ή γράψε νέο όνομα", newLabel: "νέο", peopleOff: "Τα πρόσωπα δεν έχουν φορτωθεί στο PC.",
    recording: "Καταγραφή όψεων…", recMove: "Κινήσου αργά γύρω του.", stop: "Τέλος",
    recViews: "{0} όψεις", noViews: "Δεν καταγράφηκαν όψεις — κράτα το στο κάδρο και ξαναδοκίμασε.",
  },
};

const MAX_SIDE = 960;          // live frames sent to the PC
const STILL_SIDE = 1920;       // photo mode
const MIN_INTERVAL_MS = 150;   // ~6 fps ceiling
const VIDEO_SECONDS = 5;
// teach-time augmentation variants (see tasks.AUGMENT on the server)
const AUG_ICON = { zoom_center: "🔍", flip: "⇋", darker: "◐" };
function augName(aug) { return aug ? t(`aug_${aug}`) : ""; }

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
  task: "objects", tasks: ["objects"],
  running: false, stream: null, facing: store.get("facing", "environment"),
  counting: false, drag: null,
  ws: null, wsReady: false, waiting: false, lastSent: 0, retry: 0,
  rows: [], frameW: 1, frameH: 1, ms: 0,
  selected: null,        // track id the user tapped
  still: null,           // {rows, w, h} when photo mode is showing
  naming: false, holdId: null,
  burst: null,           // {id, tid, target, timer} while teaching from video
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
  $("landLang").textContent = state.lang === "en" ? "Ελληνικά" : "English";
  updateHint();
}
function toggleLang() {
  state.lang = state.lang === "en" ? "el" : "en";
  store.set("lang", state.lang);
  applyLang();
  checkServer();
}

function toast(msg, ms = 2800) {
  const el = $("toast");
  el.textContent = msg; el.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => { el.hidden = true; }, ms);
}

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

async function api(path, body, method = "POST") {
  const res = await fetch(path, {
    method, headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || res.statusText);
  return data;
}

// -- landing ------------------------------------------------------------------
async function checkServer() {
  try {
    const st = await (await fetch("/api/status")).json();
    state.tasks = Object.keys(st.tasks || { objects: 1 });
    $("landStatus").textContent = t("serverOk", state.tasks.map((k) => t(k)).join(", "));
  } catch {
    $("landStatus").textContent = t("serverDown");
  }
  document.querySelectorAll("[data-start],#taskSeg button").forEach((b) => {
    const task = b.dataset.start || b.dataset.task;
    b.disabled = !state.tasks.includes(task);
  });
}

async function start(task) {
  $("landing").hidden = true;
  setTask(task);
  if (!state.stream) await startCamera();
  state.running = true;
  connect();
  updateHint();
}

function goHome() {
  state.running = false;
  stopBurst(false);
  closeTeach();
  const old = state.ws; state.ws = null; old?.close();
  state.stream?.getTracks().forEach((tr) => tr.stop());
  state.stream = null; video.srcObject = null;
  state.rows = []; backToLive();
  $("landing").hidden = false;
  checkServer();
}

// -- camera -------------------------------------------------------------------
async function startCamera() {
  try {
    state.stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: { ideal: state.facing }, width: { ideal: 1920 }, height: { ideal: 1080 } },
      audio: false,
    });
    video.srcObject = state.stream;
    document.body.classList.toggle("mirror", state.facing === "user");
    await video.play();
  } catch (err) {
    toast(t("cameraError", err.message || err.name), 8000);
  }
  try { await navigator.wakeLock?.request("screen"); } catch { /* optional */ }
}

// Front ("selfie") or back camera. A new camera is a new scene: reconnect so
// the server resets its tracker.
async function flipCamera() {
  state.facing = state.facing === "user" ? "environment" : "user";
  store.set("facing", state.facing);
  stopBurst(false);
  backToLive();
  state.stream?.getTracks().forEach((tr) => tr.stop());
  state.stream = null;
  await startCamera();
  if (state.running) { const old = state.ws; state.ws = null; old?.close(); connect(); }
}

// 3-2-1 so the user knows a photo / video teach is coming and can hold still.
async function countdown(n = 3) {
  state.counting = true;
  const el = $("count");
  for (let i = n; i > 0; i--) {
    el.textContent = i; el.hidden = false;
    el.style.animation = "none"; void el.offsetWidth; el.style.animation = "";
    if (navigator.vibrate) navigator.vibrate(30);
    await new Promise((r) => setTimeout(r, 700));
  }
  el.hidden = true;
  state.counting = false;
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
    diag.got++;
    let msg;
    try { msg = JSON.parse(ev.data); } catch (err) { noteError("reply", err); return; }
    if (msg.error || msg.task !== state.task) return;
    state.rows = msg.rows; state.frameW = msg.w; state.frameH = msg.h; state.ms = msg.ms;
    if (state.selected != null && !state.still && !state.rows.some((r) => r.id === state.selected)) {
      state.selected = null;
    }
    setConn("online"); renderCard(); updateHint();
  };
  ws.onclose = (ev) => {
    if (state.ws !== ws) return;          // superseded (task switch, home)
    state.wsReady = false; state.waiting = false; state.rows = [];
    setConn("offline"); renderCard(); updateHint();     // no stale card
    if (ev.code === 4000) { toast(t("replaced"), 5000); return; }   // don't fight
    if (!state.running) return;
    const delay = Math.min(8000, 500 * 2 ** state.retry++);
    setTimeout(() => { if (state.ws === ws && state.running) connect(); }, delay);
  };
}

function setConn(kind) {
  const el = $("conn");
  el.className = "dot " + (kind === "online" ? "ok" : kind === "offline" ? "bad" : "");
  el.title = kind === "online" && state.ms ? `${Math.round(state.ms)} ms` : kind;
}

// The loop must never die: any error is recorded (see the diagnostics line,
// tap the connection dot) and the next frame is always scheduled.
async function pump() {
  try {
    const now = performance.now();
    if (state.waiting && now - state.lastSent > 4000) state.waiting = false;   // lost reply
    if (state.running && state.wsReady && !state.waiting && !state.still && !state.naming
        && !document.hidden && now - state.lastSent >= MIN_INTERVAL_MS) {
      const blob = await snapshot(MAX_SIDE, 0.7);
      if (blob && state.ws && state.ws.readyState === WebSocket.OPEN) {
        state.waiting = true; state.lastSent = now;
        state.ws.send(await blob.arrayBuffer());
        diag.sent++;
      }
    }
  } catch (err) { noteError("send", err); }
  try { draw(); } catch (err) { noteError("draw", err); }
  renderDiag();
  requestAnimationFrame(pump);
}

// -- diagnostics (tap the connection dot) ---------------------------------------
const diag = { on: false, sent: 0, got: 0, err: "", t0: performance.now(), fps: 0 };
function noteError(where, err) {
  diag.err = `${where}: ${err && err.message || err}`;
  if (!noteError.shown) { noteError.shown = true; toast(diag.err, 6000); }
}
function renderDiag() {
  const el = $("diag");
  if (!diag.on) { el.hidden = true; return; }
  const now = performance.now();
  if (now - diag.t0 > 1000) { diag.fps = diag.got * 1000 / (now - diag.t0); diag.got = 0; diag.t0 = now; }
  el.hidden = false;
  el.textContent = `${state.wsReady ? "ws ok" : "ws —"} · ${diag.fps.toFixed(1)} fps · ${Math.round(state.ms)} ms · ` +
    `boxes ${source().rows.length} · video ${video.videoWidth}×${video.videoHeight}` +
    (diag.err ? ` · ${diag.err}` : "");
}

// -- drawing ------------------------------------------------------------------
function source() {
  return state.still || { rows: state.rows, w: video.videoWidth || state.frameW,
                          h: video.videoHeight || state.frameH };
}

// Map normalised frame coordinates to the screen, matching object-fit: cover.
function mapper(srcW, srcH) {
  const cw = overlay.clientWidth, ch = overlay.clientHeight;
  const scale = Math.max(cw / srcW, ch / srcH);
  const dx = (cw - srcW * scale) / 2, dy = (ch - srcH * scale) / 2;
  const mirror = state.facing === "user";
  return ([x1, y1, x2, y2]) => {
    const w = (x2 - x1) * srcW * scale;
    let x = dx + x1 * srcW * scale;
    if (mirror) x = cw - x - w;             // the picture is shown mirrored
    return [x, dy + y1 * srcH * scale, w, (y2 - y1) * srcH * scale];
  };
}

// Screen point -> normalised frame point (inverse of mapper).
function toFrame(px, py) {
  const src = source();
  const cw = overlay.clientWidth, ch = overlay.clientHeight;
  const scale = Math.max(cw / src.w, ch / src.h);
  const dx = (cw - src.w * scale) / 2, dy = (ch - src.h * scale) / 2;
  if (state.facing === "user") px = cw - px;
  const clamp = (v) => Math.min(1, Math.max(0, v));
  return [clamp((px - dx) / (src.w * scale)), clamp((py - dy) / (src.h * scale))];
}

function caption(r) {
  if (r.decision === "known") return `${r.label} · ${r.score.toFixed(2)}`;
  if (r.decision === "uncertain") return `${t("maybe")} ${r.guess}? · ${r.score.toFixed(2)}`;
  if (r.decision === "pending") return t("pending");
  return t("unknown");
}

function chip(text, x, y, color, topLimit, cw) {
  const tw = Math.min(ctx.measureText(text).width + 14, cw - 8);
  // above the box if there is room, else inside it; never under the top bar
  // or off the bottom of the screen (boxes can extend past the visible crop)
  let ty = y - 28;
  if (ty < topLimit) ty = Math.max(topLimit, y + 4);
  ty = Math.min(ty, overlay.clientHeight - 140);
  const tx = Math.max(4, Math.min(x, cw - tw - 4));
  ctx.fillStyle = color;
  ctx.beginPath(); ctx.roundRect(tx, ty, tw, 26, 7); ctx.fill();
  ctx.save(); ctx.beginPath(); ctx.rect(tx, ty, tw - 6, 26); ctx.clip();
  ctx.fillStyle = "#0b1220";
  ctx.fillText(text, tx + 7, ty + 5);
  ctx.restore();
}

function corners(x, y, w, h, color) {
  const l = Math.max(12, Math.min(28, Math.min(w, h) / 3));
  ctx.strokeStyle = color; ctx.lineWidth = 6; ctx.lineCap = "round";
  ctx.beginPath();
  for (const [cx, cy, dx, dy] of [[x, y, 1, 1], [x + w, y, -1, 1], [x, y + h, 1, -1], [x + w, y + h, -1, -1]]) {
    ctx.moveTo(cx, cy + dy * l); ctx.lineTo(cx, cy); ctx.lineTo(cx + dx * l, cy);
  }
  ctx.stroke();
}

function draw() {
  const dpr = window.devicePixelRatio || 1;
  const cw = overlay.clientWidth, ch = overlay.clientHeight;
  if (overlay.width !== cw * dpr || overlay.height !== ch * dpr) {
    overlay.width = cw * dpr; overlay.height = ch * dpr;
  }
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, cw, ch);
  if (!state.running) return;
  if (state.drag && state.drag.moved) {
    const d = state.drag;
    ctx.strokeStyle = "#f59e0b"; ctx.lineWidth = 2; ctx.setLineDash([8, 6]);
    ctx.strokeRect(Math.min(d.x0, d.x1), Math.min(d.y0, d.y1),
                   Math.abs(d.x1 - d.x0), Math.abs(d.y1 - d.y0));
    ctx.setLineDash([]);
  }
  const topLimit = $("top").offsetHeight + 4;
  const src = source();
  if (!src.rows.length) return;
  const map = mapper(src.w, src.h);
  const target = currentTarget();
  ctx.font = "600 15px system-ui, sans-serif";
  ctx.textBaseline = "top";
  for (const r of src.rows) {
    if (target && r.id === target.id) continue;            // drawn last, on top
    const [x, y, w, h] = map(r.box);
    const named = r.decision === "known" || r.decision === "uncertain";
    if (named) {
      const color = COLORS[r.decision];
      ctx.strokeStyle = color; ctx.lineWidth = 2;
      ctx.strokeRect(x, y, w, h);
      chip(caption(r), x, y, color, topLimit, cw);
    } else if (r.background) {                 // table, wall: visible but thin
      ctx.strokeStyle = "#ffffff66"; ctx.lineWidth = 1; ctx.setLineDash([5, 5]);
      ctx.strokeRect(x, y, w, h); ctx.setLineDash([]);
    } else {                                   // unnamed object: clear, tappable
      ctx.strokeStyle = "#ffffffcc"; ctx.lineWidth = 2;
      ctx.setLineDash(r.decision === "pending" ? [6, 5] : []);
      ctx.strokeRect(x, y, w, h); ctx.setLineDash([]);
      ctx.fillStyle = "#ffffffcc";
      ctx.beginPath(); ctx.arc(x + w - 2, y + 2, 11, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = "#0b1220"; ctx.textAlign = "center";
      ctx.fillText("?", x + w - 2, y - 6); ctx.textAlign = "left";
    }
  }
  if (target) {
    const [x, y, w, h] = map(target.box);
    const rec = !!state.burst;
    const color = rec ? "#ef4444" : (target.decision === "pending" || target.decision === "unknown")
      ? "#ffffff" : COLORS[target.decision];
    ctx.fillStyle = rec ? "#ef444426" : "#ffffff14";
    ctx.fillRect(x, y, w, h);
    ctx.strokeStyle = color; ctx.lineWidth = 2; ctx.strokeRect(x, y, w, h);
    corners(x, y, w, h, color);
    if (state.still) {                         // corner handles: drag to fix
      ctx.fillStyle = "#ffffff";
      for (const [hx, hy] of [[x, y], [x + w, y], [x, y + h], [x + w, y + h]]) {
        ctx.fillRect(hx - 7, hy - 7, 14, 14);
      }
    }
    chip(`${target.manual ? "✎" : "◎"} ${caption(target)}`, x, y, color, topLimit, cw);
  }
}

// Every box under the finger, smallest first. Tapping the same spot again
// steps to the next one, so a lighter on a table and the table itself are
// both reachable.
function hitTest(px, py) {
  const src = source();
  const map = mapper(src.w, src.h);
  const pad = 24;                       // fingers are bigger than small boxes
  const under = [];
  for (const r of src.rows) {
    const [x, y, w, h] = map(r.box);
    if (px >= x - pad && px <= x + w + pad && py >= y - pad && py <= y + h + pad) {
      under.push([w * h, r]);
    }
  }
  if (!under.length) return null;
  under.sort((a, b) => a[0] - b[0]);
  const rows = under.map(([, r]) => r);
  const at = rows.findIndex((r) => r.id === state.selected);
  return at >= 0 ? rows[(at + 1) % rows.length] : rows[0];
}

function currentTarget() {
  const rows = source().rows;
  if (state.burst) return rows.find((r) => r.id === state.burst.tid) || null;
  return rows.find((r) => r.id === state.selected) || rows.find((r) => r.focus) || null;
}

function renderCard() {
  const card = $("card");
  const r = currentTarget();
  if (!r || r.decision === "pending" || state.burst) { card.hidden = true; return; }
  const name = r.label || (r.guess ? `${t("maybe")} ${r.guess}?` : t("unknown"));
  const nbrs = (r.neighbours || []).map((n) => `
    <div class="nbr">${n.thumb ? `<img src="/thumb/${state.task}/${n.thumb}" alt="">` : ""}
      ${escapeHtml(n.label)}<br>${n.score.toFixed(2)}${n.aug ? ` ${AUG_ICON[n.aug] || ""}` : ""}</div>`).join("");
  card.innerHTML = `<div class="head"><span class="dec" style="color:${COLORS[r.decision]}">
      ${escapeHtml(name)}</span><small>${t(r.decision)} · ${r.score.toFixed(2)}</small></div>
    ${nbrs ? `<small>${t("nearest")}</small><div class="nbrs">${nbrs}</div>` : ""}`;
  card.hidden = false;
}

// Keep the evidence card just above the hint, however many lines the hint has.
function placeCard() {
  const hint = $("hint");
  const base = 104 + (hint.textContent ? hint.offsetHeight + 10 : 0);
  $("card").style.bottom = `calc(env(safe-area-inset-bottom) + ${base}px)`;
}

function updateHint() {
  queueMicrotask(placeCard);
  const hint = $("hint");
  if (!state.running || state.burst) { hint.textContent = ""; return; }
  const rows = source().rows;
  if (state.still) hint.textContent = t("hintPhoto");
  else if (rows.length) hint.textContent = t("hintChoose");
  else hint.textContent = state.task === "people" ? t("hintPeopleNone") : t("hintNone");
}

// -- teaching -----------------------------------------------------------------
// TEACH freezes the selection on the server at once (a "hold"), so moving the
// phone while typing the name cannot lose the object.
async function teachSelected() {
  const r = currentTarget();
  if (!r) { toast(t("nothingSelected")); return; }
  const preview = cropPreview(r.box);
  try {
    const res = await api("/api/hold", { task: state.task, id: r.id, still: !!state.still });
    openNameSheet(res.hold, preview ? [preview] : [], r);
  } catch (err) { toast(err.message, 4000); }
}

// Teach from video: collect distinct views of the chosen object for a few
// seconds while the user moves around it, then name them all at once.
async function startBurst() {
  if (state.burst) return;
  if (state.still) backToLive();
  const chosen = currentTarget();
  if (state.counting) return;
  if (!chosen) { toast(t("nothingSelected")); return; }
  state.selected = chosen.id;               // keep it chosen during the count
  await countdown(3);
  const r = state.rows.find((x) => x.id === chosen.id);
  if (!r) { toast(t("nothingSelected")); return; }
  let res;
  try {
    res = await api("/api/burst", { task: state.task, id: r.id, seconds: VIDEO_SECONDS });
  } catch (err) { toast(err.message, 4000); return; }
  state.burst = { id: res.burst, tid: r.id, target: r };
  $("rec").hidden = false; $("recLeft").textContent = VIDEO_SECONDS; $("recViews").textContent = "";
  updateHint(); renderCard();
  state.burst.timer = setInterval(async () => {
    if (!state.burst) return;
    try {
      const st = await api(`/api/burst/${state.burst.id}?task=${state.task}`, null, "GET");
      $("recLeft").textContent = Math.ceil(st.left);
      $("recViews").textContent = t("recViews", st.views);
      if (st.done) stopBurst(true);
    } catch { stopBurst(false); }
  }, 400);
}

async function stopBurst(keep) {
  const b = state.burst;
  if (!b) return;
  clearInterval(b.timer);
  state.burst = null;
  $("rec").hidden = true;
  updateHint();
  if (!keep) return;
  try {
    const res = await api(`/api/burst/${b.id}/finish?task=${state.task}`, {});
    const thumbs = Array.from({ length: res.views },
      (_, i) => `/api/hold/${res.hold}/${i}.jpg?task=${state.task}`);
    openNameSheet(res.hold, thumbs, b.target);
  } catch (err) { toast(err.message.includes("no views") ? t("noViews") : err.message, 5000); }
}

function openNameSheet(holdId, thumbs, r) {
  state.holdId = holdId;
  state.naming = true;
  $("teachThumbs").innerHTML = thumbs.map((src) => `<img src="${src}" alt="">`).join("");
  $("labelInput").value = "";
  $("labelInput").placeholder = state.task === "people" ? t("labelPerson") : t("labelObject");
  $("consentRow").hidden = state.task !== "people";
  $("consent").checked = false;
  $("sheet").hidden = false;
  loadChoices(r);
}

function closeTeach() {
  $("sheet").hidden = true;
  state.naming = false;
  state.holdId = null;
}

// What exactly will be taught: the target's region of the current picture.
function cropPreview(box) {
  const img = state.still ? frozen : video;
  const vw = state.still ? frozen.width : video.videoWidth;
  const vh = state.still ? frozen.height : video.videoHeight;
  if (!vw || !vh) return null;
  const [x1, y1, x2, y2] = box;
  const sx = x1 * vw, sy = y1 * vh, sw = (x2 - x1) * vw, sh = (y2 - y1) * vh;
  if (sw < 2 || sh < 2) return null;
  const c = document.createElement("canvas");
  const s = 192 / Math.max(sw, sh);
  c.width = Math.round(sw * s); c.height = Math.round(sh * s);
  c.getContext("2d").drawImage(img, sx, sy, sw, sh, 0, 0, c.width, c.height);
  return c.toDataURL("image/jpeg", 0.85);
}

// Existing labels as one-tap choices. The most likely one (what memory
// matched or guessed for this object) comes first, starred and pre-selected.
async function loadChoices(r) {
  const wrap = $("choicesWrap"), box = $("choices");
  box.innerHTML = ""; wrap.hidden = true;
  let labels = [];
  try {
    labels = (await (await fetch(`/api/memory?task=${state.task}`)).json()).labels || [];
  } catch { /* a typed name still works */ }
  if (!labels.length) { setTimeout(() => $("labelInput").focus(), 50); markChoice(); return; }
  const likely = r && (r.label || r.guess || (r.neighbours && r.neighbours[0] && r.neighbours[0].label));
  labels.sort((a, b) => (b.label === likely) - (a.label === likely));
  for (const g of labels) {
    const thumb = (g.examples.find((e) => e.thumb) || {}).thumb;
    const b = document.createElement("button");
    b.type = "button";
    b.className = "choice" + (g.label === likely ? " suggested" : "");
    b.dataset.label = g.label;
    b.innerHTML = `${thumb ? `<img src="/thumb/${state.task}/${thumb}" alt="">` : ""}
      <span>${g.label === likely ? "★ " : ""}${escapeHtml(g.label)}</span><span class="n">${g.count}</span>`;
    b.onclick = () => { $("labelInput").value = g.label; markChoice(); };
    box.appendChild(b);
  }
  wrap.hidden = false;
  if (likely && labels.some((g) => g.label === likely)) $("labelInput").value = likely;
  markChoice();
}

// Highlight the chip matching the typed name and filter the rest.
// Accents and case do not make a different thing: «ποτήρι» = «ποτηρι».
function fold(text) {
  return text.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLowerCase().replace(/\s+/g, " ").trim();
}

function markChoice() {
  const raw = $("labelInput").value.trim().toLowerCase().replace(/\s+/g, " ");
  const typed = fold(raw);
  let exact = false;
  document.querySelectorAll("#choices .choice").forEach((c) => {
    const label = fold(c.dataset.label);
    const on = label === typed;
    exact = exact || on;
    c.classList.toggle("on", on);
    c.hidden = typed && !on && !label.includes(typed);
    // same word typed with other accents: use the existing label as stored
    if (on && c.dataset.label !== raw) $("labelInput").value = c.dataset.label;
  });
  $("saveBtn").textContent = typed && !exact ? `${t("save")} · ${t("newLabel")}` : t("save");
}

async function submitTeach(ev) {
  ev.preventDefault();
  const label = $("labelInput").value.trim();
  if (!label || !state.holdId) return;
  if (state.task === "people" && !$("consent").checked) { toast(t("consentNeeded")); return; }
  const save = $("saveBtn");
  save.disabled = true;
  const views = $("teachThumbs").children.length || 1;
  try {
    await api("/api/teach", { task: state.task, hold: state.holdId, label, consent: $("consent").checked });
    toast(t("taught", label, views));
    closeTeach();
  } catch (err) {
    toast(err.message, 4000);
  } finally {
    save.disabled = false;
  }
}

// -- photo mode ---------------------------------------------------------------
async function takePhoto() {
  if (state.counting) return;
  await countdown(3);
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
  $("photoBtn").hidden = true; $("liveBtn").hidden = false; $("videoBtn").disabled = true;
  renderCard(); updateHint();
}

// ▶ Live after a pause: whatever box was chosen (detected, drawn or fixed)
// is followed from that frame on, by a tracker started from that exact box.
async function resumeLive() {
  const chosen = state.still && state.selected != null
    ? state.still.rows.find((r) => r.id === state.selected) : null;
  backToLive();
  if (!chosen || state.task !== "objects") return;
  try {
    const res = await api("/api/follow", { task: state.task, box: chosen.box });
    state.selected = res.id;
    toast(t("following"));
  } catch (err) { toast(err.message, 4000); }
}

function backToLive() {
  state.still = null; frozen.hidden = true; state.selected = null;
  $("photoBtn").hidden = false; $("liveBtn").hidden = true; $("videoBtn").disabled = false;
  renderCard(); updateHint();
}

// -- tasks --------------------------------------------------------------------
function setTask(task) {
  state.task = task; state.rows = []; state.selected = null;
  document.querySelectorAll("#taskSeg button").forEach((b) => b.classList.toggle("on", b.dataset.task === task));
}

function switchTask(task) {
  if (task === state.task) return;
  if (!state.tasks.includes(task)) { toast(t("peopleOff")); return; }
  stopBurst(false);
  setTask(task);
  backToLive();
  const old = state.ws; state.ws = null; old?.close();
  connect();
}

// -- memory panel ---------------------------------------------------------------
async function openMemory() {
  $("memory").hidden = false;
  $("memTitle").textContent = `${t("memory")} · ${t(state.task)}`;
  $("wipeBtn").hidden = state.task !== "people";
  await renderMemory();
}

async function renderMemory() {
  const list = $("memList");
  const data = await (await fetch(`/api/memory?task=${state.task}`)).json();
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
        <div class="view-group">
          <div class="view">${e.thumb ? `<img src="/thumb/${state.task}/${e.thumb}" alt="">` : "<img alt=''>"}
            <button data-del="${e.id}" data-n="${(e.variants || []).length}" aria-label="delete view">✕</button></div>
          ${(e.variants || []).length ? `<div class="variants">${e.variants.map((v) => `
            <div class="variant" title="${escapeHtml(augName(v.aug))}">
              ${v.thumb ? `<img src="/thumb/${state.task}/${v.thumb}" alt="">` : "<img alt=''>"}
              <span class="tag">${AUG_ICON[v.aug] || "＋"}</span>
              <button data-del="${v.id}" data-variant="1" aria-label="delete variant">✕</button></div>`).join("")}
          </div>` : ""}
        </div>`).join("")}</div>`;
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
        // a main view takes its variants with it; say so before deleting
        const n = Number(b.dataset.n || 0);
        if (!b.dataset.variant && n && !confirm(t("deleteViewConfirm", n))) return;
        await api("/api/forget_example", { task: state.task, id: b.dataset.del });
        renderMemory();
      };
    });
    list.appendChild(item);
  }
}

// -- wiring -------------------------------------------------------------------
// Tap: choose a box (again: the next one under the finger). On a photo, a
// tap on empty space or a drag marks a box of your own.
function point(ev) {
  const rect = overlay.getBoundingClientRect();
  return [ev.clientX - rect.left, ev.clientY - rect.top];
}
overlay.addEventListener("pointerdown", (ev) => {
  if (state.burst || state.counting) return;
  const [x, y] = point(ev);
  state.drag = { x0: x, y0: y, x1: x, y1: y, moved: false };
  const target = state.still && state.selected != null ? currentTarget() : null;
  if (target) {                              // near a corner of the chosen box?
    const src = source();
    const [bx, by, bw, bh] = mapper(src.w, src.h)(target.box);
    const cs = [[bx, by], [bx + bw, by], [bx, by + bh], [bx + bw, by + bh]];
    const i = cs.findIndex(([cx, cy]) => Math.hypot(cx - x, cy - y) < 32);
    if (i >= 0) {
      const opp = cs[3 - i];                 // the corner that stays put
      state.drag = { x0: opp[0], y0: opp[1], x1: x, y1: y, moved: true, edit: target.id };
    }
  }
  overlay.setPointerCapture(ev.pointerId);
});
overlay.addEventListener("pointermove", (ev) => {
  if (!state.drag) return;
  const [x, y] = point(ev);
  state.drag.x1 = x; state.drag.y1 = y;
  if (state.still && Math.hypot(x - state.drag.x0, y - state.drag.y0) > 14) state.drag.moved = true;
});
overlay.addEventListener("pointerup", () => {
  const d = state.drag;
  state.drag = null;
  if (!d) return;
  if (d.moved) {                                   // a drawn or fixed box
    if (d.edit != null && state.still) {             // the fixed box replaces it
      state.still.rows = state.still.rows.filter((r) => r.id !== d.edit);
    }
    const a = toFrame(d.x0, d.y0), b = toFrame(d.x1, d.y1);
    markRegion([Math.min(a[0], b[0]), Math.min(a[1], b[1]),
                Math.max(a[0], b[0]), Math.max(a[1], b[1])]);
    return;
  }
  const r = hitTest(d.x0, d.y0);
  if (r) {
    state.selected = r.id;
    if (navigator.vibrate) navigator.vibrate(15);
  } else if (state.still) {                        // empty spot on a photo
    const [fx, fy] = toFrame(d.x0, d.y0);
    const short = Math.min(state.still.w, state.still.h);
    const hw = 0.06 * short / state.still.w, hh = 0.06 * short / state.still.h;
    const clamp = (v) => Math.min(1, Math.max(0, v));
    markRegion([clamp(fx - hw), clamp(fy - hh), clamp(fx + hw), clamp(fy + hh)]);
    return;
  } else {
    state.selected = null;
    toast(t("liveTapHint"));
  }
  renderCard();
});

async function markRegion(box) {
  if (box[2] - box[0] < 0.005 || box[3] - box[1] < 0.005) return;
  try {
    const res = await api("/api/region", { task: state.task, box });
    state.still.rows.push(res.row);
    state.selected = res.row.id;
    if (navigator.vibrate) navigator.vibrate(15);
    renderCard(); updateHint();
  } catch (err) { toast(err.message, 4000); }
}
document.querySelectorAll("[data-start]").forEach((b) => { b.onclick = () => start(b.dataset.start); });
$("landLang").onclick = toggleLang;
$("homeBtn").onclick = goHome;
$("flipBtn").onclick = flipCamera;
$("teachBtn").onclick = teachSelected;
$("videoBtn").onclick = startBurst;
$("recStop").onclick = () => stopBurst(true);
$("cancelTeach").onclick = closeTeach;
$("labelInput").addEventListener("input", markChoice);
$("teachForm").onsubmit = submitTeach;
$("photoBtn").onclick = takePhoto;
$("liveBtn").onclick = resumeLive;
$("memBtn").onclick = openMemory;
$("conn").onclick = () => { diag.on = !diag.on; renderDiag(); };
$("closeMem").onclick = () => { $("memory").hidden = true; };
$("wipeBtn").onclick = async () => {
  if (confirm(t("wipeConfirm"))) { await api("/api/wipe", { task: "people" }); renderMemory(); }
};
document.querySelectorAll("#taskSeg button").forEach((b) => { b.onclick = () => switchTask(b.dataset.task); });
document.addEventListener("visibilitychange", () => {
  if (state.running && !document.hidden && (!state.ws || state.ws.readyState > 1)) connect();
});

(function init() {
  applyLang();
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {});
  checkServer();
  requestAnimationFrame(pump);
})();
