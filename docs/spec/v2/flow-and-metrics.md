# Spec v2: flow and metrics

Status: draft for review. Phases 5 (kanban) and 7 (metrics). Source of the flow: *PhizChat Product Project Governance V4* (pilot review draft, 2026-11-20,
not yet formally effective). The metric definitions are **not** in that document; they are a proposal (open question 4 of the README).

## Stages

The ten stages of the standard are the canonical states of **themes of kind `project`** (decision of 2026-11-23); every metric is computed on
them. They do not change per team. Standalone tasks and execution items do not use stages.

| # | stage | lead | gates (owner → evidence) |
|---|---|---|---|
| 01 | Request intake | Requester; Product triages | required info complete and impact verifiable (Product triage → RFC intake section); one Path Owner or Product Owner assigned (Business Owner → owner field) |
| 02 | Problem research | Product; Engineering and QA take part | evidence supports problem, scale and cost of inaction (Product Owner → RFC research section); Engineering and QA gave input (their leads → written input) |
| 03 | Go/no-go decision | Product Owner or Path Owner decides | proceed explicitly approved with scope and prerequisites (Product/Path Owner → decision in the RFC) |
| 04 | PRD and Jira kickoff | Product Owner; Project Manager takes over | PRD standard followed; every requirement has testable acceptance (QA); boundaries clear (Capability Owners); high-risk sign-offs (Security, DPO, Legal, Finance); Jira issue links RFC and PRD (Product Owner) |
| 05 | Solution review | Security, QA, Engineering, Product jointly | four conclusions recorded and approved or conditionally approved; blockers closed, conditions with owner and date (Project Manager) |
| 06 | Delivery planning | Project Manager | priorities and four milestones with owners and evidence; external dependencies committed in writing; Engineering and QA confirm dates |
| 07 | Build | Engineering Capability Owner | pipeline meets standard; contracts match documents; self-test covers requirement ids and exceptions; flags, migrations and hard-coded values registered |
| 08 | Testing and acceptance | QA (quality), Business (outcome) | non-waivable items pass; business acceptance complete; residual issues owned and dated; finance, privacy and permission sign-offs |
| 09 | Release preparation | Launch Owner; Engineering executes | package frozen; rollback executed outside production; monitoring and duty active; support, communication and reconciliation ready |
| 10 | Launch and closure | Project Manager; Product team; Path Owner confirms | metrics within thresholds or safe rollback; first financial reconciliation balances; project summary and actions recorded; value review scheduled |

The gate list above is the seed data; gates are rows (`stage_gates`), so a pilot change to the standard is a data change, not code.

### Routes

A project theme has a `route`, chosen at intake (stage 01 classifies it, as the standard asks); the default is `full`.

| route | stages | notes |
|---|---|---|
| `full` (full request), `supplement`, `tech` (technical governance) | 01 → 10 | 01–03 happen in the theme's RFC; the Jira link is expected from 04 |
| `bug` | intake → 06 → 10 | intake is the creation of the theme; it enters the board at 06 |
| `p0` | 07 → 10, then a post-incident record (a note attachment, required to close) | |

Skipping a stage of the route is allowed with a recorded reason (the standard asks for written approval and a recovery plan); the board
shows the skip on the card. Moving back is allowed and recorded.

### Closing

- 03 can close a theme as `declined` or `deferred` (deferred keeps the reconsideration criteria as a note).
- Leaving 10 closes it as `done`. Any stage may close it as `cancelled` or `merged` (with the theme it merged into).
- The executive `status` (`on_track`, `at_risk`…) is set by the PM in the weekly update; the stage is where the work is in the flow. Both show.

## Gates (checklist that warns)

- Each project theme shows the gates of its current stage and of the stages it passed. A gate is ticked by a person with an **evidence**: an attachment,
  a link, a Jira key or an RFC section. Who ticked it and when are kept.
- Moving a card to the next stage with open gates is **allowed**: the move records which gates were open, the card shows a warning badge
  ("2 gates open in 05"), and the theme keeps the list. A metric "moves with open gates" counts them per board.
- The non-waivable floors of the standard (financial consistency, authorization security, personal data, rollback, business acceptance) are
  marked as such; they still only warn in this version, in red.

## Boards

### The B2B board

- One board for now: the **BU B2B** board (decision of 2026-11-23). It shows the project themes of every front and Outros, with a swimlane per
  front in the fixed order.
- Its **columns are configurable** by admins: name (in the three languages), order, the **stage** it maps to, and an optional WIP limit.
  Several columns may map to one stage (for example "Build: doing" and "Build: code review" both in 07); a column cannot span two stages, so
  every move is a precise stage change or none. The default columns are the ten stages.
- Moving a card (drag, or a menu for keyboard and phone) writes one event: from column, to column, from stage, to stage, person, time, open
  gates. A move inside the same stage changes no stage metric.
- A card shows: id, title, front, owner, status, days in the current stage, items done / total, Jira keys, open blockers and decisions, open
  gates. Filters: front, tag, owner, status, blocked, aging.
- Standalone tasks are not cards on this board; they are followed on the executive view and the roadmap.

### The project kanban

- Inside each project theme: its execution items in four fixed columns, `todo`, `doing`, `blocked`, `done`. Moves are events too (item cycle
  time). A blocked item shows its blocker record.

## Metrics

All metrics come from the event log (stage changes, resolutions, item moves, blockers); nothing is typed by hand. Times are measured in **calendar days**
with decimals (proposal; business days later if wanted). They are computed for **project themes** (on the V4 stages) and, with the level filter, for **execution items** (on the project
kanban: `doing` → `done`); both levels are available with a filter (decision of 2026-11-23).

| metric | definition |
|---|---|
| **Lead time** | from the theme's creation to its close as `done` (items: creation to `done`). Per theme or item; shown as distribution (median, 85th percentile) over a period. |
| **Delivery time** | themes: from first entry into 04 (kickoff, the Jira issue) to `done`. |
| **Cycle time** | themes: from first entry into 07 (build) to `done` (routes `bug` and `p0`: from their first stage, 06 or 07). Items: first `doing` to `done`. |
| **Time in stage** | per theme and stage, the sum of every period spent in it (re-entries add up). Shown per stage as median and 85th percentile. |
| **Throughput** | themes (or items) closed as `done` per week, also per front and route. |
| **WIP** | themes open in each stage (items in each column) at a moment; compared with the column limits. |
| **Aging WIP** | for each open theme or item, days since it entered its current stage and since kickoff, plotted against the 85th percentile of finished ones: the early warning. |
| **Cumulative flow (CFD)** | for each day, the number of themes in each stage at the end of the day (closed ones in a final band), stacked. Built by replaying events, so a backward move shows on the day it happened. Also per front, and for the items of one project (its four columns). |
| **Blocked time** | total time with the blocked flag; also as a share of cycle time. |
| **Open-gate moves** | moves made with gates open, per stage and board. |
| **Triage within 2 business days** | share of themes whose 01 → next move happened within 2 business days in the requester's time zone (the standard's pilot rule). |

- Filters for every metric: period, level (themes, items, or both), front, tag, route, owner.
- Each chart has a "how is this computed" note with the definition above and the list behind it (click a point to see the themes or items).
- Themes that existed before the event log have no history; the migration creates one event at their creation and one at their stage
  (from the RFC status, `domain.md`), marked as estimated and excluded from time metrics by default.

## Acceptance (phases 5 and 7)

- A move on the B2B board records exactly one event with the right from/to stage; a move inside a stage records no stage change.
- A card can move with open gates and shows them; the open gates are kept on the event.
- Columns can be renamed, reordered and remapped by an admin without changing any recorded event.
- The metric functions are unit-tested on fixed event histories (a backward move, a skip, a re-entry, a blocked period, a decline at 03, a bug
  route, a P0 route, items in a project kanban) with expected values computed by hand in the test.
- The CFD of a known history matches a hand-built table day by day, for themes and for the items of one project.
