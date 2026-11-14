(() => {
  async function load() {
    const box = $("#list");
    try {
      const list = await api("/api/prof/assignments");
      if (!list.length) {
        box.outerHTML = `<div id="list" class="card empty"><div class="icon">📚</div><h3>No assignments yet</h3><p>Create your first assignment, then share the student page with your class.</p><button class="btn primary" onclick="openModal()">＋ New assignment</button></div>`;
        return;
      }
      box.className = "grid-cards";
      box.innerHTML = list.map(a => {
        const sub = a.submitted || 0, done = a.completed || 0, pct = sub ? Math.round(done / sub * 100) : 0;
        return `<a class="card a-card" href="/prof/assignments/${encodeURIComponent(a.id)}">
          ${a.course ? `<div class="course">${escapeHtml(a.course)}</div>` : ""}
          <h3>${escapeHtml(a.title)}</h3>
          <div class="desc">${escapeHtml(a.description || "No description")}</div>
          <div class="stats"><span>${sub} submitted · ${done} assessed</span><span class="faint">${fmtDate(a.created_at).split(",")[0]}</span></div>
          <div class="bar"><i style="width:${pct}%"></i></div>
        </a>`;
      }).join("");
    } catch (e) {
      box.outerHTML = `<div id="list" class="notice error">Couldn't load assignments: ${escapeHtml(e.message)}</div>`;
    }
  }

  const modal = $("#modal");
  window.openModal = () => { modal.classList.remove("hidden"); $("#new-error").classList.add("hidden"); setTimeout(() => $("#title").focus(), 30); };
  const closeModal = () => modal.classList.add("hidden");
  $("#new-btn").onclick = openModal;
  $("#close-modal").onclick = closeModal;
  $("#cancel-modal").onclick = closeModal;
  modal.addEventListener("click", e => { if (e.target === modal) closeModal(); });
  document.addEventListener("keydown", e => { if (e.key === "Escape") closeModal(); });

  $("#new-form").addEventListener("submit", async e => {
    e.preventDefault();
    const err = $("#new-error"); err.classList.add("hidden");
    const title = $("#title").value.trim();
    if (!title) { err.textContent = "A title is required."; err.classList.remove("hidden"); return; }
    const fd = new FormData();
    fd.append("title", title);
    fd.append("course", $("#course").value.trim());
    fd.append("description", $("#description").value.trim());
    fd.append("objectives", $("#objectives").value.trim());
    for (const f of $("#materials").files) fd.append("materials", f);
    const btn = $("#create-btn");
    setBusy(btn, true, "Creating…");
    try {
      await api("/api/prof/assignments", { method: "POST", form: fd });
      $("#new-form").reset();
      closeModal();
      toast("Assignment created");
      load();
    } catch (ex) {
      err.textContent = ex.message; err.classList.remove("hidden");
    } finally { setBusy(btn, false); }
  });

  load();
})();
