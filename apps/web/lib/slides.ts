/* Builds the .pptx in the browser (pptxgenjs is loaded only when someone exports): one slide per theme. The look is neutral until the company's slide
   template is received (docs/spec/v2/README.md, open question); only this file knows about the look. */
import type { Slide } from "./slide-model";

export async function buildPptx(slides: Slide[], lang: "pt" | "en" | "zh", fileName: string): Promise<void> {
  const { default: Pptx } = await import("pptxgenjs");
  const pptx = new Pptx();
  pptx.layout = "LAYOUT_WIDE";                                   // 13.33 x 7.5 in
  const font = lang === "zh" ? "Microsoft YaHei" : "Calibri";
  const ink = "1C1A18", muted = "6B645D", accent = "12803D";
  for (const s of slides) {
    const slide = pptx.addSlide();
    slide.background = { color: "FFFFFF" };
    slide.addText(s.title, { x: 0.6, y: 0.35, w: 12.1, h: 0.8, fontFace: font, fontSize: 28, bold: true, color: ink, valign: "top", fit: "shrink" });
    slide.addText(s.meta.map((m, i) => ({ text: `${m.label}: ${m.value}${i < s.meta.length - 1 ? "     " : ""}`, options: { color: muted } })),
      { x: 0.6, y: 1.15, w: 12.1, h: 0.4, fontFace: font, fontSize: 13 });
    if (s.jira.length) {
      slide.addText(s.jira.map((j, i) => ({ text: `${j.key}${i < s.jira.length - 1 ? "   " : ""}`, options: { hyperlink: { url: j.url, tooltip: j.url }, color: accent } })),
        { x: 0.6, y: 1.5, w: 12.1, h: 0.35, fontFace: font, fontSize: 12 });
    }
    s.answers.forEach((a, i) => {
      const y = 2.05 + i * 1.7;
      slide.addText(a.question, { x: 0.6, y, w: 12.1, h: 0.35, fontFace: font, fontSize: 14, bold: true, color: accent });
      slide.addText(a.text, { x: 0.6, y: y + 0.38, w: 12.1, h: 1.0, fontFace: font, fontSize: 15, color: a.missing ? muted : ink, italic: a.missing, valign: "top", fit: "shrink" });
      if (a.note) slide.addText(a.note, { x: 0.6, y: y + 1.35, w: 12.1, h: 0.25, fontFace: font, fontSize: 10, color: muted, italic: true });
    });
    slide.addText(s.footer, { x: 0.6, y: 7.05, w: 6, h: 0.3, fontFace: font, fontSize: 10, color: muted });
  }
  await pptx.writeFile({ fileName });
}
