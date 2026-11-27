/* The deck plan of "Describe the material" (docs/spec/v2/redesign.md, What PR 3 delivers). The Edge Function plan-deck answers with a plan written by
   a model; this file keeps only what can be traced to an active theme, before anything is shown or exported. Pure and import-free, so Node tests it
   (tests/test_deck_plan.py). Nothing here writes a sentence: it only drops, trims and counts. */
export type PlanItem = { theme: string; text: string };
export type PlanSlide =
  | { kind: "cover"; title: string; subtitle: string }
  | { kind: "numbers"; title: string; themes: string[] }
  | { kind: "decisions"; title: string; items: PlanItem[] }
  | { kind: "theme"; theme: string }
  | { kind: "roadmap"; title: string; themes: string[] }
  | { kind: "dates"; title: string; items: PlanItem[] };
export type Plan = { title: string; slides: PlanSlide[] };
export type Cleaned = { plan: Plan; dropped: number };

export const PLAN_KINDS = ["cover", "numbers", "decisions", "theme", "roadmap", "dates"] as const;
export const MAX_SLIDES = 30;
const TITLE_MAX = 120, ITEM_MAX = 280, LIST_MAX = 40;

const str = (v: unknown, max: number) => (typeof v === "string" ? v.replace(/\s+/g, " ").trim().slice(0, max).trim() : "");
const arr = (v: unknown): unknown[] => (Array.isArray(v) ? v : []);
const idOf = (v: unknown) => str(v, 20).toUpperCase();

/* Keeps the slides that can be traced to the active themes (`known`); counts the sentences dropped for having no known theme. */
export function cleanPlan(raw: unknown, known: Iterable<string>): Cleaned {
  const ids = new Set(known);
  const r = (raw && typeof raw === "object" ? raw : {}) as Record<string, unknown>;
  let dropped = 0;
  const themes = (v: unknown) => [...new Set(arr(v).map(idOf).filter(x => ids.has(x)))].slice(0, LIST_MAX);
  const items = (v: unknown) => {
    const out: PlanItem[] = [];
    for (const it of arr(v)) {
      const o = (it && typeof it === "object" ? it : {}) as Record<string, unknown>;
      const theme = idOf(o.theme), text = str(o.text, ITEM_MAX);
      if (!text) continue;
      if (!ids.has(theme)) { dropped++; continue; }
      out.push({ theme, text });
    }
    return out.slice(0, LIST_MAX);
  };
  const slides: PlanSlide[] = [];
  for (const s of arr(r.slides)) {
    if (slides.length >= MAX_SLIDES) break;
    const o = (s && typeof s === "object" ? s : {}) as Record<string, unknown>;
    const title = str(o.title, TITLE_MAX);
    switch (o.kind) {
      case "cover": slides.push({ kind: "cover", title: title || str(r.title, TITLE_MAX), subtitle: str(o.subtitle, TITLE_MAX) }); break;
      case "numbers": case "roadmap": { const t = themes(o.themes); if (t.length) slides.push({ kind: o.kind as "numbers" | "roadmap", title, themes: t }); break; }
      case "decisions": case "dates": { const i = items(o.items); if (i.length) slides.push({ kind: o.kind as "decisions" | "dates", title, items: i }); break; }
      case "theme": { const t = idOf(o.theme); if (ids.has(t)) slides.push({ kind: "theme", theme: t }); break; }
      default: break;
    }
  }
  return { plan: { title: str(r.title, TITLE_MAX), slides }, dropped };
}

/* Every theme the plan needs from the database, in the order they first appear. */
export function planThemeIds(plan: Plan): string[] {
  const out: string[] = [];
  const add = (id: string) => { if (!out.includes(id)) out.push(id); };
  for (const s of plan.slides) {
    if (s.kind === "theme") add(s.theme);
    else if (s.kind === "numbers" || s.kind === "roadmap") s.themes.forEach(add);
    else if (s.kind === "decisions" || s.kind === "dates") s.items.forEach(i => add(i.theme));
  }
  return out;
}
