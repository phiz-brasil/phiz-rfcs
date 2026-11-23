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
| Order | Move the platform first (same behavior), then the new features, and access control last (phase 2 after phase 9). One change at a time. |
| Levels | Three fixed levels: **Front → Theme → Execution item**. Themes are `project` or standalone `task`; themes link across fronts by dependencies and tags. |
| Fronts | POP, API Platform, Mini-Apps, Payments, Product Center, then Outros (permanent, last). Fronts and the front of each theme are editable. Existing RFCs: PHZ-0001 and 0005 API Platform; 0002, 0003, 0006, 0007 Payments; 0004 POP; 0008 Mini-Apps. |
| Flow | **Project themes** move through the ten V4 stages; their execution items use a simple project kanban (todo, doing, blocked, done). |
| Board | One board for now, the **BU B2B** board, with configurable columns; every column maps to one V4 stage. |
| Gates | A checklist that warns: a card can move with gates open; open gates stay visible. |
| Executive statuses | not started, on track, at risk, blocked, paused, done, cancelled (confirmed). |
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
| 1 | Next.js app on Vercel with the same pages and behavior; GitHub Pages turned off (no redirect) | new address only |
| 2 | Access only for `@phiz.com` (e-mail sign-in link first, Microsoft later), database closed to anonymous access | sign-in |
| 3 | Fronts, themes, execution items, dependencies and tags, Jira links; the RFCs and repository drafts become themes; seed of Outros; content translation | theme pages, front lists |
| 4 | Weekly updates, blockers and decisions, executive view, reader mode | the panel |
| 5 | The B2B board (V4 stages, configurable columns, gate checklists) and the project kanban | kanban |
| 6 | Roadmap from the themes' dates and milestones | roadmap |
| 7 | Metrics: lead, delivery and cycle time, CFD, throughput, WIP, aging | metrics page |
| 8 | Attachments hub (any kind of file, notes, links); the frozen archive of PHZ-0001 and PHZ-0002 moves in as attachments | attachments tab |
| 9 | Slide export (one or many themes) and AI suggestions for the three answers | slides |
| 10 | **Supabase quota** (see below): find what exceeded the free plan and fix it (cleanup, a paid plan, or moving what is heavy) | none |

Phase 1 changes no behavior on purpose: it is the riskiest move (new runtime, new host) and the compatibility suite is what proves it.

**Order of work (decision of 2026-11-23):** 1, 3, 4, 5, 6, 7, 8, 9, and **phase 2 last**, after every feature is in. Until then the site
and its data stay readable by anyone with the address (as they are today), including the weekly status of the projects once phase 4 is
in; nothing secret goes into the panel meanwhile.

**Last item, phase 10: the Supabase quota** (decision of 2026-11-23). The dashboard of the Supabase project (free plan) shows: *"Organization
exceeded its quota in the previous billing cycle. Projects will be restricted from 12 Dec, 2026 if your organization remains over quota."* It is
put last by choice, but it has a date: if the project is restricted on 2026-12-12 the whole site stops reading the database, so the work has to
start before then, whatever phase the plan is in. What to do: open **Review usage** in the Supabase dashboard, find the limit that was
exceeded (the likely ones: database size, because of the pictures stored as base64 in `rfc_assets` (about 27 MB for PHZ-0001 alone) and
`rfc_asset_staging`; egress, because every page of an RFC downloads its pictures from the API; Edge Function invocations; monthly active
users do not apply yet), then choose: clean up (delete expired rows of `rfc_asset_staging`, old `rfc_live_actions`), move the pictures to
Storage with signed URLs (phase 8 does it for attachments), or move the organization to a paid plan.

## Progress

- **Phase 0, 1**: done (specs; Next.js app on Vercel, old site off).
- **Phase 3, first slice (this branch)**: fronts, themes (project or task), execution items on a four-column kanban, dependencies between themes,
  tags, Jira links, the event log, the front of a theme and the fronts themselves editable, the published RFCs and the seven themes of Outros
  seeded, `/themes/` and `/themes/PHZ-NNNN/` in three languages. - **Phase 3, second part (this branch)**: automatic translation of theme texts (Edge Function + webhook on `themes`; person-typed text is never
  overwritten; machine translations are marked), the RFC page shows its theme's status and stage instead of the old status picker (RFCs
  without a theme keep it), and a new RFC created on `/nova/` is also created as a theme in the front chosen there (Outros by default).
  Left: the repository draft `rfcs/checkout-global` is the source of PHZ-0006 (already a theme in Payments) and is newer than the published
  version: publishing it as version 1.2 and removing the folder is waiting for a go-ahead.

## Pending

1. **(9) Slide model.** The visual model is a Google Slides deck that needs a sign-in to open. Export it (File → Download → PowerPoint or PDF)
   and add the file to the review, or share it with view access for anyone with the link.
2. **(2, last phase) Microsoft sign-in.** Needs the administrator of the company's Microsoft tenant; until then, sign-in by e-mail link to `@phiz.com`.
