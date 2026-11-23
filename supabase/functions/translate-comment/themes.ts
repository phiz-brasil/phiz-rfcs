// What to translate when a theme changes (called by the Database Webhook on public.themes). Pure: no network, no Deno, so it is tested from
// Node (tests/test_translate_plan.py).
//
// The texts of a theme (title, what_it_is, progress, problem, solution, success) are {pt, en, zh}. A language a person typed is the source
// of the other languages; a language that is empty or already a machine translation (listed in text_meta[field]) is a target, and a
// language a person typed is never overwritten. The function's own write marks its targets as machine in text_meta, so the webhook it
// triggers finds no person-typed change and does nothing.
export const FIELDS = ["title", "what_it_is", "progress", "problem", "solution", "success"] as const;
export const LANGS = ["pt", "en", "zh"] as const;
export type Lang = typeof LANGS[number];
type Texts = Partial<Record<Lang, string>>;
export type ThemeRow = Record<string, unknown> & { text_meta?: Record<string, string[]> | null };
export type Job = { field: string; src: Lang; text: string; targets: Lang[] };

const filled = (s: string | undefined) => (s ?? "").trim().length > 0;

export function translationPlan(oldRec: ThemeRow | null | undefined, rec: ThemeRow): Job[] {
  const jobs: Job[] = [];
  for (const field of FIELDS) {
    const before = ((oldRec?.[field] as Texts | undefined) ?? {});
    const now = ((rec[field] as Texts | undefined) ?? {});
    const machine = new Set<string>(rec.text_meta?.[field] ?? []);
    const changed = LANGS.filter((l) => filled(now[l]) && (now[l] ?? "") !== (before[l] ?? "") && !machine.has(l));
    if (!changed.length) continue;
    const src = changed[0];
    const targets = LANGS.filter((l) => l !== src && !changed.includes(l) && (!filled(now[l]) || machine.has(l)));
    if (targets.length) jobs.push({ field, src, text: now[src]!, targets });
  }
  return jobs;
}
