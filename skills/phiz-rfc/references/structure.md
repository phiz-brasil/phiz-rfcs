# RFC structure

The template ships 10 sections. Keep the order; add, split or drop sections when the topic needs it (PHZ-0002 has 15: inventory, mapping, two flow sections, gaps, breaking changes). Ids are short English slugs (`summary`, `context`…) and must be identical in the three languages.

| # | id | PT / EN / 中文 | What goes in it |
|---|---|---|---|
| hero | — | — | Generated, not written: the title, a one-sentence summary as the lede (what changes, for whom, how it is rolled out), and a list with status, author, collaborators, date, reviewers and systems. It comes from the metadata of the file (`title_*`, `summary_*`, `systems` in the single-file RFC; `rfc.json` for repository RFCs). Write the summary sentence with care: it is the first thing reviewers read. |
| 01 | `summary` | Resumo / Summary / 摘要 | The problem in one sentence, then the proposal as 3–5 bold-led bullets. What the RFC does *not* solve, with a link to open questions. Optional stats row with 3–4 numbers that size the problem. |
| 02 | `context` | Contexto: como funciona hoje / Context: how it works today / 背景：当前的工作方式 | How it works today, from the code: a flowchart of the systems involved, a numbered "how an operation flows" list citing classes, and a `note-box decision` linking context to proposal. |
| 03 | `goals` | Objetivos e fora de escopo / Goals and non-goals / 目标与非目标 | Verifiable goals; explicit non-goals. |
| 04 | `proposal` | Proposta / Proposal / 方案 | The design. "Today → with this RFC" table, per-repository changes table, a cutover/rollback diagram when relevant, credential or data decisions in `note-box decision`. |
| 05 | `flows` | Fluxos / Flows / 流程 | Sequence diagrams for the 1–2 flows that change most, plus state diagrams for lifecycles. Point out steps that move to another system (e.g. into the browser). |
| 06 | `changes` | Mudanças e compatibilidade / Changes and compatibility / 变更与兼容性 | Breaking changes: Change, Today, After, What to do. Units, identifiers, time windows, auth, status labels are the usual suspects. For migrations add a route-by-route mapping table (see components.md) and a "gaps" table for things with no equivalent. |
| 07 | `rollout` | Plano de implantação / Rollout plan / 实施计划 | Phase cards (Phase 0 = preparation/inventory). Then "in every phase": contract tests, pilot, metrics to watch, batch rollout. Dates only after Phase 0. |
| 08 | `risks` | Riscos / Risks / 风险 | Risk → mitigation table. |
| 09 | `questions` | Perguntas em aberto / Open questions / 待定问题 | Numbered, bold topic first, addressed to someone ("para a CredPay", "para Produto"). Everything inferred but not confirmed ends here. |
| 10 | `refs` | Referências / References / 参考资料 | Files, classes, docs consulted. Note docs that need login. |

## Tone

- Write for a reviewer who has not seen the investigation and may read in a second language.
- Lead with the decision; explain mechanisms after.
- Prefer tables over long paragraphs for comparisons. Keep each table to one idea.
- Name the evidence: "em `RoadRouteServiceImpl.getRouteByTranPayAcct`" beats "o sistema escolhe a rota".
- Mark uncertainty explicitly ("a confirmar", "não consultado") instead of smoothing it over.
- Portuguese is the reference language; translations follow it, not the other way round.

## rfc.json (repository RFCs only)

RFCs created on the site have no rfc.json: their metadata is the block at the top of `RFC.md` and the upload form.

```json
{
  "id": "PHZ-0003",
  "title": { "pt": "…", "en": "…", "zh": "…" },
  "summary": { "pt": "Uma frase.", "en": "One sentence.", "zh": "一句话。" },
  "status": "draft",
  "authors": ["Gleison"],
  "reviewers": ["Pedro Bettani", "Luciana Geromel", "Richard Liang", "Henry Wu"],
  "systems": ["channel", "card-vault"],
  "version": "1.0",
  "changelog": [
    { "version": "1.0", "date": "2026-10-16", "note": { "pt": "Primeira versão.", "en": "First version.", "zh": "首个版本。" } }
  ],
  "created": "2026-10-16",
  "updated": "2026-10-16"
}
```

`systems` is optional. `version` and `changelog` are managed by `tools/new_version.py`. In Markdown RFCs the header of the page (eyebrow, title, lede, status pill, authors, date, reviewers, systems) comes from this file.

Bump `updated` when content changes meaningfully.
