(() => {
  const id = pathPart(2);
  let subs = [];

  function row(s) {
    const files = (s.files || []).map(f => `<div title="${escapeHtml(f)}">📄 ${escapeHtml(f)}</div>`).join("") || `<span class="faint">—</span>`;
    const check = s.completed ? `<span class="check yes" title="Assessment completed">✓</span>` : `<span class="check no" title="Not completed yet"></span>`;
    const actions = s.completed
      ? `<a class="btn primary sm" href="/prof/submissions/${encodeURIComponent(s.id)}">View report</a>`
      : `${s.invite_url ? `<button class="btn sm" data-copy="${escapeHtml(s.invite_url)}">Copy invite link</button>` : ""}<button class="btn sm" disabled>View report</button>`;
    return `<tr>
      <td class="student-cell"><strong>${escapeHtml(s.student_name)}</strong><span>${escapeHtml(s.email)}</span></td>
      <td class="small">${fmtDate(s.created_at)}</td>
      <td class="files-cell">${files}</td>
      <td>${statusPill(s.status)}</td>
      <td>${check}</td>
      <td><div class="actions-cell">${actions}</div></td>
    </tr>`;
  }

  function render() {
    const q = $("#search").value.trim().toLowerCase();
    const list = subs.filter(s => !q || (s.student_name || "").toLowerCase().includes(q) || (s.email || "").toLowerCase().includes(q));
    const box = $("#table-box");
    if (!subs.length) {
      box.innerHTML = `<div class="card empty"><div class="icon">📭</div><h3>No deliverables yet</h3><p>Share the student page so students can upload their work.</p><button class="btn" onclick="document.getElementById('share-btn').click()">🔗 Copy student link</button></div>`;
      return;
    }
    if (!list.length) { box.innerHTML = `<div class="card empty">No team matches “${escapeHtml(q)}”.</div>`; return; }
    box.innerHTML = `<div class="table-wrap"><table class="data">
      <thead><tr><th>Team</th><th>Submitted</th><th>Deliverable</th><th>Status</th><th>Assessed</th><th></th></tr></thead>
      <tbody>${list.map(row).join("")}</tbody></table></div>`;
  }

  async function load() {
    try {
      const data = await api(`/api/prof/assignments/${encodeURIComponent(id)}`);
      const a = data.assignment;
      document.title = `Pythagoras · ${a.title}`;
      $("#crumb-title").textContent = a.title;
      $("#a-title").textContent = a.title;
      $("#a-course").textContent = a.course || "";
      $("#a-desc").textContent = a.description || "";
      subs = (data.submissions || []).slice().sort((x, y) => String(y.created_at).localeCompare(String(x.created_at)));
      const done = subs.filter(s => s.completed).length;
      $("#st-sub").textContent = subs.length;
      $("#st-done").textContent = done;
      $("#st-pend").textContent = subs.length - done;
      render();
    } catch (e) {
      if (e.status === 401) return;
      $("#table-box").innerHTML = `<div class="notice error">${e.status === 404 ? "This assignment doesn't exist." : "Couldn't load: " + escapeHtml(e.message)}</div>`;
    }
  }

  $("#search").addEventListener("input", render);
  $("#refresh").onclick = load;
  $("#share-btn").onclick = () => copyText(`${location.origin}/?assignment=${encodeURIComponent(id)}`, "Student link copied");
  $("#table-box").addEventListener("click", e => {
    const b = e.target.closest("[data-copy]");
    if (b) copyText(b.dataset.copy, "Invite link copied");
  });
  load();
  setInterval(() => { if (!document.hidden) load(); }, 15000);
})();
