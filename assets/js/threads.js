import { addComment, hideComment } from "./api.js";
import { paintAllBtn, renderDrawer } from "./drawer.js";
import { L, LANG_TAG, lang } from "./i18n.js";
import { EMOJIS, forSection, isReaction, showOrig, srcOf, txt } from "./model.js";
import { flashPara, paintCounts, paintMarks } from "./panels.js";
import { S, rfcId } from "./state.js";
import { el, store, when } from "./util.js";

export function trNote(c, x, rerender) {
  if (!x.can) return null;
  const p = el("p", "cmt-tr");
  p.append(el("span", null, x.translated ? `🌐 ${L().auto} · ${L().from} ${LANG_TAG[srcOf(c)] || srcOf(c)} · ` : `🌐 ${LANG_TAG[srcOf(c)] || ""} · `));
  const b = el("button", "cmt-link", x.translated ? L().orig : L().showTr); b.type = "button";
  b.addEventListener("click", () => { showOrig.has(c.id) ? showOrig.delete(c.id) : showOrig.add(c.id); rerender(); });
  p.append(b);
  return p;
}

// every open list and counter follows the data
export function rerenderAll() {
  document.querySelectorAll(".cmt-panel[data-key]").forEach(renderThreads);
  paintCounts(); paintMarks(); paintAllBtn();
  if (S.drawer) renderDrawer();
}

export function renderThreads(panel) {
  const list = panel.querySelector(".cmt-list");
  if (panel._form) panel.append(panel._form);   // park the form outside the list, which is rebuilt below
  list.replaceChildren();
  if (!S.all) { list.append(el("p", "cmt-note", "…")); return; }
  if (S.loadFailed) { list.append(el("p", "cmt-note cmt-err", L().load)); return; }
  const para = panel.dataset.para === undefined ? undefined : Number(panel.dataset.para);
  const items = forSection(panel.dataset.key, para);
  const tops = items.filter(c => !c.parent_id);
  if (!tops.length) { list.append(el("p", "cmt-note", L().empty)); return; }
  for (const c of tops) {
    const th = el("div", "cmt-thread");
    th.dataset.id = c.id;
    const replies = items.filter(r => r.parent_id === c.id);
    th.append(card(c, panel, false, replies.filter(isReaction)));
    replies.filter(r => !isReaction(r)).forEach(r => th.append(card(r, panel, true)));
    list.append(th);
  }
  placeForm(panel);
}

// the form sits under the comment being answered (after its replies); without a reply target it stays at the end
export function placeForm(panel) {
  const f = panel._form;
  if (!f) return;
  const pid = f.dataset.parent;
  const th = pid && panel.querySelector(`.cmt-thread[data-id="${CSS.escape(pid)}"]`);
  (th || panel).append(f);
}

export function card(c, panel, isReply, reacts) {
  const box = el("article", "cmt-item" + (isReply ? " cmt-reply" : ""));
  box.dataset.id = c.id;
  const meta = el("div", "cmt-meta");
  meta.append(el("strong", null, c.author), el("time", null, when(c.created_at)));
  const x = txt(c);
  if (srcOf(c) && srcOf(c) !== lang() && !x.can) meta.append(el("span", "cmt-lang", LANG_TAG[srcOf(c)] || srcOf(c)));
  if (c.para != null && panel.dataset.para === undefined) {     // section list: say which paragraph it is about
    const tag = el("button", "cmt-ptag", `¶ ${c.para + 1}`); tag.type = "button"; tag.title = L().para;
    tag.addEventListener("click", () => flashPara(c));
    meta.append(tag);
  }
  box.append(meta);
  if (x.quote) box.append(el("blockquote", "cmt-quote", x.quote));
  box.append(el("p", "cmt-body", x.body));
  const note = trNote(c, x, () => renderThreads(panel));
  if (note) box.append(note);
  if (!isReply) box.append(reactionRow(c, reacts || []));
  const acts = el("div", "cmt-acts");
  if (!isReply) {
    const rb = el("button", "cmt-link", L().reply);
    rb.type = "button";
    rb.addEventListener("click", () => setReply(panel, c));
    acts.append(rb);
  }
  acts.append(deleteControl(c, panel));
  box.append(acts);
  return box;
}

export function reactionRow(c, reacts) {
  const row = el("div", "cmt-rx");
  const me = store.get("phiz-rfc-author");
  const groups = new Map();
  for (const r of reacts) { const k = r.body.trim(); if (!groups.has(k)) groups.set(k, []); groups.get(k).push(r); }
  const mineOf = e => me && (groups.get(e) || []).find(r => r.author === me);
  for (const [emoji, rs] of groups) {
    const b = el("button", "cmt-rxchip"); b.type = "button";
    b.setAttribute("aria-pressed", String(!!mineOf(emoji)));
    b.title = rs.map(r => r.author).join(", ");
    b.append(el("span", null, emoji), el("b", null, String(rs.length)));
    b.addEventListener("click", () => react(c, emoji, row));
    row.append(b);
  }
  const add = el("button", "cmt-rxadd", "☺+"); add.type = "button";
  add.title = L().react; add.setAttribute("aria-label", L().react); add.setAttribute("aria-expanded", "false");
  const pick = el("span", "cmt-rxpick"); pick.hidden = true;
  EMOJIS.forEach(e => {
    const eb = el("button", "cmt-rxopt", e); eb.type = "button";
    eb.addEventListener("click", () => react(c, e, row));
    pick.append(eb);
  });
  add.addEventListener("click", () => { pick.hidden = !pick.hidden; add.setAttribute("aria-expanded", String(!pick.hidden)); });
  row.append(add, pick);
  return row;
}

// clicking an emoji adds it as a reply with that emoji; clicking one you already gave takes it back
export async function react(c, emoji, row) {
  const me = store.get("phiz-rfc-author");
  if (!me) { askName(row, () => react(c, emoji, row)); return; }
  row.querySelectorAll("button").forEach(b => { b.disabled = true; });
  try {
    const mine = (S.all || []).find(r => r.parent_id === c.id && r.author === me && r.body.trim() === emoji);
    if (mine) {
      await hideComment(mine.id);
      S.all = S.all.filter(r => r.id !== mine.id);
    } else {
      const data = { rfc_id: rfcId, section: c.section, parent_id: c.id, author: me, body: emoji, quote: null, lang: lang() };
      if (S.HAS_PARA && c.para != null) data.para = c.para;
      (S.all = S.all || []).push(await addComment(data));
    }
    rerenderAll();
  } catch (e) {
    console.warn("reaction", e);
    row.querySelectorAll("button").forEach(b => { b.disabled = false; });
    let err = row.querySelector(".cmt-err");
    if (!err) { err = el("span", "cmt-err"); row.append(err); }
    err.textContent = e.code === "rate" ? L().rate : L().err;
  }
}

export function askName(row, then) {
  if (row.querySelector(".cmt-rxname")) { row.querySelector(".cmt-rxname input").focus(); return; }
  const box = el("span", "cmt-rxname");
  const input = el("input"); input.maxLength = 60; input.placeholder = L().name; input.setAttribute("aria-label", L().name); input.autocomplete = "name";
  const ok = el("button", "cmt-link", L().ok); ok.type = "button";
  const go = () => { const v = input.value.trim(); if (!v) { input.focus(); return; } store.set("phiz-rfc-author", v); box.remove(); then(); };
  ok.addEventListener("click", go);
  input.addEventListener("keydown", e => { if (e.key === "Enter") { e.preventDefault(); go(); } });
  box.append(input, ok);
  row.append(box);
  input.focus();
}

// "Delete" asks once, then hides the comment (and its replies) for everyone
export function deleteControl(c, panel) {
  const wrap = el("span", "cmt-del");
  const btn = el("button", "cmt-link cmt-danger", L().del); btn.type = "button";
  btn.addEventListener("click", () => {
    const msg = el("span", "cmt-note", L().delSure);
    const yes = el("button", "cmt-link cmt-danger", L().delYes); yes.type = "button";
    const no = el("button", "cmt-link", L().delNo); no.type = "button";
    no.addEventListener("click", () => wrap.replaceChildren(btn));
    yes.addEventListener("click", async () => {
      yes.disabled = no.disabled = true;
      try {
        await hideComment(c.id);
        S.all = (S.all || []).filter(r => r.id !== c.id && r.parent_id !== c.id);
        const f = panel._form;
        if (f && f.dataset.parent === c.id) setReply(panel, null);
        rerenderAll();
      } catch (e) {
        console.warn("delete comment", e);
        msg.textContent = e.code === "rate" ? L().rate : L().delErr;
        yes.disabled = no.disabled = false;
      }
    });
    wrap.replaceChildren(msg, yes, no);
  });
  wrap.append(btn);
  return wrap;
}

export function setReply(panel, c) {
  const f = panel._form;
  f.dataset.parent = c ? c.id : "";
  const tag = f.querySelector(".cmt-replying");
  tag.hidden = !c;
  if (c) { tag.querySelector("span").textContent = `${L().replyTo} ${c.author}`; setQuote(panel, ""); }
  placeForm(panel);
  f.querySelector("textarea").focus({ preventScroll: true });
  f.scrollIntoView({ block: "nearest", behavior: "smooth" });
}

export function setQuote(panel, text) {
  const f = panel._form;
  f.dataset.quote = text || "";
  const q = f.querySelector(".cmt-quote-pre");
  q.hidden = !text;
  q.querySelector("blockquote").textContent = text || "";
}

export function buildForm(panel) {
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
      const parent = f.dataset.parent ? (S.all || []).find(x => x.id === f.dataset.parent) : null;
      const para = parent ? parent.para : (panel.dataset.para !== undefined ? Number(panel.dataset.para) : null);
      const data = { rfc_id: rfcId, section: panel.dataset.key, parent_id: f.dataset.parent || null,
                     author, body: text, quote: f.dataset.quote || null, lang: lang() };
      if (S.HAS_PARA && para != null) data.para = para;
      const saved = await addComment(data);
      store.set("phiz-rfc-author", author);
      (S.all = S.all || []).push(saved);
      body.value = "";
      setReply(panel, null); setQuote(panel, "");
      rerenderAll();
    } catch (e) {
      err.textContent = e.code === "rate" ? L().rate : L().err; err.hidden = false;
    } finally {
      send.disabled = false; send.textContent = L().send;
    }
  });
  return f;
}
