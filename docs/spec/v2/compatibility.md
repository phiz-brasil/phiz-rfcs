# Spec v2: compatibility contract

Status: draft for review. Applies from phase 1 to the end. Everything below works today and must keep working (or redirect, where
said); the suite in `packages/spec-tests` proves it against any deployment. A phase that breaks an item here is not done.

## How it is tested

- Today's 85 tests (`tests/*.py`, Python, Playwright against the static build and an in-memory fake of Supabase) are the reference for the
  behaviors. Phase 1 ports them to TypeScript in `packages/spec-tests`, keeping one test per behavior with the same names, and runs them:
  - against the **current site** once, to show the port is faithful (both green);
  - against each **preview deployment** of the new app, as a required check on every pull request.
- Data: a seeded test database (a Supabase branch, or a local Supabase in CI) with the same rows the fake holds today: PHZ-0001 and PHZ-0002 as
  imported, a site RFC with two versions and pictures, comments with replies, reactions and paragraph numbers, a status history.
- From phase 2 the suite signs in first (a test account in the test tenant, or a session created by the service key in CI only).

## Addresses

| address | today | from phase 1 |
|---|---|---|
| `/` | index of RFCs from the database, filters by status | same; from phase 3 the index of items (RFC filter keeps the old view) |
| `/rfc/?id=PHZ-NNNN` | the RFC page | same address, same page |
| `/rfc/?id=…&v=1.1` | a version, read-only | same |
| `/rfc/?id=…&c=<comment>#pt-<section>` | opens on a comment | same (after sign-in, phase 2, the user lands back here) |
| `/rfcs/PHZ-NNNN/` (and `?c=…#…`) | redirects to `/rfc/?id=…`, keeping query and hash | same, as a server redirect (308) |
| `/rfcs/PHZ-0001/v1.0.html` … `v1.6.html`, `/rfcs/PHZ-0002/v1.0.html` | archived pages | same files |
| `/rfcs/PHZ-0001/openapi/`, `/rfcs/PHZ-0001/openapi.{pt,en,zh}.yaml` | OpenAPI page and files | same |
| `/nova/`, `/nova/?edit=PHZ-NNNN` | new RFC, new version | same |
| `/comments/` | every comment, filters | same |
| `/assets/skill/phiz-rfc.zip`, `/assets/skill/phiz-rfc-skill.md` | skill download | same files, same bytes for the same sources |
| `https://phiz-brasil.github.io/phiz-rfcs/…` | the site | every path redirects to the same path on the new host (a last Pages deploy of redirect pages), kept at least 3 months |

## Data

- No existing table, column or row is dropped or rewritten by phases 1–7. New things are new tables or new nullable columns.
- `rfc_revisions` stays append-only; versions keep their numbers; `rfc_assets` keep serving the newest picture of a name up to a version.
- Comments keep `rfc_id`, `section`, `para`, `parent_id`, `quote`, `lang`, translations; hidden stays hidden; reactions stay replies with one emoji.
- `rfc_status_log` stays readable; phase 3 maps it to stages once and keeps it as history.
- The `translate-comment` function and its webhook keep working unchanged (inserts still come into `rfc_comments`).
- The database functions the page calls (`create_rfc`, `add_rfc_revision`, `stage_rfc_asset`, `hide_rfc_comment`) keep their signatures until
  phase 2; from phase 2 they require a signed-in user and take the author from the session (the `p_by` argument is ignored, kept for old callers).

## Behaviors (the current tests, by file)

| area | tests today | the contract |
|---|---|---|
| RFC page | `test_site.py`: languages, contents and diagrams; versions and archived page; old address; version time; new-version button; OpenAPI page | the three languages, numbered sections, contents rail, Mermaid diagrams, version menu with date and time, archived versions, the green new-version button |
| Comments | `test_site.py`: comment and reply placement; delete hides with replies; reaction counts as an answer and can be taken back; paragraph comments numbered and listed; page works without the `para` column | per section and per paragraph, replies under the comment, emoji reactions, delete = hide, counters, drawer and "unanswered" filter |
| Status | `test_site.py`: change from the page; live status on load | changes are logged with a name and shown everywhere (from phase 3, shown as the item's stage) |
| New RFC and versions | `test_live.py` (15 tests) | template and prompt offered; every mistake explained and blocks publishing; file or paste; preview; author and collaborators; edit adds a version and keeps the old; refused publication can be retried; hostile markup never runs; the index lists new RFCs; the comments page links to them |
| Pictures | `test_images.py` (14 tests) | PNG, JPEG, WebP only; up to 160; shrunk in the browser; names and snippets; renaming updates the text; preview; sent before publishing; unused not sent; refused by the server stops publishing; old versions keep their pictures; missing shown as such; click opens full size |
| Renderer and checks | `test_render_js.py` (14), `test_parity.py` (5) | the single-file format and all its checks; same output for the same text (snapshots from phase 1); no raw HTML for submitted text; sanitizer keeps only what the renderer makes |
| Imported RFCs | `test_import.py` (10) | PHZ-0001 and PHZ-0002 show their galleries, screens and pictures; the next version number follows; nothing the pages showed is lost |
| Terminal publishing | `test_publish.py` (7) | check without sending; images first; new RFC or new version; nothing sent on error (from phase 2, with a personal token) |
| Skill | `test_skill.py` (4) | the zip is self-contained and reproducible; the text to copy has the skill and the template; the page offers both |
| Database | `test_sql.py` (2) | every migration parses; names are ordered timestamps |

## What is allowed to change

- The look may improve, as long as the elements the tests name stay findable by role or text (the port uses accessible names, not CSS classes).
- Typed names (comment author, status author, publisher) give way to the signed-in account in phase 2; old rows keep their names.
- The Python tools and the static build are removed in phase 1, replaced by `pnpm` scripts with the same options.
