# Spec: RFC format (Markdown)

Status: **legacy folder format**. The first two RFCs were written this way; they now live in the database as single-file RFCs
(`rfc-bundle.md`, `tools/import_rfcs.py`), and new RFCs are written that way. This document stays for the Markdown syntax (sections,
directives, diagrams, code, tables), which both formats share, and for the folder layout `tools/import_rfcs.py` reads.
Implemented by `tools/rfc_md.py` (render). Versions archived before the Markdown format stay as frozen HTML pages (`versions/<v>/source.html`).

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
templates/shell.html, templates/page.css   page frame and styles shared by all Markdown RFCs
```

## rfc.json

`id` (= folder name), `title` / `summary` (`pt`, `en`, `zh`), `status`, `authors`, `reviewers`, `created`, `updated`,
`version`, `changelog`. Optional: `systems` (list of strings shown in the header), `short` (short title for the browser tab; default: the English title).
`status` is one of `draft`, `in-review`, `approved`, `implemented`, `rejected`, `superseded`.
`collaborators` (optional) lists the people who helped write it, shown in the header next to the authors, as text entries.
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

## Rules (now checked by the page and `tools/publish_rfc.py`)

The structure rules F03–F07 of the folder format are rules B05–B06 of `rfc-bundle.md` today: every `##` has an id, same section ids in the three
languages, same number of commentable blocks per section (paragraph, list item, table, diagram, code block: the numbering used by per-paragraph
comments), same number of diagrams, identical code blocks, links to existing sections, no `TODO:` markers.

## Versions

In the database every publication is a version (`rfc-bundle.md`). The folder format archived the three `.md` files and `rfc.json` into
`versions/<v>/` by hand; the versions archived that way as HTML stay as pages.

## Comments depend on structure

Comments on a paragraph are stored with the section id and the paragraph number inside the section. Keep the same paragraphs, in
the same order, in the three languages (F05). Adding or removing a paragraph in a published RFC shifts the comments after it:
prefer a new version for large edits.
