# Spec: the single-file RFC (bundle)

Status: implemented by `assets/js/render/` (reader, renderer, checks) and tested by `tests/test_render_js.py` and `tests/test_parity.py`.
Used by the RFCs people create on the site: one `.md` file that an AI can fill in from their documents and that they upload.

The body of each language is the same Markdown as `rfcs/<ID>/rfc.<lang>.md` (see `rfc-format.md`: sections, directives, diagrams, code,
tables). The bundle only adds a metadata block and splits the languages with markers. `templates/bundle/RFC.md` is the template.

## Layout

```
<!-- optional guidance comments -->
---
title_pt: …        title_en: …        title_zh: …
summary_pt: …      summary_en: …      summary_zh: …
systems: channel, card-vault            (optional, comma separated)
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

## Safety

Text a visitor submits is untrusted and is shown on a domain shared with other pages of the organisation, so:

- It is rendered **without raw HTML** (HTML comments are dropped) and the result goes through DOMPurify with a short allow-list.
- Images are kept only with `https://` links, and get `loading=lazy` and `referrerpolicy=no-referrer` (a remote image tells its host who
  is reading). Links to other sites open with `rel="noopener noreferrer"`. Only the copy button of code blocks may be a `<button>`.
- Ids are limited to `pt-…`, `en-…`, `zh-…` section ids, so they cannot shadow page globals.

RFCs that live in the repository are written by the team and may use raw HTML (status chips, legends, screenshot galleries); the
renderer takes a flag for that, and only the build and the parity tests use it.

## Same output as the build

The browser renderer (`assets/js/render/`) is a port of `tools/rfc_md.py`. `tests/test_parity.py` renders every RFC of the repository,
the template and `tests/fixtures/syntax.md` with both and compares the HTML, the section ids, the commentable blocks per section,
the header and the contents list. A change to either renderer that is not made in the other fails that test.
