/* Static-preview behaviour (GitHub Pages export only; never loaded by the hosted site).
   1. Explore filters run client-side over the rendered cards.
   2. Forms that need the server (join, sign-in, suggest) are disabled with a note.
   3. The review form compiles replies into text to copy or email.
   4. Crescent Compass runs the same deterministic policy in the browser over api/resources.json:
      hard constraints are filters, the show test is P(current) > 0.75, nothing is invented.
      No decision record can be written here; the hosted site records every answer. */
(function () {
  const S = window.PC_STATIC || { base: "/" };
  const BASE = S.base.replace(/\/$/, "");

  // ---- 1. Explore filters ------------------------------------------------------------
  const filters = document.querySelector("form.filters");
  if (filters) {
    const cards = Array.from(document.querySelectorAll(".cards .card"));
    const count = document.querySelector("p.lede[aria-live]");
    const freeBtn = filters.querySelector("button[name=free]");
    let freeOnly = freeBtn && freeBtn.getAttribute("aria-pressed") === "true";
    function apply() {
      const f = new FormData(filters);
      const age = f.get("age"), group = f.get("group"), cat = f.get("category"), com = f.get("community"), access = f.get("access"), q = (f.get("q") || "").toLowerCase().trim();
      if (filters.dataset.group !== undefined && group !== filters.dataset.group) {   // group pages are pre-rendered subsets
        location.href = BASE + "/explore/" + (group ? "group/" + group + "/" : ""); return;
      }
      let n = 0;
      for (const c of cards) {
        const [lo, hi, cost, acc, community, category, grp, text] = c.dataset.f.split("|");
        let ok = true;
        if (age !== "" && age !== null && (Number(age) < Number(lo) || Number(age) > Number(hi))) ok = false;
        if (freeOnly && cost !== "free") ok = false;
        if (cat && category !== cat) ok = false;
        if (com && community !== com && community !== "countywide") ok = false;
        if (access && acc !== "verified_yes") ok = false;              // unknown is never accessible
        if (q && !text.includes(q)) ok = false;
        c.hidden = !ok; if (ok) n++;
      }
      if (count) count.textContent = n + " listing" + (n === 1 ? "" : "s") + " match. Unknown access is shown as unknown, never as accessible.";
    }
    filters.addEventListener("submit", e => { e.preventDefault(); apply(); });
    if (freeBtn) freeBtn.addEventListener("click", e => { e.preventDefault(); freeOnly = !freeOnly; freeBtn.setAttribute("aria-pressed", String(freeOnly)); apply(); });
  }

  // ---- 2. Server-only forms ---------------------------------------------------------------
  document.querySelectorAll("form[method=post], form[method=POST]").forEach(form => {
    if (form.classList.contains("qa") || form.classList.contains("compass-form")) return;
    const note = document.createElement("p"); note.className = "notice-ok static-note"; note.setAttribute("role", "status");
    note.textContent = "Static preview: accounts, sign-in and suggestions need the hosted site, so this form is shown but cannot send anything.";
    form.prepend(note);
    form.querySelectorAll("button[type=submit], input[type=submit]").forEach(b => { b.disabled = true; });
    form.addEventListener("submit", e => e.preventDefault());
  });

  // ---- 3. Review replies ----------------------------------------------------------------
  const qa = document.querySelector("form.qa");
  if (qa) {
    qa.addEventListener("submit", async e => {
      e.preventDefault();
      const who = qa.querySelector("#reviewer");
      const parts = ["Pleasant Crescent review replies" + (who && who.value ? " from " + who.value : ""), ""];
      qa.querySelectorAll(".qcard").forEach(card => {
        const t = card.querySelector("textarea");
        if (t && t.value.trim()) parts.push(card.querySelector("h3").textContent.trim(), t.value.trim(), "");
      });
      const text = parts.join("\n");
      let box = qa.querySelector(".static-out");
      if (!box) { box = document.createElement("div"); box.className = "static-out"; qa.appendChild(box); }
      let copied = false;
      try { await navigator.clipboard.writeText(text); copied = true; } catch (err) { copied = false; }
      const mail = S.reviewEmail ? `<a class="btn secondary" href="mailto:${S.reviewEmail}?subject=${encodeURIComponent("Pleasant Crescent review replies")}&body=${encodeURIComponent(text)}">Open in email</a>` : "";
      box.innerHTML = `<p class="notice-ok" role="status">${copied ? "Copied to your clipboard. " : ""}This static preview cannot store replies: paste the text below into an email or message to Alex.</p><textarea rows="10" readonly aria-label="Your compiled replies">${text.replace(/[&<>]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]))}</textarea>${mail}`;
      box.scrollIntoView({ behavior: "smooth", block: "nearest" });
    });
  }

  // ---- 4. Crescent Compass, static policy -------------------------------------------------
  let rules = null, data = null, events = null;
  async function load() {
    if (!rules) rules = await fetch(BASE + "/api/compass_rules.json").then(r => r.json());
    if (!data) data = await fetch(BASE + "/api/resources.json").then(r => r.json());
    if (!events) events = await fetch(BASE + "/api/events.json").then(r => r.json()).catch(() => ({ items: [] }));
  }
  const AGE_RE = /(\d{1,2})\s*(?:-|to)?\s*(?:year|yr|y\/o|yo)|(?:age|aged|ages)\s*(\d{1,2})|(\d{1,2})\s*(?:year|yr)s?\s*old|toddler|baby|teen/i;
  function wordRe(w) { return new RegExp("\\b" + w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "s?\\b"); }
  function parse(question) {
    const q = question.toLowerCase();
    const it = { age: null, free_only: false, max_cost: null, requires_accessibility: false, categories: [], community: null, wants_events: false, text: question, source: "rules-static" };
    const m = q.match(AGE_RE);
    if (m) { for (const g of m.slice(1)) if (g && /^\d+$/.test(g)) { it.age = Number(g); break; } if (it.age === null) for (const [w, a] of Object.entries(rules.word_ages)) if (m[0].toLowerCase().includes(w)) it.age = a; }
    if (it.age === null) for (const [w, a] of Object.entries(rules.word_ages)) if (q.includes(w)) { it.age = a; break; }
    if (/\bfree\b|no cost|cheap|budget|don't want to pay/.test(q)) it.free_only = true;
    const m2 = q.match(/under\s*\$?(\d+)|less than\s*\$?(\d+)|\$(\d+)/); if (m2) it.max_cost = Number(m2.slice(1).find(g => g));
    if (/wheelchair|accessible|pushchair|stroller|step-free|mobility/.test(q)) it.requires_accessibility = true;
    for (const [cat, words] of Object.entries(rules.keywords)) if (words.some(w => wordRe(w).test(q))) it.categories.push(cat);
    if (it.categories.includes("after_school") && it.categories.includes("school") && !/high school|elementary|middle school|charter|academy/.test(q)) it.categories = it.categories.filter(c => c !== "school");
    for (const [key, label] of rules.communities) if (q.includes(label)) { it.community = key; break; }
    if (/this week|weekend|today|tomorrow|event|what's on|whats on|happening/.test(q)) it.wants_events = true;
    return it;
  }
  function structured(it) { return it.age !== null || it.free_only || it.max_cost !== null || it.requires_accessibility || it.categories.length > 0 || !!it.community; }
  function search(k) {
    let items = data.items.slice();
    if (k.age !== null && k.age !== undefined) items = items.filter(d => d.min_age <= k.age && d.max_age >= k.age);
    if (k.free_only) items = items.filter(d => d.cost_status === "free");
    if (k.max_cost !== null && k.max_cost !== undefined) items = items.filter(d => d.cost_status === "free" || (d.cost_status === "priced" && d.cost_usd !== null && d.cost_usd <= k.max_cost));
    if (k.requires_accessibility) items = items.filter(d => d.accessibility_status === "verified_yes");
    if (k.categories && k.categories.length) items = items.filter(d => k.categories.includes(d.category));
    if (k.community) items = items.filter(d => d.community === k.community || d.community === "countywide");
    if (k.text) {
      const toks = (k.text.toLowerCase().match(/[a-z]{4,}/g) || []).filter(t => !rules.stopwords.includes(t));
      if (toks.length) items = items.filter(d => toks.some(t => (d.name + " " + d.description).toLowerCase().includes(t)));
    }
    items.sort((a, b) => ((b.p_current || 0) - (a.p_current || 0)) || a.name.localeCompare(b.name));
    return items.slice(0, 20);
  }
  const u = () => rules.utilities;
  function showAct(p) { return p * u().show_true + (1 - p) * u().show_false > u().abstain; }
  function decide(it, maxItems) {
    const calls = [];
    const text = structured(it) ? "" : it.text;
    const leftover = (text.toLowerCase().match(/[a-z]{4,}/g) || []).filter(t => !rules.stopwords.includes(t) && !rules.event_words.includes(t));
    const eventsOnly = it.wants_events && !structured(it) && leftover.length === 0;
    const k = { age: it.age, free_only: it.free_only, max_cost: it.max_cost, requires_accessibility: it.requires_accessibility, categories: it.categories.length ? it.categories : null, community: it.community, text };
    let res = [];
    if (!eventsOnly) { res = search(k); calls.push("search_published_resources"); }
    const broadened = [];
    for (const [key, label] of [["categories", "type of activity"], ["community", "community"], ["free_only", "cost"]]) {
      if (eventsOnly || res.length || !k[key]) continue;
      k[key] = key === "free_only" ? false : null; res = search(k); calls.push("search_published_resources"); broadened.push(label);
    }
    let ev = [];
    if (it.wants_events) { const now = Date.now(); ev = (events.items || []).filter(e => !e.is_past && new Date(e.start_at) - now < 7 * 86400e3 && (!it.free_only || e.cost_status === "free") && (it.age === null || (e.min_age <= it.age && e.max_age >= it.age))); calls.push("search_events"); }
    const shown = [], withheld = [];
    for (const d of res) {
      if (d.p_current === null || d.p_current === undefined) { withheld.push(Object.assign({}, d, { why: "no verification on record" })); continue; }
      if (showAct(d.p_current)) shown.push(d); else withheld.push(Object.assign({}, d, { why: `P(current)=${d.p_current.toFixed(2)} below the show threshold under the published utilities` }));
    }
    let question = null;
    if (it.age === null && shown.length >= 2) {
      const bands = Array.from(new Set(shown.map(d => d.min_age + "-" + d.max_age))).map(s => s.split("-").map(Number));
      if (bands.length > 1 && bands.some(a => bands.some(b => a[1] < b[0] || b[1] < a[0]))) question = "How old is your child? I can narrow this to the right age band (optional).";
    }
    let action, reason;
    if (!shown.length && !ev.length && withheld.length) { action = "show_low_confidence"; reason = "matches exist but none is recently verified; shown with their status, not recommended"; }
    else if (!shown.length && !ev.length) { action = "explain_unknown"; reason = "no published listing matches; nothing is invented"; }
    else if (question && shown.length > 3) { action = "ask"; reason = "age would change which safe suggestions apply"; }
    else { action = "show"; reason = `${shown.length} listing(s) pass the Bayes show test`; }
    if (broadened.length && action === "show") reason += `; no exact match, so ${broadened.join(", ")} was relaxed`;
    return { action, reason, shown: shown.slice(0, maxItems), withheld: withheld.slice(0, maxItems), events: ev.slice(0, maxItems), question, calls, broadened };
  }
  const BAND = { recently_verified: "recently verified", verified_this_season: "verified this season", needs_recheck: "needs a re-check", unverified: "not yet verified" };
  const ACCESS = { verified_yes: "verified accessible", verified_no: "verified not accessible", unknown: "access unknown" };
  const COST = { free: "free", priced: "priced", variable: "variable cost", unknown: "cost unknown" };
  function ago(iso) { if (!iso) return "not yet verified"; const days = Math.floor((Date.now() - new Date(iso)) / 86400e3); return days === 0 ? "checked today" : `checked ${days} day${days === 1 ? "" : "s"} ago`; }
  function line(d) { const cost = COST[d.cost_status] + (d.cost_status === "priced" && d.cost_usd !== null ? ` ($${Math.round(d.cost_usd)})` : ""); return `${d.name}: ${d.category_label.toLowerCase()}, ages ${d.min_age} to ${d.max_age}, ${cost}, ${ACCESS[d.accessibility_status]}, ${ago(d.last_verified_at)}.`; }
  function compose(dec) {
    const L = [];
    if (dec.action === "show_low_confidence") { L.push("I found a match, but it has not been re-verified recently enough for me to recommend it outright. Here it is with its status:"); dec.withheld.forEach(d => L.push("• " + line(d) + (d.why ? ` (${d.why})` : ""))); L.push("You can check the source link on the listing page, or ask again later once an editor has re-verified it."); }
    else if (dec.action === "explain_unknown") { L.push("I could not find a published listing that matches. I only suggest places that an editor has verified, so I will not guess."); L.push("You could broaden the search (drop the age or cost filter) or browse the full Explore list."); }
    else {
      if (dec.broadened.length) L.push("Nothing matched exactly, so I relaxed the " + dec.broadened.join(" and ") + " and kept your other requirements.");
      if (dec.shown.length) { L.push(`Here ${dec.shown.length === 1 ? "is" : "are"} ${dec.shown.length} recently checked option${dec.shown.length === 1 ? "" : "s"} from the published directory:`); dec.shown.forEach(d => L.push("• " + line(d))); }
      if (dec.events.length) { L.push("Coming up:"); dec.events.forEach(e => L.push(`• ${e.title}: ${new Date(e.start_at).toLocaleString()}, ${COST[e.cost_status]}, ages ${e.min_age} to ${e.max_age}.`)); }
      if (dec.withheld.length) { L.push("Also listed, but not re-verified recently enough for me to recommend outright:"); dec.withheld.forEach(d => L.push("• " + line(d) + (d.why ? ` (${d.why})` : ""))); }
    }
    if (dec.question) L.push(dec.question);
    return L.join("\n");
  }
  window.PCCompassStatic = {
    async ask(question) {
      await load();
      if (["forget that", "forget", "clear memory", "start over"].includes(question.toLowerCase().trim().replace(/[ .!]+$/, "")))
        return { action: "forget", text: "Nothing to clear: this static preview keeps no memory between questions.", provenance: { policy_version: "compass-0.1-static", tools: [], limitations: [] } };
      const it = parse(question);
      const dec = decide(it, 4);
      return { action: dec.action, reason: dec.reason, text: compose(dec), items: dec.shown, withheld: dec.withheld, events: dec.events, question: dec.question,
        provenance: { policy_version: "compass-0.1-static", projection_version: data.projection_version, tools: dec.calls, allow_list: ["search_published_resources", "search_events"],
          audit_index: "none", audit_hash: "static preview", llm_used: false, intent: it, memory_used: [],
          limitations: ["Static preview: the same deterministic policy runs in your browser over the published snapshot; no decision record is written to the audit log (the hosted site records every answer).",
            "Only published, editor-verified records are used; nothing is inferred about places not listed.", "Access status 'unknown' is never presented as accessible.", "Verification dates are shown; conditions can change between checks."] } };
    }
  };
})();
