// Pythagoras: shared helpers for every page.
const BLOOM = { 1: "Remember", 2: "Understand", 3: "Apply", 4: "Analyze", 5: "Evaluate", 6: "Create" };

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function mmss(sec) {
  const s = Math.max(0, Math.floor(Number(sec) || 0));
  return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
}

function fmtDate(v) {
  if (v == null || v === "") return "—";
  const d = typeof v === "number" ? new Date(v < 1e12 ? v * 1000 : v) : new Date(v);
  if (isNaN(d)) return String(v);
  return d.toLocaleString(undefined, { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

function fmtSize(n) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(0)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}

class ApiError extends Error {
  constructor(status, detail) { super(detail); this.status = status; }
}

// fetch wrapper: JSON in/out, throws ApiError with the server's detail. On prof pages a 401 sends to login.
async function api(path, { method = "GET", body, form } = {}) {
  const opts = { method, headers: {}, credentials: "same-origin" };
  if (form) opts.body = form;
  else if (body !== undefined) { opts.headers["Content-Type"] = "application/json"; opts.body = JSON.stringify(body); }
  let res;
  try { res = await fetch(path, opts); }
  catch (e) { throw new ApiError(0, "Can't reach the server. Check your connection and try again."); }
  if (res.status === 401 && path.startsWith("/api/prof/") && !path.endsWith("/login")) {
    location.href = "/prof/login?next=" + encodeURIComponent(location.pathname);
    throw new ApiError(401, "Please sign in");
  }
  const type = res.headers.get("content-type") || "";
  const data = type.includes("json") ? await res.json().catch(() => null) : await res.text();
  if (!res.ok) {
    let detail = data && data.detail ? data.detail : (typeof data === "string" && data ? data : res.statusText);
    if (Array.isArray(detail)) detail = detail.map(d => d.msg || JSON.stringify(d)).join("; ");
    throw new ApiError(res.status, String(detail || `Error ${res.status}`));
  }
  return data;
}

function toast(msg, kind = "") {
  let box = document.getElementById("toasts");
  if (!box) { box = document.createElement("div"); box.id = "toasts"; document.body.appendChild(box); }
  const t = document.createElement("div");
  t.className = "toast " + kind;
  t.textContent = msg;
  box.appendChild(t);
  setTimeout(() => { t.style.transition = "opacity .3s"; t.style.opacity = "0"; setTimeout(() => t.remove(), 300); }, 3200);
}

async function copyText(text, label = "Copied") {
  try { await navigator.clipboard.writeText(text); toast(label); }
  catch {
    const ta = document.createElement("textarea"); ta.value = text; document.body.appendChild(ta); ta.select();
    try { document.execCommand("copy"); toast(label); } catch { toast("Copy failed", "error"); }
    ta.remove();
  }
}

function setBusy(btn, busy, label) {
  if (!btn) return;
  if (busy) { btn.dataset.label = btn.innerHTML; btn.disabled = true; btn.innerHTML = `<span class="spinner"></span> ${escapeHtml(label || "Working…")}`; }
  else { btn.disabled = false; if (btn.dataset.label) btn.innerHTML = btn.dataset.label; }
}

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
const pathPart = i => decodeURIComponent(location.pathname.split("/").filter(Boolean)[i] || "");

const STATUS = {
  preparing: ["Preparing", "amber"], ready: ["Invited", "blue"], in_progress: ["In progress", "accent"],
  completed: ["Completed", "green"], error: ["Error", "red"],
};
function statusPill(s) {
  const [label, cls] = STATUS[s] || [s || "—", ""];
  return `<span class="pill ${cls}">${escapeHtml(label)}</span>`;
}

// prof pages: a #logout button in the top bar
function bindLogout() {
  const b = document.getElementById("logout");
  if (b) api("/api/prof/auth").then(a => { if (!a.password) b.remove(); }).catch(() => { });
  if (b) b.onclick = async () => { try { await api("/api/prof/logout", { method: "POST" }); } catch { } location.href = "/prof/login"; };
}
document.addEventListener("DOMContentLoaded", bindLogout);
