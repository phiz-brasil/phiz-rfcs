/* Builds the .pptx in the browser (pptxgenjs is loaded only when someone exports). The look is our own model, based on the design of the company's B2B deck
   (docs/spec/v2/slides.md): deep green, off-white and one bright-green surface, a small label on top, rounded cards. Only this file knows about the look;
   every colour is in the table of the spec (tests/test_slides.py reads this file and checks it). */
import { summaryOf, type Lang, type Slide } from "./slide-model";
import type { Plan } from "./deck-plan";

type Deck = InstanceType<typeof import("pptxgenjs").default>;
type PSlide = ReturnType<Deck["addSlide"]>;
type Mark = (slide: PSlide, text: string, color?: string) => unknown;

const DARK = "07301F", DEEP = "0E4A2D", BRIGHT = "1DB954", ACTION = "15803D", PAPER = "F2F7F3", INK = "0B2A1A", MUTED = "5F6F66", ORANGE = "F59E3F";
const WARN_BG = "FDEBDD", WARN_INK = "8A3B12", LINE = "CFE0D5";
const STATUS_DOT: Record<string, string> = { on_track: BRIGHT, done: ACTION, at_risk: ORANGE, blocked: WARN_INK, not_started: MUTED, paused: MUTED, cancelled: MUTED };
const ROWS_PER_SLIDE = 10;

export type DeckOptions = { deck?: boolean; date?: string; output?: "file" | "blob" };

export async function buildPptx(slides: Slide[], lang: Lang, fileName: string, opts: DeckOptions = {}): Promise<Blob | void> {
  const { default: Pptx } = await import("pptxgenjs");
  const pptx = new Pptx();
  pptx.layout = "LAYOUT_WIDE";                                   // 13.33 x 7.5 in
  const font = lang === "zh" ? "Microsoft YaHei" : "Calibri";
  const date = opts.date ?? new Date().toISOString().slice(0, 10);
  const S = summaryOf(slides, lang);
  const L = S.labels;
  const label = (slide: ReturnType<typeof pptx.addSlide>, text: string, color = ACTION) =>
    slide.addText(text, { x: 0.6, y: 0.3, w: 12.1, h: 0.3, fontFace: font, fontSize: 10, bold: true, color });
  const footer = (slide: ReturnType<typeof pptx.addSlide>, text: string, color = MUTED) =>
    slide.addText(text, { x: 0.6, y: 7.05, w: 12.1, h: 0.3, fontFace: font, fontSize: 10, color });

  if (opts.deck) {
    // cover: the dark surface, the label with the date, the title, and the ring of the product reduced to concentric circles
    const cover = pptx.addSlide();
    cover.background = { color: DARK };
    cover.addShape(pptx.ShapeType.ellipse, { x: 7.3, y: 0.95, w: 5.6, h: 5.6, fill: { color: DEEP } });
    cover.addShape(pptx.ShapeType.ellipse, { x: 8.1, y: 1.75, w: 4.0, h: 4.0, fill: { color: DARK } });
    cover.addShape(pptx.ShapeType.ellipse, { x: 8.8, y: 2.45, w: 2.6, h: 2.6, fill: { color: BRIGHT } });
    cover.addText("P", { shape: pptx.ShapeType.roundRect, x: 0.7, y: 0.7, w: 0.6, h: 0.6, fill: { color: BRIGHT }, color: DARK, bold: true, fontSize: 20, fontFace: font, align: "center", valign: "middle", rectRadius: 0.12 });
    cover.addText(`${L.cover} · ${date}`, { x: 0.7, y: 2.2, w: 6.2, h: 0.35, fontFace: font, fontSize: 12, bold: true, color: BRIGHT, charSpacing: 2 });
    cover.addText(L.coverTitle, { x: 0.7, y: 2.6, w: 6.4, h: 1.8, fontFace: font, fontSize: 44, bold: true, color: "FFFFFF", valign: "top", fit: "shrink" });
    cover.addText(`${S.total} ${L.themes}`, { x: 0.7, y: 4.6, w: 6.2, h: 0.5, fontFace: font, fontSize: 18, color: "FFFFFF" });
    cover.addText(`${L.asOf} ${date}`, { x: 0.7, y: 6.6, w: 6.2, h: 0.3, fontFace: font, fontSize: 10, color: BRIGHT });

    // overview: a table with a dark header and one coloured dot per status (ten rows per slide)
    for (let from = 0; from < Math.max(S.rows.length, 1); from += ROWS_PER_SLIDE) {
      const ov = pptx.addSlide();
      ov.background = { color: PAPER };
      label(ov, `${L.cover} · ${L.overview}`);
      ov.addText(L.overview, { x: 0.6, y: 0.65, w: 12.1, h: 0.7, fontFace: font, fontSize: 28, bold: true, color: INK });
      const head = [L.theme, L.front, L.status, L.due, L.answers].map(t => ({ text: t, options: { bold: true, color: "FFFFFF", fill: { color: DARK }, fontFace: font, fontSize: 11 } }));
      const body = S.rows.slice(from, from + ROWS_PER_SLIDE).map(r => [
        { text: `${r.id} · ${r.title}`, options: { color: INK, bold: true } },
        { text: r.front, options: { color: INK } },
        { text: [{ text: "● ", options: { color: STATUS_DOT[r.status] ?? MUTED } }, { text: r.statusLabel, options: { color: INK } }] as never, options: {} },
        { text: r.due, options: { color: INK } },
        { text: r.answers, options: { color: INK, align: "center" as const } },
      ].map(c => ({ ...c, options: { fontFace: font, fontSize: 11, fill: { color: "FFFFFF" }, border: { type: "solid" as const, color: LINE, pt: 0.75 }, ...c.options } })));
      ov.addTable([head, ...body] as never, { x: 0.6, y: 1.6, w: 12.1, colW: [5.2, 2.0, 2.0, 1.7, 1.2], rowH: 0.42, valign: "middle" });
      footer(ov, `${L.asOf} ${date}`);
    }

    // the number: the one surface in bright green
    const num = pptx.addSlide();
    num.background = { color: BRIGHT };
    label(num, `${L.cover} · ${date}`, DARK);
    num.addText(String(S.total), { x: 0.6, y: 1.2, w: 5.6, h: 3.0, fontFace: font, fontSize: 150, bold: true, color: DARK, valign: "middle" });
    num.addText(L.themes, { x: 6.3, y: 2.2, w: 6.4, h: 1.0, fontFace: font, fontSize: 36, bold: true, color: DARK, valign: "middle" });
    num.addText(`${S.risky} ${L.risky}`, { x: 6.3, y: 3.3, w: 6.4, h: 0.7, fontFace: font, fontSize: 20, color: DARK, valign: "top" });
    S.byStatus.slice(0, 4).forEach((b, i) => {
      const x = 0.6 + i * 3.1;
      num.addShape(pptx.ShapeType.line, { x, y: 5.3, w: 2.8, h: 0, line: { color: DARK, width: 1 } });
      num.addText(`${b.count}`, { x, y: 5.4, w: 2.8, h: 0.7, fontFace: font, fontSize: 30, bold: true, color: DARK });
      num.addText(b.label, { x, y: 6.1, w: 2.8, h: 0.4, fontFace: font, fontSize: 12, color: DARK });
    });
  }

  // a theme: the label, the title, the three questions as three cards (problem dark, solution white, success bright), the meta as pills, the Jira links
  for (const s of slides) themeSlide(pptx, s, font, label, footer);

  if (opts.deck) {
    // what is missing: the answers still not explained or not confirmed, in the soft orange box
    const gap = pptx.addSlide();
    gap.background = { color: PAPER };
    label(gap, `${L.cover} · ${date}`);
    gap.addText(L.gaps, { x: 0.6, y: 0.65, w: 12.1, h: 0.7, fontFace: font, fontSize: 28, bold: true, color: INK });
    const lines = S.gaps.length
      ? S.gaps.map(g => `${g.id} · ${g.title}: ${[...g.missing.map(m => `${m} (${L.missing})`), ...g.unconfirmed.map(m => `${m} (${L.unconfirmed})`)].join("; ")}`)
      : [L.gapsNone];
    gap.addShape(pptx.ShapeType.roundRect, { x: 0.6, y: 1.6, w: 12.1, h: 5.1, fill: { color: S.gaps.length ? WARN_BG : "FFFFFF" }, line: { color: LINE, width: 1 }, rectRadius: 0.12 });
    gap.addText(lines.map(t => ({ text: t, options: { breakLine: true, bullet: S.gaps.length ? true : false } })),
      { x: 0.9, y: 1.85, w: 11.5, h: 4.6, fontFace: font, fontSize: 15, color: S.gaps.length ? WARN_INK : INK, valign: "top", paraSpaceAfter: 6, fit: "shrink" });
    footer(gap, `${L.asOf} ${date}`);
  }
  if (opts.output === "blob") return (await pptx.write({ outputType: "blob" })) as Blob;
  await pptx.writeFile({ fileName });
}

/* A theme: the label, the title, the three questions as three cards (problem dark, solution white, success bright), the meta as pills, the Jira links */
function themeSlide(pptx: Deck, s: Slide, font: string, label: Mark, footer: Mark) {
  const slide = pptx.addSlide();
  slide.background = { color: PAPER };
  label(slide, `${s.front} · ${s.id}`);
  slide.addText(s.title, { x: 0.6, y: 0.65, w: 12.1, h: 0.9, fontFace: font, fontSize: 28, bold: true, color: INK, valign: "top", fit: "shrink" });
  s.answers.forEach((a, i) => {
    const x = 0.6 + i * 4.15, y = 1.75, w = 3.95, h = 3.95;
    const warn = a.missing;
    const fill = warn ? WARN_BG : i === 0 ? DARK : i === 2 ? BRIGHT : "FFFFFF";
    const qColor = warn ? WARN_INK : i === 0 ? ORANGE : i === 2 ? DARK : ACTION;
    const tColor = warn ? WARN_INK : i === 0 ? "FFFFFF" : INK;
    slide.addShape(pptx.ShapeType.roundRect, { x, y, w, h, fill: { color: fill }, line: { color: warn || i === 1 ? LINE : fill, width: 1 }, rectRadius: 0.12 });
    slide.addText(a.question, { x: x + 0.25, y: y + 0.2, w: w - 0.5, h: 0.9, fontFace: font, fontSize: 12, bold: true, color: qColor, valign: "top", fit: "shrink" });
    slide.addText(a.text, { x: x + 0.25, y: y + 1.1, w: w - 0.5, h: h - 1.9, fontFace: font, fontSize: 15, color: tColor, italic: warn, valign: "top", fit: "shrink" });
    if (a.note) slide.addText(a.note, { x: x + 0.25, y: y + h - 0.65, w: w - 0.5, h: 0.45, fontFace: font, fontSize: 10, italic: true, color: i === 0 ? ORANGE : WARN_INK, valign: "bottom" });
  });
  s.meta.forEach((m, i) => {
    slide.addText(`${m.label}: ${m.value}`, { shape: pptx.ShapeType.roundRect, x: 0.6 + i * 3.1, y: 5.95, w: 2.95, h: 0.45, fontFace: font, fontSize: 11, color: INK, fill: { color: "FFFFFF" }, line: { color: LINE, width: 1 }, rectRadius: 0.2, align: "center", valign: "middle", fit: "shrink" });
  });
  if (s.jira.length) {
    slide.addText(s.jira.map((j, i) => ({ text: `${j.key}${i < s.jira.length - 1 ? "   " : ""}`, options: { hyperlink: { url: j.url, tooltip: j.url }, color: ACTION } })),
      { x: 0.6, y: 6.55, w: 12.1, h: 0.35, fontFace: font, fontSize: 12 });
  }
  footer(slide, s.footer);
}

/* -- "Describe the material" (docs/spec/v2/redesign.md, What PR 3 delivers): a cleaned deck plan drawn with the same look. The theme slides and the
   numbers come from the database (`slides`, built by slideOf); the model only chose the themes and wrote the titles and the short sentences. */
export type PlanData = { slides: Map<string, Slide>; starts: Map<string, string> };

export async function buildPlanPptx(plan: Plan, data: PlanData, lang: Lang, fileName: string, opts: Omit<DeckOptions, "deck"> = {}): Promise<Blob | void> {
  const { default: Pptx } = await import("pptxgenjs");
  const pptx = new Pptx();
  pptx.layout = "LAYOUT_WIDE";
  const font = lang === "zh" ? "Microsoft YaHei" : "Calibri";
  const date = opts.date ?? new Date().toISOString().slice(0, 10);
  const L = summaryOf([], lang).labels;
  const label = (slide: ReturnType<typeof pptx.addSlide>, text: string, color = ACTION) =>
    slide.addText(text, { x: 0.6, y: 0.3, w: 12.1, h: 0.3, fontFace: font, fontSize: 10, bold: true, color });
  const footer = (slide: ReturnType<typeof pptx.addSlide>, text: string, color = MUTED) =>
    slide.addText(text, { x: 0.6, y: 7.05, w: 12.1, h: 0.3, fontFace: font, fontSize: 10, color });
  const of = (ids: string[]) => ids.map(id => data.slides.get(id)).filter((s): s is Slide => !!s);
  const head = (slide: ReturnType<typeof pptx.addSlide>, kicker: string, title: string) => {
    slide.background = { color: PAPER };
    label(slide, `${kicker} · ${date}`);
    slide.addText(title, { x: 0.6, y: 0.65, w: 12.1, h: 0.8, fontFace: font, fontSize: 28, bold: true, color: INK, valign: "top", fit: "shrink" });
  };

  for (const p of plan.slides) {
    if (p.kind === "cover") {
      const cover = pptx.addSlide();
      cover.background = { color: DARK };
      cover.addShape(pptx.ShapeType.ellipse, { x: 7.3, y: 0.95, w: 5.6, h: 5.6, fill: { color: DEEP } });
      cover.addShape(pptx.ShapeType.ellipse, { x: 8.1, y: 1.75, w: 4.0, h: 4.0, fill: { color: DARK } });
      cover.addShape(pptx.ShapeType.ellipse, { x: 8.8, y: 2.45, w: 2.6, h: 2.6, fill: { color: BRIGHT } });
      cover.addText("P", { shape: pptx.ShapeType.roundRect, x: 0.7, y: 0.7, w: 0.6, h: 0.6, fill: { color: BRIGHT }, color: DARK, bold: true, fontSize: 20, fontFace: font, align: "center", valign: "middle", rectRadius: 0.12 });
      cover.addText(`${L.cover} · ${date}`, { x: 0.7, y: 2.2, w: 6.2, h: 0.35, fontFace: font, fontSize: 12, bold: true, color: BRIGHT, charSpacing: 2 });
      cover.addText(p.title || plan.title || L.coverTitle, { x: 0.7, y: 2.6, w: 6.4, h: 1.8, fontFace: font, fontSize: 40, bold: true, color: "FFFFFF", valign: "top", fit: "shrink" });
      if (p.subtitle) cover.addText(p.subtitle, { x: 0.7, y: 4.6, w: 6.2, h: 0.9, fontFace: font, fontSize: 18, color: "FFFFFF", valign: "top", fit: "shrink" });
      cover.addText(`${L.asOf} ${date}`, { x: 0.7, y: 6.6, w: 6.2, h: 0.3, fontFace: font, fontSize: 10, color: BRIGHT });
    } else if (p.kind === "numbers") {
      const S = summaryOf(of(p.themes), lang);
      const num = pptx.addSlide();
      num.background = { color: BRIGHT };
      label(num, `${p.title || L.numbers} · ${date}`, DARK);
      num.addText(String(S.total), { x: 0.6, y: 1.2, w: 5.6, h: 3.0, fontFace: font, fontSize: 150, bold: true, color: DARK, valign: "middle" });
      num.addText(L.themes, { x: 6.3, y: 2.2, w: 6.4, h: 1.0, fontFace: font, fontSize: 36, bold: true, color: DARK, valign: "middle" });
      num.addText(`${S.risky} ${L.risky}`, { x: 6.3, y: 3.3, w: 6.4, h: 0.7, fontFace: font, fontSize: 20, color: DARK, valign: "top" });
      S.byStatus.slice(0, 4).forEach((b, i) => {
        const x = 0.6 + i * 3.1;
        num.addShape(pptx.ShapeType.line, { x, y: 5.3, w: 2.8, h: 0, line: { color: DARK, width: 1 } });
        num.addText(`${b.count}`, { x, y: 5.4, w: 2.8, h: 0.7, fontFace: font, fontSize: 30, bold: true, color: DARK });
        num.addText(b.label, { x, y: 6.1, w: 2.8, h: 0.4, fontFace: font, fontSize: 12, color: DARK });
      });
    } else if (p.kind === "decisions" || p.kind === "dates") {
      const slide = pptx.addSlide();
      const warn = p.kind === "decisions";
      head(slide, warn ? L.decisions : L.dates, p.title || (warn ? L.decisions : L.dates));
      const lines = p.items.map(i => `${data.slides.get(i.theme)?.title ?? i.theme}: ${i.text}`);
      slide.addShape(pptx.ShapeType.roundRect, { x: 0.6, y: 1.6, w: 12.1, h: 5.1, fill: { color: warn ? WARN_BG : "FFFFFF" }, line: { color: LINE, width: 1 }, rectRadius: 0.12 });
      slide.addText(lines.map(t => ({ text: t, options: { breakLine: true, bullet: true } })),
        { x: 0.9, y: 1.85, w: 11.5, h: 4.6, fontFace: font, fontSize: 16, color: warn ? WARN_INK : INK, valign: "top", paraSpaceAfter: 8, fit: "shrink" });
      footer(slide, `${L.asOf} ${date}`);
    } else if (p.kind === "roadmap") {
      const rows = of(p.themes).sort((a, b) => (a.due === "—" ? "9" : a.due).localeCompare(b.due === "—" ? "9" : b.due));
      for (let from = 0; from < rows.length; from += ROWS_PER_SLIDE) {
        const slide = pptx.addSlide();
        head(slide, L.roadmap, p.title || L.roadmap);
        const cols = [L.theme, L.front, L.status, L.start, L.due].map(t => ({ text: t, options: { bold: true, color: "FFFFFF", fill: { color: DARK }, fontFace: font, fontSize: 11 } }));
        const body = rows.slice(from, from + ROWS_PER_SLIDE).map(s => [
          { text: `${s.id} · ${s.title}`, options: { color: INK, bold: true } },
          { text: s.front, options: { color: INK } },
          { text: [{ text: "● ", options: { color: STATUS_DOT[s.status] ?? MUTED } }, { text: s.meta[2]?.value ?? s.status, options: { color: INK } }] as never, options: {} },
          { text: data.starts.get(s.id) || "—", options: { color: INK } },
          { text: s.due, options: { color: INK } },
        ].map(c => ({ ...c, options: { fontFace: font, fontSize: 11, fill: { color: "FFFFFF" }, border: { type: "solid" as const, color: LINE, pt: 0.75 }, ...c.options } })));
        slide.addTable([cols, ...body] as never, { x: 0.6, y: 1.6, w: 12.1, colW: [5.2, 2.0, 2.0, 1.45, 1.45], rowH: 0.42, valign: "middle" });
        footer(slide, `${L.asOf} ${date}`);
      }
    } else if (p.kind === "theme") {
      const s = data.slides.get(p.theme);
      if (s) themeSlide(pptx, s, font, label, footer);
    }
  }
  if (opts.output === "blob") return (await pptx.write({ outputType: "blob" })) as Blob;
  await pptx.writeFile({ fileName });
}
