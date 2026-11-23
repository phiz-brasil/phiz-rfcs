# Spec v2: domain

Status: draft for review. Phases 3 to 9. Table names are proposals; the migration of each phase fixes them.

Source of the model: the request "Painel de Acompanhamento PhizChat" (2026-11-23), reconciled with the earlier requests: three fixed levels,
**Frente → Tema → Item de execução**. The earlier idea of free-depth parents and children is replaced by these levels plus dependencies
between themes (decision of 2026-11-23).

## Front (Frente)

Groups the themes of one area. Fixed list, in this order on every view, followed by **Outros**:

| order | front | scope |
|---|---|---|
| 1 | **POP** (full name: PhizChat Open Platform) | the portal where business customers manage their accounts and activity: business accounts, partner access to several accounts, permissions, verification, KYB in the portal, and the content and social portal reached from POP |
| 2 | **API Platform** | APIs: Single Message API, Outbound API, migration of the old API used by the CRM, recontact rules and blocks, addressing by hash or phone, group APIs, the investigation of bots for groups (group API management in POP may show as a dependency) |
| 3 | **Mini-Apps** | mini-apps: clean-up, organization of the showcase with the current UX, mini-app factory, strategy and next steps, benchmarks, initiatives in Mexico |
| 4 | **Payments** | Global Checkout, payments architecture and its handoff, payments to influencers, alignment on BaaS and Sub at PicPay |
| 5 | **Product Center** (same name in the three languages) | PDLC, methodologies, OKRs, roadmap process, weekly B2C–B2B alignment, consolidated follow-up of POCs while their front is open, review of Henry's designs; the A/B testing platform starts here if shared across teams (in POP if only for the content and social portal) |
| — | **Outros** | permanent, always last: themes in discovery, cross-cutting or outside the fronts |

Fronts are rows (`fronts`: key, names in the three languages, order, scope text), so a name or scope change is data. A theme moved from
Outros to a front keeps all its history (the move is an event).

## Theme (Tema)

The main unit of executive follow-up, weekly update, roadmap and slide export.

| field | meaning |
|---|---|
| `id` | `PHZ-NNNN`, from the sequence RFCs already use (`rfc_ids`): every RFC id is a theme id, so no link breaks |
| `kind` | `project` (has execution items and a project kanban; moves through the V4 stages) or `task` (standalone task: done in the theme itself, no items, no stages) |
| `front` | its one main grouping (a front or Outros) |
| `title` | translatable text (see Languages) |
| `owner` | the person accountable (Path Owner / PM) |
| `status` | the health shown to executives: `not_started`, `on_track`, `at_risk`, `blocked`, `paused`, `done`, `cancelled` |
| `stage` | projects only: the V4 stage (`flow-and-metrics.md`); tasks have none |
| `what_it_is` | one sentence: what this theme is (stable) |
| `progress` | one sentence: how it is going now (comes from the latest weekly update) |
| `problem`, `solution`, `success` | the three slide answers (see Executive summary) |
| `start_date`, `due_date` | start and estimated completion; every change of `due_date` is kept with who, when and why |
| `milestones` | name, date, done or not; shown on the roadmap |
| `tags` | free labels for views across fronts: Mission China, Before Leave China, Arriving in Brazil, alinhamento com Luizinho, status para Anderson… |
| `dependencies` | links to other themes (`depends on`, `blocks`, `related`), across fronts, without copying the theme |
| `jira` | Jira links (see below) |
| `created_at`, `created_by` | |

All changes are appended to `theme_events` (who, when, field, old and new value). Stage changes are what the metrics read.

### Initial themes

Seeded in phase 3, all in **Outros**, with only their names (PMs fill the rest): PhizShop e vendas via live, Merchant Golden Silver,
diagnóstico de Estopim, Ingoo e Café, revisão de acessos ao PhizAdmin, Game Center, Deeper Link.

The RFCs already published become themes of kind `project`, with their RFC as the theme's document. Proposed fronts (confirm in review):

| RFC | proposed front | stage from its status |
|---|---|---|
| PHZ-0001 PhizChat Business Messaging API | API Platform | in-review → 03 |
| PHZ-0002 Migração CredPay → GruPag | Payments | draft → 01 |
| PHZ-0003 PhizChat Payments | Payments | draft → 01 |
| PHZ-0004 Evolução da OpenPlatform | POP | draft → 01 |
| PHZ-0005 Business Account: conversas e mensagens IM | API Platform | draft → 01 |
| PHZ-0006 Checkout global | Payments | draft → 01 |
| PHZ-0007 Relatório de análise de pagamentos | Payments | rejected → 03, closed as declined |
| PHZ-0008 APIs pz.* do PhizClip | Outros | draft → 01 |

Status mapping for any RFC: `draft` → 01, `in-review` → 03, `approved` → 04, `implemented` → 10 (done), `rejected` → 03 (declined),
`superseded` → closed. From then on the RFC page shows the theme's stage instead of the old status, and the status picker goes away
(the status log stays as history).

RFC drafts written in the repository (`rfcs/<name>/RFC.md` with `anexos/`) are imported as draft themes with their document and attachments,
and drafting moves to the app (decision of 2026-11-23).

## Execution item (Item de execução)

A task or delivery inside a theme of kind `project`.

| field | meaning |
|---|---|
| `id`, `theme_id` | |
| `title`, `owner` | |
| `column` | the project kanban: `todo`, `doing`, `blocked`, `done` (fixed in this version) |
| `due_date` | optional |
| `milestone` | if set, the item also shows on the roadmap as a milestone of its theme |
| `jira` | Jira links |

Changes go to the same event log (with the item id), so item cycle time is measurable too.

## Weekly update

PMs update each theme every week. An update is a record, never overwritten; the theme shows the latest and the history.

| field | meaning |
|---|---|
| `theme_id`, `week` (ISO week), `author`, `created_at` | |
| `progress` | the one-sentence progress shown on the executive view |
| `advanced` | what moved forward |
| `next_step` | |
| `status_change` | old → new status, if it changed |
| `due_change` | old → new estimated date and the reason, if it changed |
| `blockers`, `decisions` | links to the records below, created or updated in the same form |
| `dependencies` | changes to dependencies, if any |

Several updates in one week are allowed; the executive view uses the latest. A theme with no update in the current week is flagged
("no update this week") on the executive view and in the PM's list.

## Blockers and decisions

Records of their own, linked to a theme and, when it applies, to an execution item.

| field | blocker | decision |
|---|---|---|
| what | what is blocked and why | what must be decided |
| who | owner of the unblock | who decides |
| by when | optional | optional deadline |
| needs leadership | flag | flag |
| state | open, resolved (with when and how) | open, decided (with the decision), dropped |

Open records with **needs leadership** are highlighted at the top of the executive view and of their front.

## Jira links

- `jira_links (theme_id or item_id, url, label)`: an address to an issue in the company Jira, pasted by a person. The page shows the issue key
  read from the address (`ABC-123`) and opens Jira in a new tab. No token, no reading from Jira, no base address to configure (decision of
  2026-11-23). Several links per theme or item.
- Following the V4 standard, the B2B board warns when a project reaches stage 04 without a Jira link.

## Attachments

Everything that supports a theme and is not the RFC text: HTML exports, PowerPoint, PDFs, spreadsheets, pictures, audio of meetings, notes,
links. Versions of the RFC document stay as they are (decision of 2026-11-23); attachments are a hub next to them.

| field | meaning |
|---|---|
| `id`, `theme_id` (and optional `item_id`) | |
| `kind` | `file`, `note` (Markdown written in the app) or `link` (Figma, Confluence…) |
| `name`, `description` | |
| `file` | private Storage path, content type, size, checksum |
| `stage` | optional: the V4 stage it is evidence for (ties a gate's evidence to it) |
| `replaces` | optional: the attachment this one is a new edition of |
| `created_at`, `created_by` | |

- The summary is a table per theme (with its items) of every attachment: kind, name, who, when, size, stage, latest edition, plus the pictures
  of its RFC in a group of their own; another page lists attachments across themes with filters.
- Files go straight from the browser to Storage with a signed upload address the server issues after checking size (proposal: 50 MB).
  Audio and video play in the page; HTML is a download; notes render with the RFC renderer.
- **The frozen archive moves in.** What the first two RFCs left outside the database (`apps/web/legacy/`: the versions of PHZ-0001 and
  PHZ-0002 archived as HTML pages, the pictures they use, and the OpenAPI reference of PHZ-0001) becomes attachments of those themes in this
  phase, and `apps/web/legacy/` is removed; the old addresses (`/rfcs/<ID>/v1.0.html`, `/rfcs/PHZ-0001/openapi/`) redirect to the attachments.
  After that the repository holds no RFC content (decision of 2026-11-23).

## Executive summary and slides

- Each theme keeps `what_it_is`, `progress` and the three slide answers in fields of their own.
- The three answers (`problem`, `solution`, `success`) have a state each: `missing`, `suggested` (by the AI, not confirmed) or `confirmed` (by a
  person, with who and when), and their sources (RFC section, paragraph, attachment).
- **Suggest with AI** reads the theme's RFC, notes, text attachments and recent weekly updates and fills what it can support with a citation.
  When the documents do not answer, the field stays `missing` with a sentence saying what is missing ("The RFC does not state how success
  will be measured."). A suggestion never overwrites a confirmed answer. A person confirms or edits.
- **Export** for themes of kind `project` and `task`, one or many: one slide per theme answering, in this order, *What problem are we
  addressing with this theme?*, *What is the proposed solution, in short?*, *What does success look like for this theme and how will we know
  it was reached?*, plus title, front, owner, status, estimated completion and Jira links. A missing answer is written on the slide as "Not
  explained yet: <what is missing>". Language chosen at export (pt-BR, en, zh-Hans). Visual model: the Google Slides deck the requester
  shared (to be received as a file, see README).

## Languages

- The interface is in pt-BR, en and zh-Hans: navigation, labels, statuses, executive view, reader mode, kanban, roadmap and slide labels.
  **PhizChat**, **POP** and **Product Center** are written the same in every language.
- Texts written by people (titles, sentences, weekly updates, blockers, decisions, slide answers) are stored once, with the original language
  and the translations attached to the same record (`translations` of that record: language, text, `machine` or `reviewed`, who reviewed).
- On save the text is translated automatically (the Cloudflare Workers AI model the comments already use); anyone can correct a translation,
  which then shows as reviewed. A machine translation is marked as such on the page. Editing the original marks its translations as outdated
  and translates again (a reviewed translation is kept until someone accepts the new one).

## Views

- **Executive view**: themes grouped by front in the fixed order, then Outros. Per theme: progress sentence, owner, status, estimated completion,
  main milestones with dates, open blockers and decisions that need attention, and "no update this week". Leadership items on top. A click opens
  the theme. Filters: tag (Mission China…), status, owner, front.
- **Reader mode**: the executive view, theme details and roadmap with every create, edit and update control hidden; a switch in the header, on
  by default for people who only read (remembered per person). It hides controls; it does not replace permissions (`platform.md`).
- **Roadmap**: built from the themes' own dates (start, milestones, estimated completion) and the items marked as milestones, grouped by front and
  Outros; a change on a theme shows on the roadmap at once. Themes without dates stay on the executive view and are listed under the timeline
  as "no dates".
- **Theme page**: what it is, progress, the three answers, status, dates and their history, milestones, weekly updates, blockers and decisions,
  dependencies, Jira links, attachments, the RFC (if any) and, for projects, the project kanban.
