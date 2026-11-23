# Spec v2: domain

Status: draft for review. Phases 3, 6 and 7. Names of tables are proposals; the migration of each phase fixes them.

## Item

The unit of work the board shows. It replaces "an RFC" as the main thing in the app; an RFC becomes a document an item may have.

| field | meaning |
|---|---|
| `id` | `PHZ-NNNN`, from the sequence RFCs already use (`rfc_ids`), so every RFC id is also an item id and no link breaks |
| `type` | see below |
| `title` | in PT-BR, EN-US and 中文 (one required, the others may be empty and fall back to it) |
| `parent_id` | another item, or none |
| `stage` | the stage of the standard the item is in (`flow-and-metrics.md`); `null` for types that do not follow stages |
| `resolution` | `null` while open; `done`, `declined`, `deferred`, `merged` or `cancelled` once closed |
| `owner` | the Path Owner or Product Owner (one person, as the standard requires) |
| `people` | other roles of the standard when known: Capability Owners, Project Manager, QA Owner, Launch Owner, Business Owner |
| `blocked` | a flag with a reason, set and cleared by people; its periods count in metrics |
| `created_at`, `created_by` | |

All changes to an item are appended to `item_events` (who, when, what field, old and new value). Stage changes are the events the metrics read.

### Types

Proposal (open question 1):

| type | from the standard | route | example |
|---|---|---|---|
| `initiative` | — | none (rolls up its children) | Message API |
| `full_request` | full product request | 01 → 10 | Outbound API |
| `supplement` | supplement or small enhancement | 01 → 10, lighter research | Single Message API, a new field |
| `bug` | standard bug | bug intake → 06 → 10 | |
| `p0` | P0 incident | 07 → 10 → post-incident record | |
| `tech` | technical governance | 01 → 10 (confirm) | |
| `task` | — | board columns only | POC Ambar |

### Parents and children

- Any item may have one parent and any number of children, at any depth ("Message API" → "Outbound API" → …). An item with neither is fine
  ("POC Ambar").
- The database refuses cycles (a trigger walks up the parents) and a parent from another board is allowed (a cross-team initiative).
- A parent shows a roll-up: its children by stage and resolution, the oldest open child, and open gates below it. A parent's own stage is
  set by people; the app does not move it automatically (proposal; it may suggest).
- Deleting is not offered; an item is closed with a resolution (`cancelled` included). Moving an item to another parent is an event.

## RFC document

- The existing tables stay as they are: `rfc_revisions` (append-only versions 1.0, 1.1…), `rfc_assets` (pictures in the text), comments keyed by
  RFC id, section and paragraph, status log. An item's RFC is the RFC with the same id.
- An item may have no RFC (a bug, a task). Creating an RFC for an item uses the current new-RFC page, which gets the item id.
- **Versions do not change** (decision of 2026-11-23): publishing the document still creates a version; the version menu keeps showing them.
- The RFC status (`draft`, `in-review`, …) is replaced, for items, by the stage and resolution. The status badge of an RFC page shows the
  stage of its item from phase 3; the status log stays readable as history.

## Attachments (phase 6)

Everything that supports an item and is not the RFC text: HTML exports, PowerPoint, PDFs, spreadsheets, pictures, audio of meetings, notes,
links.

| field | meaning |
|---|---|
| `id`, `item_id` | |
| `kind` | `file`, `note` (Markdown text written in the app) or `link` (an address, for example a Figma or Confluence page) |
| `name`, `description` | |
| `file` | for files: storage path in a private bucket, content type, size, checksum |
| `stage` | optional: the stage it is evidence for (ties a gate's evidence to a file) |
| `replaces` | optional: the attachment this one is a new edition of, so "the latest deck" and its history are both visible |
| `created_at`, `created_by` | |

- The **summary** is a table per item (and per item with its children) of every attachment: kind, name, who, when, size, stage, latest edition,
  plus the pictures of its RFC (`rfc_assets`) in a group of their own. A page lists attachments across all items with filters (type, kind,
  person, period).
- Files go straight from the browser to Storage with a signed upload address that the server issues after checking the user and the size
  limit. Nothing large goes through the database (the pictures of the RFC text stay where they are).
- Audio and video play in the page; HTML is offered as a download (`platform.md`, security). Notes render with the RFC renderer.

## Jira links (phase 3)

- `item_jira_links (item_id, key, url, note)`; an item may have several (an Epic and its stories, issues of several projects).
- The key is validated (`[A-Z][A-Z0-9]+-\d+`); the URL is built from the company Jira base address (admin setting, open question 8) or pasted
  whole. The item page and the card show the keys; clicking opens Jira in a new tab.
- Following the standard: the board warns when an item reaches 04 without a Jira link, and when it has a link before 04 (the standard creates
  the Jira issue at kickoff).
- Search: typing a Jira key in the app's search finds the item linked to it.

## Executive summary (phase 7)

Four fields per item, each with a state:

| field | the question it answers |
|---|---|
| `one_liner` | what this item is, in one sentence |
| `problem` | the pain or problem being solved |
| `solution` | how it is being solved; the solution being applied |
| `success_metric` | how we will know it worked (the metric and, if known, the target) |

- Each field is `missing`, `suggested` (written by the AI, not yet confirmed), or `confirmed` (by a person, with who and when). A field also keeps
  its **sources**: the RFC section, paragraph or attachment it came from.
- **"Suggest with AI"** reads the item's RFC (current version), its notes and text attachments, and fills the fields it can support with a
  citation. The prompt forbids inventing: when the documents do not answer, the field stays `missing` with a sentence saying what is missing
  ("The RFC does not state a success metric."). A suggestion never overwrites a confirmed field.
- The executive view lists items (filter by board, type, stage, parent) with the four fields; a `missing` field is shown in red as a problem
  to resolve, not hidden.
- **Export**: one item or a selection to a `.pptx`, one slide per item: title, id, stage, owner, the four fields, Jira keys. A missing field
  is written on the slide as "Not explained yet: <what is missing>". Optional cover slide with the list. The language of the deck is
  chosen at export (PT-BR, EN-US, 中文). Company template: open question 10.
