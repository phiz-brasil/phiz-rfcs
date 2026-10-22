---
name: phiz-rfc
description: Fills in the PHIZ RFC template (RFC.md, one file with Portuguese, English and Chinese) from the documents the user provides, ready to upload on the "Nova RFC" page of the PHIZ RFC site. Use it whenever someone wants to write an RFC, a technical proposal ("proposta técnica"), a design doc or a migration plan for PHIZ, or hands over documents (specs, meeting notes, tickets, code) to be turned into one.
---

# PHIZ RFC: filling in RFC.md

An RFC is a technical proposal that reviewers in Brazil and China read and comment on, in their own language. You turn the user's documents into **one file, `RFC.md`**, that they upload on the **＋ Nova RFC** page of the RFC site (https://phiz-brasil.github.io/phiz-rfcs/nova/). The site checks it, shows a preview and publishes it. You do not publish anything yourself.

## Steps

### 1. Understand before writing

- Ask only what you cannot find in the documents: the decision the RFC asks for, who must review it, what is out of scope.
- Read every document first. Note what each one settles and what it leaves open. Separate what you **verified** from what you **inferred**: inferences become open questions, never facts.
- Never copy secrets, tokens, passwords or customer data into the RFC. The page is shared with anyone who has the link.

### 2. Start from the template

Open `assets/RFC.md` (in this skill's folder). It has a metadata block at the top and the same ten sections in three languages. Every spot to fill is marked **`TODO:`**. Keep, add, split or drop sections as the topic needs: `references/structure.md` says what goes in each one.

### 3. Write the Portuguese section first

Short sentences, concrete nouns, one idea per paragraph. Tables for anything that is "today vs. after". Name the evidence (files, classes, endpoints, documents) so reviewers can check. Say what is not done or not verified ("a confirmar") instead of smoothing it over. `references/markdown.md` has the syntax of every component: tables, callouts, stats, phases, open questions, endpoints, code and diagrams.

### 4. Diagrams

Where a picture explains a mechanism, draw it as text with Mermaid (current architecture, before/after, one key flow, a lifecycle): `references/mermaid.md` has patterns and the mistakes that break rendering. A diagram is a ```` ```mermaid Caption ```` block with the caption on the opening line.

### 5. Translate to English and Chinese

Translate the Portuguese into the `en` and `zh` sections keeping **the same sections, `{#ids}`, paragraphs, list items, tables, diagrams and code blocks, in the same order.** The site numbers paragraphs per section and comments are stored by that number, so an extra or missing paragraph in one language would attach comments to the wrong text. Translate the labels inside diagrams too, but keep technical names (endpoints, status codes, class names). Code blocks are identical in the three languages (comments in English). Chinese uses full-width punctuation (`，。：（）`).

### 6. Check before handing it over

- No `TODO:` left anywhere, including the metadata block.
- Same section ids, in the same order, in the three languages.
- Same number of paragraphs, list items, tables, diagrams and code blocks in each section, in all languages.
- Every code block names a language (`json`, `bash`, `http`, `python`, `yaml`, `java`, `javascript`, `typescript`, `dart`, `kotlin`, `go`, `sql`, `text`).
- Links to other sections point to a section id that exists: `[text](#id)`.
- Only Markdown: no HTML, no scripts, images only as `https://` links.

### 7. Deliver

Give the user the **complete file**, from the first `<!--` to the last paragraph: save it as `RFC.md` if you can create files, otherwise print it in one code block. Tell them to open **＋ Nova RFC**, upload (or paste) the file, check the preview, type their name and the collaborators' names, and publish. The site lists anything still wrong.
