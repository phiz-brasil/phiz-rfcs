---
name: phiz-rfc
description: Writes, updates and publishes PHIZ RFCs (technical proposals, migration plans, API designs, architecture changes) on the phiz-rfcs site, in the house format — trilingual PT-BR / EN-US / 中文 page with contents rail, numbered sections, Mermaid diagrams, mapping tables, phases, risks and open questions, plus on-page comments. Use it whenever the user asks for an RFC, a "proposta técnica", a design doc, a migration plan or a write-up to send to reviewers in Brazil and China, wants to change reviewers/status of an existing RFC (PHZ-NNNN), or asks to turn an investigation done in the PHIZ repos (phiz-flutter, phiz-microwd-*, phiz-pay-*, phiz-inner*, PhizPay…) into a document — even if they don't say "RFC".
---

# PHIZ RFCs

RFCs live in the **database** (Supabase) of the `phiz-rfcs` site (`~/Projetos/phiz-rfcs`, remote `phiz-brasil/phiz-rfcs`, Pages at `https://phiz-brasil.github.io/phiz-rfcs/`). Each one is **one file**: a metadata block and the same content in Portuguese, English and Chinese, separated by `<!-- lang:pt|en|zh -->`. The site turns it into a page (`/rfc/?id=PHZ-NNNN`) with contents rail, numbered sections, Mermaid diagrams, tables, phases, risks, open questions and on-page comments. The format and its checked rules are in `docs/spec/rfc-bundle.md` of the repository (read it when unsure); the template is `templates/bundle/RFC.md`.

Writing an RFC does not touch git: you write the file, check it with `tools/publish_rfc.py` and publish it. Every publication is a new version (1.0, 1.1…); anyone can edit on the site (**＋ Nova RFC**, `/nova/?edit=PHZ-NNNN`). The folder `rfcs/` is the legacy of the first two RFCs, kept for what the database cannot hold: older versions archived as HTML pages, PHZ-0001's OpenAPI generator and the pictures those pages use. Do not add RFCs there; `tools/import_rfcs.py` moved the current versions to the database.

This is the maintainer edition. It lives in the repository at `skills/phiz-rfc/`; install it with `ln -sfn ~/Projetos/phiz-rfcs/skills/phiz-rfc ~/.claude/skills/phiz-rfc` so it follows the repository. People outside the repository get the self-contained edition (`site/SKILL.md`) from the site.

Setup once per machine: `cd ~/Projetos/phiz-rfcs && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`, then use `.venv/bin/python` for the tools below.

## Workflow

### 1. Understand and research before writing

An RFC is only as good as the investigation behind it. Before drafting:

- Pin down the decision the RFC asks for, who reviews it, and what is out of scope. Ask only what you cannot find.
- When the user gives documents (specs, partner docs, meeting notes, tickets), read them all first and note what each one settles and what it leaves open.
- Read the real code across the PHIZ repos (usually cloned under `~/Projetos`). Name classes, files, endpoints, tables and service codes; reviewers trust an RFC that points at code. When a repo is missing locally, `gh search code "<term>" --owner phiz-general` and `gh api repos/phiz-general/<repo>/...` find it.
- For partner documentation behind a login, open it in the built-in browser and let the user sign in; read with `get_page_text` or the page's own API calls.
- Separate what you verified from what you inferred. Inferences become open questions, not facts.

### 2. Start from the template

Copy `templates/bundle/RFC.md` to a working file outside the repository (for example `~/rfc-drafts/<slug>/rfc.md`; put the images next to it). For a new version of an RFC that exists, start from its current text: `/nova/?edit=PHZ-NNNN` shows it, or read it from the database (`rfc_revisions`, newest `rev`). Every spot to fill is marked `TODO:`; the check refuses the file while one is left.

### 3. Fill the Portuguese section

Fill the `pt` section completely before translating, so structure and facts settle once. Keep, add, split or drop sections as the topic needs; every section is `## Title {#id}` with a short English slug. Read `references/structure.md` for what goes in each section and `references/markdown.md` for the syntax of each component (tables, coloured labels, callouts, stats, phases, questions, endpoints, diagrams, code, images and galleries, screen cards). The metadata block holds the three titles, the three summaries (one sentence each), `systems` and, optionally, `reviewers: Name (BR), Name (CN)`.

Writing that works for this audience (reviewers in Brazil and China, some reading in a second language):

- Short sentences, concrete nouns, one idea per paragraph. Tables for anything that is "today vs. after" or "old vs. new".
- Say what is not done or not verified. "A confirmar na Fase 0" is better than a silent assumption.
- Every number in the stats list must be countable from the document (e.g. rows in the mapping tables).
- Keep internal names in backticks; never put secrets, tokens or customer data in the file — the RFC is public to anyone with the link.

### 4. Diagrams and images

Use 4–6 Mermaid diagrams where a picture explains the mechanism: current architecture (flowchart), before/after (flowchart with subgraphs), a key flow (sequenceDiagram), lifecycle (stateDiagram-v2), cutover/rollback (flowchart with a decision node). Read `references/mermaid.md` for the patterns and the syntax traps that break rendering. A diagram is a ```` ```mermaid Caption ```` block; the caption sits on the opening line. Pictures made elsewhere are PNG/JPEG/WebP files cited as `![alt](asset:name.png)`.

### 5. Translate

Translate to the `en` and `zh` sections keeping the same sections, ids, paragraphs, list items, tables, diagrams and code blocks, **in the same order**: the page numbers paragraphs per section and comments are stored by that number, so a missing or extra paragraph in one language would attach comments to the wrong text (the check reports it). Translate diagram labels too (node text, messages, state transitions), but keep identifiers such as endpoints, status codes, class names and Mermaid subgraph ids unchanged. Code blocks must be identical in the three languages (comments in English). Chinese uses full-width punctuation (`，。：（）`) and `、` in lists; phase headings use `：`.

### 6. Check

```bash
cd ~/Projetos/phiz-rfcs
.venv/bin/python tools/publish_rfc.py ~/rfc-drafts/<slug>/rfc.md --check
```

It runs the checks of the page (B01–B10 of `docs/spec/rfc-bundle.md`): metadata, the three languages, same section ids, same paragraphs/tables/diagrams/code, no `TODO:`, no raw HTML, every image cited exists. Fix every error; warnings are advice.

### 7. Publish and verify

Publishing makes the RFC public. Confirm with the user first, and say plainly that internal service names and partner details will be readable by anyone with the link. Then follow `references/publish.md`: `tools/publish_rfc.py … --by "<name>"` (add `--id PHZ-NNNN --note "…"` for a new version), open the address it prints in the built-in browser and verify all three languages — sections, contents rail and every Mermaid diagram rendered without "Syntax error". Report what you checked.

## RFCs from other people (single file)

People outside the repository create RFCs on the site's **＋ Nova RFC** page: they download `templates/bundle/RFC.md`, get an AI to fill it in from their documents, and upload it (the page checks it, shows a preview and publishes). The site offers them a self-contained edition of this skill for that (`skills/phiz-rfc/site/SKILL.md`, built into `phiz-rfc.zip` by `tools/build.py`). When someone asks you to fill that template from their documents, follow `skills/phiz-rfc/site/SKILL.md`: same sections, ids, paragraphs, diagrams and code blocks in the three languages, no `TODO:` left, no raw HTML. Author and collaborators are not in the file: the person types them on the upload page. Do not publish it yourself unless they ask.

## Common follow-ups

- **Status**: changed on the page, from the badge in the header (anyone can; each change is logged with a name). **Reviewers / systems**: the metadata block, in a new version.
- **A change to a published RFC**: a new version through `tools/publish_rfc.py --id` or `/nova/?edit=`; the previous versions stay readable under the version menu.
- **Comments**: stored in Supabase and shown on the page (per section, per paragraph, reactions); setup and moderation are in `references/publish.md`. Comments are keyed by section id and paragraph number — renaming an id orphans its comments and adding a paragraph shifts the ones after it, so keep ids stable once an RFC is in review and prefer a new version for big edits.
