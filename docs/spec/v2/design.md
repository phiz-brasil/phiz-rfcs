# Spec v2: design

Status: in progress (decision of 2026-11-23: redesign the app as a management tool, "more consolidated and simple", in PhizChat's colours on the
layout of nium.com/developers).

## Language

| from the reference layout | in this app |
|---|---|
| dark top bar, boxed monospace wordmark | a deep PhizChat green bar (`#0B3B22`) with `PHIZCHAT` in the bright green; three menus (*Tracking*: executive view, B2B board, roadmap, metrics; *Portfolio*: themes; *Documents*: RFCs, attachments, comments) and a *Preferences* menu (name, reader mode, language) |
| warm stone page, white rounded panels | a light green-grey page (`#EEF1EC`), white panels with 12 px corners, compact spacing for daily use |
| monospace uppercase eyebrows over light display headings | an eyebrow (*Tracking*, *Portfolio*, *Documents*) over a light 300-weight heading |
| big numbers split by thin rules | the KPI band of the executive view on the dark green (each number is also a filter), and the same numbers per front in a table below it |
| one loud highlight block | the yellow *Needs leadership* block |

Colours come from the PhizChat app (`sources/PHZ-0001/whatsapp-design/phiz.css`): green `#15803D` (action), bright green `#25D366` (brand mark,
current page), soft green `#E6F4EA`, ink `#17201C`, muted `#56625C`, red `#B42318`, amber, the banner yellow `#FFF4C2`. Every colour is a token at
the top of `apps/web/app/themes/themes.css`. Fonts: Manrope (display), IBM Plex Sans (text), IBM Plex Mono (eyebrows, ids, labels). There is no dark
mode in this version.

## Parts

1. **Foundations and navigation** (done; adjusted after review: grouped menus, greener, more compact, numbers per front): tokens, top bar with grouped menu, page head, panels, cards, tables, badges, the KPI band on the executive view.
2. **Consolidated overview** (done): one home page for leadership (KPIs, what needs attention, each front in one line, next milestones), and the executive
   view as a compact table instead of one card per theme. Done as `/overview/` (the brand leads there): six numbers (active, on track, at risk or
   blocked, overdue, no update this week, need leadership; each opens the executive view filtered with `?f=`), what needs attention, the next four weeks,
   each front in one line with its status mix, and the themes updated this week. The executive view is one table grouped by front; its numbers filter it.
3. **Theme page and lists** (done): the theme page in sections/tabs (summary, updates, items, gates, attachments, history) with the editing form folded away;
   the themes list as a dense table. Done as: a header with the key facts (status, stage, owner, estimate in red when overdue, progress) and the actions
   (open the RFC, export the slide, edit), a sticky menu of sections (summary, weekly update, blockers and decisions, execution, attachments, Jira and
   dependencies, history), the theme's data read-only until *Edit theme data* is pressed, and one aligned table per front on the themes page.
4. **The pages that came from the old site** (RFC list, RFC page, new RFC, comments) in the same look.
