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
| Users | Only `@phizchat.com`; everyone is a member (can edit); reader mode hides the controls for people who only read. Microsoft sign-in waits for a tenant administrator (see `platform.md`). |
| Hosting | Vercel (company Pro/Team account) for the app; Supabase stays as database, auth and file storage. |
| Stack | Node.js ecosystem: TypeScript, Next.js. |

## The files

| file | covers |
|---|---|
| [`platform.md`](platform.md) | Architecture, hosting, repository, access, security, how the code is organized |
| [`domain.md`](domain.md) | Fronts, themes, execution items, weekly updates, blockers and decisions, Jira links, attachments, executive summary, languages, views |
| [`flow-and-metrics.md`](flow-and-metrics.md) | Stages, routes, gates, the B2B board and the project kanban, and the exact definition of each metric |
| [`compatibility.md`](compatibility.md) | What must keep working (addresses, data, behaviors) and the tests that prove it |
| [`guardrail.md`](guardrail.md) | The three rules of every change (spec first, tests, no regression), the checker `tools/guardrail.py`, the CI job and the hook of Claude Code, and the only way to skip a rule |
| [`redesign.md`](redesign.md) | The redesign of 2026-11-26: Painel with List and Timeline, theme page in one scroll, inline editing, deliveries with a period, urgency, PDLC B2B naming, Export by description and Google Slides (top bar unchanged, nothing removed) |

## Phases

Each phase is one pull request (or a short series), reviewable and testable on its own preview deployment.

| phase | delivers | user-visible change |
|---|---|---|
| 0 | These specs; the compatibility contract | none |
| 1 | Next.js app on Vercel with the same pages and behavior; GitHub Pages turned off (no redirect) | new address only |
| 2 | Access only for `@phizchat.com` (e-mail sign-in link first, Microsoft later), database closed to anonymous access | sign-in |
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

- **Phase 4 (this branch)**: weekly updates (the progress sentence, what moved forward, next step, status and estimate with the reason for a changed estimate;
  every update kept; a theme without an update in the current ISO week is flagged), blockers and decisions (owner or decider, deadline, *needs
  leadership*, resolved or decided with text), the executive view at `/executive/` with the leadership list on top and filters, execution items
  that can be milestones with a date, and reader mode (a switch, remembered; `?mode=reader|edit`). Translation of the new texts extends the
  same webhook to three more tables. Reader mode only hides controls: it is not a permission (there are no profiles until the sign-in phase,
  decision of 2026-11-23).

- **Phase 5 (this branch)**: the B2B board at `/board/` (migration `20261127000000_board_columns.sql`): configurable columns (each maps to one stage, several
  may map to the same one), a swimlane per front, drag or menu to move, one `move` event per move with the gates that were open, a mandatory reason
  when a move skips a stage of the route or leaves it (routes: full 01–10, bug 06–10, P0 07–10), the gate checklist on each project theme (ticked
  with an evidence; open gates warn, non-waivable ones in red), WIP limits, filters (front, tag, owner, status, blocked, aging), and the "no Jira link
  from 04" warning. The project kanban of the execution items already existed (phase 3). Column configuration is open to anyone with a name until the
  sign-in phase makes it admin-only. A `move` event is the stage change of that move (it replaces the `stage` event the theme form writes); the metrics
  phase must read both.

- **Phase 6 (this branch)**: the roadmap at `/roadmap/` (no new migration): the time axis is whole months covering every date shown and today; a theme is a bar
  (start to estimate), or a marker when it has one date; milestones are diamonds; open themes past their estimate are flagged *Overdue*; themes with
  no dates are listed under the timeline. Filters: status, front, tag, owner. Everything is read from `themes` and the milestone items.

- **Phase 7 (this branch)**: the flow metrics at `/metrics/` (no new migration), computed in the browser by the pure module `apps/web/lib/metrics.ts` from the event
  log, read page by page (Supabase returns 1000 rows a request). Definitions as in `flow-and-metrics.md`, made exact: median = middle value; 85th percentile =
  nearest rank; a stage change is a `stage` or `move` event whose stages differ; the CFD counts each UTC day at its last millisecond; business days are Mon–Fri
  in UTC (the requester's time zone is not known). A theme with part of its history never recorded is *estimated* and excluded from the time metrics by default.
  Items: lead = creation → done, cycle = first `doing` → done.

- **Phase 8, first part (this branch)**: the attachments hub (migration `20261128000000_attachments.sql`): files, notes and links, editions, stage and item ties, previews
  by signed address, HTML only as a download, a panel on each theme and `/attachments/`. Until the sign-in phase the bucket policies let the public key upload and read
  (the same openness as the rest of the data); they are tightened to authenticated users then. 

- **Phase 8, second part (this branch)**: the frozen archive moved in. Migration `20261129000000_attachments_archive.sql` lets `add_attachment` carry `archive_version`,
  `archive_date` and `archive_note`; 13 attachments were uploaded to production (PHZ-0001 v1.0–v1.6 and PHZ-0002 v1.0 as self-contained HTML with the CSS inlined, one
  ZIP with the pictures of PHZ-0001, the OpenAPI page and the three YAML files; SHA-256 checked after the upload). `apps/web/legacy/` is gone; the RFC page lists
  archived versions from the attachments; `/rfcs/<ID>/<anything>` redirects to the theme's attachments.

- **Phase 9 (this branch)**: slides and AI suggestions. Migration `20261130000000_theme_answers.sql`; Edge Function `suggest-summary` (Cloudflare Workers AI; quotations verified
  word for word against the documents, else the answer is *missing*); the Summary panel of a theme; `/slides/` exporting a .pptx in the browser (pptxgenjs, loaded on
  demand). **Not done**: the visual model of the company's slide deck (the Google Slides link was not readable; the look is neutral and lives in `apps/web/lib/slides.ts`).
  Decision taken without asking: the model is a Workers AI model because its secrets already exist for the translation; switching to another model is the
  `CF_SUGGEST_MODEL` variable, or a different `ask()` in the function.

- **Phase 10, first measure (this branch)**: `docs/spec/v2/quota.md`. The previous cycle went over **Egress**: every visit to an RFC read all of its images (base64 in `rfc_assets`, three languages): ≈ 32 MB
  for PHZ-0001. Images are now read on demand (visible language, near the viewport) and remembered by the browser; nothing is stored or migrated differently. The Storage/CDN move and a paid plan
  are the next levers if the usage page still shows more than 3 GB a month.

- **Phase 2, slice 1 (this branch)**: `docs/spec/v2/login.md`. `/login/` (e-mail link and 6-digit code, `@phizchat.com` only), the session in `localStorage`, `assets/auth.js` wrapping `fetch` so every request
  carries the token (old and React pages), the account in the menu with *Sign out*, the account name on writes, and the guard behind `auth.required` (false). Nothing changes for visitors until slices 2 (database lock,
  migration written and applied only when the owner says) and 3 (go-live). Prerequisites for the owner: custom SMTP and the Auth URL settings.

- **Phase 2, long window (this branch)**: the session ends only on an invalid refresh token (400/401/403); the token is renewed silently before it is needed and one tab at a time (Web Locks);
  a session unused for a month renews on the first request. Supabase settings for the owner are in `login.md` (no short time-box or inactivity timeout).

- **Migrations by the CI (2026-11-25)**: `docs/spec/v2/migrations.md`. Merging into `main` runs `supabase db push`; no more SQL pasted by hand. Needs the three GitHub secrets and one `baseline` run (up to `20261204000000`).

## Pending

Updated 2026-11-25 (the slide model and the Microsoft sign-in are done: `slides.md`, `login.md`).

**Development**
1. **Refuse sign-up of other domains in Supabase** (an Auth hook): today anyone can ask for a code and create an Auth user; the lock keeps them out, but the user exists. Specified in `login.md` ("Sign-up of other domains").
2. **SQL tests on a real Postgres.** The lock is checked by its structure (pglast) and a fake; running it needs a Postgres in the test environment (the owner's word for installing `pgserver`).
3. **Egress of the Supabase project.** Check on 2026-12-01 (scheduled) against the 5 GB of the plan; if it is still above ~3 GB a month, the next levers are a public Storage bucket with a long cache for the images (they are still base64 in the database) or a paid plan. Grace period until 2026-12-12 (`quota.md`).
4. **Slides: the richer layouts of the company's deck** (roadmap, comparison tables, phone screens), only if wanted.

**Decisions of the owner**
5. The draft folder `rfcs/checkout-global` (PHZ-0006): does it become an RFC of the app?
6. The list of admins (`app_admins` is empty: every member is admin).
7. The sender of the e-mails (today a personal Gmail, about 500 a day) and the address of the site (`phiz-rfcs.vercel.app`): both need the company's DNS or Vercel/Supabase/Entra settings.

**Content, not code**
8. Themes PHZ-0009 to 0015 have no RFC (their slide answers say *not explained yet*); the status and the estimated completion of every theme are empty until the weekly updates are filled.

**To watch**: the CI runs the tests with 2 workers (`guardrail.md`); if timeouts come back, go to 1. The Entra client secret expires on 2028-11-24 (`login.md`).
