# Spec: RFC format (Markdown)

Status: implemented by `tools/rfc_md.py` (render + checks), `tools/check_rfc.py` (CLI), `tools/new_rfc.py` (scaffold).
Every RFC follows it. Versions archived before the Markdown format stay as frozen HTML pages (`versions/<v>/source.html`).

## Why

An RFC must be easy to fill in (by a person or by the `phiz-rfc` skill from other documents), easy to review in a diff, and
identical in structure in PT-BR, EN-US and 中文. The format is a contract between authors, the skill, the validator and the
site features that depend on structure (contents rail, per-paragraph comments, versions).

## Layout

```
rfcs/PHZ-NNNN/
  rfc.json        metadata
  rfc.pt.md       content in Portuguese (reference language)
  rfc.en.md       content in English
  rfc.zh.md       content in Simplified Chinese
  openapi_gen.py optional: defines build(lang) returning the OpenAPI spec; the page ends with a Swagger UI and the YAML files are published
  <other files>   images…: copied to the site next to the page
  versions/<v>/   frozen copy of the three .md files and rfc.json of an older version
templates/rfc/    skeleton copied by tools/new_rfc.py (same layout, with TODO: markers)
templates/shell.html, templates/page.css   page frame and styles shared by all Markdown RFCs
```

## rfc.json

`id` (= folder name), `title` / `summary` (`pt`, `en`, `zh`), `status`, `authors`, `reviewers`, `created`, `updated`,
`version`, `changelog`. Optional: `systems` (list of strings shown in the header), `short` (short title for the browser tab; default: the English title).
`status` is one of `draft`, `in-review`, `approved`, `implemented`, `rejected`, `superseded`.
`authors` entries are text or `{"pt": …, "en": …, "zh": …}` when the text differs by language. `reviewers` entries are names, or
`{"name": "Pedro Bettani", "country": "BR"}` (`BR` or `CN`), which the header shows as `Pedro Bettani (Brasil / Brazil / 巴西)`.
`details` adds rows to the header: `[{"label": {"pt": …, "en": …, "zh": …}, "value": {"pt": …, "en": …, "zh": …}}]` (the value may
contain inline HTML such as `<code>`).
The header of the page (eyebrow, title, lede, status, authors, date, reviewers, systems) is generated from this file; the
Markdown files contain only the body.

## Markdown body

CommonMark plus GFM tables. Raw HTML is allowed as an escape hatch.

- **Sections**: every level-2 heading starts a section and needs an id: `## Resumo {#summary}`. Sections are numbered
  automatically (01, 02…). Nothing may come before the first `##`. Ids are lowercase slugs, unique, and the same in the
  three languages and in the same order.
- `###` and `####` are sub-headings. `[text](#id)` links to a section.
- **Tables** are wrapped for the site. Variants: `::: table map` (also `changes`, `num`) around one table.
- **Diagrams**: a fenced block `mermaid` followed by the caption on the info line:
  ```` ```mermaid Caption in this language ````. The caption may use inline Markdown; when it contains backticks, open the block with `~~~mermaid` instead of backticks. Translate the labels, keep identifiers.
- **Code**: fenced blocks with a language (`json`, `bash`, `http`, `python`, `yaml`, `java`, `javascript`, `typescript`, `dart`,
  `kotlin`, `go`). Samples are shared: the block must be identical in the three languages (comments in English).
- **Callouts**: `::: note Label`, `::: decision Label`, `::: risk Label` (the label is optional; each has a default per language).
- **Stats**: `::: stats` with a list; each item starts with a bold number: `- **8** integrations today`.
- **Phases**: `::: phases` with `##### PHASE 0: Preparation` headings, each followed by a list.
- **Open questions**: `::: questions` around a numbered list; start each item with a bold topic.
- **Endpoints**: `::: endpoints` with items `- POST /v1/payment — Charges the card`.

In Chinese, CommonMark does not close `**bold：**中文` when punctuation touches a CJK letter; the renderer fixes `**…**` pairs left
in running text, so write bold the same way in the three languages.

Everything the template shows is part of the contract; nothing else is required. Add, split or drop sections as the topic needs.

## Rules checked (`tools/check_rfc.py`, run in CI and by `tools/build.py`)

Errors stop the build; warnings do not.

| id | rule |
|---|---|
| F01 | `rfc.json` exists, is valid, `id` matches the folder, `status` and `version` are valid, `version` is in `changelog`. |
| F02 | The three files `rfc.pt.md`, `rfc.en.md`, `rfc.zh.md` exist. |
| F03 | Every `##` has an id; ids are unique slugs; nothing before the first `##`. |
| F04 | Same section ids in the same order in the three languages. |
| F05 | Same number of commentable blocks per section in the three languages (paragraph, list item, table, diagram, code block: the numbering used by per-paragraph comments, so a mismatch would attach comments to the wrong paragraph). |
| F06 | Same number of diagrams, and code blocks with the same content, in the three languages. |
| F07 | Every `[..](#id)` points to an existing section id; directives are known and well formed. |
| F08 | No `TODO:` markers left (error), no default `summary` text (warning). |
| F09 | `openapi_gen.py`, when present, builds a spec for the three languages. |

## Versions

`tools/new_version.py` archives the three `.md` files and `rfc.json` into `versions/<current>/`, bumps the version and adds the
changelog entry. The archived version is rendered with the templates of the day, at `/rfcs/<ID>/v<version>.html`.
Typos and small fixes do not need a new version.

## Comments depend on structure

Comments on a paragraph are stored with the section id and the paragraph number inside the section. Keep the same paragraphs, in
the same order, in the three languages (F05). Adding or removing a paragraph in a published RFC shifts the comments after it:
prefer a new version for large edits.
