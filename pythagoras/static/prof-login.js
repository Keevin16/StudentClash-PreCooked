api("/api/prof/auth").then(a => { if (!a.password) location.replace("/prof"); }).catch(() => { });  // no password set: no login
$("#login-form").addEventListener("submit", async e => {
  e.preventDefault();
  const btn = $("#login-btn"), err = $("#login-error");
  err.classList.add("hidden");
  setBusy(btn, true, "Signing in…");
  try {
    await api("/api/prof/login", { method: "POST", body: { password: $("#password").value } });
    const next = new URLSearchParams(location.search).get("next");
    location.href = next && next.startsWith("/prof") ? next : "/prof";
  } catch (ex) {
    err.textContent = ex.status === 401 ? "Wrong password. Try again." : ex.message;
    err.classList.remove("hidden");
    setBusy(btn, false);
    $("#password").select();
  }
});
