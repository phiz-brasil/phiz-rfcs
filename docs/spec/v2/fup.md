# Spec v2: FUP (follow-up meeting mode)

Status: proposed (2026-11-25). Owner's decisions of 2026-11-25: a FUP page inside the site, with the look of the FUP prototype used on
2026-11-24; what is recorded in the meeting goes straight to the themes; recording and transcription come later.

## Why

The weekly follow-up with the leadership was prepared and run on 2026-11-24 in a separate prototype (agenda, one theme per screen, live
notes, minutes). It worked, but everything recorded there had to be copied back into the themes by hand. This page brings that flow into the
site so a FUP reads the themes and writes back to them, with no copy.

## What the user sees

`/fup/` lists the FUPs (date, title, open or closed) and has *New FUP*. `/fup/<id>/` has three tabs:

1. **Agenda.** Every active theme, grouped by front in the fronts' order, one row each: kind of treatment (*Inform*, *Discuss*, *Decide*),
   the number of points to validate answered (`2/5`), a star (favourite) and *On the agenda / Off*. A band on top counts themes on the
   agenda, decisions, discussions, informs, points answered and favourites. New FUPs come with a suggested agenda: themes at risk or blocked,
   with open decisions, or with no update in the last 7 days are on; the rest is off, and any theme can be switched.
2. **Presentation.** One theme per screen, previous and next (buttons and the left and right arrows). The card shows the front, PHZ id,
   kind, status, the *what it is* sentence, the last update (progress, what moved, next step), the open points to validate as checkboxes,
   and the theme's attachments and links. A side panel records: the theme status (*On track*, *At risk*, *Blocked*), and a record of type
   *Note*, *Decision* or *Action*, with *To do / Doing / Done* and, for an action, a due date. Records of this theme in this FUP are listed
   under it; the progress chip of each one cycles on click (and moves the execution item it created). A note can be deleted; decisions and
   actions are already in the theme and are changed there.
3. **Minutes.** Generated from the FUP: per theme its status and records, then all decisions, all actions with progress and due date, the
   points still open and the favourites. A *Copy minutes* button.

*Close FUP* saves a snapshot (agenda and records, as they were) and writes one weekly update to each theme that got records (see below). A
closed FUP is read-only.

## Where the records go (no copy of the themes)

| recorded in the FUP | written to |
|---|---|
| status | the theme's status (`update_theme`), immediately |
| decision | a decision of the theme, created and decided with the same text (`save_theme_decision` + `decide_theme_decision`) |
| action | an execution item of the theme (`save_theme_item`: title, column from To do / Doing / Done, due date). Task themes, which have no items, get the action as an open decision instead |
| note | kept in the FUP; goes into *what moved forward* of the weekly update written at closing |
| point to validate answered | the open decision of the theme is decided with the text typed (or "Answered in the FUP of <date>") |

Points to validate are the theme's open decisions (`theme_decisions` with state `open`). Nothing new is invented for them.

On closing, each theme with at least one record gets one weekly update (`post_theme_update`): progress *Treated in the FUP of <date>.*
(unless one is typed), what moved forward = the notes and decisions, next step = the actions with their dates. A theme updated this way
counts as updated this week on the executive view.

Owners are typed inside the text of the record (decision of 2026-11-24): there is no owner field in the FUP.

## Data

Migration `supabase/migrations/20261204000000_fup.sql`:

- `fup_meetings`: `id uuid`, `title text` (1–120), `held_on date`, `agenda jsonb` (array of `{theme, kind: inform|discuss|decide, on, star}`),
  `log jsonb` (array of `{theme, type: note|decision|action, text, progress: todo|doing|done, due, ref}` where `ref` is the id of the row it
  created), `closed_at timestamptz`, `snapshot jsonb`, `created_by`, `created_at`, `updated_at`.
- `save_fup(p_id uuid, p jsonb, p_by text)`: creates or updates title, date, agenda and log while open; refuses a closed FUP.
- `close_fup(p_id uuid, p_by text)`: sets `closed_at`, freezes `snapshot` (agenda, log, and each theme's status at closing) and writes the
  weekly updates above in the same transaction.
- Same access as the other theme tables: members read and write; RLS and grants as in `20261201000000_member_lock.sql`.
- Mirrored in `tests/fake_themes.py`.

## Look

The FUP pages use the look of the 2026-11-24 prototype, on purpose different from the rest of the site (owner's decision of 2026-11-25): a full
PhizChat-green band with the title and the tabs, Space Grotesk for titles and Inter for text, large rounded cards, pill chips per kind (green
*Inform*, blue *Discuss*, amber *Decide*), an amber *What we need* box and the points to validate as checkboxes. The site's top bar stays on
top. The colours are new tokens `--fup-*` at the top of `apps/web/app/themes/themes.css`, so the rule "no colour outside the tokens" still holds;
the two fonts load only on `/fup/`.

## Out of scope (later)

Recording and transcription; the reader/manager/PM lenses; editing the theme's other fields from the FUP; a FUP per executive with
"since the last FUP with this person".

## How it is checked

- `tests/test_sql.py` parses the migration; `tests/test_fup.py` (fake Supabase): create a FUP, suggested agenda, each record type lands in the
  right table, a task theme gets an action as a decision, answering a point decides the decision, closing writes one update per theme with
  records and freezes the snapshot, a closed FUP refuses changes.
- Playwright: the three tabs render in pt, en and zh; arrows move between themes; recording a decision shows it on the theme page; the minutes
  contain every record; the page works at 400 px wide.
