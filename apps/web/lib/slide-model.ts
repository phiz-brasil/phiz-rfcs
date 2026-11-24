/* What goes on the slide of a theme (docs/spec/v2/domain.md, Executive summary and slides): the three answers in the language chosen at export, plus title, front,
   owner, status, estimated completion and Jira links. Pure and import-free, so Node tests it (tests/test_slides.py). A missing answer is written as
   "Not explained yet: <what is missing>", never filled in. */
export type Lang = "pt" | "en" | "zh";
type Texts = Partial<Record<Lang, string>>;
export type SlideTheme = { id: string; kind: string; front: string; title: Texts; owner: string | null; status: string; due_date: string | null;
  problem: Texts; solution: Texts; success: Texts; answers?: Record<string, { state: string; missing?: string }> | null };
export type SlideJira = { theme_id: string; url: string; issue_key: string | null; label: string | null };
export type SlideFront = { key: string; name: Texts };
export type Slide = { id: string; title: string; status: string; front: string; due: string; meta: { label: string; value: string }[]; jira: { key: string; url: string }[];
  answers: { question: string; text: string; missing: boolean; unconfirmed: boolean; note: string }[]; footer: string };

export const QUESTIONS: Record<Lang, [string, string, string]> = {
  pt: ["Que problema estamos tratando com este tema?", "Qual é a solução proposta, em resumo?", "O que é sucesso para este tema e como saberemos que foi atingido?"],
  en: ["What problem are we addressing with this theme?", "What is the proposed solution, in short?", "What does success look like for this theme and how will we know it was reached?"],
  zh: ["这个主题要解决什么问题？", "拟议的解决方案是什么（简述）？", "这个主题的成功标准是什么，我们如何知道已达成？"],
};
export const LABELS: Record<Lang, Record<string, string>> = {
  pt: { front: "Frente", owner: "Responsável", status: "Status", due: "Conclusão estimada", jira: "Jira", none: "—", notExplained: "Ainda não explicado", unconfirmed: "Sugestão da IA, ainda não confirmada" },
  en: { front: "Front", owner: "Owner", status: "Status", due: "Estimated completion", jira: "Jira", none: "—", notExplained: "Not explained yet", unconfirmed: "AI suggestion, not confirmed yet" },
  zh: { front: "业务线", owner: "负责人", status: "状态", due: "预计完成", jira: "Jira", none: "—", notExplained: "尚未说明", unconfirmed: "AI 建议，尚未确认" },
};
export const STATUS: Record<Lang, Record<string, string>> = {
  pt: { not_started: "Não iniciado", on_track: "No prazo", at_risk: "Em risco", blocked: "Bloqueado", paused: "Pausado", done: "Concluído", cancelled: "Cancelado" },
  en: { not_started: "Not started", on_track: "On track", at_risk: "At risk", blocked: "Blocked", paused: "Paused", done: "Done", cancelled: "Cancelled" },
  zh: { not_started: "未开始", on_track: "按计划", at_risk: "有风险", blocked: "受阻", paused: "已暂停", done: "已完成", cancelled: "已取消" },
};

const LANGS: Lang[] = ["pt", "en", "zh"];
/* the text in the chosen language, or the first language that has one */
export function said(t: Texts | null | undefined, lang: Lang): string {
  if (t?.[lang]?.trim()) return t[lang]!.trim();
  for (const l of LANGS) if (t?.[l]?.trim()) return t[l]!.trim();
  return "";
}

export function slideOf(theme: SlideTheme, jira: SlideJira[], fronts: SlideFront[], lang: Lang): Slide {
  const L = LABELS[lang];
  const front = said(fronts.find(f => f.key === theme.front)?.name, lang) || theme.front;
  const fields = ["problem", "solution", "success"] as const;
  const answers = fields.map((f, i) => {
    const text = said(theme[f], lang);
    const a = theme.answers?.[f];
    const missing = !text;
    return {
      question: QUESTIONS[lang][i],
      text: missing ? `${L.notExplained}${a?.missing ? `${lang === "zh" ? "：" : ": "}${a.missing}` : ""}` : text,
      missing,
      unconfirmed: !missing && a?.state === "suggested",
      note: !missing && a?.state === "suggested" ? L.unconfirmed : "",
    };
  });
  return {
    id: theme.id,
    title: said(theme.title, lang) || theme.id,
    status: theme.status,
    front,
    due: theme.due_date ? theme.due_date.slice(0, 10) : L.none,
    meta: [
      { label: L.front, value: front },
      { label: L.owner, value: theme.owner || L.none },
      { label: L.status, value: STATUS[lang][theme.status] ?? theme.status },
      { label: L.due, value: theme.due_date ? theme.due_date.slice(0, 10) : L.none },
    ],
    jira: jira.filter(j => j.theme_id === theme.id).map(j => ({ key: j.issue_key || j.label || j.url, url: j.url })),
    answers,
    footer: theme.id,
  };
}

/* The words of the slides that are not a theme (cover, overview, the number, what is missing), docs/spec/v2/slides.md */
export const DECK: Record<Lang, Record<string, string>> = {
  pt: { cover: "PORTFÓLIO", coverTitle: "Acompanhamento de temas", themes: "temas", overview: "Onde estamos", risky: "em risco ou bloqueados", gaps: "O que falta",
    gapsNone: "Todas as respostas estão explicadas e confirmadas.", theme: "Tema", answers: "Respostas", asOf: "Em", problem: "problema", solution: "solução", success: "sucesso",
    missing: "não explicado", unconfirmed: "não confirmado" },
  en: { cover: "PORTFOLIO", coverTitle: "Theme tracking", themes: "themes", overview: "Where we are", risky: "at risk or blocked", gaps: "What is missing",
    gapsNone: "Every answer is explained and confirmed.", theme: "Theme", answers: "Answers", asOf: "As of", problem: "problem", solution: "solution", success: "success",
    missing: "not explained", unconfirmed: "not confirmed" },
  zh: { cover: "项目组合", coverTitle: "主题跟踪", themes: "个主题", overview: "当前进展", risky: "有风险或受阻", gaps: "还缺什么",
    gapsNone: "所有回答都已说明并确认。", theme: "主题", answers: "回答", asOf: "截至", problem: "问题", solution: "方案", success: "成功标准",
    missing: "尚未说明", unconfirmed: "尚未确认" },
};
const FIELDS = ["problem", "solution", "success"] as const;
const STATUS_ORDER = ["not_started", "on_track", "at_risk", "blocked", "paused", "done", "cancelled"];

export type Summary = {
  total: number; risky: number; byStatus: { status: string; label: string; count: number }[];
  rows: { id: string; title: string; front: string; status: string; statusLabel: string; due: string; answers: string }[];
  gaps: { id: string; title: string; missing: string[]; unconfirmed: string[] }[]; labels: Record<string, string>;
};

/* The overview, the big number and "what is missing" of a set of slides (the answers count only when they are explained AND confirmed). Pure. */
export function summaryOf(slides: Slide[], lang: Lang): Summary {
  const D = DECK[lang];
  const byStatus = STATUS_ORDER.map(k => ({ status: k, label: STATUS[lang][k], count: slides.filter(s => s.status === k).length })).filter(b => b.count > 0);
  const rows = slides.map(s => ({
    id: s.id, title: s.title, front: s.front, status: s.status, statusLabel: STATUS[lang][s.status] ?? s.status, due: s.due,
    answers: `${s.answers.filter(a => !a.missing && !a.unconfirmed).length}/${s.answers.length}`,
  }));
  const gaps = slides.map(s => ({
    id: s.id, title: s.title,
    missing: s.answers.map((a, i) => (a.missing ? D[FIELDS[i]] : "")).filter(Boolean),
    unconfirmed: s.answers.map((a, i) => (a.unconfirmed ? D[FIELDS[i]] : "")).filter(Boolean),
  })).filter(g => g.missing.length || g.unconfirmed.length);
  return { total: slides.length, risky: slides.filter(s => s.status === "at_risk" || s.status === "blocked").length, byStatus, rows, gaps, labels: { ...D, ...LABELS[lang] } };
}
