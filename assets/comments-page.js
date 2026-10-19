/* Central comments page: every visible comment of every RFC, newest first, with filters.
   Reads the same Supabase table as the RFC pages (public read-only key). Replying happens on the
   RFC page itself: each card links to the comment in its section (?c=<id>). */
(function () {
  const META = window.PHIZ_COMMENTS || { cfg: {}, rfcs: [] };
  const cfg = META.cfg || {};
  const T = {
    pt: { all: "Todas", fAll: "Todos", fOpen: "Sem resposta", fNew: "Novos",
          sum: (n, o, f) => `${n} comentários · ${o} sem resposta · ${f} novos desde sua última visita`,
          open: "Abrir na RFC e responder", replies: n => n === 1 ? "1 resposta" : `${n} respostas`,
          noReply: "Sem resposta", none: "Nenhum comentário ainda.", noneF: "Nada neste filtro.",
          load: "Não foi possível carregar os comentários.", off: "Os comentários na página não estão configurados.",
          newTag: "novo", search: "Buscar por texto ou autor", loading: "Carregando…",
          auto: "Tradução automática", from: "de", orig: "Ver original", showTr: "Ver tradução" },
    en: { all: "All", fAll: "All", fOpen: "Unanswered", fNew: "New",
          sum: (n, o, f) => `${n} comments · ${o} unanswered · ${f} new since your last visit`,
          open: "Open in the RFC and reply", replies: n => n === 1 ? "1 reply" : `${n} replies`,
          noReply: "No reply yet", none: "No comments yet.", noneF: "Nothing in this filter.",
          load: "Could not load comments.", off: "On-page comments are not configured.",
          newTag: "new", search: "Search text or author", loading: "Loading…",
          auto: "Machine translation", from: "from", orig: "Show original", showTr: "Show translation" },
    zh: { all: "全部", fAll: "全部", fOpen: "未回复", fNew: "新评论",
          sum: (n, o, f) => `共 ${n} 条评论 · ${o} 条未回复 · 自上次访问以来 ${f} 条新评论`,
          open: "在 RFC 中打开并回复", replies: n => `${n} 条回复`,
          noReply: "尚无回复", none: "还没有评论。", noneF: "此筛选下没有内容。",
          load: "无法加载评论。", off: "尚未配置页面评论。",
          newTag: "新", search: "按内容或作者搜索", loading: "加载中…",
          auto: "机器翻译", from: "原文", orig: "查看原文", showTr: "查看译文" }
  };
  const LANG_TAG = { pt: "PT", en: "EN", zh: "中文" };
  const LOC = { pt: "pt-BR", en: "en-US", zh: "zh-CN" };
  const lang = () => document.documentElement.dataset.lang || "pt";
  const L = () => T[lang()] || T.pt;
  const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; };
  const ts = iso => Date.parse(iso) || 0;
  const store = {
    get(k) { try { return localStorage.getItem(k) || ""; } catch (e) { return ""; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
  };
  const when = iso => { try { return new Date(iso).toLocaleString(LOC[lang()], { dateStyle: "medium", timeStyle: "short" }); } catch (e) { return iso; } };
  const rfcById = Object.fromEntries((META.rfcs || []).map(r => [r.id, r]));
  const pick = (d, l) => (d && (d[l] || d.pt || d.en)) || "";

  const SEEN = "phiz-rfc-seen:all";
  const seenAt = ts(store.get(SEEN));
  let rows = null, failed = false, newIds = new Set();
  let fRfc = "all", fState = "all", q = "";

  const root = document.getElementById("cmt-root");
  const sb = cfg.supabaseUrl && cfg.supabaseKey ? {
    url: cfg.supabaseUrl.replace(/\/+$/, "") + "/rest/v1/rfc_comments",
    headers: Object.assign({ apikey: cfg.supabaseKey }, /^eyJ/.test(cfg.supabaseKey) ? { Authorization: "Bearer " + cfg.supabaseKey } : {})
  } : null;

  async function load() {
    if (!sb) { rows = []; render(); return; }
    try {
      const base = "id,rfc_id,section,parent_id,author,body,quote,lang,created_at";
      const q = c => `?select=${c}&order=created_at.desc&limit=5000`;
      let r = await fetch(sb.url + q(base + ",translations,src_lang"), { headers: sb.headers });
      if (r.status === 400) r = await fetch(sb.url + q(base), { headers: sb.headers });   // translation columns not created yet
      if (!r.ok) throw new Error("HTTP " + r.status);
      const data = await r.json();
      const tops = new Set(data.filter(c => !c.parent_id).map(c => c.id));
      rows = data.filter(c => !c.parent_id || tops.has(c.parent_id));
      const me = store.get("phiz-rfc-author");
      newIds = new Set(rows.filter(c => ts(c.created_at) > seenAt && c.author !== me).map(c => c.id));
      store.set(SEEN, new Date().toISOString());
    } catch (e) {
      console.warn("comments", e); rows = []; failed = true;
    }
    render();
  }

  const showOrig = new Set();
  const srcOf = c => c.src_lang || c.lang;
  function txt(c) {
    const t = c.translations && c.translations[lang()];
    const can = !!t && srcOf(c) !== lang() && t.body !== c.body;
    if (!can || showOrig.has(c.id)) return { body: c.body, quote: c.quote, translated: false, can };
    return { body: t.body, quote: c.quote ? (t.quote || c.quote) : null, translated: true, can };
  }

  function sectionTitle(c) {
    const r = rfcById[c.rfc_id];
    return pick(r && r.sections && r.sections[c.section], lang()) || c.section;
  }

  function render() {
    root.replaceChildren();
    if (!sb) { root.append(el("p", "empty", L().off)); return; }
    if (rows === null) { root.append(el("p", "empty", L().loading)); return; }
    if (failed) { root.append(el("p", "empty err", L().load)); return; }

    const repliesOf = id => rows.filter(r => r.parent_id === id).sort((a, b) => ts(a.created_at) - ts(b.created_at));
    const tops = rows.filter(c => !c.parent_id);
    const fresh = c => newIds.has(c.id) || repliesOf(c.id).some(r => newIds.has(r.id));
    const inRfc = tops.filter(c => fRfc === "all" || c.rfc_id === fRfc);
    const needle = q.trim().toLowerCase();
    const texts = c => [c.author, c.body, c.quote || "", ...Object.values(c.translations || {}).flatMap(t => [t.body || "", t.quote || ""])];
    const match = c => !needle || [...texts(c), ...repliesOf(c.id).flatMap(texts)].some(s => s.toLowerCase().includes(needle));

    // filters
    const bar = el("div", "cbar");
    const rfcChips = el("div", "filters"); rfcChips.setAttribute("role", "group");
    const ids = [...new Set([...(META.rfcs || []).map(r => r.id), ...tops.map(c => c.rfc_id)])].sort().reverse();
    [["all", L().all], ...ids.map(id => [id, id])].forEach(([k, label]) => {
      const n = k === "all" ? tops.length : tops.filter(c => c.rfc_id === k).length;
      const b = el("button"); b.type = "button"; b.setAttribute("aria-pressed", String(fRfc === k));
      b.append(document.createTextNode(label + " "), el("b", null, String(n)));
      b.onclick = () => { fRfc = k; render(); };
      rfcChips.append(b);
    });
    const stChips = el("div", "filters"); stChips.setAttribute("role", "group");
    const cnt = { all: inRfc.length, open: inRfc.filter(c => !repliesOf(c.id).length).length, new: inRfc.filter(fresh).length };
    [["all", L().fAll], ["open", L().fOpen], ["new", L().fNew]].forEach(([k, label]) => {
      const b = el("button", k === "open" ? "st-open" : k === "new" ? "st-new" : ""); b.type = "button";
      b.setAttribute("aria-pressed", String(fState === k));
      b.append(document.createTextNode(label + " "), el("b", null, String(cnt[k])));
      b.onclick = () => { fState = k; render(); };
      stChips.append(b);
    });
    const search = el("input", "csearch"); search.type = "search"; search.placeholder = L().search;
    search.setAttribute("aria-label", L().search); search.value = q;
    search.oninput = () => { q = search.value; const pos = search.selectionStart; render(); const s = root.querySelector(".csearch"); s.focus(); s.setSelectionRange(pos, pos); };
    bar.append(rfcChips, stChips, search);
    root.append(bar, el("p", "csum", L().sum(rows.length, tops.filter(c => !repliesOf(c.id).length).length, rows.filter(c => newIds.has(c.id)).length)));

    const shown = inRfc
      .filter(c => fState === "open" ? !repliesOf(c.id).length : fState === "new" ? fresh(c) : true)
      .filter(match)
      .sort((a, b) => {
        const la = Math.max(ts(a.created_at), ...repliesOf(a.id).map(r => ts(r.created_at)));
        const lb = Math.max(ts(b.created_at), ...repliesOf(b.id).map(r => ts(r.created_at)));
        return lb - la;   // most recent activity first
      });
    if (!tops.length) { root.append(el("p", "empty", L().none)); return; }
    if (!shown.length) { root.append(el("p", "empty", L().noneF)); return; }

    const list = el("ul", "clist");
    for (const c of shown) {
      const r = rfcById[c.rfc_id];
      const reps = repliesOf(c.id);
      const li = el("li", "ccard" + (fresh(c) ? " is-new" : ""));
      const top = el("div", "ctop");
      top.append(el("span", "id", c.rfc_id), el("span", "csec", sectionTitle(c)));
      if (fresh(c)) top.append(el("span", "cnew", L().newTag));
      if (!reps.length) top.append(el("span", "copen", L().noReply));
      li.append(top);
      if (r) li.append(el("p", "ctitle", pick(r.title, lang())));
      li.append(item(c));
      if (reps.length) {
        const rl = el("div", "creps");
        rl.append(el("p", "crepn", L().replies(reps.length)));
        reps.forEach(x => rl.append(item(x, true)));
        li.append(rl);
      }
      const a = el("a", "cgo", L().open);
      a.href = `../rfcs/${encodeURIComponent(c.rfc_id)}/?c=${encodeURIComponent(c.id)}#${lang()}-${c.section}`;
      li.append(a);
      list.append(li);
    }
    root.append(list);
  }

  function item(c, isReply) {
    const box = el("div", "citem" + (isReply ? " crep" : "") + (newIds.has(c.id) ? " is-new" : ""));
    const meta = el("div", "cmeta");
    meta.append(el("strong", null, c.author), el("time", null, when(c.created_at)));
    const x = txt(c);
    if (srcOf(c)) meta.append(el("span", "clang", LANG_TAG[srcOf(c)] || srcOf(c)));
    if (isReply && newIds.has(c.id)) meta.append(el("span", "cnew", L().newTag));
    box.append(meta);
    if (x.quote) box.append(el("blockquote", "cquote", x.quote));
    box.append(el("p", "cbody", x.body));
    if (x.can) {
      const p = el("p", "ctr");
      p.append(document.createTextNode(x.translated ? `🌐 ${L().auto} · ${L().from} ${LANG_TAG[srcOf(c)] || srcOf(c)} · ` : "🌐 "));
      const b = el("button", "clink", x.translated ? L().orig : L().showTr); b.type = "button";
      b.onclick = () => { showOrig.has(c.id) ? showOrig.delete(c.id) : showOrig.add(c.id); render(); };
      p.append(b); box.append(p);
    }
    return box;
  }

  new MutationObserver(render).observe(document.documentElement, { attributes: true, attributeFilter: ["data-lang"] });
  render();
  load();
})();
