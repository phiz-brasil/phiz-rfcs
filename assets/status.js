/* Live RFC status (stored in Supabase, table rfc_status_log; the build-time status in rfc.json is the fallback).
   - RFC page: shows the current status and lets anyone change it from the badge in the header.
   - Index: shows the current status of every RFC and rebuilds the status filters.
   Every change is appended to rfc_status_log with the name typed by the person (nobody can edit or delete it from the page). */
(function () {
  const cfg = window.PHIZ_SITE || {};
  const c = cfg.comments || window.PHIZ_CMT || {};
  if (!c.supabaseUrl || !c.supabaseKey || window.PHIZ_FROZEN) return;   // archived versions keep the status they had
  const base = c.supabaseUrl.replace(/\/+$/, "") + "/rest/v1/";
  const headers = Object.assign({ apikey: c.supabaseKey },
    /^eyJ/.test(c.supabaseKey) ? { Authorization: "Bearer " + c.supabaseKey } : {});

  const LANGS = ["pt", "en", "zh"];
  const STATUS = {
    "draft":       { pt: "Rascunho",     en: "Draft",       zh: "草稿" },
    "in-review":   { pt: "Em revisão",   en: "In review",   zh: "评审中" },
    "approved":    { pt: "Aprovada",     en: "Approved",    zh: "已批准" },
    "implemented": { pt: "Implementada", en: "Implemented", zh: "已实现" },
    "rejected":    { pt: "Rejeitada",    en: "Rejected",    zh: "已拒绝" },
    "superseded":  { pt: "Substituída",  en: "Superseded",  zh: "已被取代" }
  };
  const T = {
    pt: { change: "Alterar status", name: "Seu nome", needName: "Informe seu nome.", note: "A mudança fica registrada com seu nome.",
          err: "Não foi possível alterar. Tente de novo.", rate: "Muitas mudanças seguidas. Espere um minuto.", by: "por", all: "Todas" },
    en: { change: "Change status", name: "Your name", needName: "Enter your name.", note: "The change is recorded with your name.",
          err: "Could not change the status. Please try again.", rate: "Too many changes in a row. Wait a minute.", by: "by", all: "All" },
    zh: { change: "更改状态", name: "你的名字", needName: "请填写名字。", note: "此次更改会记录你的名字。",
          err: "无法更改状态，请重试。", rate: "更改过于频繁，请一分钟后再试。", by: "由", all: "全部" }
  };
  const lang = () => document.documentElement.dataset.lang || "pt";
  const L = () => T[lang()] || T.pt;
  const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; };
  const store = {
    get(k) { try { return localStorage.getItem(k) || ""; } catch (e) { return ""; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
  };
  const trio = (s, cls) => LANGS.map(l => { const n = el("span", cls, STATUS[s][l]); n.dataset.l = l; return n; });
  const stamp = r => {
    try { return `${L().by} ${r.author} · ${new Date(r.created_at).toLocaleString({ pt: "pt-BR", en: "en-US", zh: "zh-CN" }[lang()], { dateStyle: "medium", timeStyle: "short" })}`; }
    catch (e) { return ""; }
  };

  async function current(rfcId) {
    const q = `rfc_status_current?select=rfc_id,status,author,created_at${rfcId ? "&rfc_id=eq." + encodeURIComponent(rfcId) : ""}`;
    const r = await fetch(base + q, { headers });
    if (!r.ok) throw new Error("HTTP " + r.status);
    return r.json();
  }

  /* ---------- RFC page ---------- */
  const rfcId = window.PHIZ_RFC_ID;

  function setSwap(node, s) {                       // rewrite the three language spans of a badge
    node.dataset.st = s;
    node.querySelectorAll("[data-l]").forEach(n => { if (STATUS[s][n.dataset.l]) n.textContent = STATUS[s][n.dataset.l]; });
  }
  function applyToPage(row) {
    const s = row.status;
    if (!STATUS[s]) return;
    const badge = document.querySelector(".rfcno.st");
    if (badge) { setSwap(badge, s); badge.title = stamp(row); }
    document.querySelectorAll(".lang").forEach(box => {          // hero pill and eyebrow, one per language
      const l = box.dataset.lang;
      box.querySelectorAll("dt").forEach(dt => {
        if (!/^(status|状态)$/i.test(dt.textContent.trim())) return;
        const pill = dt.nextElementSibling && dt.nextElementSibling.querySelector(".pill");
        if (pill) { pill.dataset.st = s; if (STATUS[s][l]) pill.textContent = STATUS[s][l]; }
      });
      const eb = box.querySelector(".eyebrow");
      if (eb && STATUS[s][l] && eb.textContent.includes(" · ")) eb.textContent = eb.textContent.split(" · ")[0] + " · " + STATUS[s][l];
    });
    window.PHIZ_STATUS_NOW = s;
  }

  function picker(badge) {
    badge.classList.add("st-btn");
    badge.setAttribute("role", "button"); badge.tabIndex = 0; badge.setAttribute("aria-haspopup", "true"); badge.setAttribute("aria-expanded", "false");
    const pop = el("div", "st-pop"); pop.hidden = true;
    const title = el("p", "st-title"); title.textContent = L().change;
    const name = el("input"); name.maxLength = 60; name.autocomplete = "name"; name.value = store.get("phiz-rfc-author");
    const err = el("p", "st-err"); err.hidden = true;
    const note = el("p", "st-note");
    const list = el("div", "st-list");
    const refreshText = () => { title.textContent = L().change; name.placeholder = L().name; name.setAttribute("aria-label", L().name); note.textContent = L().note; };
    Object.keys(STATUS).forEach(s => {
      const b = el("button", "st-opt"); b.type = "button"; b.dataset.st = s;
      b.append(...trio(s));
      b.addEventListener("click", async () => {
        const author = name.value.trim();
        if (!author) { err.textContent = L().needName; err.hidden = false; name.focus(); return; }
        list.querySelectorAll("button").forEach(x => { x.disabled = true; });
        try {
          const r = await fetch(base + "rfc_status_log", {
            method: "POST", headers: Object.assign({ "Content-Type": "application/json", Prefer: "return=minimal" }, headers),
            body: JSON.stringify({ rfc_id: rfcId, status: s, author })
          });
          if (!r.ok) { const e = new Error("HTTP " + r.status); e.rate = r.status === 429 || /PT429|rate limit/.test(await r.text().catch(() => "")); throw e; }
          store.set("phiz-rfc-author", author);
          applyToPage({ status: s, author, created_at: new Date().toISOString() });
          close();
        } catch (e) {
          err.textContent = e.rate ? L().rate : L().err; err.hidden = false;
        } finally {
          list.querySelectorAll("button").forEach(x => { x.disabled = false; });
        }
      });
      list.append(b);
    });
    name.addEventListener("input", () => { err.hidden = true; });
    pop.append(title, name, err, list, note);
    badge.after(pop);
    const open = () => { refreshText(); err.hidden = true; pop.hidden = false; badge.setAttribute("aria-expanded", "true"); sync(); if (!name.value) name.focus(); };
    function close() { pop.hidden = true; badge.setAttribute("aria-expanded", "false"); }
    const sync = () => list.querySelectorAll(".st-opt").forEach(b => b.setAttribute("aria-current", String(b.dataset.st === (window.PHIZ_STATUS_NOW || badge.dataset.st))));
    badge.addEventListener("click", () => (pop.hidden ? open() : close()));
    badge.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); pop.hidden ? open() : close(); } if (e.key === "Escape") close(); });
    pop.addEventListener("keydown", e => { if (e.key === "Escape") { close(); badge.focus(); } });
    document.addEventListener("click", e => { if (!pop.hidden && !pop.contains(e.target) && !badge.contains(e.target)) close(); });
  }

  async function initPage() {
    const badge = document.querySelector(".rfcno.st");
    if (badge) picker(badge);
    try { const rows = await current(rfcId); if (rows[0]) applyToPage(rows[0]); } catch (e) { console.warn("status", e); }
  }

  /* ---------- index ---------- */
  async function initIndex() {
    let rows;
    try { rows = await current(); } catch (e) { console.warn("status", e); return; }
    const byId = new Map(rows.map(r => [r.rfc_id, r]));
    document.querySelectorAll(".card-li[data-rfc]").forEach(li => {
      const r = byId.get(li.dataset.rfc);
      if (!r || !STATUS[r.status]) return;
      li.dataset.status = r.status;
      const badge = li.querySelector(".badge");
      if (badge) setSwap(badge, r.status);
    });
    const filters = document.querySelector(".filters");
    if (!filters) return;
    const used = Object.keys(STATUS).filter(s => [...document.querySelectorAll(".card-li")].some(li => li.dataset.status === s));
    filters.replaceChildren();
    const chip = (v, labels) => {
      const b = el("button"); b.type = "button"; b.dataset.filter = v; b.setAttribute("aria-pressed", String(v === "all"));
      LANGS.forEach(l => { const n = el("span", null, labels[l]); n.dataset.l = l; b.append(n); });
      filters.append(b);
    };
    chip("all", { pt: T.pt.all, en: T.en.all, zh: T.zh.all });
    used.forEach(s => chip(s, STATUS[s]));
    document.querySelectorAll(".card-li").forEach(li => { li.hidden = false; });
  }

  if (rfcId) initPage();
  else if (window.PHIZ_STATUS_INDEX) initIndex();
})();
