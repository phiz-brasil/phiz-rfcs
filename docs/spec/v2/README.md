# Spec v2: from an RFC site to a delivery tracker

Status: **draft for review** (phase 0). Nothing here is built yet. Each file is a spec in the SDD sense: what the system must do and
how we will know it does, written before the code. A phase starts only after its spec is reviewed; the code of a phase is done when
the acceptance tests the spec lists pass, together with the compatibility suite (`compatibility.md`).

## Why

The site started as a place to write and discuss RFCs. Teams now need it to follow work day to day: a kanban board on the flow of
the *PhizChat Product Project Governance V4* standard (pilot draft, 2026-11-20), flow metrics, a hierarchy of items, links to the
company Jira, all the attachments of an item in one place, an executive view that exports to slides, and access limited to the
company.

## Sources

- The first request (2026-11-23): kanban on the flow of the *PhizChat Product Project Governance V4* (pilot draft, 2026-11-20), flow metrics,
  attachments, Jira links, executive view with slides, sign-in for the company domain, Node.js, SDD.
- The request *Painel de Acompanhamento PhizChat* (2026-11-23): fronts, themes and execution items, weekly updates by PMs, blockers and
  decisions, reader mode, roadmap, slides with three questions, three languages. Where the two overlapped, the decisions below settle it.

## Decisions taken (2026-11-23)

| topic | decision |
|---|---|
| Order | Move the platform first (same behavior), then access control, then the new features. One change at a time. |
| Levels | Three fixed levels: **Front → Theme → Execution item**. Themes are `project` or standalone `task`; themes link across fronts by dependencies and tags. |
| Fronts | POP, API Platform, Mini-Apps, Payments, Product Center, then Outros (permanent, last). |
| Flow | **Project themes** move through the ten V4 stages; their execution items use a simple project kanban (todo, doing, blocked, done). |
| Board | One board for now, the **BU B2B** board, with configurable columns; every column maps to one V4 stage. |
| Gates | A checklist that warns: a card can move with gates open; open gates stay visible. |
| Metrics | Lead time (creation → done), delivery time (04 → done), cycle time (07 → done) in calendar days, plus CFD, throughput, WIP, aging; for themes and items with a filter. |
| Sentences | Two: *what it is* (stable) and *progress* (weekly), plus the three slide answers (problem, solution, success). |
| Executive view | AI suggests the slide answers from the RFC and attachments; a person confirms; a missing answer is shown as missing, never invented. |
| Languages | pt-BR, en, zh-Hans. People's texts are stored once with automatic translations (the comments' model), editable and marked as reviewed. |
| Versions | Keep the versions of the RFC document; add an attachments hub. |
| RFCs | Published RFCs become project themes; their status maps to a V4 stage and the old status picker goes away. Repository drafts move into the app. |
| Jira | Links only: paste the issue address, click to open Jira. No token, no sync, no settings. |
| Users | Only `@phiz.com`; everyone is a member (can edit); reader mode hides the controls for people who only read. Microsoft sign-in waits for a tenant administrator (see `platform.md`). |
| Hosting | Vercel (company Pro/Team account) for the app; Supabase stays as database, auth and file storage. |
| Stack | Node.js ecosystem: TypeScript, Next.js. |

## The files

| file | covers |
|---|---|
| [`platform.md`](platform.md) | Architecture, hosting, repository, access, security, how the code is organized |
| [`domain.md`](domain.md) | Fronts, themes, execution items, weekly updates, blockers and decisions, Jira links, attachments, executive summary, languages, views |
| [`flow-and-metrics.md`](flow-and-metrics.md) | Stages, routes, gates, the B2B board and the project kanban, and the exact definition of each metric |
| [`compatibility.md`](compatibility.md) | What must keep working (addresses, data, behaviors) and the tests that prove it |

## Phases

Each phase is one pull request (or a short series), reviewable and testable on its own preview deployment.

| phase | delivers | user-visible change |
|---|---|---|
| 0 | These specs; the compatibility contract | none |
| 1 | Next.js app on Vercel with the same pages and behavior; old addresses redirect; GitHub Pages retired; repository private | new address only |
| 2 | Access only for `@phiz.com` (e-mail sign-in link first, Microsoft later), database closed to anonymous access | sign-in |
| 3 | Fronts, themes, execution items, dependencies and tags, Jira links; the RFCs and repository drafts become themes; seed of Outros; content translation | theme pages, front lists |
| 4 | Weekly updates, blockers and decisions, executive view, reader mode | the panel |
| 5 | The B2B board (V4 stages, configurable columns, gate checklists) and the project kanban | kanban |
| 6 | Roadmap from the themes' dates and milestones | roadmap |
| 7 | Metrics: lead, delivery and cycle time, CFD, throughput, WIP, aging | metrics page |
| 8 | Attachments hub (any kind of file, notes, links) | attachments tab |
| 9 | Slide export (one or many themes) and AI suggestions for the three answers | slides |

Phase 1 changes no behavior on purpose: it is the riskiest move (new runtime, new host) and the compatibility suite is what proves it.
Phase 2 comes before any panel data: the weekly status of company projects should not be readable by anyone with the address.

## Pending

1. **(9) Slide model.** The visual model is a Google Slides deck that needs a sign-in to open. Export it (File → Download → PowerPoint or PDF)
   and add the file to the review, or share it with view access for anyone with the link.
2. **(3) Fronts of the existing RFCs.** Confirm the table in `domain.md` (initial themes), especially PHZ-0005 (Business Account) and PHZ-0008 (PhizClip).
3. **(4) Statuses.** Confirm the executive statuses: not started, on track, at risk, blocked, paused, done, cancelled.
4. **(2, later) Microsoft sign-in.** Needs the administrator of the company's Microsoft tenant; until then, sign-in by e-mail link to `@phiz.com`.
