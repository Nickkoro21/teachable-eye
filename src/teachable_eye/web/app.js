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
    step3t: "Teach", step3: "it a name: type it, or hold 🎤 and say “this is my hat”. Video captures several views while you move around it.",
    step4t: "Check", step4: "— green means known, orange means unsure, grey means unknown.",
    startObjects: "Start · Objects", startPeople: "Start · People",
    privacy: "Everything it learns stays on your PC. Faces are stored only with the person's consent and can be forgotten at any time.",
    serverOk: "PC connected · {0}", serverDown: "PC not reachable",
    offlineTitle: "The PC is not answering.",
    offlineHelp: "On the phone, turn Tailscale on (it must say Connected). On the PC, the server starts by itself after sign-in; keep the PC awake. This page checks again every few seconds.",
    objects: "Objects", people: "People", memory: "Memory", photo: "⏸ Photo", live: "▶ Live",
    video: "Video", teach: "TEACH", teachTitle: "Name this", save: "Save", cancel: "Cancel",
    labelObject: "e.g. hat", labelPerson: "e.g. person-a",
    consent: "This person agreed to be remembered on this device.",
    hintChoose: "Tap a box to make it active (tap again for the next one under your finger). Pinch to zoom.",
    hintActive: "Active box: TEACH, 🎤 or Video. Drag it or its corners to fix it (the picture pauses), ✕ to drop it.",
    chooseFirst: "Several boxes: tap the one you mean first.",
    dropped: "Dropped: it will not be offered again.", removed: "Box removed.",
    pausedEdit: "Paused so you can fix the box: drag it, or drag its corners.",
    zoomNo: "This camera cannot zoom here: pause with Photo and pinch the photo.",
    hintNone: "Point the camera at something.", hintPeopleNone: "Point the camera at a face.",
    hintPhoto: "Paused: tap a box to make it active; drag it to move, corners to resize, ✕ to drop it; drag on empty space for a new box; pinch to zoom. TEACH, or ▶ Live to follow it.",
    following: "Following your box.",
    labelAll: "Label all", labelAllShort: "All", labelAllHint: "Each number matches a box on the photo. Empty = skip.",
    skipPh: "(skip)", saveAll: "Save {0}", taughtMany: "Taught {0} labels.",
    addBox: "+ New box: drag on the photo", drawNow: "Drag on the photo to draw the new box.",
    consentAll: "These people agreed to be remembered on this device.", noBoxes: "No boxes on this photo.",
    deleteViewConfirm: "Delete this view and its {0} variants?",
    augNote: "Each view also stores variants: zoom, mirror, darker (see Memory).",
    augNotePeople: "Each view also stores variants: mirror, darker (see Memory).",
    saving: "Saving…",
    say: "🎤 Say", listening: "Listening… release when you are done.",
    micShort: "Hold 🎤 while you speak, then let go.", heard: "Heard: “{0}”",
    micError: "Microphone unavailable: {0}", recognising: "Recognising…",
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
    assistTitle: "✨ Claude help (cloud, optional)",
    assistNote: "Name suggestions, a second opinion, report summaries. Objects only; pictures with a face never leave the PC.",
    testBadge: "🧪 test", evalMode: "🧪 Test set: save for evaluation, do not teach",
    saveTest: "Save to test set", savedTest: "Saved {1} test views of “{0}” (not taught).",
    savedTestMany: "Saved {0} labels to the test set (not taught).",
    suggestNames: "✨ Suggest names (Claude)", suggesting: "Asking Claude…",
    suggested: "Claude suggested {0} names — check them before saving.", faceKept: "face: not sent",
    askClaude: "✨ Ask Claude", asking: "Asking Claude…", claudeSays: "Claude",
    noMatch: "none of the taught ones", teachAs: "Teach as “{0}”",
    conf_high: "sure", conf_medium: "fairly sure", conf_low: "unsure",
    testSet: "Test set", runEval: "Run evaluation", running: "Evaluating…",
    testIntro: "Test views are never taught. Save views of taught things in other light, angles and places — and things never taught (they should come out unknown). Then run the evaluation.",
    testEmpty: "No test views yet. In TEACH or Label all, tick 🧪 Test set.",
    stranger: "never taught", taughtTag: "taught", bandsCur: "now", bandsRec: "recommended",
    colCorrect: "correct", colDanger: "dangerous", colUnsure: "unsure", colStrangers: "strangers → unknown",
    dangerNote: "Dangerous = a confident wrong name. It must stay 0.",
    fullReport: "Full report", summary: "✨ Summary for managers (Claude)",
    askPh: "Ask about your memory… (Claude)", evalViews: "{0} test views",
  },
  el: {
    tagline: "Δείξ' του λίγα παραδείγματα. Θυμάται — στη δική σου συσκευή.",
    step1t: "Στόχευσε", step1: "την κάμερα σε κάτι· εμφανίζονται πλαίσια γύρω από ό,τι βλέπει.",
    step2t: "Διάλεξε", step2: "ένα πλαίσιο (πάτα το· ξαναπάτα για το επόμενο κάτω από το δάχτυλο).",
    step3t: "Μάθε", step3: "του ένα όνομα: γράψ' το, ή κράτα το 🎤 και πες «αυτό είναι το καπέλο μου». Το Βίντεο παίρνει πολλές όψεις καθώς κινείσαι γύρω του.",
    step4t: "Έλεγξε", step4: "— πράσινο: γνωστό, πορτοκαλί: αβέβαιο, γκρι: άγνωστο.",
    startObjects: "Έναρξη · Αντικείμενα", startPeople: "Έναρξη · Πρόσωπα",
    privacy: "Ό,τι μαθαίνει μένει στο PC σου. Τα πρόσωπα αποθηκεύονται μόνο με συναίνεση και διαγράφονται όποτε θέλεις.",
    serverOk: "PC συνδεδεμένο · {0}", serverDown: "Το PC δεν απαντά",
    offlineTitle: "Το PC δεν απαντά.",
    offlineHelp: "Στο κινητό, άνοιξε το Tailscale (πρέπει να γράφει Connected). Στο PC, ο server ξεκινά μόνος του μετά τη σύνδεση στα Windows· κράτα το PC ξύπνιο. Η σελίδα ξαναελέγχει κάθε λίγα δευτερόλεπτα.",
    objects: "Αντικείμενα", people: "Πρόσωπα", memory: "Μνήμη", photo: "⏸ Φωτό", live: "▶ Ζωντανά",
    video: "Βίντεο", teach: "ΜΑΘΕ", teachTitle: "Δώσε όνομα", save: "Αποθήκευση", cancel: "Άκυρο",
    labelObject: "π.χ. καπέλο", labelPerson: "π.χ. person-a",
    consent: "Το πρόσωπο συμφώνησε να το θυμάται αυτή η συσκευή.",
    hintChoose: "Πάτα ένα πλαίσιο για να γίνει ενεργό (ξαναπάτα για το επόμενο). Δύο δάχτυλα για ζουμ.",
    hintActive: "Ενεργό πλαίσιο: ΜΑΘΕ, 🎤 ή Βίντεο. Σύρε το ή τις γωνίες του για διόρθωση (η εικόνα παγώνει), ✕ για να το απορρίψεις.",
    chooseFirst: "Υπάρχουν πολλά πλαίσια: πάτα πρώτα αυτό που εννοείς.",
    dropped: "Απορρίφθηκε: δεν θα σου ξαναπροταθεί.", removed: "Το πλαίσιο αφαιρέθηκε.",
    pausedEdit: "Πάγωσε για να διορθώσεις το πλαίσιο: σύρε το ή τις γωνίες του.",
    zoomNo: "Αυτή η κάμερα δεν κάνει ζουμ εδώ: πάτα Φωτό και κάνε ζουμ στη φωτογραφία.",
    hintNone: "Στόχευσε την κάμερα σε κάτι.", hintPeopleNone: "Στόχευσε την κάμερα σε ένα πρόσωπο.",
    hintPhoto: "Παύση: πάτα ένα πλαίσιο για να γίνει ενεργό· σύρε το για μετακίνηση, τις γωνίες για μέγεθος, ✕ για απόρριψη· σύρε σε κενό σημείο για νέο· δύο δάχτυλα για ζουμ. ΜΑΘΕ, ή ▶ Ζωντανά για να το ακολουθήσει.",
    following: "Ακολουθώ το πλαίσιό σου.",
    labelAll: "Ετικέτες σε όλα", labelAllShort: "Όλα", labelAllHint: "Κάθε αριθμός αντιστοιχεί σε πλαίσιο στη φωτογραφία. Κενό = παράλειψη.",
    skipPh: "(παράλειψη)", saveAll: "Αποθήκευση {0}", taughtMany: "Έμαθα {0} ετικέτες.",
    addBox: "+ Νέο πλαίσιο: σύρε πάνω στη φωτογραφία", drawNow: "Σύρε πάνω στη φωτογραφία για το νέο πλαίσιο.",
    consentAll: "Τα πρόσωπα συμφώνησαν να τα θυμάται αυτή η συσκευή.", noBoxes: "Δεν υπάρχουν πλαίσια σε αυτή τη φωτογραφία.",
    deleteViewConfirm: "Διαγραφή αυτής της όψης και των {0} παραγώγων της;",
    augNote: "Κάθε όψη αποθηκεύει και παράγωγα: ζουμ, καθρέφτης, σκοτεινό (δες Μνήμη).",
    augNotePeople: "Κάθε όψη αποθηκεύει και παράγωγα: καθρέφτης, σκοτεινό (δες Μνήμη).",
    saving: "Αποθήκευση…",
    say: "🎤 Πες", listening: "Ακούω… άφησε το κουμπί όταν τελειώσεις.",
    micShort: "Κράτα πατημένο το 🎤 όσο μιλάς και μετά άφησέ το.", heard: "Άκουσα: «{0}»",
    micError: "Το μικρόφωνο δεν είναι διαθέσιμο: {0}", recognising: "Αναγνώριση…",
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
    assistTitle: "✨ Βοήθεια από το Claude (cloud, προαιρετική)",
    assistNote: "Προτάσεις ονομάτων, δεύτερη γνώμη, σύνοψη αναφορών. Μόνο αντικείμενα· εικόνες με πρόσωπο δεν φεύγουν ποτέ από το PC.",
    testBadge: "🧪 δοκιμή", evalMode: "🧪 Σύνολο δοκιμής: αποθήκευση για αξιολόγηση, όχι μάθηση",
    saveTest: "Αποθήκευση για δοκιμή", savedTest: "Αποθηκεύτηκαν {1} όψεις δοκιμής του «{0}» (δεν το έμαθε).",
    savedTestMany: "Αποθηκεύτηκαν {0} ετικέτες για δοκιμή (δεν τις έμαθε).",
    suggestNames: "✨ Πρότεινε ονόματα (Claude)", suggesting: "Ρωτάω το Claude…",
    suggested: "Το Claude πρότεινε {0} ονόματα — έλεγξέ τα πριν την αποθήκευση.", faceKept: "πρόσωπο: δεν στάλθηκε",
    askClaude: "✨ Ρώτα το Claude", asking: "Ρωτάω το Claude…", claudeSays: "Claude",
    noMatch: "κανένα από τα γνωστά", teachAs: "Μάθε το ως «{0}»",
    conf_high: "σίγουρο", conf_medium: "μάλλον", conf_low: "αβέβαιο",
    testSet: "Δοκιμή", runEval: "Αξιολόγηση", running: "Αξιολογώ…",
    testIntro: "Οι όψεις δοκιμής δεν διδάσκονται ποτέ. Αποθήκευσε όψεις από γνωστά αντικείμενα σε άλλο φως, γωνία και μέρος — και αντικείμενα που δεν έμαθε ποτέ (πρέπει να βγουν «άγνωστο»). Μετά πάτα Αξιολόγηση.",
    testEmpty: "Δεν υπάρχουν όψεις δοκιμής. Στο ΜΑΘΕ ή στο «Όλα», τσέκαρε 🧪 Σύνολο δοκιμής.",
    stranger: "δεν το έμαθε", taughtTag: "γνωστό", bandsCur: "τώρα", bandsRec: "προτεινόμενο",
    colCorrect: "σωστά", colDanger: "επικίνδυνα", colUnsure: "αβέβαια", colStrangers: "άγνωστα → «άγνωστο»",
    dangerNote: "Επικίνδυνο = σίγουρο λάθος όνομα. Πρέπει να μένει 0.",
    fullReport: "Πλήρης αναφορά", summary: "✨ Σύνοψη για προϊσταμένους (Claude)",
    askPh: "Ρώτα για τη μνήμη σου… (Claude)", evalViews: "{0} όψεις δοκιμής",
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
  counting: false, drag: null, multi: null,
  ws: null, wsReady: false, waiting: false, lastSent: 0, retry: 0,
  rows: [], frameW: 1, frameH: 1, ms: 0,
  selected: null,        // track id the user tapped
  still: null,           // {rows, w, h} when photo mode is showing
  naming: false, holdId: null,
  burst: null,           // {id, tid, target, timer} while teaching from video
  evalMode: store.get("evalMode", "0") === "1",   // save to the test set, not memory
  assist: { ready: false, enabled: false },       // Claude help on the PC
  assistOn: store.get("assist", "0") === "1",     // ...and opted in on this phone
  opinion: null,         // Claude's second opinion for the chosen box
  memTab: "memory", lastEval: null,
  dismissed: new Set(),  // live track ids the user dropped with ✕
  view: { s: 1, x: 0, y: 0 },   // pinch zoom of the paused photo (screen space)
  pinch: null, camZoom: null,
};

// Claude help is offered only when the PC has it, this phone opted in, and
// the task is objects (faces are never sent).
function assistOk() { return state.assist.ready && state.assistOn && state.task === "objects"; }

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
// The landing page keeps checking until the PC answers (Tailscale may be
// off on the phone, or the PC asleep or still starting).
async function checkServer() {
  let up = false;
  try {
    const res = await fetch("/api/status", { cache: "no-store" });
    const st = await res.json();
    state.tasks = Object.keys(st.tasks || { objects: 1 });
    $("landStatus").textContent = t("serverOk", state.tasks.map((k) => t(k)).join(", "));
    up = true;
  } catch {
    $("landStatus").textContent = t("serverDown");
  }
  $("offline").hidden = up;
  clearTimeout(checkServer.timer);
  if (!up && !$("landing").hidden) checkServer.timer = setTimeout(checkServer, 4000);
  if (!up) {
    document.querySelectorAll("[data-start]").forEach((b) => { b.disabled = true; });
    return;
  }
  try { state.assist = await (await fetch("/api/assist")).json(); } catch { /* optional */ }
  $("assistRow").hidden = !state.assist.enabled;
  $("assistToggle").checked = state.assistOn;
  $("assistToggle").disabled = !state.assist.ready;
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
  state.dismissed.clear();               // track ids restart with the tracker
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
  return state.still || { rows: state.rows.filter((r) => !state.dismissed.has(r.id)),
                          w: video.videoWidth || state.frameW,
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
    const v = state.still ? state.view : { s: 1, x: 0, y: 0 };   // pinch zoom
    return [x * v.s + v.x, (dy + y1 * srcH * scale) * v.s + v.y, w * v.s,
            (y2 - y1) * srcH * scale * v.s];
  };
}

// Screen point -> normalised frame point (inverse of mapper).
function toFrame(px, py) {
  const src = source();
  const cw = overlay.clientWidth, ch = overlay.clientHeight;
  const scale = Math.max(cw / src.w, ch / src.h);
  const dx = (cw - src.w * scale) / 2, dy = (ch - src.h * scale) / 2;
  if (state.still) {                          // undo the pinch zoom first
    px = (px - state.view.x) / state.view.s;
    py = (py - state.view.y) / state.view.s;
  }
  if (state.facing === "user") px = cw - px;
  const clamp = (v) => Math.min(1, Math.max(0, v));
  return [clamp((px - dx) / (src.w * scale)), clamp((py - dy) / (src.h * scale))];
}

function caption(r) {
  if (r.tested) return `🧪 ${r.label}`;
  if (r.taught) return `✓ ${r.label}`;
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
  if (state.multi) {                         // numbered badges = list rows
    state.multi.forEach((id, i) => {
      const r = src.rows.find((q) => q.id === id);
      if (!r) return;
      const [x, y] = map(r.box);
      ctx.fillStyle = r.id === state.selected ? "#14b8a6" : "#e8eefc";
      ctx.beginPath(); ctx.arc(x + 12, y + 12, 12, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = "#0b1220"; ctx.textAlign = "center";
      ctx.fillText(String(i + 1), x + 12, y + 4); ctx.textAlign = "left";
    });
  }
  if (target) {
    const [x, y, w, h] = map(target.box);
    const rec = !!state.burst;
    const active = rec || target.id === state.selected;
    const color = rec ? "#ef4444" : (target.decision === "pending" || target.decision === "unknown")
      ? "#ffffff" : COLORS[target.decision];
    if (active) {                              // the box TEACH / 🎤 / Video act on
      ctx.fillStyle = rec ? "#ef444426" : "#ffffff14";
      ctx.fillRect(x, y, w, h);
      ctx.strokeStyle = color; ctx.lineWidth = 3; ctx.strokeRect(x, y, w, h);
      corners(x, y, w, h, color);
      if (!rec) {
        ctx.fillStyle = "#ffffff";             // corner handles: drag to resize
        for (const [hx, hy] of [[x, y], [x + w, y], [x, y + h], [x + w, y + h]]) {
          ctx.fillRect(hx - 8, hy - 8, 16, 16);
        }
        const [cx, cy] = closeSpot(x, y, w, h); // ✕: drop this box
        ctx.fillStyle = "#ef4444";
        ctx.beginPath(); ctx.arc(cx, cy, 14, 0, Math.PI * 2); ctx.fill();
        ctx.strokeStyle = "#ffffff"; ctx.lineWidth = 2.5;
        ctx.beginPath(); ctx.moveTo(cx - 5, cy - 5); ctx.lineTo(cx + 5, cy + 5);
        ctx.moveTo(cx + 5, cy - 5); ctx.lineTo(cx - 5, cy + 5); ctx.stroke();
      }
    } else {                                   // only a suggestion: dashed
      ctx.strokeStyle = color; ctx.lineWidth = 2; ctx.setLineDash([8, 6]);
      ctx.strokeRect(x, y, w, h); ctx.setLineDash([]);
    }
    chip(`${target.manual ? "✎" : active ? "◎" : "○"} ${caption(target)}`, x, y, color, topLimit, cw);
  }
}

// Where the ✕ of the active box is drawn: just under its bottom edge.
function closeSpot(x, y, w, h) {
  return [x + w / 2, Math.min(y + h + 18, overlay.clientHeight - 150)];
}

// What TEACH / 🎤 / Video / Claude act on: the box the user made active.
// With nothing active and only one candidate on screen there is no doubt,
// so that one becomes active; otherwise the user is asked to choose.
function activeTarget() {
  const rows = source().rows;
  const chosen = rows.find((r) => r.id === state.selected);
  if (chosen) return chosen;
  const candidates = rows.filter((r) => !r.background && r.decision !== "pending");
  if (candidates.length === 1) {
    state.selected = candidates[0].id;
    updateHint();
    return candidates[0];
  }
  toast(t(rows.length ? "chooseFirst" : "nothingSelected"), 3500);
  return null;
}

// ✕ on the active box: not interested in it. On a photo the box goes away;
// live, that track is not drawn or offered again (until the camera restarts).
function dismiss(id) {
  if (state.still) {
    state.still.rows = state.still.rows.filter((r) => r.id !== id);
    if (state.multi) {
      state.multi = state.multi.filter((m) => m !== id);
      const row = $("multiList").querySelector(`.mrow[data-id="${id}"]`);
      if (row) row.remove();
      $("multiList").querySelectorAll(".mrow .num").forEach((n, i) => { n.textContent = i + 1; });
      updateMultiSave();
    }
    toast(t("removed"));
  } else {
    const row = state.rows.find((r) => r.id === id);
    state.dismissed.add(id);
    if (row && row.manual) api("/api/unfollow", { task: state.task, id }).catch(() => {});
    toast(t("dropped"));
  }
  if (state.selected === id) state.selected = null;
  if (navigator.vibrate) navigator.vibrate(20);
  renderCard(); updateHint();
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
  const r = source().rows.find((q) => q.id === state.selected) || null;
  // No evidence card on the live view: it covered the picture and the box's
  // own caption already says known / maybe / unknown (author's feedback,
  // 2026-10-16). The card only carries Claude's opinion, when asked for.
  const asked = r && state.opinion && state.opinion.rid === r.id;
  const offer = r && assistOk() && (r.decision === "uncertain" || r.decision === "unknown");
  if (!r || r.decision === "pending" || state.burst || !(asked || offer)) { card.hidden = true; return; }
  card.innerHTML = opinionHtml(r);
  card.classList.toggle("compact", !asked);
  card.hidden = false;
}

// -- Claude's second opinion (R38): advice next to the memory's answer ----------
function opinionHtml(r) {
  const op = state.opinion && state.opinion.rid === r.id ? state.opinion : null;
  if (op && op.pending) return `<div class="opinion">${t("asking")}</div>`;
  if (op) {
    const what = op.match ? `«${escapeHtml(op.match)}»` : t("noMatch");
    return `<div class="opinion"><b>${t("claudeSays")}:</b> ${what} · ${t(`conf_${op.confidence}`)}
      <br><small>${escapeHtml(op.reason)}</small>
      ${op.match ? `<br><button type="button" data-teach-as="1">${escapeHtml(t("teachAs", op.match))}</button>` : ""}</div>`;
  }
  if (assistOk() && (r.decision === "uncertain" || r.decision === "unknown") && !state.burst) {
    return `<button type="button" class="askclaude" data-ask="1">${t("askClaude")}</button>`;
  }
  return "";
}

async function askOpinion() {
  const r = activeTarget();
  if (!r) return;
  const preview = cropPreview(r.box);
  state.opinion = { rid: r.id, pending: true };
  renderCard();
  try {
    const { hold } = await api("/api/hold", { task: state.task, id: r.id, still: !!state.still });
    const res = await api("/api/assist/opinion", { task: state.task, hold, lang: state.lang });
    state.opinion = { rid: r.id, hold, preview, ...res };
  } catch (err) {
    state.opinion = null;
    toast(err.message, 5000);
  }
  renderCard();
}

$("card").addEventListener("click", (ev) => {
  if (ev.target.closest("[data-ask]")) askOpinion();
  const op = state.opinion;
  if (ev.target.closest("[data-teach-as]") && op && op.match) {
    state.opinion = null;
    openNameSheet(op.hold, op.preview ? [op.preview] : [], { label: op.match });
  }
});

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
  else if (rows.some((r) => r.id === state.selected)) hint.textContent = t("hintActive");
  else if (rows.length) hint.textContent = t("hintChoose");
  else hint.textContent = state.task === "people" ? t("hintPeopleNone") : t("hintNone");
}

// -- teaching -----------------------------------------------------------------
// TEACH freezes the selection on the server at once (a "hold"), so moving the
// phone while typing the name cannot lose the object.
async function teachSelected() {
  const r = activeTarget();
  if (!r) return;
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
  if (state.counting) return;
  if (state.still) backToLive();
  const chosen = activeTarget();
  if (!chosen) return;
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
  // faces are aligned, so people get no zoom variant (tasks.AUGMENT)
  document.querySelector(".augnote").textContent = t(state.task === "people" ? "augNotePeople" : "augNote");
  $("consent").checked = false;
  setEvalMode(state.evalMode);
  $("sheet").hidden = false;
  return loadChoices(r);
}

// 🧪 Test set (R34): views go to data/eval, never to memory. The choice is
// remembered (a collection session is long) and shown as a badge on top.
function setEvalMode(on) {
  state.evalMode = !!on;
  store.set("evalMode", on ? "1" : "0");
  $("evalMode").checked = state.evalMode;
  $("multiEval").checked = state.evalMode;
  $("evalBadge").hidden = !state.evalMode;
  document.querySelector(".augnote").hidden = state.evalMode;
  if (state.naming) markChoice();
  if (state.multi) updateMultiSave();
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
  $("saveBtn").textContent = state.evalMode ? t("saveTest")
    : typed && !exact ? `${t("save")} · ${t("newLabel")}` : t("save");
}

async function submitTeach(ev) {
  ev.preventDefault();
  const label = $("labelInput").value.trim();
  if (!label || !state.holdId) return;
  if (state.task === "people" && !$("consent").checked) { toast(t("consentNeeded")); return; }
  const save = $("saveBtn");
  save.disabled = true;
  save.textContent = t("saving");
  const views = $("teachThumbs").children.length || 1;
  try {
    const res = await api("/api/teach", { task: state.task, hold: state.holdId, label,
                                          consent: $("consent").checked, eval: state.evalMode });
    toast(state.evalMode ? t("savedTest", label, res.eval) : t("taught", label, views));
    closeTeach();
  } catch (err) {
    toast(err.message, 4000);
  } finally {
    save.disabled = false;
    markChoice();                    // the button's own label again
  }
}

// -- label all (R32) -----------------------------------------------------------
// Every box of the paused photo in one list: real objects first (left to
// right), background last. Pre-filled when memory already knows the object.
async function openMulti() {
  if (!state.still) return;
  const rows = [...state.still.rows].sort((a, b) =>
    (a.background - b.background) || (a.box[0] - b.box[0]));
  if (!rows.length) { toast(t("noBoxes")); return; }
  let labels = [];
  try {
    labels = (await (await fetch(`/api/memory?task=${state.task}`)).json()).labels || [];
  } catch { /* typed names still work */ }
  $("labelOptions").innerHTML = labels.map((g) => `<option value="${escapeHtml(g.label)}">`).join("");
  state.multiLabels = labels.map((g) => g.label);
  state.multi = rows.map((r) => r.id);
  const list = $("multiList");
  list.innerHTML = "";
  rows.forEach((r, i) => list.appendChild(multiRow(r, i)));
  $("multiConsentRow").hidden = state.task !== "people";
  $("multiConsent").checked = false;
  $("multiSuggest").hidden = !assistOk();
  $("multiSuggest").disabled = false;
  $("multiSuggest").textContent = t("suggestNames");
  $("multiEval").checked = state.evalMode;
  $("multi").hidden = false;
  updateMultiSave();
}

// One list row per box. Selecting a row highlights its box on the photo,
// where its corners can be dragged to fix it.
function multiRow(r, i, value) {
  const row = document.createElement("div");
  row.className = "mrow";
  row.dataset.id = r.id;
  const thumb = cropPreview(r.box);
  const known = value ?? (r.taught || r.decision === "known" ? r.label : "");
  const hint = r.decision === "uncertain" && r.guess ? `${t("maybe")} ${r.guess}?` : t("skipPh");
  row.innerHTML = `<span class="num">${i + 1}</span>
    ${thumb ? `<img src="${thumb}" alt="">` : "<img alt=''>"}
    <input list="labelOptions" autocomplete="off" maxlength="60"
           value="${escapeHtml(known || "")}" placeholder="${escapeHtml(hint)}">`;
  row.addEventListener("click", () => selectMultiRow(Number(row.dataset.id)));
  row.querySelector("input").addEventListener("focus", () => selectMultiRow(Number(row.dataset.id)));
  row.querySelector("input").addEventListener("input", updateMultiSave);
  return row;
}

function selectMultiRow(id, scroll) {
  state.selected = id;
  $("multiList").querySelectorAll(".mrow").forEach((m) => {
    const on = Number(m.dataset.id) === id;
    m.classList.toggle("on", on);
    if (on && scroll) m.scrollIntoView({ block: "nearest", behavior: "smooth" });
  });
}

// A box was fixed (replaces row `replaced`, keeping its number and text) or
// drawn new (becomes the next number).
function multiAdopt(row, replaced) {
  const list = $("multiList");
  const at = replaced != null ? state.multi.indexOf(replaced) : -1;
  if (at >= 0) {
    const old = list.querySelector(`.mrow[data-id="${replaced}"]`);
    const typed = old ? old.querySelector("input").value : "";
    state.multi[at] = row.id;
    const fresh = multiRow(row, at, typed);
    if (old) old.replaceWith(fresh); else list.appendChild(fresh);
  } else {
    state.multi.push(row.id);
    list.appendChild(multiRow(row, state.multi.length - 1));
  }
  selectMultiRow(row.id, true);
  updateMultiSave();
}

function multiItems() {
  return [...$("multiList").querySelectorAll(".mrow")].map((row) => {
    let label = row.querySelector("input").value.trim();
    // same word with other accents/case: use the label as stored
    const same = (state.multiLabels || []).find((l) => fold(l) === fold(label));
    if (label && same) label = same;
    return { id: Number(row.dataset.id), label };
  }).filter((it) => it.label);
}

// ✨ Claude suggests names for the rows still empty (R37). They are only
// pre-filled: the user reviews them and nothing is saved until Save.
async function suggestNames() {
  const rows = [...$("multiList").querySelectorAll(".mrow")]
    .filter((row) => !row.querySelector("input").value.trim());
  if (!rows.length) return;
  const btn = $("multiSuggest");
  btn.disabled = true; btn.textContent = t("suggesting");
  try {
    const res = await api("/api/assist/names", { task: state.task, lang: state.lang,
      ids: rows.map((row) => Number(row.dataset.id)) });
    let n = 0;
    for (const it of res.items) {
      const input = $("multiList").querySelector(`.mrow[data-id="${it.id}"] input`);
      if (!input || input.value.trim()) continue;
      if (it.skipped) { input.placeholder = `🔒 ${t("faceKept")}`; continue; }
      if (it.name) { input.value = it.name; input.classList.add("ai"); n++; }
    }
    toast(t("suggested", n), 4000);
  } catch (err) { toast(err.message, 5000); }
  btn.disabled = false; btn.textContent = t("suggestNames");
  updateMultiSave();
}

function updateMultiSave() {
  const n = multiItems().length;
  $("multiSave").textContent = state.evalMode ? `${t("saveTest")} · ${n}` : t("saveAll", n);
  $("multiSave").disabled = n === 0;
}

function closeMulti() {
  $("multi").hidden = true;
  state.multi = null;
}

async function saveMulti(ev) {
  ev.preventDefault();
  const items = multiItems();
  if (!items.length) return;
  if (state.task === "people" && !$("multiConsent").checked) { toast(t("consentNeeded")); return; }
  $("multiSave").disabled = true;
  $("multiSave").textContent = t("saving");
  let done = 0;
  for (const it of items) {
    try {
      const { hold } = await api("/api/hold", { task: state.task, id: it.id, still: true });
      await api("/api/teach", { task: state.task, hold, label: it.label,
                                consent: $("multiConsent").checked, eval: state.evalMode });
      const r = state.still && state.still.rows.find((q) => q.id === it.id);
      if (r) Object.assign(r, state.evalMode ? { tested: true, label: it.label.toLowerCase() }
                                             : { taught: true, label: it.label.toLowerCase() });
      done++;
    } catch (err) { toast(`${it.label}: ${err.message}`, 4000); }
  }
  closeMulti();
  toast(state.evalMode ? t("savedTestMany", done) : t("taughtMany", done));
  renderCard();
}

// -- voice teach (R21) --------------------------------------------------------
// Hold 🎤 and say "this is my hat" / «αυτό είναι το καπέλο μου». The phone
// records 16 kHz mono PCM (Web Audio), the PC transcribes it with Whisper in
// the app's language and returns the label; the name sheet opens pre-filled
// and nothing is saved until Save. Audio is never stored.
const VOICE_RATE = 16000, VOICE_MAX_S = 12;
const mic = { on: false, ctx: null, stream: null, src: null, node: null, chunks: [], samples: 0 };

async function micStart() {
  if (mic.on) return false;
  mic.on = true; mic.chunks = []; mic.samples = 0;
  try {
    mic.ctx = mic.ctx || new (window.AudioContext || window.webkitAudioContext)();
    await mic.ctx.resume();
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true } });
    if (!mic.on) { stream.getTracks().forEach((tr) => tr.stop()); return false; }  // let go during the prompt
    mic.stream = stream;
  } catch (err) {
    mic.on = false;
    toast(t("micError", err.message || err.name), 5000);
    return false;
  }
  mic.src = mic.ctx.createMediaStreamSource(mic.stream);
  mic.node = mic.ctx.createScriptProcessor(4096, 1, 1);
  mic.node.onaudioprocess = (e) => {
    if (!mic.on || mic.samples > VOICE_MAX_S * mic.ctx.sampleRate) return;
    const chunk = new Float32Array(e.inputBuffer.getChannelData(0));
    mic.chunks.push(chunk); mic.samples += chunk.length;
  };
  mic.src.connect(mic.node); mic.node.connect(mic.ctx.destination);
  toast(t("listening"), VOICE_MAX_S * 1000);
  return true;
}

// Stop recording; a 16-bit PCM WAV at 16 kHz, or null if nothing was heard.
function micStop() {
  const was = mic.on;
  mic.on = false;
  try { mic.src && mic.src.disconnect(); mic.node && mic.node.disconnect(); } catch { /* already */ }
  if (mic.stream) mic.stream.getTracks().forEach((tr) => tr.stop());
  mic.stream = mic.src = mic.node = null;
  if (!was || !mic.samples) return null;
  const all = new Float32Array(mic.samples);
  let at = 0;
  for (const c of mic.chunks) { all.set(c, at); at += c.length; }
  return encodeWav(resample(all, mic.ctx.sampleRate, VOICE_RATE), VOICE_RATE);
}

function resample(x, from, to) {
  if (from === to) return x;
  const n = Math.floor(x.length * to / from), out = new Float32Array(n), step = from / to;
  for (let i = 0; i < n; i++) {               // average the samples each output covers
    const a = Math.floor(i * step), b = Math.min(x.length, Math.floor((i + 1) * step));
    let sum = 0;
    for (let j = a; j < b; j++) sum += x[j];
    out[i] = b > a ? sum / (b - a) : x[a] || 0;
  }
  return out;
}

function encodeWav(x, rate) {
  const buf = new ArrayBuffer(44 + x.length * 2), v = new DataView(buf);
  const str = (o, s) => { for (let i = 0; i < s.length; i++) v.setUint8(o + i, s.charCodeAt(i)); };
  str(0, "RIFF"); v.setUint32(4, 36 + x.length * 2, true); str(8, "WAVE");
  str(12, "fmt "); v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true);
  v.setUint32(24, rate, true); v.setUint32(28, rate * 2, true); v.setUint16(32, 2, true);
  v.setUint16(34, 16, true); str(36, "data"); v.setUint32(40, x.length * 2, true);
  for (let i = 0; i < x.length; i++) {
    const s = Math.max(-1, Math.min(1, x[i]));
    v.setInt16(44 + i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }
  return new Blob([buf], { type: "audio/wav" });
}

// Press-and-hold on `btn`: start() when pressed (returns false to cancel),
// done(wav) when released.
function holdToTalk(btn, start, done) {
  let active = false;
  btn.addEventListener("pointerdown", async (ev) => {
    ev.preventDefault();
    if (active || state.burst || state.counting) return;
    active = true;
    btn.classList.add("rec");
    try { btn.setPointerCapture(ev.pointerId); } catch { /* fine */ }
    if (!(await start())) { active = false; btn.classList.remove("rec"); micStop(); }
  });
  const end = async () => {
    if (!active) return;
    active = false;
    btn.classList.remove("rec");
    await done(micStop());
  };
  btn.addEventListener("pointerup", end);
  btn.addEventListener("pointercancel", end);
  btn.addEventListener("contextmenu", (ev) => ev.preventDefault());
}

async function transcribe(wav) {
  if (!wav) { toast(t("micShort"), 3500); return null; }
  toast(t("recognising"), 8000);
  try {
    const res = await fetch(`/api/voice?lang=${state.lang}`, {
      method: "POST", body: wav, headers: { "Content-Type": "audio/wav" } });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) { toast(data.error || res.statusText, 5000); return null; }
    toast(t("heard", data.text), 4000);
    return data;
  } catch (err) { toast(err.message, 5000); return null; }
}

// 🎤 on the live view: freeze the chosen box at once (as TEACH does), record
// while held, then open the name sheet with what was heard.
const say = { hold: null, target: null, preview: null };
async function sayStart() {
  const r = activeTarget();
  if (!r) return false;
  say.target = r;
  say.preview = cropPreview(r.box);
  say.hold = api("/api/hold", { task: state.task, id: r.id, still: !!state.still })
    .then((res) => res.hold).catch((err) => { toast(err.message, 4000); return null; });
  return micStart();
}

async function sayDone(wav) {
  const res = await transcribe(wav);
  const hold = await say.hold;
  if (!res || !hold) return;
  await openNameSheet(hold, say.preview ? [say.preview] : [], say.target);
  $("labelInput").value = res.label || res.text;
  markChoice();
}

// -- photo mode ---------------------------------------------------------------
async function takePhoto() {
  if (state.counting) return;
  await countdown(3);
  await capturePhoto();
}

async function capturePhoto() {
  const blob = await snapshot(STILL_SIDE, 0.9);
  if (!blob) return false;
  const res = await fetch(`/api/still?task=${state.task}`, { method: "POST", body: blob,
    headers: { "Content-Type": "image/jpeg" } });
  const data = await res.json();
  if (!res.ok) { toast(data.error || res.statusText, 4000); return false; }
  frozen.width = grab.width; frozen.height = grab.height;
  frozen.getContext("2d").drawImage(grab, 0, 0);
  frozen.hidden = false;
  state.still = { rows: data.rows, w: data.w, h: data.h };
  state.selected = null;
  resetView();
  $("photoBtn").hidden = true; $("liveBtn").hidden = false;
  $("videoBtn").hidden = true; $("labelAllBtn").hidden = false;
  renderCard(); updateHint();
  return true;
}

// Dragging a live box pauses first (a moving box cannot be fixed): the photo
// is taken at once and the same object is made active on it.
async function freezeForEdit(target) {
  if (state.counting || state.still) return;
  state.counting = true;                     // no other gesture meanwhile
  try {
    if (!(await capturePhoto())) return;
  } finally { state.counting = false; }
  let best = null, bestIou = 0.1;
  for (const r of state.still.rows) {
    const v = boxIou(r.box, target.box);
    if (v > bestIou) { best = r; bestIou = v; }
  }
  if (!best) {                               // not found again: keep the user's box
    await markRegion(target.box);
  } else {
    state.selected = best.id;
  }
  toast(t("pausedEdit"), 3500);
  renderCard(); updateHint();
}

function boxIou(a, b) {
  const w = Math.max(0, Math.min(a[2], b[2]) - Math.max(a[0], b[0]));
  const h = Math.max(0, Math.min(a[3], b[3]) - Math.max(a[1], b[1]));
  const inter = w * h;
  const union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter;
  return union > 0 ? inter / union : 0;
}

// -- pinch zoom ----------------------------------------------------------------
// On a paused photo the picture itself is zoomed (boxes follow, so a small
// part can be boxed precisely); live, the camera's own zoom is used when the
// phone offers it.
function resetView() {
  state.view = { s: 1, x: 0, y: 0 };
  applyView();
}

function applyView() {
  const v = state.view, cw = overlay.clientWidth;
  const mirror = state.facing === "user" ? ` translateX(${cw}px) scaleX(-1)` : "";
  frozen.style.transform = `translate(${v.x}px, ${v.y}px) scale(${v.s})${mirror}`;
  $("zoomReset").hidden = !(state.still ? v.s > 1.01 : state.camZoom && state.camZoom.value > state.camZoom.min);
}

function pinchStart(pts) {
  const [a, b] = pts;
  const p = { d0: Math.hypot(a[0] - b[0], a[1] - b[1]) || 1, m0: [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2],
              v0: { ...state.view } };
  if (!state.still) {
    const track = state.stream && state.stream.getVideoTracks()[0];
    const caps = track && track.getCapabilities ? track.getCapabilities() : {};
    if (caps.zoom) {
      const now = (track.getSettings().zoom) || caps.zoom.min;
      state.camZoom = { track, min: caps.zoom.min, max: caps.zoom.max, value: now };
      p.z0 = now;
    } else {
      p.noZoom = true;
      toast(t("zoomNo"), 4000);
    }
  }
  state.pinch = p;
}

function pinchMove(pts) {
  const p = state.pinch, [a, b] = pts;
  const k = Math.hypot(a[0] - b[0], a[1] - b[1]) / p.d0;
  const m = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];
  if (state.still) {
    const s = Math.min(6, Math.max(1, p.v0.s * k));
    // the picture point under the fingers stays under the fingers
    const cx = (p.m0[0] - p.v0.x) / p.v0.s, cy = (p.m0[1] - p.v0.y) / p.v0.s;
    const cw = overlay.clientWidth, ch = overlay.clientHeight;
    state.view = { s,
      x: Math.min(0, Math.max(cw - cw * s, m[0] - cx * s)),
      y: Math.min(0, Math.max(ch - ch * s, m[1] - cy * s)) };
    applyView();
  } else if (!p.noZoom && state.camZoom) {
    const z = Math.min(state.camZoom.max, Math.max(state.camZoom.min, p.z0 * k));
    const now = performance.now();
    if (Math.abs(z - state.camZoom.value) > 0.05 && !(p.busyUntil > now)) {
      p.busyUntil = now + 80;
      state.camZoom.value = z;
      state.camZoom.track.applyConstraints({ advanced: [{ zoom: z }] }).catch(() => {});
      applyView();
    }
  }
}

$("zoomReset").onclick = () => {
  if (state.still) { resetView(); return; }
  if (state.camZoom) {
    state.camZoom.value = state.camZoom.min;
    state.camZoom.track.applyConstraints({ advanced: [{ zoom: state.camZoom.min }] }).catch(() => {});
    applyView();
  }
};

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
  resetView();
  $("photoBtn").hidden = false; $("liveBtn").hidden = true;
  $("videoBtn").hidden = false; $("labelAllBtn").hidden = true;
  closeMulti();
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
  $("askForm").hidden = !assistOk();
  $("askInput").placeholder = t("askPh");
  await showMemTab(state.memTab);
}

async function showMemTab(tab) {
  state.memTab = tab;
  document.querySelectorAll("#memTabs button").forEach((b) => b.classList.toggle("on", b.dataset.tab === tab));
  $("memPane").hidden = tab !== "memory";
  $("testPane").hidden = tab !== "test";
  $("wipeBtn").hidden = tab !== "memory" || state.task !== "people";
  if (tab === "test") await renderTest(); else await renderMemory();
}

// ✨ Questions about memory (R40): answered from labels, counts and dates only.
async function askMemory(ev) {
  ev.preventDefault();
  const q = $("askInput").value.trim();
  if (!q) return;
  const out = $("askOut");
  out.hidden = false; out.textContent = t("asking");
  try {
    const res = await api("/api/assist/ask", { question: q, lang: state.lang });
    out.textContent = res.text;
  } catch (err) { out.textContent = err.message; }
}

// -- test set and evaluation (R34, R35) --------------------------------------------
async function renderTest() {
  const list = $("testList");
  const [ev, mem] = await Promise.all([
    fetch(`/api/eval?task=${state.task}`).then((r) => r.json()),
    fetch(`/api/memory?task=${state.task}`).then((r) => r.json())]);
  const taught = new Set((mem.labels || []).map((g) => g.label));
  if (state.lastEval && state.lastEval.task === state.task) renderEval(state.lastEval);
  else $("evalResult").innerHTML = "";
  $("runEval").disabled = !(ev.items || []).length;
  if (!(ev.items || []).length) { list.innerHTML = `<p class="empty">${t("testEmpty")}</p>`; return; }
  const groups = {};
  for (const it of ev.items) (groups[it.label] = groups[it.label] || []).push(it);
  list.innerHTML = "";
  for (const [label, items] of Object.entries(groups)) {
    const item = document.createElement("div");
    item.className = "mem-item";
    const known = taught.has(label);
    item.innerHTML = `<div class="mem-row"><div class="name"><b>${escapeHtml(label)}</b>
        <small>${t("evalViews", items.length)} · <span class="${known ? "tag-taught" : "tag-stranger"}">
        ${known ? t("taughtTag") : t("stranger")}</span></small></div></div>
      <div class="views testviews">${items.map((it) => `<div class="view">
        <img src="/api/eval/${state.task}/${it.id}.jpg" alt="" loading="lazy">
        <button data-del="${it.id}" aria-label="delete test view">✕</button></div>`).join("")}</div>`;
    item.querySelectorAll("[data-del]").forEach((b) => {
      b.onclick = async () => {
        await api("/api/eval/forget", { task: state.task, id: b.dataset.del });
        renderTest();
      };
    });
    list.appendChild(item);
  }
}

async function runEval() {
  const btn = $("runEval");
  btn.disabled = true; btn.textContent = t("running");
  try {
    state.lastEval = await api("/api/eval/run", { task: state.task });
    renderEval(state.lastEval);
  } catch (err) { toast(err.message, 5000); }
  btn.disabled = false; btn.textContent = t("runEval");
}

function renderEval(r) {
  const pct = (x) => (x == null ? "—" : `${Math.round(100 * x)}%`);
  const line = (name, c) => `<tr><td>${name}<br><small>${c.threshold.toFixed(2)} / ${c.margin.toFixed(2)}</small></td>
    <td>${c.correct}/${c.enrolled} <small>${pct(c.correct_rate)}</small></td>
    <td class="${c.dangerous ? "bad" : "ok"}">${c.dangerous}</td>
    <td>${c.uncertain}</td>
    <td>${c.rejected}/${c.strangers} <small>${pct(c.reject_rate)}</small></td></tr>`;
  const notes = (r.notes || []).map((n) => `<li>${escapeHtml(n)}</li>`).join("");
  $("evalResult").innerHTML = `<div class="evalres">
    <table><tr><th></th><th>${t("colCorrect")}</th><th>${t("colDanger")}</th><th>${t("colUnsure")}</th>
      <th>${t("colStrangers")}</th></tr>
      ${line(t("bandsCur"), r.current)}${line(t("bandsRec"), r.recommended)}</table>
    <ul><li>${t("dangerNote")}</li>${notes}</ul>
    <a href="/api/reports/${r.report}.md" target="_blank" rel="noopener">${t("fullReport")}</a>
    ${assistOk() ? `<button type="button" class="askclaude" id="sumBtn">${t("summary")}</button>` : ""}
    <div id="sumOut" class="answer" hidden></div></div>`;
  const sum = $("sumBtn");
  if (sum) sum.onclick = async () => {
    const out = $("sumOut");
    out.hidden = false; out.textContent = t("asking"); sum.disabled = true;
    try {
      out.textContent = (await api("/api/assist/summary", { report: r.report, lang: state.lang })).text;
    } catch (err) { out.textContent = err.message; }
    sum.disabled = false;
  };
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
// Fingers on the overlay: one = tap / drag, two = pinch zoom.
const fingers = new Map();
overlay.addEventListener("pointerdown", (ev) => {
  if (state.burst || state.counting) return;
  const [x, y] = point(ev);
  fingers.set(ev.pointerId, [x, y]);
  try { overlay.setPointerCapture(ev.pointerId); } catch { /* not all pointers can be captured */ }
  if (fingers.size === 2) { state.drag = null; pinchStart([...fingers.values()]); return; }
  if (fingers.size > 2 || state.pinch) return;
  state.drag = { x0: x, y0: y, x1: x, y1: y, moved: false };
  const target = source().rows.find((r) => r.id === state.selected);
  if (!target) return;
  const src = source();
  const [bx, by, bw, bh] = mapper(src.w, src.h)(target.box);
  const [cx, cy] = closeSpot(bx, by, bw, bh);
  if (Math.hypot(cx - x, cy - y) < 22) {       // ✕ of the active box
    state.drag.close = target.id;
    return;
  }
  // faces are aligned from their landmarks: people boxes are chosen or
  // dropped, never moved or resized by hand
  if (state.task === "people") return;
  const cs = [[bx, by], [bx + bw, by], [bx, by + bh], [bx + bw, by + bh]];
  const i = cs.findIndex(([qx, qy]) => Math.hypot(qx - x, qy - y) < 30);
  const inside = x >= bx && x <= bx + bw && y >= by && y <= by + bh;
  if (!state.still && (i >= 0 || inside)) {   // live: a drag pauses first
    state.drag.liveEdit = target;
  } else if (i >= 0) {                        // resize: the opposite corner stays
    const opp = cs[3 - i];
    state.drag = { x0: opp[0], y0: opp[1], x1: x, y1: y, moved: true, edit: target.id };
  } else if (inside) {                        // move the whole box
    state.drag = { move: [bx, by, bw, bh], sx: x, sy: y, x0: bx, y0: by,
                   x1: bx + bw, y1: by + bh, moved: false, edit: target.id };
  }
});
overlay.addEventListener("pointermove", (ev) => {
  if (!fingers.has(ev.pointerId)) return;
  const [x, y] = point(ev);
  fingers.set(ev.pointerId, [x, y]);
  if (state.pinch) { if (fingers.size >= 2) pinchMove([...fingers.values()]); return; }
  const d = state.drag;
  if (!d) return;
  if (d.liveEdit) {
    if (Math.hypot(x - d.x0, y - d.y0) > 14) { state.drag = null; freezeForEdit(d.liveEdit); }
    return;
  }
  if (d.move) {
    const dx = x - d.sx, dy = y - d.sy;
    const [bx, by, bw, bh] = d.move;
    d.x0 = bx + dx; d.y0 = by + dy; d.x1 = bx + bw + dx; d.y1 = by + bh + dy;
    if (Math.hypot(dx, dy) > 8) d.moved = true;
    return;
  }
  d.x1 = x; d.y1 = y;
  if (state.still && Math.hypot(x - d.x0, y - d.y0) > 14) d.moved = true;
});
overlay.addEventListener("pointercancel", (ev) => {
  fingers.delete(ev.pointerId);
  if (fingers.size < 2) state.pinch = null;
  state.drag = null;
});
overlay.addEventListener("pointerup", (ev) => {
  fingers.delete(ev.pointerId);
  if (state.pinch) {                         // end of a pinch is never a tap
    if (fingers.size < 2) state.pinch = null;
    state.drag = null;
    return;
  }
  const d = state.drag;
  state.drag = null;
  if (!d) return;
  if (d.close != null) {
    const [x, y] = point(ev);
    if (Math.hypot(x - d.x0, y - d.y0) < 24) dismiss(d.close);
    return;
  }
  if (d.moved) {                                   // a drawn or fixed box
    if (d.edit != null && state.still) {             // the fixed box replaces it
      state.still.rows = state.still.rows.filter((r) => r.id !== d.edit);
    }
    const a = toFrame(d.x0, d.y0), b = toFrame(d.x1, d.y1);
    markRegion([Math.min(a[0], b[0]), Math.min(a[1], b[1]),
                Math.max(a[0], b[0]), Math.max(a[1], b[1])], d.edit);
    return;
  }
  const r = hitTest(d.x0, d.y0);
  if (r) {
    state.selected = r.id;
    if (state.multi) selectMultiRow(r.id, true);
    if (navigator.vibrate) navigator.vibrate(15);
    updateHint();
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

async function markRegion(box, replaced) {
  if (box[2] - box[0] < 0.005 || box[3] - box[1] < 0.005) return;
  try {
    const res = await api("/api/region", { task: state.task, box });
    state.still.rows.push(res.row);
    state.selected = res.row.id;
    if (state.multi) multiAdopt(res.row, replaced);
    if (navigator.vibrate) navigator.vibrate(15);
    renderCard(); updateHint();
  } catch (err) { toast(err.message, 4000); }
}
document.querySelectorAll("[data-start]").forEach((b) => { b.onclick = () => start(b.dataset.start); });
$("landLang").onclick = toggleLang;
$("homeBtn").onclick = goHome;
$("flipBtn").onclick = flipCamera;
$("labelAllBtn").onclick = openMulti;
$("multiCancel").onclick = closeMulti;
$("multiAdd").onclick = () => toast(t("drawNow"), 3500);
$("multiSuggest").onclick = suggestNames;
holdToTalk($("micBtn"), sayStart, sayDone);
holdToTalk($("sheetMic"), () => micStart(), async (wav) => {
  const res = await transcribe(wav);
  if (res) { $("labelInput").value = res.label || res.text; markChoice(); }
});
$("evalMode").onchange = (ev) => setEvalMode(ev.target.checked);
$("multiEval").onchange = (ev) => setEvalMode(ev.target.checked);
$("assistToggle").onchange = (ev) => { state.assistOn = ev.target.checked; store.set("assist", state.assistOn ? "1" : "0"); };
document.querySelectorAll("#memTabs button").forEach((b) => { b.onclick = () => showMemTab(b.dataset.tab); });
$("askForm").onsubmit = askMemory;
$("runEval").onclick = runEval;
$("multiForm").onsubmit = saveMulti;
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
  $("evalBadge").hidden = !state.evalMode;
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {});
  checkServer();
  requestAnimationFrame(pump);
})();
