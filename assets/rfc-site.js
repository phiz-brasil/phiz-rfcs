/* Hosted-RFC enhancements: Mermaid rendering for the active language + comments.
   Comments use Supabase when site.config.json has comments.supabaseUrl and comments.supabaseKey
   (stored on the page, no GitHub login); otherwise giscus, otherwise a pre-filled GitHub issue. */
(function () {
  const cfg = window.PHIZ_SITE || {};
  const rfcId = window.PHIZ_RFC_ID || "RFC";
  const frozen = !!window.PHIZ_FROZEN;   // archived version: read-only, no new comments
  const T = {
    pt: { btn: "Comentar", fallback: "Abrir no GitHub", need: "Comentários usam sua conta do GitHub.",
          name: "Seu nome", body: "Escreva um comentário", send: "Comentar", sending: "Enviando…", reply: "Responder",
          replyTo: "Respondendo a", cancel: "Cancelar", empty: "Nenhum comentário nesta seção ainda.", quote: "Comentar trecho",
          on: "Sobre o trecho:", load: "Não foi possível carregar os comentários.", err: "Não foi possível enviar. Tente de novo.",
          rate: "Muitos comentários seguidos. Espere um minuto e tente de novo.", needName: "Informe seu nome.",
          needBody: "Escreva o comentário.", public: "Comentários são públicos e ficam salvos nesta página.",
          removeQuote: "Remover trecho" },
    en: { btn: "Comment", fallback: "Open on GitHub", need: "Comments use your GitHub account.",
          name: "Your name", body: "Write a comment", send: "Comment", sending: "Sending…", reply: "Reply",
          replyTo: "Replying to", cancel: "Cancel", empty: "No comments on this section yet.", quote: "Comment on selection",
          on: "On the passage:", load: "Could not load comments.", err: "Could not send. Please try again.",
          rate: "Too many comments in a row. Wait a minute and try again.", needName: "Enter your name.",
          needBody: "Write the comment.", public: "Comments are public and saved on this page.",
          removeQuote: "Remove passage" },
    zh: { btn: "评论", fallback: "在 GitHub 打开", need: "评论需要使用 GitHub 账号。",
          name: "你的名字", body: "写下评论", send: "评论", sending: "发送中…", reply: "回复",
          replyTo: "回复", cancel: "取消", empty: "本节还没有评论。", quote: "评论所选内容",
          on: "关于这段内容：", load: "无法加载评论。", err: "发送失败，请重试。",
          rate: "评论过于频繁，请一分钟后再试。", needName: "请填写名字。",
          needBody: "请填写评论内容。", public: "评论是公开的，并保存在本页面。",
          removeQuote: "移除引用" }
  };
  const LANG_TAG = { pt: "PT", en: "EN", zh: "中文" };
  const lang = () => document.documentElement.dataset.lang || "pt";
  const L = () => T[lang()] || T.pt;
  const dark = () => matchMedia("(prefers-color-scheme: dark)").matches || document.documentElement.dataset.theme === "dark";

  /* ---------- Mermaid ---------- */
  function initMermaid() {
    if (!window.mermaid) return;
    window.mermaid.initialize({ startOnLoad: false, securityLevel: "strict", theme: dark() ? "dark" : "neutral", flowchart: { htmlLabels: true } });
  }
  async function renderMermaid() {
    if (!window.mermaid) return;
    const nodes = [...document.querySelectorAll(".lang.active pre.mermaid:not([data-processed])")];
    if (!nodes.length) return;
    try { await window.mermaid.run({ nodes }); } catch (e) { console.warn("mermaid", e); }
  }

  /* ---------- helpers ---------- */
  const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; };
  function sectionKey(h) { return h.id.replace(/^(pt|en|zh)-/, ""); }
  function titleOf(h) { const c = h.cloneNode(true); c.querySelectorAll(".cmt-btn").forEach(x => x.remove()); c.querySelectorAll(".n").forEach(x => x.append(" ")); return c.textContent.replace(/\s+/g, " ").trim(); }
  function issueUrl(key, title) {
    const t = encodeURIComponent(`[${rfcId} · ${key}] `);
    const b = encodeURIComponent(`RFC: ${rfcId}\nSection: ${title}\nLink: ${location.href.split("#")[0]}#${key}\n\n`);
    return `https://github.com/${cfg.repo}/issues/new?labels=rfc-comment&title=${t}&body=${b}`;
  }
  function when(iso) {
    const loc = { pt: "pt-BR", en: "en-US", zh: "zh-CN" }[lang()];
    try { return new Date(iso).toLocaleString(loc, { dateStyle: "medium", timeStyle: "short" }); } catch (e) { return iso; }
  }
  const store = {
    get(k) { try { return localStorage.getItem(k) || ""; } catch (e) { return ""; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
  };

  /* ---------- Supabase provider ---------- */
  const sb = !frozen && cfg.comments && cfg.comments.supabaseUrl && cfg.comments.supabaseKey ? {
    url: cfg.comments.supabaseUrl.replace(/\/+$/, "") + "/rest/v1/rfc_comments",
    // new publishable keys (sb_publishable_…) go only in "apikey"; legacy anon keys are JWTs and also go in Authorization
    headers: Object.assign({ apikey: cfg.comments.supabaseKey },
      /^eyJ/.test(cfg.comments.supabaseKey) ? { Authorization: "Bearer " + cfg.comments.supabaseKey } : {})
  } : null;
  const COLS = "id,rfc_id,section,parent_id,author,body,quote,lang,created_at";
  let all = null;          // comments of this RFC; null while loading
  let loadFailed = false;

  async function loadAll() {
    try {
      const q = `?select=${COLS}&rfc_id=eq.${encodeURIComponent(rfcId)}&order=created_at.asc&limit=2000`;
      const r = await fetch(sb.url + q, { headers: sb.headers });
      if (!r.ok) throw new Error("HTTP " + r.status);
      all = await r.json();
      loadFailed = false;
    } catch (e) {
      console.warn("comments", e);
      all = []; loadFailed = true;
    }
    paintCounts(); paintMarks();
    document.querySelectorAll(".cmt-panel[data-key]").forEach(renderThreads);
  }

  async function addComment(row) {
    const r = await fetch(sb.url + "?select=" + COLS, {
      method: "POST",
      headers: Object.assign({ "Content-Type": "application/json", Prefer: "return=representation" }, sb.headers),
      body: JSON.stringify(row)
    });
    if (r.status === 429) throw Object.assign(new Error("rate"), { code: "rate" });
    if (!r.ok) throw new Error("HTTP " + r.status);
    const rows = await r.json();
    return rows[0];
  }

  // replies whose parent was hidden by a moderator are not shown or counted
  const forSection = key => {
    const rows = (all || []).filter(c => c.section === key);
    const tops = new Set(rows.filter(c => !c.parent_id).map(c => c.id));
    return rows.filter(c => !c.parent_id || tops.has(c.parent_id));
  };

  function paintCounts() {
    document.querySelectorAll(".lang h2[id] .cmt-btn").forEach(b => {
      const n = forSection(sectionKey(b.closest("h2"))).length;
      let c = b.querySelector(".cmt-n");
      if (!c) { c = el("span", "cmt-n"); b.append(c); }
      c.textContent = n ? String(n) : "";
      c.hidden = !n;
    });
  }

  /* Highlight commented passages in the active language, Confluence-style. */
  function paintMarks() {
    document.querySelectorAll("mark.cmt-mark").forEach(m => { const p = m.parentNode; m.replaceWith(...m.childNodes); p.normalize(); });
    if (!all) return;
    const cur = lang();
    for (const c of all) {
      if (!c.quote || c.parent_id || c.lang !== cur) continue;
      const h = document.getElementById(`${cur}-${c.section}`);
      const sec = h && h.closest("section");
      if (!sec) continue;
      const walker = document.createTreeWalker(sec, NodeFilter.SHOW_TEXT, {
        acceptNode: n => n.parentElement.closest("h2, .cmt-panel, pre, figure, mark") ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT
      });
      for (let n = walker.nextNode(); n; n = walker.nextNode()) {
        const i = n.data.indexOf(c.quote);
        if (i < 0) continue;
        const r = document.createRange();
        r.setStart(n, i); r.setEnd(n, i + c.quote.length);
        const m = el("mark", "cmt-mark");
        m.dataset.id = c.id;
        m.title = `${c.author}: ${c.body.slice(0, 120)}`;
        r.surroundContents(m);
        m.addEventListener("click", () => openPanel(h, h.querySelector(".cmt-btn"), { focusId: c.id }));
        break;
      }
    }
  }

  function renderThreads(panel) {
    const list = panel.querySelector(".cmt-list");
    list.replaceChildren();
    if (!all) { list.append(el("p", "cmt-note", "…")); return; }
    if (loadFailed) { list.append(el("p", "cmt-note cmt-err", L().load)); return; }
    const items = forSection(panel.dataset.key);
    const tops = items.filter(c => !c.parent_id);
    if (!tops.length) { list.append(el("p", "cmt-note", L().empty)); return; }
    for (const c of tops) {
      const th = el("div", "cmt-thread");
      th.append(card(c, panel, false));
      items.filter(r => r.parent_id === c.id).forEach(r => th.append(card(r, panel, true)));
      list.append(th);
    }
  }

  function card(c, panel, isReply) {
    const box = el("article", "cmt-item" + (isReply ? " cmt-reply" : ""));
    box.dataset.id = c.id;
    const meta = el("div", "cmt-meta");
    meta.append(el("strong", null, c.author), el("time", null, when(c.created_at)));
    if (c.lang && c.lang !== lang()) meta.append(el("span", "cmt-lang", LANG_TAG[c.lang] || c.lang));
    box.append(meta);
    if (c.quote) box.append(el("blockquote", "cmt-quote", c.quote));
    box.append(el("p", "cmt-body", c.body));
    if (!isReply) {
      const rb = el("button", "cmt-link", L().reply);
      rb.type = "button";
      rb.addEventListener("click", () => setReply(panel, c));
      box.append(rb);
    }
    return box;
  }

  function setReply(panel, c) {
    const f = panel.querySelector("form");
    f.dataset.parent = c ? c.id : "";
    const tag = f.querySelector(".cmt-replying");
    tag.hidden = !c;
    if (c) { tag.querySelector("span").textContent = `${L().replyTo} ${c.author}`; setQuote(panel, ""); }
    f.querySelector("textarea").focus();
  }

  function setQuote(panel, text) {
    const f = panel.querySelector("form");
    f.dataset.quote = text || "";
    const q = f.querySelector(".cmt-quote-pre");
    q.hidden = !text;
    q.querySelector("blockquote").textContent = text || "";
  }

  function buildForm(panel) {
    const f = el("form", "cmt-form");
    f.noValidate = true;
    const replying = el("div", "cmt-replying"); replying.hidden = true;
    const rc = el("button", "cmt-link", L().cancel); rc.type = "button"; rc.addEventListener("click", () => setReply(panel, null));
    replying.append(el("span"), rc);
    const qp = el("div", "cmt-quote-pre"); qp.hidden = true;
    const qx = el("button", "cmt-link", L().removeQuote); qx.type = "button"; qx.addEventListener("click", () => setQuote(panel, ""));
    qp.append(el("span", "cmt-note", L().on), el("blockquote", "cmt-quote"), qx);
    const name = el("input"); name.name = "author"; name.maxLength = 60; name.placeholder = L().name; name.autocomplete = "name";
    name.setAttribute("aria-label", L().name);
    name.value = store.get("phiz-rfc-author");
    const body = el("textarea"); body.name = "body"; body.maxLength = 4000; body.rows = 3; body.placeholder = L().body;
    body.setAttribute("aria-label", L().body);
    const trap = el("input", "cmt-trap"); trap.name = "website"; trap.tabIndex = -1; trap.autocomplete = "off"; trap.setAttribute("aria-hidden", "true");
    const err = el("p", "cmt-err"); err.hidden = true; err.setAttribute("aria-live", "polite");
    const send = el("button", "cmt-send", L().send); send.type = "submit";
    const row = el("div", "cmt-row"); row.append(el("span", "cmt-note", L().public), send);
    [name, body].forEach(i => i.addEventListener("input", () => { err.hidden = true; }));
    f.append(replying, qp, name, body, trap, err, row);
    f.addEventListener("submit", async ev => {
      ev.preventDefault();
      if (trap.value) return;
      const author = name.value.trim(), text = body.value.trim();
      if (!author) { err.textContent = L().needName; err.hidden = false; name.focus(); return; }
      if (!text) { err.textContent = L().needBody; err.hidden = false; body.focus(); return; }
      send.disabled = true; send.textContent = L().sending;
      try {
        const saved = await addComment({ rfc_id: rfcId, section: panel.dataset.key, parent_id: f.dataset.parent || null,
                                         author, body: text, quote: f.dataset.quote || null, lang: lang() });
        store.set("phiz-rfc-author", author);
        (all = all || []).push(saved);
        body.value = "";
        setReply(panel, null); setQuote(panel, "");
        renderThreads(panel); paintCounts(); paintMarks();
      } catch (e) {
        err.textContent = e.code === "rate" ? L().rate : L().err; err.hidden = false;
      } finally {
        send.disabled = false; send.textContent = L().send;
      }
    });
    return f;
  }

  /* ---------- panel ---------- */
  const giscusReady = () => cfg.repo && cfg.repo !== "OWNER/REPO" && cfg.giscus && cfg.giscus.repoId && cfg.giscus.categoryId;

  function openPanel(h, btn, opts) {
    opts = opts || {};
    const key = sectionKey(h);
    let panel = h.nextElementSibling;
    const isOpen = panel && panel.classList.contains("cmt-panel");
    if (isOpen && !opts.quote && !opts.focusId) { panel.remove(); btn.setAttribute("aria-expanded", "false"); return; }
    if (!isOpen) {
      panel = el("div", "cmt-panel");
      if (sb) {
        panel.dataset.key = key;
        panel.append(el("div", "cmt-list"), buildForm(panel));
        renderThreads(panel);
      } else if (giscusReady()) {
        const s = document.createElement("script");
        s.src = "https://giscus.app/client.js"; s.async = true; s.crossOrigin = "anonymous";
        const a = {
          repo: cfg.repo, "repo-id": cfg.giscus.repoId, category: cfg.giscus.category, "category-id": cfg.giscus.categoryId,
          mapping: "specific", term: `${rfcId}#${key}`, strict: "0", "reactions-enabled": "1", "emit-metadata": "0",
          "input-position": "top", theme: "preferred_color_scheme", lang: { pt: "pt", en: "en", zh: "zh-CN" }[lang()], loading: "lazy"
        };
        Object.entries(a).forEach(([k, v]) => s.setAttribute("data-" + k, v));
        panel.append(el("p", "cmt-note", L().need), s);
      } else {
        const p = el("p", "cmt-note");
        const link = el("a", null, L().fallback);
        link.href = issueUrl(key, titleOf(h)); link.target = "_blank"; link.rel = "noopener";
        p.append(link); panel.append(p);
      }
      h.after(panel);
      btn.setAttribute("aria-expanded", "true");
    }
    if (sb && opts.quote) { setReply(panel, null); setQuote(panel, opts.quote); }
    if (opts.focusId) {
      const item = panel.querySelector(`.cmt-item[data-id="${CSS.escape(opts.focusId)}"]`);
      if (item) { item.scrollIntoView({ block: "center" }); item.classList.add("cmt-flash"); setTimeout(() => item.classList.remove("cmt-flash"), 1600); }
    }
  }

  function decorate() {
    document.querySelectorAll(".lang h2[id]").forEach(h => {
      if (h.querySelector(".cmt-btn")) return;
      const b = document.createElement("button");
      b.type = "button"; b.className = "cmt-btn"; b.setAttribute("aria-expanded", "false");
      b.innerHTML = '<span aria-hidden="true">💬</span> <span class="cmt-l"></span>';
      b.addEventListener("click", () => openPanel(h, b));
      h.append(b);
    });
    document.querySelectorAll(".cmt-btn .cmt-l").forEach(n => { n.textContent = L().btn; });
    if (sb) paintCounts();
  }

  /* ---------- select text → comment ---------- */
  let fab = null;
  function hideFab() { if (fab) fab.hidden = true; }
  function onSelect() {
    if (!sb) return;
    const s = getSelection();
    if (!s || s.isCollapsed || !s.rangeCount) return hideFab();
    const text = s.toString().replace(/\s+/g, " ").trim();
    const range = s.getRangeAt(0);
    const anc = range.commonAncestorContainer;
    const node = anc.nodeType === 1 ? anc : anc.parentElement;
    const sec = node && node.closest(".lang.active section");
    if (!text || text.length > 500 || !sec || node.closest(".cmt-panel, h2, pre, .cmt-fab")) return hideFab();
    const h = sec.querySelector("h2[id]");
    if (!h) return hideFab();
    if (!fab) {
      fab = el("button", "cmt-fab"); fab.type = "button";
      fab.addEventListener("mousedown", e => e.preventDefault());
      document.body.append(fab);
    }
    fab.textContent = "💬 " + L().quote;
    const rect = range.getBoundingClientRect();
    fab.style.top = `${window.scrollY + rect.top - 42}px`;
    fab.style.left = `${Math.max(8, Math.min(window.scrollX + rect.left, window.scrollX + innerWidth - 220))}px`;
    fab.hidden = false;
    fab.onclick = () => { hideFab(); getSelection().removeAllRanges(); openPanel(h, h.querySelector(".cmt-btn"), { quote: text }); };
  }
  document.addEventListener("mouseup", () => setTimeout(onSelect, 0));
  document.addEventListener("keyup", e => { if (e.shiftKey) onSelect(); });
  document.addEventListener("selectionchange", () => { const s = getSelection(); if (!s || s.isCollapsed) hideFab(); });

  /* ---------- wiring ---------- */
  function refresh() { if (!frozen) decorate(); renderMermaid(); if (sb) paintMarks(); }

  // close the version history when clicking elsewhere
  document.addEventListener("click", e => { document.querySelectorAll("details.vers[open]").forEach(d => { if (!d.contains(e.target)) d.open = false; }); });

  initMermaid();
  new MutationObserver(refresh).observe(document.documentElement, { attributes: true, attributeFilter: ["data-lang"] });
  window.addEventListener("load", refresh);
  document.addEventListener("DOMContentLoaded", refresh);
  if (document.readyState !== "loading") refresh();
  if (sb) loadAll();
})();
