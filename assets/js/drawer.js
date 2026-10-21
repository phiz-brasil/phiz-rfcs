import { L, LANG_TAG, lang } from "./i18n.js";
import { isNew, srcOf, txt, visible } from "./model.js";
import { openPanel } from "./panels.js";
import { S, rfcId, sb } from "./state.js";
import { setReply, trNote } from "./threads.js";
import { el, sectionKey, store, titleOf, ts, when } from "./util.js";

export const SEEN_KEY = "phiz-rfc-seen:" + rfcId;      // when this browser last opened the list
S.seenAt = ts(store.get(SEEN_KEY));

export function paintAllBtn() {
  if (!sb || S.all === null) return;
  let b = document.querySelector(".cmt-all");
  if (!b) {
    b = el("button", "cmt-all"); b.type = "button"; b.setAttribute("aria-haspopup", "dialog");
    b.addEventListener("click", () => (S.drawer ? closeDrawer() : openDrawer()));
    const langs = document.querySelector("header .langs");
    if (langs) langs.before(b); else document.body.append(b);
  }
  const v = visible(), fresh = v.filter(isNew).length;
  b.replaceChildren(el("span", null, "💬"), el("span", "cmt-all-l", L().all), el("span", "cmt-n", String(v.length)));
  if (fresh) b.append(el("span", "cmt-new", `${fresh} ${L().newN}`));
  b.title = L().drawer;
}

export function openDrawer() {
  S.newIds = new Set(visible().filter(isNew).map(c => c.id));
  S.drawer = el("aside", "cmt-drawer");
  S.drawer.setAttribute("role", "dialog"); S.drawer.setAttribute("aria-modal", "false"); S.drawer.setAttribute("aria-label", L().drawer);
  document.body.append(S.drawer);
  document.querySelector(".cmt-all")?.setAttribute("aria-expanded", "true");
  renderDrawer();
  S.drawer.querySelector(".cmt-x").focus();
  // everything visible now counts as seen next time
  store.set(SEEN_KEY, new Date().toISOString());
  S.seenAt = Date.now();
  paintAllBtn();
}

export function closeDrawer() {
  if (!S.drawer) return;
  S.drawer.remove(); S.drawer = null;
  const b = document.querySelector(".cmt-all");
  if (b) { b.setAttribute("aria-expanded", "false"); b.focus(); }
}
document.addEventListener("keydown", e => { if (e.key === "Escape" && S.drawer) closeDrawer(); });

export function renderDrawer() {
  const v = visible();
  const tops = v.filter(c => !c.parent_id);
  const repliesOf = id => v.filter(r => r.parent_id === id);
  const fresh = c => S.newIds.has(c.id) || repliesOf(c.id).some(r => S.newIds.has(r.id));
  const counts = { all: tops.length, open: tops.filter(c => !repliesOf(c.id).length).length, new: tops.filter(fresh).length };

  const head = el("div", "cmt-d-head");
  const x = el("button", "cmt-x", "✕"); x.type = "button"; x.setAttribute("aria-label", L().close); x.addEventListener("click", closeDrawer);
  head.append(el("h2", null, L().drawer), x);

  const chips = el("div", "cmt-chips"); chips.setAttribute("role", "group");
  [["all", L().fAll], ["open", L().fOpen], ["new", L().fNew]].forEach(([k, label]) => {
    const c = el("button", "cmt-chip"); c.type = "button";
    c.setAttribute("aria-pressed", String(S.dFilter === k));
    c.append(document.createTextNode(label + " "), el("b", null, String(counts[k])));
    c.addEventListener("click", () => { S.dFilter = k; renderDrawer(); });
    chips.append(c);
  });

  const body = el("div", "cmt-d-body");
  const order = new Map([...document.querySelectorAll(".lang.active h2[id]")].map((h, i) => [sectionKey(h), i]));
  const shown = tops
    .filter(c => S.dFilter === "open" ? !repliesOf(c.id).length : S.dFilter === "new" ? fresh(c) : true)
    .sort((a, b) => (order.get(a.section) ?? 999) - (order.get(b.section) ?? 999) || ts(b.created_at) - ts(a.created_at));
  if (S.loadFailed) body.append(el("p", "cmt-note cmt-err", L().load));
  else if (!tops.length) body.append(el("p", "cmt-note", L().none));
  else if (!shown.length) body.append(el("p", "cmt-note", L().noneF));
  let lastSec = null;
  for (const c of shown) {
    const h = document.getElementById(`${lang()}-${c.section}`);
    if (c.section !== lastSec) {
      lastSec = c.section;
      body.append(el("h3", "cmt-d-sec", h ? titleOf(h) : c.section));
    }
    const reps = repliesOf(c.id);
    const it = el("article", "cmt-d-item" + (fresh(c) ? " is-new" : ""));
    const meta = el("div", "cmt-meta");
    meta.append(el("strong", null, c.author), el("time", null, when(c.created_at)));
    const x = txt(c);
    if (srcOf(c) && srcOf(c) !== lang() && !x.can) meta.append(el("span", "cmt-lang", LANG_TAG[srcOf(c)] || srcOf(c)));
    if (fresh(c)) meta.append(el("span", "cmt-newtag", L().newTag));
    it.append(meta);
    if (x.quote) it.append(el("blockquote", "cmt-quote", x.quote));
    it.append(el("p", "cmt-body cmt-clamp", x.body));
    const note = trNote(c, x, renderDrawer);
    if (note) it.append(note);
    if (reps.length) {
      const last = reps[reps.length - 1];
      const r = el("p", "cmt-d-rep");
      r.append(el("b", null, L().replies(reps.length) + " · "), document.createTextNode(`${last.author}: ${txt(last).body.slice(0, 140)}`));
      it.append(r);
    }
    const foot = el("div", "cmt-d-foot");
    foot.append(el("span", reps.length ? "cmt-note" : "cmt-note cmt-open", reps.length ? "" : L().noReplies));
    const go = el("button", "cmt-link", L().open); go.type = "button";
    go.addEventListener("click", () => {
      closeDrawer();
      if (!h) return;
      h.scrollIntoView({ block: "start" });
      const p = h.nextElementSibling;
      if (p && p.classList.contains("cmt-panel")) p.remove();
      openPanel(h, h.querySelector(".cmt-btn"), { focusId: c.id });
      const f = h.nextElementSibling && h.nextElementSibling.querySelector("form");
      if (f) setReply(h.nextElementSibling, c);
    });
    foot.append(go);
    it.append(foot);
    body.append(it);
  }

  const foot = el("div", "cmt-d-end");
  const a = el("a", null, L().central); a.href = "../../comments/";
  foot.append(el("p", "cmt-note", L().newHint), a);
  S.drawer.replaceChildren(head, chips, body, foot);
}

/* ?c=<comment id> (links from the central comments page) opens that comment in its section */
export function openFromLink() {
  if (S.linkDone) return; S.linkDone = true;
  const id = new URLSearchParams(location.search).get("c");
  if (!id || !S.all) return;
  const c = S.all.find(x => x.id === id);
  if (!c) return;
  const top = c.parent_id ? S.all.find(x => x.id === c.parent_id) || c : c;
  const h = document.getElementById(`${lang()}-${c.section}`);
  if (!h) return;
  setTimeout(() => {
    h.scrollIntoView({ block: "start" });
    openPanel(h, h.querySelector(".cmt-btn"), { focusId: c.id });
    if (h.nextElementSibling && h.nextElementSibling.querySelector("form")) setReply(h.nextElementSibling, top);
  }, 50);
}
