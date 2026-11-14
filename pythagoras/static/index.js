(() => {
  let files = [];
  const form = $("#submit-form"), drop = $("#dropzone"), input = $("#files"), errBox = $("#form-error");

  async function loadAssignments() {
    const wrap = $("#assignment-wrap");
    try {
      const list = await api("/api/assignments");
      if (!list.length) {
        wrap.innerHTML = `<div class="notice">No open assignments yet. Check back once your professor has published one.</div>`;
        $("#submit-btn").disabled = true;
        return;
      }
      wrap.innerHTML = `<select id="assignment" required>
        <option value="" disabled ${list.length > 1 ? "selected" : ""}>Choose an assignment…</option>
        ${list.map(a => `<option value="${escapeHtml(a.id)}" ${list.length === 1 ? "selected" : ""}>${escapeHtml(a.title)}${a.course ? " — " + escapeHtml(a.course) : ""}</option>`).join("")}
      </select>`;
      const pre = new URLSearchParams(location.search).get("assignment");
      if (pre && list.some(a => String(a.id) === pre)) $("#assignment").value = pre;
    } catch (e) {
      wrap.innerHTML = `<div class="notice error">Couldn't load assignments: ${escapeHtml(e.message)} <button class="btn sm" type="button" id="retry-a">Retry</button></div>`;
      $("#retry-a").onclick = loadAssignments;
    }
  }

  function renderChips() {
    $("#chips").innerHTML = files.map((f, i) =>
      `<span class="chip"><span class="name" title="${escapeHtml(f.name)}">${escapeHtml(f.name)}</span><span class="size">${fmtSize(f.size)}</span><button type="button" data-i="${i}" aria-label="Remove">×</button></span>`).join("");
  }
  function addFiles(list) {
    for (const f of list) if (!files.some(g => g.name === f.name && g.size === f.size)) files.push(f);
    renderChips();
  }
  $("#chips").addEventListener("click", e => {
    const b = e.target.closest("button[data-i]");
    if (b) { files.splice(+b.dataset.i, 1); renderChips(); }
  });
  drop.addEventListener("click", () => input.click());
  drop.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); input.click(); } });
  input.addEventListener("change", () => { addFiles(input.files); input.value = ""; });
  ["dragenter", "dragover"].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.add("over"); }));
  ["dragleave", "drop"].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.remove("over"); }));
  drop.addEventListener("drop", e => addFiles(e.dataTransfer.files));

  function showError(msg) { errBox.textContent = msg; errBox.classList.remove("hidden"); }

  form.addEventListener("submit", async e => {
    e.preventDefault();
    errBox.classList.add("hidden");
    const sel = $("#assignment"), name = $("#name").value.trim(), email = $("#email").value.trim();
    if (!sel || !sel.value) return showError("Please choose an assignment.");
    if (!name) return showError("Please enter your team name.");
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return showError("Please enter a valid contact email for the team.");
    if (!files.length) return showError("Please add at least one file of your deliverable.");

    const fd = new FormData();
    fd.append("assignment_id", sel.value);
    fd.append("name", name);
    fd.append("email", email);
    files.forEach(f => fd.append("files", f));
    const btn = $("#submit-btn");
    setBusy(btn, true, "Uploading…");
    try {
      const res = await api("/api/submissions", { method: "POST", form: fd });
      $("#form-card").classList.add("hidden");
      $("#success-card").classList.remove("hidden");
      $("#success-msg").innerHTML = res.email_configured
        ? `Pythagoras is reading your project now. As soon as your interview is ready (usually a couple of minutes) we'll email the link to <strong>${escapeHtml(res.email || email)}</strong>. Open it when you're somewhere quiet — the interview starts from there.`
        : `Your project was uploaded. Pythagoras is reading it now — your interview will be ready in a couple of minutes.`;
      if (res.invite_url) {
        $("#direct-link").classList.remove("hidden");
        $("#invite-url").value = res.invite_url;
        $("#open-invite").href = res.invite_url;
      }
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      showError(err.message);
    } finally {
      setBusy(btn, false);
    }
  });

  $("#copy-invite").onclick = () => copyText($("#invite-url").value, "Link copied");
  $("#again").onclick = () => {
    files = []; renderChips(); form.reset();
    $("#direct-link").classList.add("hidden");
    $("#success-card").classList.add("hidden"); $("#form-card").classList.remove("hidden");
    loadAssignments();
  };

  // one-click demo: a ready-made case, straight to the interview
  api("/api/demo").then(d => {
    $("#demo-headline").textContent = d.headline;
    $("#demo-blurb").textContent = d.blurb;
    $("#demo-docs").textContent = `${d.documents} documents`;
    $("#demo-cta").textContent = `Use the ${d.label} case`;
  }).catch(() => $("#demo-card").classList.add("hidden"));
  $("#sample-button").onclick = async () => {
    const btn = $("#sample-button");
    btn.disabled = true; $("#demo-cta").textContent = "Preparing the conversation…"; $("#demo-error").classList.add("hidden");
    try { location.href = (await api("/api/demo", { method: "POST" })).invite_url; }
    catch (e) { btn.disabled = false; $("#demo-cta").textContent = "Try again"; $("#demo-error").textContent = e.message; $("#demo-error").classList.remove("hidden"); }
  };

  loadAssignments();
})();
