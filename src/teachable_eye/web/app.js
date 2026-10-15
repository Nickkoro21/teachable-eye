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
    objects: "Objects", people: "People", memory: "Memory", photo: "Photo", live: "Live",
    video: "Video", teach: "TEACH", teachTitle: "Name this", save: "Save", cancel: "Cancel",
    labelObject: "e.g. hat", labelPerson: "e.g. person-a",
    consent: "This person agreed to be remembered on this device.",
    hintChoose: "Tap a box to choose it — tap again for the next one under your finger.",
    hintNone: "Point the camera at something.", hintPeopleNone: "Point the camera at a face.",
    hintPhoto: "Photo: tap a box, then TEACH. Live returns to the camera.",
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
    objects: "Αντικείμενα", people: "Πρόσωπα", memory: "Μνήμη", photo: "Φωτό", live: "Ζωντανά",
    video: "Βίντεο", teach: "ΜΑΘΕ", teachTitle: "Δώσε όνομα", save: "Αποθήκευση", cancel: "Άκυρο",
    labelObject: "π.χ. καπέλο", labelPerson: "π.χ. person-a",
    consent: "Το πρόσωπο συμφώνησε να το θυμάται αυτή η συσκευή.",
    hintChoose: "Πάτα ένα πλαίσιο για να το διαλέξεις — ξαναπάτα για το επόμενο.",
    hintNone: "Στόχευσε την κάμερα σε κάτι.", hintPeopleNone: "Στόχευσε την κάμερα σε ένα πρόσωπο.",
    hintPhoto: "Φωτό: πάτα ένα πλαίσιο και ΜΑΘΕ. Το «Ζωντανά» επιστρέφει στην κάμερα.",
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
  running: false, stream: null,
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
  $("langBtn").textContent = state.lang === "en" ? "EL" : "EN";
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
      video: { facingMode: { ideal: "environment" }, width: { ideal: 1920 }, height: { ideal: 1080 } },
      audio: false,
    });
    video.srcObject = state.stream;
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
    setConn("offline");
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

async function pump() {
  const now = performance.now();
  if (state.running && state.wsReady && !state.waiting && !state.still && !state.naming
      && !document.hidden && now - state.lastSent >= MIN_INTERVAL_MS) {
    const blob = await snapshot(MAX_SIDE, 0.7);
    if (blob && state.ws && state.ws.readyState === WebSocket.OPEN) {
      state.waiting = true; state.lastSent = now;
      state.ws.send(await blob.arrayBuffer());
    }
  }
  draw();
  requestAnimationFrame(pump);
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
  return ([x1, y1, x2, y2]) => [dx + x1 * srcW * scale, dy + y1 * srcH * scale,
                                (x2 - x1) * srcW * scale, (y2 - y1) * srcH * scale];
}

function caption(r) {
  if (r.decision === "known") return `${r.label} · ${r.score.toFixed(2)}`;
  if (r.decision === "uncertain") return `${t("maybe")} ${r.guess}? · ${r.score.toFixed(2)}`;
  if (r.decision === "pending") return t("pending");
  return t("unknown");
}

function chip(text, x, y, color, topLimit, cw) {
  const tw = Math.min(ctx.measureText(text).width + 14, cw - 8);
  let ty = y - 28;
  if (ty < topLimit) ty = y + 4;            // keep it out from under the top bar
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
    chip(`◎ ${caption(target)}`, x, y, color, topLimit, cw);
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
      ${escapeHtml(n.label)}<br>${n.score.toFixed(2)}</div>`).join("");
  card.innerHTML = `<div class="head"><span class="dec" style="color:${COLORS[r.decision]}">
      ${escapeHtml(name)}</span><small>${t(r.decision)} · ${r.score.toFixed(2)}</small></div>
    ${nbrs ? `<small>${t("nearest")}</small><div class="nbrs">${nbrs}</div>` : ""}`;
  card.hidden = false;
}

function updateHint() {
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
  const r = currentTarget();
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
function markChoice() {
  const typed = $("labelInput").value.trim().toLowerCase().replace(/\s+/g, " ");
  let exact = false;
  document.querySelectorAll("#choices .choice").forEach((c) => {
    const on = c.dataset.label === typed;
    exact = exact || on;
    c.classList.toggle("on", on);
    c.hidden = typed && !on && !c.dataset.label.includes(typed);
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
  if (state.burst) return;
  const rect = overlay.getBoundingClientRect();
  const r = hitTest(ev.clientX - rect.left, ev.clientY - rect.top);
  state.selected = r ? r.id : null;
  if (navigator.vibrate && r) navigator.vibrate(15);
  renderCard();
});
document.querySelectorAll("[data-start]").forEach((b) => { b.onclick = () => start(b.dataset.start); });
$("landLang").onclick = toggleLang;
$("langBtn").onclick = toggleLang;
$("homeBtn").onclick = goHome;
$("teachBtn").onclick = teachSelected;
$("videoBtn").onclick = startBurst;
$("recStop").onclick = () => stopBurst(true);
$("cancelTeach").onclick = closeTeach;
$("labelInput").addEventListener("input", markChoice);
$("teachForm").onsubmit = submitTeach;
$("photoBtn").onclick = takePhoto;
$("liveBtn").onclick = backToLive;
$("memBtn").onclick = openMemory;
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
