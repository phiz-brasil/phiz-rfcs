# Spec v2: flow and metrics

Status: draft for review. Phases 4 and 5. Source of the flow: *PhizChat Product Project Governance V4* (pilot review draft, 2026-11-20,
not yet formally effective). The metric definitions are **not** in that document; they are a proposal (open question 4 of the README).

## Stages

The ten stages of the standard are the canonical states every metric is computed on. They do not change per team.

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

| type | route | notes |
|---|---|---|
| `full_request`, `supplement`, `tech` | 01 → 10 | 01–03 happen in the item's RFC; the Jira link is expected from 04 |
| `bug` | intake → 06 → 10 | "intake" is the creation of the item; it enters the board at 06 |
| `p0` | 07 → 10, then a post-incident record (an attachment of kind note, required to close) | |
| `initiative`, `task` | none | follow board columns only; not counted in stage metrics |

Skipping a stage of the route is allowed with a recorded reason (the standard asks for written approval and a recovery plan); the board
shows the skip on the card. Moving back is allowed and recorded.

### Closing

- 03 can close an item as `declined` or `deferred` (deferred keeps the reconsideration criteria as a note).
- Leaving 10 closes it as `done`. Any stage may close it as `cancelled` or `merged` (with the item it merged into).

## Gates (checklist that warns)

- Each item shows the gates of its current stage and of the stages it passed. A gate is ticked by a person with an **evidence**: an attachment,
  a link, a Jira key or an RFC section. Who ticked it and when are kept.
- Moving a card to the next stage with open gates is **allowed**: the move records which gates were open, the card shows a warning badge
  ("2 gates open in 05"), and the item keeps the list. A metric "moves with open gates" counts them per board.
- The non-waivable floors of the standard (financial consistency, authorization security, personal data, rollback, business acceptance) are
  marked as such; they still only warn in this version, in red.

## Boards and columns

- A **board** belongs to a team or product line (open question 3) and selects items by a filter (types, parent, team).
- A board has **columns**, configured by admins: name (in the three languages), order, the **stage** it maps to, and an optional WIP limit.
  Several columns may map to one stage (for example "Build: doing" and "Build: code review" both in 07); a column cannot span two stages, so
  every move on any board is a precise stage change or none.
- For `task` and `initiative` items, columns map to a board-only state (`todo`, `doing`, `done`) instead of a stage.
- Moving a card: drag between columns or a menu (keyboard and phone). It writes one event: from column, to column, from stage, to stage, user,
  time, open gates. A move inside the same stage changes no stage metric.
- A card shows: id, title, type, owner, children count, Jira keys, days in the current stage, blocked flag, open gates, and the parent.
- Filters: person, type, parent, blocked, aging. Swimlanes by parent (initiative) optional.

## Metrics

All metrics come from `item_events` (stage changes, resolution, blocked flag); nothing is typed by hand. Times are measured in **calendar days**
with decimals (proposal; business days later if wanted). Items of types without a route are excluded unless a filter includes them.

| metric | definition |
|---|---|
| **Lead time** | from the item's creation to its close as `done`. Per item; shown as distribution (median, 85th percentile) over a period. |
| **Delivery time** | from first entry into 04 (kickoff, the Jira issue) to `done`. |
| **Cycle time** | from first entry into 07 (build) to `done`. For `bug` and `p0`, from first entry into their first stage of build (06 or 07). |
| **Time in stage** | per item and stage, the sum of every period spent in it (re-entries add up). Shown per stage as median and 85th percentile. |
| **Throughput** | items closed as `done` per week (also per board and type). |
| **WIP** | items open in each stage at a moment; compared with the column limits. |
| **Aging WIP** | for each open item, days since it entered its current stage and since kickoff, plotted against the 85th percentile of finished items: the early warning. |
| **Cumulative flow (CFD)** | for each day, the number of items in each stage at the end of the day (closed items in a final band), stacked. Built by replaying events, so a backward move is shown on the day it happened. |
| **Blocked time** | total time with the blocked flag; also as a share of cycle time. |
| **Open-gate moves** | moves made with gates open, per stage and board. |
| **Triage within 2 business days** | share of items whose 01 → next move happened within 2 business days in the requester's time zone (the standard's pilot rule). |

- Filters for every metric: period, board, type, owner, parent (with or without descendants). Open question 5 decides whether items with
  children are counted.
- Each chart has a "how is this computed" note with the definition above and the item list behind it (click a point to see the items).
- Items closed before phase 4 have no events; the migration creates one synthetic event per item at its creation and one at its known stage
  (from the RFC status, README open question 2), marked as estimated and excluded from time metrics by default.

## Acceptance (phases 4 and 5)

- A move on any board records exactly one event with the right from/to stage; a move inside a stage records no stage change.
- A card can move with open gates and shows them; the open gates are kept on the event.
- Columns of one board can be renamed, reordered and remapped by an admin without changing any recorded event.
- The metric functions are unit-tested on fixed event histories (including a backward move, a skip, a re-entry, a blocked period, a decline at
  03, a bug route and a P0 route) with expected values computed by hand in the test.
- The CFD of a known history matches a hand-built table day by day.
