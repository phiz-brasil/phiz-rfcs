# Slides: the visual model (decided 2026-11-24)

Status: this document. The model replaces the neutral look of `apps/web/lib/slides.ts` (phase 9 left it open because the Google Slides link was not readable). It is **our own model, based on the design of the deck "PhizChat Empresas — B2B Strategy"** (33 slides, read on 2026-11-24 in the owner's browser). Nothing is copied from it: no text, no image, no logo; only the visual language.

## What the deck looks like (what we keep)

- **Three surfaces**: deep green (almost black) for the slides that set the problem and the cover; off-white for the slides that explain; bright green for the one big number that must be remembered.
- **A small green label** in the top-left corner of every explanatory slide (`Where to start · PhizChat Empresas`); an **orange label** (uppercase) on the dark ones.
- **Heavy sans-serif titles**, short, in ink green; body in regular weight; numbers large and bold.
- **Rounded cards** on the off-white; **dark table header** with light text and **green dots**; a **soft orange box** for what is broken; a **pale green box** for the rule that reassures.
- A **ring of segments** on the cover (the product wheel), reduced here to concentric circles.

## The model (our colours come from `design.md`; no new colour outside this table)

| Name | Hex | Use |
|---|---|---|
| `DARK` | `07301F` | cover, problem card, table header |
| `DEEP` | `0E4A2D` | ring on the cover |
| `BRIGHT` | `1DB954` | the success card, the big number slide, dots |
| `ACTION` | `15803D` | labels and links on the light surface |
| `PAPER` | `F2F7F3` | background of the explanatory slides |
| `INK` | `0B2A1A` | titles and text on the light surface |
| `MUTED` | `5F6F66` | secondary text |
| `ORANGE` | `F59E3F` | label and number on the dark surface |
| `WARN_BG` / `WARN_INK` | `FDEBDD` / `8A3B12` | "not explained yet" and the note of an unconfirmed suggestion |
| `LINE` | `CFE0D5` | card outline |

Fonts: Manrope-like sans (`Calibri` when the machine has no other; `Microsoft YaHei` for Chinese), as before.

## The slides

1. **A theme (always, one per theme — what the export produced before, same texts and same count).** Light surface: green label `<front> · <id>`; the title; the three questions as three cards side by side: the **problem** on the dark card (orange question, white answer), the **solution** on a white card, the **success** on the bright-green card (dark text). An answer that is missing is a `WARN_BG` card with the text *Not explained yet: …* in italics; a suggestion nobody confirmed keeps its note (*AI suggestion, not confirmed yet*) in `WARN_INK`. Below: the four meta items (*Front, Owner, Status, Estimated completion*) as small pills, the Jira keys as links, the theme id and the date of the export.
2. **Optional, with "Include cover and overview" (off by default, so the plain export is unchanged):**
   - **Cover** (dark): the logo-like rounded square, the label `PORTFOLIO · <date>`, the title, the number of themes, the concentric circles.
   - **Overview** (light): a table (theme, front, status, estimated completion, answers) with a dark header and one coloured dot per status; more than 10 rows go to the next slide.
   - **The number** (bright green): how many themes and how many are *at risk or blocked*.
   - **What is missing** (light, orange box): for each theme the answers still *not explained* or *not confirmed*. When nothing is missing, the slide says so.

## Rules

- **The answers come from the documents**: the deck shows what the theme holds at the moment of the export (confirmed answers; AI suggestions marked as such; the rest *not explained yet*). Nothing is filled in by the model. The snapshot is "as of" the date written on the cover.
- A missing answer is never hidden: it is orange on the slide and counted on *What is missing*.
- The three languages (pt-BR, en, zh-Hans) are chosen at export, as before; the labels of the new slides exist in the three.
- `slide-model.ts` stays pure (no imports) and Node-tested; only `slides.ts` knows about colours and positions.

## Checks (tests/test_slides.py)

- `summaryOf`: counts by status, the number *at risk or blocked*, the rows, the gaps (missing and unconfirmed) in the three languages; a theme with nothing missing is not in *What is missing*.
- The plain export is unchanged: one slide per theme, the same texts, the same Jira links, the same order.
- With the option on: cover first, overview, the number, the theme slides in the order of the list, *What is missing* last; the count of slides is `3 + themes + 1` (more than 10 themes add overview slides).
- The palette: every colour used in `slides.ts` is in the table above (a test reads the file).
