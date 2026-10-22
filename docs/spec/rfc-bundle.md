# Spec: the single-file RFC (bundle)

Status: implemented by `assets/js/render/` (reader, renderer, checks) and `tools/rfc_md.py` (the Python twin), tested by
`tests/test_render_js.py` and `tests/test_parity.py`. **Every RFC is a bundle stored in the database**: one `.md` file that an AI can
fill in from the documents and that people upload on the site (or publish with `tools/publish_rfc.py`).

The body of each language is Markdown (sections, directives, diagrams, code, tables: see `rfc-format.md`, which describes the syntax
and the folder format the first RFCs were written in). The bundle adds a metadata block and splits the languages with markers.
`templates/bundle/RFC.md` is the template.

## Layout

```
<!-- optional guidance comments -->
---
title_pt: …        title_en: …        title_zh: …
summary_pt: …      summary_en: …      summary_zh: …
systems: channel, card-vault            (optional, comma separated)
reviewers: Pedro Bettani (BR), Richard Liang (CN)     (optional; (BR) or (CN) shows the country)
created: 2026-10-15                     (optional; the date shown as "created": imported RFCs keep their original date)
---
<!-- lang:pt -->
## Resumo {#summary}
…
<!-- lang:en -->
## Summary {#summary}
…
<!-- lang:zh -->
## 摘要 {#summary}
…
```

Author, collaborators, status and version are not in the file: the upload form takes the author and the collaborators, the status
starts as draft (changed on the page afterwards) and the version is counted by the site.

## Rules checked in the browser before an upload is accepted

| id | rule |
|---|---|
| B01 | The file starts with the metadata block (comments before it are allowed). |
| B02 | `title_*` and `summary_*` exist for the three languages. |
| B03 | `<!-- lang:pt -->`, `<!-- lang:en -->` and `<!-- lang:zh -->` each appear once; nothing but comments comes before the first one. |
| B04 | No `TODO:` marker is left, in the metadata or in the text. |
| B05 | Each language renders: every `##` has an id, no duplicate ids, links point to existing sections, code blocks name a language. |
| B06 | Same section ids in the same order, same number of commentable blocks per section, same number of diagrams, and identical code blocks in the three languages (rules F04, F05 and F06 of `rfc-format.md`). |
| B07 | Size: at most 600 KB. |
| B08 | Every cited image (`![alt](asset:name.png)`) is attached, or stored by an earlier version; attachments that are not cited are not sent (warning). An image may differ by language (translated screens): one file per language. |
| B09 | Attachments: PNG, JPEG or WebP, at most 160 per RFC and 1 MB each (the page shrinks larger pictures to 1600 px and re-encodes them). |
| B10 | No raw HTML (`tools/publish_rfc.py` checks it; the page shows it as text). |

## Safety

Text a visitor submits is untrusted and is shown on a domain shared with other pages of the organisation, so:

- It is rendered **without raw HTML** (HTML comments are dropped) and the result goes through DOMPurify with a short allow-list.
- Images are kept only with `https://` links, and get `loading=lazy` and `referrerpolicy=no-referrer` (a remote image tells its host who
  is reading). Links to other sites open with `rel="noopener noreferrer"`. Only the copy button of code blocks may be a `<button>`.
- Attached images are written `![alt](asset:name.png)` (name: `[a-z0-9][a-z0-9._-]{0,59}`). The renderer emits `<img data-asset="name">` with
  no `src`; the viewer fetches the bytes from `rfc_assets` and shows them as blob URLs. Uploads go through `stage_rfc_asset` (a token
  groups the pictures of one submission) and are finalised atomically inside `create_rfc` / `add_rfc_revision` (`p_token`). The server
  checks the magic bytes, the 1 MB size and the 160 image limit. A version shows the newest picture of each name stored at or before
  its revision, so replacing a picture does not change older versions. Migrations: `20261023000000_rfc_assets.sql`, `20261024000000_more_images.sql`.
- Ids are limited to `pt-…`, `en-…`, `zh-…` section ids, so they cannot shadow page globals.

The renderer has a flag that lets raw HTML through; only the parity tests use it (the legacy RFC folders were written with raw HTML).

## What the Markdown offers beyond CommonMark

Directives (`::: name`), each rendered the same by both renderers: `note`, `decision`, `risk`, `table` (+ `changes`, `num`, `map`), `stats`,
`phases`, `questions`, `endpoints`, and the ones that replace raw HTML:

| syntax | shows |
|---|---|
| `::: gallery` / `::: gallery phones` + list items `- ![alt](asset:name.png) **A1.** Caption` | pictures with captions, in a grid (`phones`: narrow tall screens) |
| `::: screens` + `##### Title \| Where it shows` headings, each followed by a list | one card per menu item or screen |
| `::: legend` + list items `- [label]{eq} what it means` | the key of the coloured labels |
| `::: caption` + one paragraph | a note under a table or code block; it takes no paragraph number |
| `[text]{eq}` (`eq`, `ch`, `gap`, `new`, `yes`, `part`, `no`) | a small coloured label in running text or in a table cell |
| `<br>` | a line break (the one HTML tag allowed; useful inside table cells) |

## Same output as the build

The browser renderer (`assets/js/render/`) is a port of `tools/rfc_md.py`. `tests/test_parity.py` renders every RFC of the repository,
the template, the RFCs as the importer converts them and `tests/fixtures/syntax.md` with both and compares the HTML, the section ids, the commentable blocks per section,
the header and the contents list. A change to either renderer that is not made in the other fails that test.

## Where an uploaded RFC lives

The site stores each upload in the database instead of the repository (`supabase/migrations/20261022000000_live_rfcs.sql`):

- **Ids** come from one sequence (`rfc_ids`, `create_rfc` takes the next `PHZ-NNNN`; `reserve_rfc_id` reserves one).
- **Revisions** are append-only (`rfc_revisions`: the file as uploaded, the extracted metadata, authors, collaborators, who edited, an optional
  note). Creating is `create_rfc`, editing is `add_rfc_revision`; the version is `1.0`, then `1.1`, `1.2`… Nothing is overwritten, and any version
  can be read at `/rfc/?id=PHZ-NNNN&v=1.1` (read-only).
- **Limits** per origin: 5 creations an hour (20 a day) and 30 revisions an hour (200 a day); 600 KB a file; 10 authors, 20 collaborators.
- **Moderation**: set `hidden = true` on the row of `rfc_ids` in the Table Editor to take an RFC off the site (and `false` to bring it back).
- Comments, reactions, status and per-paragraph comments work as for any RFC: they are keyed by the `PHZ-NNNN` id.

## The RFCs that came from the repository

PHZ-0001 and PHZ-0002 were written in the folder format (`rfcs/<ID>/`). `tools/import_rfcs.py` converted their current versions into bundles and
inserted them as revisions with the service-role key (`SUPABASE_SERVICE_KEY=… .venv/bin/python tools/import_rfcs.py`; `--dry-run` converts and
checks only). The conversion replaces the raw HTML with the Markdown above, turns the pictures into attachments named after their path and
language (`pt-whatsapp-b01-architecture.png`), and keeps the revision number of the version (1.7 is revision 8, so the next version made on
the site is 1.8). `tests/test_import.py` checks that nothing the pages showed is lost: same commentable blocks per section (so comments keep
their paragraph), same diagrams and code, same text.

What the database does not hold stays in `rfcs/<ID>/` and is published by `tools/build.py`: versions archived as HTML pages (`/rfcs/<ID>/v<version>.html`,
listed in the version menu through `archive.json`), the OpenAPI generator of PHZ-0001 (`/rfcs/PHZ-0001/openapi/` and the YAML files) and the images those
pages use. The old address `/rfcs/<ID>/` redirects to `/rfc/?id=<ID>`.
