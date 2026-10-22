---
name: phiz-rfc
description: Writes, updates and publishes PHIZ RFCs (technical proposals, migration plans, API designs, architecture changes) on the phiz-rfcs site, in the house format — trilingual PT-BR / EN-US / 中文 page with contents rail, numbered sections, Mermaid diagrams, mapping tables, phases, risks and open questions, plus on-page comments. Use it whenever the user asks for an RFC, a "proposta técnica", a design doc, a migration plan or a write-up to send to reviewers in Brazil and China, wants to change reviewers/status of an existing RFC (PHZ-NNNN), or asks to turn an investigation done in the PHIZ repos (phiz-flutter, phiz-microwd-*, phiz-pay-*, phiz-inner*, PhizPay…) into a document — even if they don't say "RFC".
---

# PHIZ RFCs

RFCs live in the `phiz-rfcs` repository (`~/Projetos/phiz-rfcs`, remote `phiz-brasil/phiz-rfcs`) and are published by GitHub Pages at `https://phiz-brasil.github.io/phiz-rfcs/`. Each RFC is one page in three languages. New RFCs are written in **Markdown**; the format and its checked rules are in `docs/spec/rfc-format.md` of the repository (read it when unsure).

```
rfcs/PHZ-NNNN/
  rfc.json        id, titles, summary, status, authors, reviewers, systems, version, changelog
  rfc.pt.md       content in Portuguese, written first (reference language)
  rfc.en.md       translation, same sections, paragraphs, diagrams and code blocks
  rfc.zh.md       translation (Simplified Chinese), same structure
templates/rfc/    the skeleton `tools/new_rfc.py` copies; every spot to fill is marked `TODO:`
```

The header of the page (title, lede, status, authors, date, reviewers, systems) is generated from `rfc.json`; the `.md` files hold only the body. `tools/build.py` turns `rfcs/*` into `dist/`; the Pages workflow runs `tools/check_rfc.py` and the build on every push to `main`.

Every RFC, including PHZ-0001 and PHZ-0002, follows this format. PHZ-0001 also has `openapi_gen.py` (the OpenAPI spec shown as a Swagger UI at the end of its page); its older versions (v1.0–v1.6) and PHZ-0002 v1.0 are frozen HTML pages in `versions/` that are never edited.

This is the maintainer edition. It lives in the repository at `skills/phiz-rfc/`; install it with `ln -sfn ~/Projetos/phiz-rfcs/skills/phiz-rfc ~/.claude/skills/phiz-rfc` so it follows the repository.

Setup once per machine: `cd ~/Projetos/phiz-rfcs && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`, then use `.venv/bin/python` for the tools below.

## Workflow

### 1. Understand and research before writing

An RFC is only as good as the investigation behind it. Before drafting:

- Pin down the decision the RFC asks for, who reviews it, and what is out of scope. Ask only what you cannot find.
- When the user gives documents (specs, partner docs, meeting notes, tickets), read them all first and note what each one settles and what it leaves open.
- Read the real code across the PHIZ repos (usually cloned under `~/Projetos`). Name classes, files, endpoints, tables and service codes; reviewers trust an RFC that points at code. When a repo is missing locally, `gh search code "<term>" --owner phiz-general` and `gh api repos/phiz-general/<repo>/...` find it.
- For partner documentation behind a login, open it in the built-in browser and let the user sign in; read with `get_page_text` or the page's own API calls.
- Separate what you verified from what you inferred. Inferences become open questions, not facts.

### 2. Create the RFC from the template

```bash
cd ~/Projetos/phiz-rfcs
.venv/bin/python tools/new_rfc.py --pt "Título" --en "Title" --zh "标题" --author "Gleison"
```

It picks the next free `PHZ-NNNN`, copies `templates/rfc/` to `rfcs/<ID>/` (10 standard sections in the three languages) and prints the next steps. For an existing RFC, edit its files; to publish a change as a new version, run `tools/new_version.py` first (see the repository README).

### 3. Fill the Portuguese version

Fill `rfc.pt.md` completely before translating, so structure and facts settle once. Keep, add, split or drop sections as the topic needs; every section is `## Title {#id}` with a short English slug. Read `references/structure.md` for what goes in each section and `references/markdown.md` for the syntax of each component (tables, mapping chips, callouts, stats, phases, questions, endpoints, diagrams, code). Replace every `TODO:` marker; the checker refuses the file while one is left.

Writing that works for this audience (reviewers in Brazil and China, some reading in a second language):

- Short sentences, concrete nouns, one idea per paragraph. Tables for anything that is "today vs. after" or "old vs. new".
- Say what is not done or not verified. "A confirmar na Fase 0" is better than a silent assumption.
- Every number in the stats list must be countable from the document (e.g. rows in the mapping tables).
- Keep internal names in backticks; never put secrets, tokens or customer data on the page — the site is public.

### 4. Diagrams

Use 4–6 Mermaid diagrams where a picture explains the mechanism: current architecture (flowchart), before/after (flowchart with subgraphs), a key flow (sequenceDiagram), lifecycle (stateDiagram-v2), cutover/rollback (flowchart with a decision node). Read `references/mermaid.md` for the patterns and the syntax traps that break rendering. A diagram is a ```` ```mermaid Caption ```` block; the caption sits on the opening line.

### 5. Translate

Translate to `rfc.en.md` and `rfc.zh.md` keeping the same sections, ids, paragraphs, list items, tables, diagrams and code blocks, **in the same order**: the page numbers paragraphs per section and comments are stored by that number, so a missing or extra paragraph in one language would attach comments to the wrong text (the checker reports it). Translate diagram labels too (node text, messages, state transitions), but keep identifiers such as endpoints, status codes, class names and Mermaid subgraph ids unchanged. Code blocks must be identical in the three languages (comments in English). Chinese uses full-width punctuation (`，。：（）`) and `、` in lists; phase headings use `：`.

Fill `rfcs/<ID>/rfc.json`: `summary` in the three languages (one sentence each), `reviewers` (names only), `systems`, `status`.

### 6. Check and build locally

```bash
cd ~/Projetos/phiz-rfcs
.venv/bin/python tools/check_rfc.py <ID>     # F01–F08: ids, TODOs, same structure in the three languages, links
.venv/bin/python tools/build.py              # the build runs the same check
```

Fix every error before going on; warnings are advice. Optionally preview with `python3 -m http.server -d dist 8000` and look at the three languages.

### 7. Publish and verify

Publishing makes the RFC public. Confirm with the user before the first push of a new RFC, and say plainly that internal service names and partner details will be readable by anyone with the link. Then follow `references/publish.md`: commit (message in Portuguese, attribution line from the session's reminder), push, wait for the Pages run, and verify the live page in the browser in all three languages — sections, contents rail and every Mermaid diagram rendered without "Syntax error". Report what you checked.

## RFCs from the site (single file)

People outside the repository create RFCs on the site's **＋ Nova RFC** page: they download `templates/bundle/RFC.md` (one file: a metadata block and the three languages separated by `<!-- lang:pt|en|zh -->`), get an AI to fill it in from their documents, and upload it. The site offers them a self-contained edition of this skill for that (`skills/phiz-rfc/site/SKILL.md`, built into `phiz-rfc.zip` by `tools/build.py`). When someone asks you to fill that template from their documents, follow `skills/phiz-rfc/site/SKILL.md` and the format in `docs/spec/rfc-bundle.md`: same sections, ids, paragraphs, diagrams and code blocks in the three languages, no `TODO:` left, no raw HTML. Author and collaborators are not in the file: the person types them on the upload page. Do not publish it yourself; the person uploads it.

## Common follow-ups

- **Reviewers / status / systems**: edit `rfc.json` only (`reviewers`: names or `{"name": …, "country": "BR"|"CN"}`; `status`: `draft`, `in-review`, `approved`, `implemented`, `rejected`, `superseded`). The header, the index and the status badge follow; nothing to change in the `.md` files.
- **A change to a published RFC**: run `tools/new_version.py <ID> --note-pt … --note-en … --note-zh …` before editing, so the published version is archived.
- **Comments**: stored in Supabase and shown on the page (per section, per paragraph, reactions); setup and moderation are in the repository README and `references/publish.md`. Comments are keyed by section id and paragraph number — renaming an id orphans its comments and adding a paragraph shifts the ones after it, so keep ids stable once an RFC is in review and prefer a new version for big edits.
