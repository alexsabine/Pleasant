/* Crescent Compass drawer: one question at a time, provenance on every answer. */
(function () {
  const toggle = document.getElementById("compass-toggle");
  const drawer = document.getElementById("compass-drawer");
  if (!toggle || !drawer) return;
  const log = drawer.querySelector(".compass-log");
  const form = drawer.querySelector(".compass-form");
  const input = form.querySelector("#compass-q");
  const closeBtn = drawer.querySelector("[data-close]");

  function open(v) {
    drawer.hidden = !v; toggle.setAttribute("aria-expanded", String(v));
    if (v) input.focus(); else toggle.focus();
  }
  toggle.addEventListener("click", () => open(drawer.hidden));
  closeBtn.addEventListener("click", () => open(false));
  document.addEventListener("keydown", e => { if (e.key === "Escape" && !drawer.hidden) open(false); });
  drawer.querySelectorAll(".suggest button").forEach(b => b.addEventListener("click", () => { input.value = b.textContent; form.requestSubmit(); }));

  function csrf() { const i = form.querySelector("input[name=csrfmiddlewaretoken]"); if (i) return i.value; const m = document.cookie.match(/csrftoken=([^;]+)/); return m ? m[1] : ""; }
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])); }
  function add(role, text, prov) {
    const d = document.createElement("div"); d.className = "msg " + role; d.textContent = text;
    if (prov) {
      const p = document.createElement("div"); p.className = "prov";
      const tools = (prov.tools || []).join(", ") || "none";
      p.innerHTML = `Action: <b>${esc(prov.action)}</b> · tools: ${esc(tools)} · projection v${esc(prov.projection_version)} · audit #${esc(prov.audit_index)} ${esc(String(prov.audit_hash || "").slice(0, 10))} · model phrasing: ${prov.llm_used ? "on" : "off"}` +
        `<details><summary>Why and limits</summary>${esc(prov.reason || "")}<ul>${(prov.limitations || []).map(l => "<li>" + esc(l) + "</li>").join("")}</ul></details>`;
      d.appendChild(p);
    }
    log.appendChild(d); log.scrollTop = log.scrollHeight;
  }
  form.addEventListener("submit", async e => {
    e.preventDefault();
    const q = input.value.trim(); if (!q) return;
    add("user", q); input.value = "";
    const thinking = document.createElement("div"); thinking.className = "msg bot"; thinking.textContent = "Checking the verified directory…"; log.appendChild(thinking);
    try {
      const r = await fetch(form.dataset.url, { method: "POST", headers: { "Content-Type": "application/json", "X-CSRFToken": csrf() }, body: JSON.stringify({ question: q }) });
      const data = await r.json();
      thinking.remove();
      add("bot", data.text || data.error || "No answer.", Object.assign({ action: data.action, reason: data.reason }, data.provenance || {}));
    } catch (err) { thinking.textContent = "Compass is unavailable right now. The Explore list still works."; }
  });
})();
