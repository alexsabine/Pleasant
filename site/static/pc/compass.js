/* Crescent Compass drawer: one question at a time, provenance on every answer. */
(function () {
  const toggle = document.getElementById("compass-toggle");
  const drawer = document.getElementById("compass-drawer");
  if (!toggle || !drawer) return;
  const log = drawer.querySelector(".compass-log");
  const form = drawer.querySelector(".compass-form");
  const input = form.querySelector("#compass-q");
  const closeBtn = drawer.querySelector("[data-close]");

  const guide = JSON.parse(log.dataset.guide || "{}");
  // Phone keyboards: Android (with interactive-widget=resizes-content) shrinks the layout viewport,
  // iOS does not. Size the drawer to the *visual* viewport so the question box always sits above
  // the keyboard on both.
  const vv = window.visualViewport;
  // Chrome on Android exposes the keyboard directly (VirtualKeyboard API): ask it to overlay and
  // read its height, which also makes env(keyboard-inset-height) available to the CSS.
  let kbdInset = 0;
  const vk = navigator.virtualKeyboard;
  if (vk) {
    try { vk.overlaysContent = true; } catch (err) { /* older builds */ }
    vk.addEventListener("geometrychange", e => { const r = (e.target && e.target.boundingRect) || vk.boundingRect; kbdInset = r ? Math.round(r.height) : 0; fit(); });
  }
  function fit() {
    if (drawer.hidden) return;
    if (window.matchMedia("(max-width: 640px)").matches) {
      const h = vv ? vv.height : window.innerHeight;
      const top = vv ? vv.offsetTop : 0;
      drawer.style.top = Math.round(top) + "px";
      drawer.style.height = Math.round(h) + "px";
      drawer.style.paddingBottom = kbdInset ? kbdInset + "px" : "";
    } else { drawer.style.height = ""; drawer.style.top = ""; drawer.style.paddingBottom = ""; }
    log.scrollTop = log.scrollHeight;
  }
  if (vv) { vv.addEventListener("resize", fit); vv.addEventListener("scroll", fit); }
  window.addEventListener("resize", fit);
  let fitTimer = null;
  function fitForAWhile() {   // keyboards animate; re-measure for 1.5 s after focus and after blur
    if (fitTimer) clearInterval(fitTimer);
    let n = 0;
    fitTimer = setInterval(() => { fit(); if (++n > 15) { clearInterval(fitTimer); fitTimer = null; } }, 100);
  }
  input.addEventListener("focus", fitForAWhile);
  input.addEventListener("blur", () => { kbdInset = 0; fitForAWhile(); });
  let guideStep = -1, guideAnswers = [];
  function open(v) {
    drawer.hidden = !v; toggle.setAttribute("aria-expanded", String(v));
    document.body.classList.toggle("compass-open", v);
    if (v) fit(); else { drawer.style.height = ""; drawer.style.top = ""; }
    if (v && !log.children.length && guide.intro) add("bot", guide.intro);
    if (v) input.focus(); else toggle.focus();
  }
  function askNext() {
    const q = guide.questions[guideStep];
    add("bot", `Question ${guideStep + 1} of ${guide.questions.length}. ${q.text}\n(Type your answer, or "skip", or "stop".)`);
  }
  async function finishGuide() {
    guideStep = -1;
    const answers = guideAnswers.filter(a => a.answer); guideAnswers = [];
    if (!answers.length) { add("bot", "No answers to pass on. Ask me anything about the county whenever you like."); return; }
    if (window.PC_STATIC) {
      const text = ["Compass guide answers", ""].concat(answers.flatMap(a => [a.question, a.answer, ""])).join("\n");
      let copied = false; try { await navigator.clipboard.writeText(text); copied = true; } catch (err) { copied = false; }
      add("bot", (copied ? "Copied to your clipboard. " : "") + "This static preview cannot store answers: please paste the text below into an email or message to Alex.\n\n" + text);
      return;
    }
    try {
      const r = await fetch(form.dataset.url.replace(/ask$/, "feedback"), { method: "POST", headers: { "Content-Type": "application/json", "X-CSRFToken": csrf() }, body: JSON.stringify({ answers }) });
      const d = await r.json();
      add("bot", d.saved ? guide.closing : "I could not save the answers; please use the review page instead.");
    } catch (err) { add("bot", "I could not reach the server to save the answers; please use the review page instead."); }
  }
  function startGuide() {
    if (!guide.questions || !guide.questions.length) return;
    guideStep = 0; guideAnswers = [];
    add("user", "Help shape Compass");
    add("bot", "Thank you. There are " + guide.questions.length + " short questions; skip any you like, and nothing you say is published.");
    askNext(); input.focus();
  }
  drawer.querySelectorAll("[data-guide-start]").forEach(b => b.addEventListener("click", startGuide));
  toggle.addEventListener("click", () => open(drawer.hidden));
  closeBtn.addEventListener("click", () => open(false));
  document.addEventListener("keydown", e => { if (e.key === "Escape" && !drawer.hidden) open(false); });
  drawer.querySelectorAll(".suggest button:not([data-guide-start])").forEach(b => b.addEventListener("click", () => { input.value = b.textContent; form.requestSubmit(); }));

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
    if (guideStep >= 0) {   // guide mode: the input answers the current question
      const low = q.toLowerCase().replace(/[.!]+$/, "");
      if (low === "stop" || low === "forget that") { await finishGuide(); return; }
      if (low !== "skip") guideAnswers.push({ key: guide.questions[guideStep].key, question: guide.questions[guideStep].text, answer: q });
      guideStep += 1;
      if (guideStep < guide.questions.length) askNext(); else await finishGuide();
      return;
    }
    const thinking = document.createElement("div"); thinking.className = "msg bot"; thinking.textContent = "Checking the verified directory…"; log.appendChild(thinking);
    try {
      if (window.PC_STATIC && window.PCCompassStatic) {
        const data = await window.PCCompassStatic.ask(q);
        thinking.remove();
        add("bot", data.text, Object.assign({ action: data.action, reason: data.reason }, data.provenance || {}));
        return;
      }
      const r = await fetch(form.dataset.url, { method: "POST", headers: { "Content-Type": "application/json", "X-CSRFToken": csrf() }, body: JSON.stringify({ question: q }) });
      const data = await r.json();
      thinking.remove();
      add("bot", data.text || data.error || "No answer.", Object.assign({ action: data.action, reason: data.reason }, data.provenance || {}));
    } catch (err) { thinking.textContent = "Compass is unavailable right now. The Explore list still works."; }
  });
})();
