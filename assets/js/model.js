import { lang } from "./i18n.js";
import { S } from "./state.js";
import { store, ts } from "./util.js";

/* Machine translation (stored by the translate-comment function): show the comment in the page language */
export const showOrig = new Set();
export const srcOf = c => c.src_lang || c.lang;
export function txt(c) {
  const t = c.translations && c.translations[lang()];
  const translated = !!t && srcOf(c) !== lang() && t.body !== c.body;
  if (!translated || showOrig.has(c.id)) return { body: c.body, quote: c.quote, translated: false, can: translated };
  return { body: t.body, quote: c.quote ? (t.quote || c.quote) : null, translated: true, can: true };
}

// replies whose parent was hidden by a moderator are not shown or counted
// `para` (a number) keeps only the comments of that paragraph; without it, the whole section
export const forSection = (key, para) => {
  const rows = (S.all || []).filter(c => c.section === key);
  const tops = new Set(rows.filter(c => !c.parent_id && (para === undefined || c.para === para)).map(c => c.id));
  return rows.filter(c => c.parent_id ? tops.has(c.parent_id) : tops.has(c.id));
};

/* ---------- reactions: a reply that is only emoji ---------- */
export const REACT_RE = /^(?:\p{Extended_Pictographic}|\p{Emoji_Modifier}|\uFE0F|\u200D|\u20E3)+$/u;
export const isReaction = c => !!c.parent_id && c.body.length <= 16 && REACT_RE.test(c.body.trim());
export const EMOJIS = ["👍", "❤️", "👌", "✅", "🎉", "👀", "🙏", "😄"];

export const visible = () => {
  const rows = S.all || [];
  const tops = new Set(rows.filter(c => !c.parent_id).map(c => c.id));
  return rows.filter(c => !c.parent_id || tops.has(c.parent_id));
};
// a comment is "new" if it arrived after the last visit and was not written by this browser's author name
export const isNew = c => ts(c.created_at) > S.seenAt && c.author !== store.get("phiz-rfc-author");
