# Spec v2: from an RFC site to a delivery tracker

Status: **draft for review** (phase 0). Nothing here is built yet. Each file is a spec in the SDD sense: what the system must do and
how we will know it does, written before the code. A phase starts only after its spec is reviewed; the code of a phase is done when
the acceptance tests the spec lists pass, together with the compatibility suite (`compatibility.md`).

## Why

The site started as a place to write and discuss RFCs. Teams now need it to follow work day to day: a kanban board on the flow of
the *PhizChat Product Project Governance V4* standard (pilot draft, 2026-11-20), flow metrics, a hierarchy of items, links to the
company Jira, all the attachments of an item in one place, an executive view that exports to slides, and access limited to the
company.

## Decisions taken (2026-11-23)

| topic | decision |
|---|---|
| Order | Move the platform first (same behavior), then turn on login. One change at a time. |
| Board | Columns are configurable per board; every column maps to one stage of the standard, so metrics stay comparable. |
| Gates | A checklist that warns: a card can move with gates open; open gates stay visible on the card and the item. |
| Versions | Keep the versions of the RFC document as they are, and add an attachments hub with a summary. |
| Users | Only `@phiz.com` accounts, through Microsoft sign-in (Entra ID). |
| Executive view | AI suggests (from the RFC and attachments), a person confirms; a missing answer is shown as missing, never invented. |
| Jira | Links only: keys and URLs on the item, opening the company Jira. No API token, no status sync. |
| Hosting | Vercel (company Pro/Team account) for the app; Supabase stays as database, auth and file storage. |
| Stack | Node.js ecosystem: TypeScript, Next.js. |

## The files

| file | covers |
|---|---|
| [`platform.md`](platform.md) | Architecture, hosting, repository, authentication, roles, security, how the code is organized |
| [`domain.md`](domain.md) | Items, types, parents and children, RFC documents, attachments, Jira links, executive summary: the data model |
| [`flow-and-metrics.md`](flow-and-metrics.md) | Stages, routes, gates, boards and columns, and the exact definition of each metric |
| [`compatibility.md`](compatibility.md) | What must keep working (addresses, data, behaviors) and the tests that prove it |

## Phases

Each phase is one pull request (or a short series), reviewable and testable on its own preview deployment.

| phase | delivers | user-visible change |
|---|---|---|
| 0 | These specs; the compatibility contract | none |
| 1 | Next.js app on Vercel with the same pages and behavior; old addresses redirect; GitHub Pages retired; repository private | new address only |
| 2 | Sign-in with Microsoft for `@phiz.com`, roles, database closed to anonymous access | login |
| 3 | Items: types, parent and children, the RFC as a document of an item, Jira links; existing RFCs become items | item page, tree |
| 4 | Boards with configurable columns, stage changes logged, gate checklists | kanban |
| 5 | Metrics: lead time, cycle time, CFD, throughput, WIP, aging | metrics page |
| 6 | Attachments hub: files of any kind (HTML, PPT, images, audio, notes, links) in storage, with a summary per item and across items | attachments tab |
| 7 | Executive view and export to slides (one item or many) | executive tab, .pptx |

Phase 1 changes no behavior on purpose: it is the riskiest move (new runtime, new host) and the compatibility suite is what proves it.

## Open questions

Answer them in review; each one names the phase that needs it.

1. **(3) Item types.** The standard has full request, supplement, bug, P0 incident and technical governance. Your example "POC Ambar" is a
   plain task with no children. Proposal: those five plus `task` (follows only the board, no stage route) and `initiative` (a parent that
   groups items, like "Message API"). Keep, rename or drop?
2. **(3) Existing RFCs.** Proposal for their starting stage: `draft` → 01, `in-review` → 03, `approved` → 04, `implemented` → 10 (done),
   `rejected` → 03 (declined), `superseded` → closed. Is that right for the RFCs already published?
3. **(4) Boards.** One board per team (PhizChat, PhizPay…) or per product line? Who may change the columns of a board?
4. **(5) Which time counts.** Proposal: lead time from creation to done, delivery time from kickoff (04) to done, cycle time from build (07)
   to done; calendar days (not business days) at first. The standard defines none of these; confirm or change.
5. **(5) Parents in metrics.** Count only items without children (the work), only parents, or both with a filter?
6. **(2) Roles.** Proposal: everyone with `@phiz.com` is a member (read, comment, create and edit items, move cards); admins (by e-mail list)
   configure boards, roles and moderation. Is a read-only role needed (for example, for leadership)?
7. **(2) Who registers the app in Entra ID.** Sign-in needs an app registration in the company tenant (client id, secret, redirect URL).
   Who is the tenant administrator?
8. **(3) Jira address.** The base URL of the company Jira (for example `https://<company>.atlassian.net`) and the project keys in use.
9. **(1) Repository drafts.** People write RFC drafts in the repository (`rfcs/checkout-global/RFC.md` with `anexos/`). With the app, should
   drafts move to the app (draft items with attachments) or keep living in the repository until published?
10. **(7) Slide template.** Is there a company PowerPoint template (master slide, fonts, colors) the export must follow?
