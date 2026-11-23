# Spec v2: design

Status: in progress (decision of 2026-11-23: redesign the app as a management tool, "more consolidated and simple", in PhizChat's colours on the
layout of nium.com/developers).

## Language

| from the reference layout | in this app |
|---|---|
| near-black top bar, boxed monospace wordmark | `PHIZCHAT` in the bright PhizChat green, main menu, a *Documents* menu, name / reader mode / language on the right |
| warm stone page, white rounded panels | page `#ECEAE3`, panels white with 18 px corners; filter bars on a lighter stone panel |
| monospace uppercase eyebrows over light display headings | an eyebrow (*Tracking*, *Portfolio*, *Documents*) over a light 300-weight heading |
| big numbers split by thin rules | the KPI band of the executive view (each number is also a filter) |
| one loud highlight block | the yellow *Needs leadership* block |

Colours come from the PhizChat app (`sources/PHZ-0001/whatsapp-design/phiz.css`): green `#15803D` (action), bright green `#25D366` (brand mark,
current page), soft green `#E6F4EA`, ink `#17201C`, muted `#56625C`, red `#B42318`, amber, the banner yellow `#FFF4C2`. Every colour is a token at
the top of `apps/web/app/themes/themes.css`. Fonts: Manrope (display), IBM Plex Sans (text), IBM Plex Mono (eyebrows, ids, labels). There is no dark
mode in this version.

## Parts

1. **Foundations and navigation** (done): tokens, top bar with grouped menu, page head, panels, cards, tables, badges, the KPI band on the executive view.
2. **Consolidated overview**: one home page for leadership (KPIs, what needs attention, each front in one line, next milestones), and the executive
   view as a compact table instead of one card per theme.
3. **Theme page and lists**: the theme page in sections/tabs (summary, updates, items, gates, attachments, history) with the editing form folded away;
   the themes list as a dense table.
4. **The pages that came from the old site** (RFC list, RFC page, new RFC, comments) in the same look.
