# PHIZ RFCs

Static site for the PHIZ Open Platform RFCs, published on GitHub Pages.

- **Index** (`/`): every RFC with status, authors and reviewers; filter by status; PT-BR / EN-US / 中文.
- **RFC page** (`/rfcs/PHZ-0001/`): the document, with Mermaid diagrams and a **Comment** button on every section.
- **Comments**: saved on the page itself (Supabase), Confluence-style: comment on a section or select a passage and comment on it; replies, highlighted passages and a counter per section. No GitHub account needed. Comments are shared across the three languages. Fallbacks: [giscus](https://giscus.app) if configured, otherwise a pre-filled GitHub Issue.

> ⚠️ **GitHub Pages on a free plan needs a public repository, so the site and every RFC are public.**
> Do not commit secrets, internal hostnames, customer data or anything not meant to be public. `noindex` keeps search engines away, but anyone with the link can read it.

## Publish (one time)

1. Create a **public** repo on GitHub and push this folder to `main`.
2. **Settings → Pages → Source: GitHub Actions**. The workflow in `.github/workflows/pages.yml` builds and deploys on every push. The site will be at `https://<user-or-org>.github.io/<repo>/`.
3. Enable comments on the page (Supabase):
   1. Create a free project at <https://supabase.com> (any region; `sa-east-1` is closest to Brazil).
   2. Apply the migrations in [`supabase/migrations`](supabase/migrations), in file order: **SQL Editor → New query**, paste each file and run it (or `supabase link` then `supabase db push`). They create `rfc_comments`, the access rules and the rate limits, and are safe to run again (see *Database migrations* below).
   3. **Project Settings → API**: copy the **Project URL** and the **publishable** key (`sb_publishable_…`, or the legacy `anon` key). Never use the `secret`/`service_role` key here.
   4. Put both in `site.config.json` → `comments.supabaseUrl` and `comments.supabaseKey`. Push.

   The publishable key is meant to be public: with it, visitors can only read visible comments and add new ones. Nobody can edit or delete through the page.

   **Moderation**: in **Table Editor → rfc_comments**, set `hidden = true` on a comment to hide it (its replies disappear with it), or delete the row.

   Until this is done, the Comment button uses giscus (if `giscus.repoId`/`categoryId` are set) or opens a pre-filled GitHub Issue.
4. Give reviewers repo access only if you want them to *write* RFCs; reading and commenting need no account.

### Following comments

- **Index**: the header shows the total number of comments and how many are new; each RFC card shows its count, how many threads have no reply and how many are new.
- **Central page** (`/comments/`): every comment of every RFC, most recent activity first. Filter by RFC, by *Unanswered* or *New*, or search by text or author. *Open in the RFC and reply* jumps to the comment in its section (link `rfcs/<ID>/?c=<comment id>#<lang>-<section>`) with the reply form ready.
- **On each RFC**: the *Comments* button in the header opens a side panel with every thread of that RFC, grouped by section, with the same filters.

“New” means new since this browser last opened that list (stored in `localStorage`, nothing on the server); comments signed with the name you use in the form do not count as new for you.

### Automatic translation of comments (Cloudflare Workers AI)

Comments are shown in the language selected on the page (PT-BR, EN-US or 中文), with a *Machine translation · Show original* note. Translations are made once on the server and stored with the comment, so every reader sees the same text in any browser. Until this is set up, comments simply appear as written.

1. **Database**: apply [`20261016000000_translations.sql`](supabase/migrations/20261016000000_translations.sql) (and the ones before it, if not applied yet). It adds the read-only columns `translations` and `src_lang`.
2. **Cloudflare keys** (free, no card needed for the free allowance of 10,000 Neurons a day, roughly several hundred comments):
   1. Create an account at <https://dash.cloudflare.com/sign-up>. Your **Account ID** is on the right side of the dashboard home (or in the URL after `dash.cloudflare.com/`).
   2. **My Profile → API Tokens → Create Token → Create Custom Token**, permission **Account · Workers AI · Read** (the "Workers AI" template also works). Copy the token; it is shown once.

   When the daily allowance is used up, translation calls fail until 00:00 UTC; comments keep showing in the original language.
3. **Function**: deploy [`supabase/functions/translate-comment`](supabase/functions/translate-comment/index.ts) with JWT verification **off** (the webhook authenticates with a shared secret instead):

   ```bash
   supabase login
   supabase link --project-ref <project ref, from the Supabase URL>
   supabase secrets set CF_ACCOUNT_ID=<account id> CF_API_TOKEN=<token> TRANSLATE_WEBHOOK_SECRET=<long random string>
   supabase functions deploy translate-comment --no-verify-jwt
   ```

   Without the CLI: **Edge Functions → Deploy a new function → Via editor**, name it `translate-comment`, paste the file, turn off *Verify JWT*, and add the three secrets under **Edge Functions → Secrets**.
4. **Webhook**: **Database → Webhooks → Create a new hook**: table `rfc_comments`, event **Insert**, type **Supabase Edge Functions** → `translate-comment`, method `POST`, HTTP header `x-webhook-secret: <same secret>`.
5. **Existing comments**: translate the ones already posted (repeat until it returns `{"translated":0}`; 50 per call):

   ```bash
   curl -X POST "https://<project ref>.supabase.co/functions/v1/translate-comment" \
     -H "x-webhook-secret: <same secret>" -H "Content-Type: application/json" -d '{"backfill":true}'
   ```

The model (`m2m100`) does not detect the source language, so the function guesses it (Chinese characters, or Portuguese vs English by accents and common words) and falls back to the page language the author was using; a very short comment such as “ok” stays untranslated. A new comment shows in its original language for a second or two, then in translation on the next load. Check the function's **Logs** in Supabase if translations do not appear (wrong token or account id, missing secret, or the daily Workers AI allowance).

### Changing the status from the page

The status badge in the header of each RFC is a button (`EM REVISÃO ▾`): pick a status, type your name once (remembered in the browser) and it changes for everyone, with no rebuild. The index, the header badge and the status pill and eyebrow in the three languages all follow the live status. There is no login: anyone with the link can change it, so every change is kept in `rfc_status_log` with the name typed, an origin rate limit (10 a minute) applies, and archived versions (`v1.0.html`) keep the status they had.

1. **Database**: apply [`20261019000000_status.sql`](supabase/migrations/20261019000000_status.sql). It creates `rfc_status_log` (append-only) and the view `rfc_status_current`.
2. Nothing else to configure; the page uses the same Supabase keys as the comments. Until step 1 is done, the page shows the status from `rfcs/<ID>/rfc.json` and changing it fails with an error message.
3. **Undo a wrong change**: **Table Editor → rfc_status_log**, delete the row; the previous one becomes current. The `status` in `rfc.json` is only the starting value (before the first change in the page).

### Deleting comments

Every comment (and reply) has a **Excluir / Delete / 删除** link; it asks once and then removes the comment for everyone. Deleting a comment also removes its replies. There is no login: anyone with the link can delete, so “delete” only **hides** the comment (`hidden = true`, with `hidden_at`, `hidden_by` and an origin rate limit of 10 a minute); nothing is erased from the database.

1. **Database**: apply [`20261020000000_hide_comments.sql`](supabase/migrations/20261020000000_hide_comments.sql). It adds the columns `hidden_at` and `hidden_by` and the function `hide_rfc_comment`, which is the only way the page can hide a comment. Until this is done, the button shows “Could not delete”.
2. **Restore a comment**: **Table Editor → rfc_comments**, set `hidden = false` on the comment and on its replies (they are hidden together).

### Comments on each paragraph, and emoji reactions

- **Per paragraph**: every paragraph, list item, table, diagram and code block has a small 💬 button in the right margin (on hover; with a counter once it has comments). It opens a comment box right under that paragraph. Paragraphs are numbered per section in document order (`para` 0, 1, 2…), so the same number points to the same paragraph in PT-BR, EN-US and 中文: **keep the structure of the three languages aligned** (same paragraphs in the same order). If you add or remove a paragraph in a published RFC, comments after that point move with the numbers, so prefer a new version for big edits. The section list still shows everything, with a `¶ N` tag on paragraph comments (click it to jump to the paragraph).
- **Reactions**: each comment has `☺+` to react with 👍 ❤️ 👌 ✅ 🎉 👀 🙏 😄; reactions show as small counters and clicking one you gave takes it back. A reaction is saved as a reply that contains only an emoji, so **it counts as an answer** (“Sem resposta” in the comments list and on the comments page does not include it). Typing only an emoji as a reply does the same.

1. **Database**: apply [`20261021000000_paragraph_comments.sql`](supabase/migrations/20261021000000_paragraph_comments.sql): the `para` column and the insert trigger (replies inherit `para`; the rate limit is 15 a minute / 150 a day so reactions do not hit it). Until it runs, the page works as before without the paragraph buttons.
2. **Translation function**: redeploy [`supabase/functions/translate-comment`](supabase/functions/translate-comment/index.ts) (Edge Functions → translate-comment → paste the file → Deploy). It now skips emoji-only text, so reactions do not use the translation allowance.

## Database migrations

The database is described by numbered files in [`supabase/migrations`](supabase/migrations) (`<timestamp>_<name>.sql`, the Supabase CLI convention), one per feature, applied in order:

| file | what it adds |
|---|---|
| `20261015000000_comments` | `rfc_comments`, insert rules, public-key permissions |
| `20261016000000_translations` | `translations` and `src_lang` (filled by the `translate-comment` function) |
| `20261019000000_status` | `rfc_status_log` and `rfc_status_current` (status changed from the page) |
| `20261020000000_hide_comments` | `hide_rfc_comment` (delete from the page = hide) |
| `20261021000000_paragraph_comments` | `para` (comment per paragraph), reactions and the current rate limits |

Every file is idempotent (`if not exists` / `or replace`), so applying all of them again is safe. To change the database, add a **new** file with a later timestamp; never edit one that has been applied. Apply a new file in the Supabase **SQL Editor** (paste and run) or with `supabase db push`.

## Tests

The page scripts have smoke tests that run in a real browser against the built site, with the Supabase API replaced by a small in-memory fake (`tests/fake_supabase.py`): languages and diagrams, versions, status change, comment and reply placement, delete, reactions, paragraph comments, and a database without the `para` column.

```bash
.venv/bin/pip install -r requirements-dev.txt
PW_CHANNEL=chrome .venv/bin/python -m unittest discover -s tests -v   # uses your Chrome; CI installs Playwright's Chromium
```

RFCs created on the site are covered by `tests/test_live.py` (new-RFC page, viewer, edit, index, hostile content); the migrations are parsed by `tests/test_sql.py`. The Python and JavaScript renderers are compared by `tests/test_parity.py`; `tests/test_render_js.py` covers the single-file reader and the sanitizer (including XSS vectors).

The page scripts live in `assets/js/` as ES modules (`main.js` is the entry; `state.js` holds the config and the only shared mutable state).

## Add a new RFC

New RFCs are written in Markdown (format and rules: [`docs/spec/rfc-format.md`](docs/spec/rfc-format.md)). One-time setup of the tools:

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt   # then use .venv/bin/python below
```

```bash
.venv/bin/python tools/new_rfc.py --pt "Título" --en "Title" --zh "标题" --author "Gleison"
```

This takes the next free `PHZ-NNNN` and copies [`templates/rfc/`](templates/rfc) to `rfcs/<ID>/`: `rfc.json` (title, summary, status, authors, reviewers, version) and `rfc.pt.md`, `rfc.en.md`, `rfc.zh.md` with the 10 standard sections. Every spot to fill is marked `TODO:`.

1. Fill `rfc.pt.md` (Portuguese first), then translate to `rfc.en.md` and `rfc.zh.md` with the same sections, paragraphs, diagrams and code blocks.
2. Fill `summary`, `reviewers` and `systems` in `rfc.json`.
3. Check: `.venv/bin/python tools/check_rfc.py <ID>` (leftover `TODO:`, section ids, the same number of paragraphs/tables/diagrams in the three languages, links). The build runs the same check and stops on errors.
4. Preview: `.venv/bin/python tools/build.py && python3 -m http.server -d dist 8000`.
5. `git add rfcs/<ID> && git commit -m "<ID>: …" && git push`.

With Claude Code, the `phiz-rfc` skill follows this workflow: it reads the documents you give it, fills the template, translates, runs the check and builds.

Open it as a pull request if you want review before it appears in the index.

## The single-file RFC and the browser renderer

An RFC can also be written as **one `.md` file** with a metadata block and the three languages ([`docs/spec/rfc-bundle.md`](docs/spec/rfc-bundle.md); template: [`templates/bundle/RFC.md`](templates/bundle/RFC.md); prompt to give any AI together with your documents: [`templates/bundle/PROMPT.md`](templates/bundle/PROMPT.md)). The file is read and rendered **in the browser** by `assets/js/render/` (markdown-it and DOMPurify from `assets/vendor/`), with no raw HTML and sanitized output, because it comes from people outside the team. That renderer is a port of `tools/rfc_md.py`; `tests/test_parity.py` renders every RFC with both and fails when they differ, so a change to one renderer has to be made in the other.

## RFCs created on the site

Anyone can create an RFC from the site, with no account and no code: **＋ Nova RFC** on the index (`/nova/`) walks through four steps: download the template, ask an AI to fill it in (the page shows a ready prompt), upload the file (checked in the browser, with a preview in the three languages), and say who wrote it (author and collaborators). The RFC is stored in Supabase and shown at `/rfc/?id=PHZ-NNNN` straight away, with comments, reactions, status and version history; **Nova versão** on its page uploads a new version (anyone can; every version is kept). It appears in the index next to the repository RFCs. Format: [`docs/spec/rfc-bundle.md`](docs/spec/rfc-bundle.md).

1. **Database**: apply [`20261022000000_live_rfcs.sql`](supabase/migrations/20261022000000_live_rfcs.sql) (it creates the shared id sequence, the revisions and the functions the page calls). Until then the page says it cannot publish.
2. **Take one down**: **Table Editor → rfc_ids**, set `hidden = true` on the row.
3. `tools/new_rfc.py` now asks the same sequence for the next id, so a repository RFC and a site RFC never collide (it falls back to the next id in the repository, with a warning, when the database cannot be reached).

## Versions

Every RFC has a version (`MAJOR.MINOR`, in `rfc.json` → `version`) and a changelog. The page header shows it (`v1.1 ▾`); clicking it lists every version with its date and a note in the three languages. Old versions stay available as read-only pages at `/rfcs/<ID>/v<version>.html`, with a banner pointing to the current one (no new comments on them).

To publish a new version of an RFC that was already published:

```bash
python3 tools/new_version.py PHZ-0001 --note-pt "O que mudou" --note-en "What changed" --note-zh "变更内容"
```

Run it **before** editing, with the last published version committed. It archives the RFC as it is in git HEAD (`rfc.*.md` and `rfc.json`) into `rfcs/<ID>/versions/<current>/`, bumps the version (minor by default; `--major`, or `--set 2.0`) and adds the changelog entry. Then edit `rfcs/<ID>/rfc.*.md`, check, rebuild and commit as usual. Typo fixes do not need a new version.

Notes: archived pages reuse the RFC's current `mocks/` and OpenAPI files. Comments are keyed by section id and shared by all versions, so keep section ids stable.

## Status

The starting status is `status` in `rfc.json`; after the first change made on the page (see above) the live status in Supabase wins. Allowed values:
`draft` · `in-review` · `approved` · `implemented` · `rejected` · `superseded`

## Preview locally

```bash
.venv/bin/python tools/check_rfc.py
.venv/bin/python tools/build.py
python3 -m http.server -d dist 8000   # http://localhost:8000
```

Open the site through the local server (as above), not from the `dist/index.html` file: the page scripts are ES modules, which browsers do not load from `file://`.

Every pull request runs the same check and build, plus the smoke tests (`.github/workflows/check.yml`); the site itself is deployed only from `main` (`pages.yml`).

## Notes

- Every RFC is Markdown (`rfcs/<ID>/rfc.{pt,en,zh}.md`) rendered by `tools/build.py`; nothing generated is committed. Versions archived before the Markdown format (PHZ-0001 v1.0–v1.6, PHZ-0002 v1.0) remain as frozen HTML pages in `versions/<v>/source.html`.
- PHZ-0001 ends with a Swagger UI. The spec comes from `rfcs/PHZ-0001/openapi_gen.py` (`build(lang)`), and the build publishes `openapi.{pt,en,zh}.yaml` next to the page (needs `PyYAML`, in `requirements.txt`; Swagger UI itself is loaded from jsDelivr).
- The screens of PHZ-0001 sections 03 (WhatsApp reference) and 04 (PhizChat opt-in, boards P* and Q*, which also use `phiz.css`) come from `sources/PHZ-0001/whatsapp-design/` (English `.dc.html` files plus `i18n.json` with PT-BR and 中文). Render them with `python3 tools/render_wa_mocks.py sources/PHZ-0001/whatsapp-design rfcs/PHZ-0001/mocks` (needs playwright, beautifulsoup4 and a CJK font such as Noto Sans CJK SC).
- `.github/workflows/keepalive.yml` reads one row from Supabase every Monday and Thursday, because free projects are paused after about a week without activity (it fails, and GitHub emails you, if the project is already paused: restore it in the Supabase dashboard).
- Mermaid is bundled in `assets/` (v10.9.1), so diagrams do not depend on a CDN. Fonts and Swagger UI load from Google Fonts and jsDelivr.
- Reachability from mainland China is not guaranteed for github.io, Google Fonts, Supabase or giscus. If a reviewer there has trouble, send them the PDF/HTML of the RFC directly.
- Prefer private hosting later? The same `dist/` folder works unchanged on Cloudflare Pages + Access or S3 + CloudFront.
