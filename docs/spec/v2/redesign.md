# Spec v2: redesign of the pages (Linear-like, one panel, inline editing)

Status: **approved by the owner** (2026-11-26), with the two open points answered the same day (Google sign-in for Slides; the same AI model). Built in four pull requests (end of this file).

## Why

The site works, but the owner finds it confusing to use and fears it will fall out of use (2026-11-26): eleven pages answer the same
question in different cuts (overview, executive view, board, roadmap, metrics), the theme page has seven tabs, the weekly update is hidden,
and nothing can be edited where it is read. The owner explored a redesign in a clickable prototype (Claude Design, 2026-11-26) and approved
its organization. This spec moves that organization into the site **without removing any function** and **without changing the top bar**.

## Sources

- The prototype *PhizChat Command Center — protótipo*, version 2 (2026-11-26), and the owner's comments on it in the same session.
- The *PDLC B2B* document (the norm called "V4" until now): the ten stages and the gates with owner and evidence.
- The existing specs: `domain.md`, `flow-and-metrics.md`, `fup.md`, `slides.md`, `design.md`, `compatibility.md`.

## Decisions taken (2026-11-26)

| topic | decision |
|---|---|
| Top bar | **Unchanged.** `Shell.tsx` keeps the bar, its three menus, the user menu (name, reader mode, language, sign out). The prototype's side bar is **not** built; its entries already live in the menus. |
| Nothing removed | Every function of the current site stays (list in *Where each function goes*). Addresses keep working (`compatibility.md`). |
| Reference | The look of Linear (quiet, dense, 13 px text, thin borders, a dot for health, small phase icons), with PhizChat's tokens. No new colour outside `themes.css`. |
| Name of the flow | The ten stages are the **PDLC B2B** (product development life cycle between Brazil and China, from idea to rollout). Every interface text that says "V4" or "norma V4" says *PDLC B2B* (pt), *B2B PDLC* (en), *B2B PDLC* (zh). Data keys (`stage`, gate keys) do not change. |
| Fronts | **POP, Payments, Mini-Apps, Parcerias e POCs, Novos negócios, Outros** (Outros stays a front, last). *API Platform* is merged into **POP** (its themes move, the move is an event; its scope text joins POP's). *Product Center* is removed (it has no theme). Data, applied only when the owner says. |
| Hierarchy | **Front › Theme › Delivery**. A *delivery* (*entrega*) is the existing **execution item**; it gains a **start date**, so it has a period (start → due). No new level. |
| Two dates per theme | **Period** (bar on the timeline) and **forecast** (the main milestone: `due_date`, shown as a diamond). When a theme has deliveries with dates, its period is the span of their periods; the forecast stays its own field. |
| Executive blocks | Each line shows **the theme first, then what must be communicated, then the urgency**. **No person's name** in these blocks. |
| Urgency | Blockers and decisions get `urgency`: `urgent`, `important`, `info` (pt *Urgente, Importante, Informativo*). Milestones show *planned*. Default: `important` when *needs leadership*, else `info`. |
| Editing | **Inline**, where the thing is read: titles, sentences, status, owner, forecast, front, stage, kind, deliveries. No separate "edit mode" button. Reader mode shows the same page with plain text and no controls. |
| Dates on the timeline | Quarter columns. Clicking a quarter sets the period by quarter (start of quarter / end of quarter); the theme page and the forms keep exact dates. |
| Languages | The interface stays in three languages (new texts in `i18n.ts`). |

## Where each function goes

| function today | page today | where it goes |
|---|---|---|
| KPI numbers, what needs attention, next weeks, fronts in one line, updated this week | `/overview/` | **Painel** (`/overview/`): the three blocks, the filters, the counter of themes without update |
| executive table by front, filters, *only what needs attention* | `/executive/` | Painel, **List** view. `/executive/` keeps working (same page, restyled) |
| roadmap from dates and milestones | `/roadmap/` | Painel, **Timeline** view, with deliveries. `/roadmap/` keeps working |
| themes by front, new theme, edit fronts | `/themes/` | Painel List + *New theme* in the Painel head; *Edit fronts* stays on `/themes/` |
| theme page (7 tabs) | `/themes/<id>/` | **one page, one scroll** (below) |
| weekly update form and history | theme tab | theme page, *Update of the week* card (form + history) |
| blockers and decisions, needs leadership | theme tab | theme page, with urgency; open ones also on the Painel |
| execution items kanban, milestones | theme tab | theme page, **Deliveries**: list (period, column, owner) or kanban; milestones are items with the flag |
| gates checklist | theme tab | theme page, right column, gates of the current and earlier stages, with owner and evidence |
| attachments (file, note, link, editions, stage) | theme tab, `/attachments/` | theme page right column (main + history); `/attachments/` restyled |
| Jira links, dependencies | theme tab | theme page right column |
| history (events) | theme tab | theme page, *Activity* |
| summary for slides (AI suggestion, confirm) | theme tab | theme page, *Summary for slides* |
| board by stage, move, columns, filters | `/board/` | unchanged in function, restyled, named *PDLC B2B* |
| metrics | `/metrics/` | unchanged in function, restyled |
| slides (choose themes, language, cover) | `/slides/` | **Export**: *Choose themes* (today's function) and *Describe the material* (new, below) |
| FUP list, agenda, presentation, minutes | `/fup/` | unchanged in function (`fup.md`), restyled |
| RFC list, RFC page, new RFC, comments | `/`, `/rfc/`, `/nova/`, `/comments/` | unchanged; restyled with `theme-v2.css` as today |
| sign-in, language, reader mode, name | user menu | unchanged |

## Painel (`/overview/`)

Head: the page keeps its name in the menu and its title (*Visão geral* / *Overview* / *总览*, the top bar does not change); the six numbers stay
(compact) and still open the executive view filtered; view switch **List | Timeline** (remembered in the browser); *New theme* opens the form of
`/themes/` (`/themes/?new=1`). List and Timeline show the **open** themes; choosing the status *done* or *cancelled* in the filter shows those.

1. **Three blocks** (one row of three panels, stacked on a phone):
   - *Needs you*: open blockers and decisions with *needs leadership* or urgency `urgent`, ordered urgent → important → info.
   - *Latest decisions*: the last decided decisions (four), with their date.
   - *Next milestones*: forecasts and milestone items in the next 90 days, ordered by date.
   Each line: **theme title** (bold, small) · date if any · **urgency badge**; under it, the text to communicate. A click opens the theme.
   No owner, author or decider is shown in these blocks.
2. **Filters** in one row: front, owner, status, tag, kind; toggles *Only what needs attention* and *N without update this week*; *Clear*.
   A front chosen shows its scope text under the head.
3. **List**: grouped by front in the fronts' order. Row: phase icon (filled by stage, coloured by health), title, *what it is* in grey on the
   same line, the progress sentence under it, a *no update* chip when stale; then **status**, **owner**, **forecast** as inline selects.
4. **Timeline**: quarters from the current one, five columns, a *Today* line. Row: caret, phase icon, **title and what-it-is editable in
   place**, a button to open the theme; the bar is the period, the diamond the forecast. The caret opens the **deliveries**: one thin bar each,
   coloured by its column, name editable, *+ New delivery* (Enter). A delivery is not deleted (no function deletes an execution item today, and
   blockers, decisions, Jira links and attachments may point to it): it is closed by moving it to *Done*. Clicking a quarter: on a delivery, stretches or shrinks its period;
   on a theme without deliveries, its period; on a theme with deliveries, sets the forecast. *Open all / Close all*.

## Theme page (`/themes/<id>/`)

One scroll, two columns (the right one stacks under on a phone). Top bar and breadcrumb as today.

- **Main column**: phase icon + **title** (inline), **what it is** (inline), kind and tags (add with Enter, remove ×);
  *Update of the week* (health badge, last update date; *New update* opens the form: progress, what moved, next step, status, forecast and the
  reason when the forecast changes; history below); **Deliveries** (list | kanban: name, column, start → due, owner, milestone flag, remove;
  *+ New delivery*); **Blockers and decisions** (open first, with *needs leadership*, urgency, owner/decider, deadline; resolve / decide /
  reopen; add form); **Summary for slides** (three answers, state, who confirmed, *Suggest with AI*, *Confirm*); **Activity** (events, newest
  first).
- **Right column**: *Properties* (health, PDLC stage, phase derived from it, days in the stage, kind, owner, forecast, period, front, id), all
  inline; *RFC* (status, version, author, reviewers, comments / unanswered / new, open); *Jira and dependencies* (keys, add by Enter; *depends
  on / blocks / related to* + theme); *Attachments* (main ones with download, new edition, remove; *History (N)* folded; add file / note / link
  with stage and *new edition of*); *Gates of the PDLC B2B* (current and earlier stages; text, owner role, evidence; tick with evidence);
  *Export this theme's slide*.

Phase from stage: 01–02 *Discovery*, 03–06 *Definition*, 07–08 *Build*, 09–10 *Launched*.

## Export (`/slides/`)

Two modes, same options (slide language pt-BR / en-US / zh, *include cover and overview*):

- **Choose themes**: today's function (filters, select all, one slide per theme with the three answers), with the count of confirmed answers
  per theme.
- **Describe the material** (new): a text box ("Payments status for Gustavo, with blockers and next dates"). An Edge Function `plan-deck`
  receives the request and the data of the active themes (titles, sentences, status, dates, open blockers and decisions, confirmed answers,
  milestones) and returns a **deck plan** (JSON: slides of fixed kinds — cover, overview numbers, needs decision, one per theme, roadmap, next
  dates — each sentence tied to its theme id). The page shows a **preview** and *Download .pptx* uses the existing generator. Nothing is
  invented: a sentence without a source theme is dropped; a missing answer shows as missing (as in `slides.md`).
- **Google Slides** (decision of 2026-11-26): before creating the deck in Google Slides, the page asks the person to **sign in with Google**
  (Google Identity Services, scope `drive.file` only: the app sees only the files it creates). The generated .pptx is uploaded to the person's
  Drive with conversion to Google Slides, and the new deck opens in a new tab. The Google token stays in the browser memory of that tab (never
  stored, never sent to Supabase). *Download .pptx* keeps working without Google. Needs an OAuth client id of the company's Google Cloud
  (the owner creates it; the id is public, the secret is not used).

## Data (migration `20261209000000_redesign.sql`; merging to `main` applies it, `migrations.md`, so the merge is the owner's call)

- `theme_items.start_date date` (nullable; `start_date <= due_date` when both, else `invalid period`). `save_theme_item` accepts `start_date`;
  a change of the period is an event `item_period` (old and new start and due).
- `theme_blockers.urgency` and `theme_decisions.urgency`: `text not null default 'info' check (urgency in ('urgent','important','info'))`;
  backfill `important` where `needs_leadership`; the save functions accept it.
- Fronts (data, same file or a separate one the owner applies): rename/merge *API Platform* into *POP* (move its themes with an event,
  join the scope texts), delete *Product Center* if it has no theme, insert *Parcerias e POCs* and *Novos negócios* before *Outros*.
- The fake Supabase (`tests/fake_themes.py`) mirrors the same rules.

## Acceptance (tests written from this spec)

- The top bar is byte-for-byte the same component on every page (snapshot of its links and menus).
- Every address in `compatibility.md` answers as before; `/executive/` and `/roadmap/` still render their data.
- Painel: blocks show theme → text → urgency, never an owner/decider name; *Needs you* ordering; filters combine; stale counter matches the
  themes without an update in the ISO week; List inline select changes status (one `update_theme`, one event); Timeline quarter click on a
  delivery saves `start_date`/`due_date` at quarter bounds; on a theme with deliveries sets `due_date`; new delivery by Enter.
- Theme page: one scroll (no tab list); every section of today's tabs is present; inline title edit saves and writes an event; reader mode
  shows no input, select or edit button; gates of stages > current are not shown; phase derived from stage.
- Urgency: saved, defaulted, validated (SQL + fake), shown.
- Export: *Describe* sends the request and the theme data, renders the preview from a stubbed plan, drops a sentence with an unknown theme,
  downloads a .pptx; *Create in Google Slides* asks for the Google sign-in first (stubbed in tests) and uploads with conversion; *Choose themes*
  behaves as today.
- No text says "V4" in the interface; *PDLC B2B* in the three languages.

## Tests changed on purpose (PR 1)

`tests/test_overview.py` tested the overview of design part 2 (attention list, next four weeks, front table, updated this week). Those parts are
replaced by the three blocks, the front heads of the List (same numbers and status mix) and the *without update* filter; their tests were rewritten
against this spec. The tests of the numbers and of the executive view they open are unchanged.
In `tests/test_weekly.py`, the two tests of the old *Exige a liderança* list now read the **Precisa de vocês** block (same rows: open blockers and
decisions that need the leadership, earliest deadline first, each line opening its theme; the empty text is *Nada precisa de vocês agora.*).

## Delivery plan (one pull request each, in this order)

1. **Painel** — spec (this file), migration (start date of items, urgency), `/overview/` rebuilt (blocks, filters, List, Timeline with
   deliveries, inline edit), tests.
2. **Theme page** — one scroll, right column, inline edit, deliveries list|kanban, tests.
3. **FUP and Export** — restyle FUP; Export with the two modes and the `plan-deck` function (deployed only when the owner says), tests.
4. **Look of the remaining pages and the name** — board (*PDLC B2B*), metrics, attachments, comments, RFC pages; "V4" removed from the texts;
   fronts data file, tests.

## Open (owner)

- ~~Google Slides~~: sign in with Google before creating the deck (above), decision of 2026-11-26.
- The Google OAuth client id (company Google Cloud), to be created by the owner before PR 3 goes live.
- ~~Which model writes the deck plan~~: the same Workers AI model already used for the suggestions (`CF_SUGGEST_MODEL`), decision of 2026-11-26.
