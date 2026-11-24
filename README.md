# PHIZ RFCs

The PHIZ RFC site: a Next.js app on Vercel (<https://phiz-rfcs.vercel.app>), with the RFCs, comments and pictures in Supabase.

- **Index** (`/`): every RFC with status, authors and reviewers; filter by status; PT-BR / EN-US / 中文.
- **RFC page** (`/rfc/?id=PHZ-0001`): the document, with Mermaid diagrams and a **Comment** button on every section.
- **Comments**: saved on the page itself (Supabase), Confluence-style: comment on a section or select a passage and comment on it; replies, highlighted passages and a counter per section. No GitHub account needed. Comments are shared across the three languages. Fallbacks: [giscus](https://giscus.app) if configured, otherwise a pre-filled GitHub Issue.

> ⚠️ **Until sign-in arrives (phase 2 of [`docs/spec/v2`](docs/spec/v2/README.md)), the site and every RFC are readable by anyone with the address.**
> Do not commit or publish secrets, internal hostnames, customer data or anything not meant to be public. `noindex` keeps search engines away.

## Set up (one time)

1. **Vercel**: in the company team, import the GitHub repository with **Root Directory** `apps/web` (`apps/web/vercel.json` installs from the
   repository root). Every push to `main` deploys <https://phiz-rfcs.vercel.app>; every pull request gets a preview address.
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

### Automatic translation of theme texts

The texts people write in a theme (title, what it is, progress, the three slide answers) are translated by the same function, with the same
Cloudflare account. A language a person typed is the source for the languages that are empty or already machine translations; what a person
typed is never overwritten, and a machine translation that someone edits becomes a person's text (the page marks machine translations with
**auto**). To turn it on, after applying [`20261125000000_theme_translations.sql`](supabase/migrations/20261125000000_theme_translations.sql):

1. Redeploy the function with **both files** of [`supabase/functions/translate-comment`](supabase/functions/translate-comment): `index.ts` and `themes.ts`
   (in the dashboard editor, add `themes.ts` as a second file next to `index.ts`).
2. **Database → Webhooks → Create a new hook**: table `themes`, events **Insert** and **Update**, type **Supabase Edge Functions** → `translate-comment`,
   method `POST`, HTTP header `x-webhook-secret: <same secret>`.

What is translated is decided by [`themes.ts`](supabase/functions/translate-comment/themes.ts), tested by `tests/test_translate_plan.py`.

The same webhook also translates the weekly updates, blockers and decisions: create one webhook per table, **`theme_updates`** (Insert),
**`theme_blockers`** and **`theme_decisions`** (Insert and Update), all calling `translate-comment` with the same header (and redeploy the function:
`index.ts` and `themes.ts` changed).

### Changing the status from the page

The status badge in the header of each RFC is a button (`EM REVISÃO ▾`): pick a status, type your name once (remembered in the browser) and it changes for everyone, with no rebuild. The index, the header badge and the status pill and eyebrow in the three languages all follow the live status. There is no login: anyone with the link can change it, so every change is kept in `rfc_status_log` with the name typed, an origin rate limit (10 a minute) applies, and archived versions (`v1.0.html`) keep the status they had.

1. **Database**: apply [`20261019000000_status.sql`](supabase/migrations/20261019000000_status.sql). It creates `rfc_status_log` (append-only) and the view `rfc_status_current`.
2. Nothing else to configure; the page uses the same Supabase keys as the comments. Until step 1 is done, the page shows Draft and changing it fails with an error message.
3. **Undo a wrong change**: **Table Editor → rfc_status_log**, delete the row; the previous one becomes current.

### Deleting comments

Every comment (and reply) has a **Excluir / Delete / 删除** link; it asks once and then removes the comment for everyone. Deleting a comment also removes its replies. There is no login: anyone with the link can delete, so “delete” only **hides** the comment (`hidden = true`, with `hidden_at`, `hidden_by` and an origin rate limit of 10 a minute); nothing is erased from the database.

1. **Database**: apply [`20261020000000_hide_comments.sql`](supabase/migrations/20261020000000_hide_comments.sql). It adds the columns `hidden_at` and `hidden_by` and the function `hide_rfc_comment`, which is the only way the page can hide a comment. Until this is done, the button shows “Could not delete”.
2. **Restore a comment**: **Table Editor → rfc_comments**, set `hidden = false` on the comment and on its replies (they are hidden together).

### Comments on each paragraph, and emoji reactions

- **Per paragraph**: every paragraph, list item, table, diagram and code block has a small 💬 button in the right margin (on hover; with a counter once it has comments). It opens a comment box right under that paragraph. Paragraphs are numbered per section in document order (`para` 0, 1, 2…), so the same number points to the same paragraph in PT-BR, EN-US and 中文: **keep the structure of the three languages aligned** (same paragraphs in the same order). If you add or remove a paragraph in a published RFC, comments after that point move with the numbers, so prefer a new version for big edits. The section list still shows everything, with a `¶ N` tag on paragraph comments (click it to jump to the paragraph).
- **Reactions**: each comment has `☺+` to react with 👍 ❤️ 👌 ✅ 🎉 👀 🙏 😄; reactions show as small counters and clicking one you gave takes it back. A reaction is saved as a reply that contains only an emoji, so **it counts as an answer** (“Sem resposta” in the comments list and on the comments page does not include it). Typing only an emoji as a reply does the same.

1. **Database**: apply [`20261021000000_paragraph_comments.sql`](supabase/migrations/20261021000000_paragraph_comments.sql): the `para` column and the insert trigger (replies inherit `para`; the rate limit is 15 a minute / 150 a day so reactions do not hit it). Until it runs, the page works as before without the paragraph buttons.
2. **Translation function**: redeploy [`supabase/functions/translate-comment`](supabase/functions/translate-comment/index.ts) (Edge Functions → translate-comment → paste the file → Deploy). It now skips emoji-only text, so reactions do not use the translation allowance.

## The phiz-rfc skill

The skill that helps write RFCs lives in the repository, in [`skills/phiz-rfc/`](skills/phiz-rfc), in two editions:

- **Maintainer edition** (`SKILL.md`): the full workflow in this repository (research the PHIZ code, write the file, check and publish with `tools/publish_rfc.py`). Install it with `ln -sfn ~/Projetos/phiz-rfcs/skills/phiz-rfc ~/.claude/skills/phiz-rfc`, so it follows the repository.
- **Site edition** (`site/SKILL.md`): self-contained, for people outside the repository. It fills `RFC.md` from their documents, ready to upload on **＋ Nova RFC**. The build packs it with the template and the references it needs into `phiz-rfc.zip`, and also as one text (`phiz-rfc-skill.md`, to paste as instructions into any AI). Both are offered on the new-RFC page (*Prefer a skill?*), with install steps for Claude Code, Claude and other AIs.

Edit the skill in the repository, not in `~/.claude`; the downloads are rebuilt on every deploy.

## Database migrations

The database is described by numbered files in [`supabase/migrations`](supabase/migrations) (`<timestamp>_<name>.sql`, the Supabase CLI convention), one per feature, applied in order:

| file | what it adds |
|---|---|
| `20261015000000_comments` | `rfc_comments`, insert rules, public-key permissions |
| `20261016000000_translations` | `translations` and `src_lang` (filled by the `translate-comment` function) |
| `20261019000000_status` | `rfc_status_log` and `rfc_status_current` (status changed from the page) |
| `20261020000000_hide_comments` | `hide_rfc_comment` (delete from the page = hide) |
| `20261021000000_paragraph_comments` | `para` (comment per paragraph), reactions and the current rate limits |
| `20261022000000_live_rfcs` | `rfc_ids`, `rfc_revisions` and the functions that create RFCs and versions (every RFC lives here) |
| `20261023000000_rfc_assets` | pictures of the RFCs (`rfc_assets`, `stage_rfc_asset`) |
| `20261024000000_more_images` | up to 160 pictures per RFC and a larger upload limit |
| `20261124000000_themes` | fronts, themes, execution items, dependencies, Jira links and the event log; the RFCs become themes (`/themes/`) |
| `20261125000000_theme_translations` | `themes.text_meta` (which languages of a text are machine translations) and `update_theme` keeping it |
| `20261126000000_weekly_updates` | weekly updates, blockers and decisions of the themes (`theme_updates`, `theme_blockers`, `theme_decisions`) and the functions that write them |
| `20261127000000_board_columns` | the B2B board: `stage_gates` (the V4 gates, seeded), `board_columns` (the ten default columns), `theme_gate_checks`, and the functions to move a card, tick a gate and configure columns |
| `20261128000000_attachments` | the attachments hub: a private Storage bucket `attachments` (50 MB a file, policies for the public key), the table `attachments` and `add_attachment` / `hide_attachment` |
| `20261129000000_attachments_archive` | `add_attachment` accepts `archive_version`, `archive_date`, `archive_note` (the archived pages of old RFC versions) |
| `20261130000000_theme_answers` | `themes.answers` (state of the three slide answers), `suggest_theme_answers`, `confirm_theme_answers`, and `update_theme` confirming a text a person wrote |

Every file is idempotent (`if not exists` / `or replace`), so applying all of them again is safe. To change the database, add a **new** file with a later timestamp; never edit one that has been applied. Apply a new file in the Supabase **SQL Editor** (paste and run) or with `supabase db push`.

## Themes

`/themes/` lists the **themes** by **front** (POP, API Platform, Mini-Apps, Payments, Product Center, then Outros); `/themes/PHZ-NNNN/` is the page
of one theme: type (project or standalone task), front, status, V4 stage, owner, dates, tags, the sentences and the three slide answers (each
written in the reader's language and kept per language), execution items on a four-column kanban, Jira links (paste the address; the page shows the
issue key and opens Jira in another tab), dependencies on themes of other fronts, the link to the theme's RFC and the history of every change.
The front of a theme and the fronts themselves (name, scope, order) are editable. An RFC that is a theme shows the theme's status and stage in its header (the old status picker is only for RFCs without a theme), and a new RFC created on **＋ Nova RFC** is also created as a theme, in the front chosen there (Outros by default). Plan and decisions: [`docs/spec/v2`](docs/spec/v2/README.md).
Apply [`20261124000000_themes.sql`](supabase/migrations/20261124000000_themes.sql) first: it also turns the published RFCs into themes.

Each theme page also has the **weekly update** (the progress sentence, what moved forward, the next step, and the status and estimate, which change the
theme; every update is kept), **blockers** and **decisions** (who, by when, and a flag that sends them to the top of the executive view). `/executive/`
is the **executive view**: what needs the leadership on top, then every theme by front with its progress sentence, owner, status, estimate, next
milestones (execution items marked as milestones) and flags (*no update this week*, open blockers and decisions), with filters. **Reader mode**
(button in the header, remembered; `?mode=reader` or `?mode=edit` in a link) hides every control to create or edit.

`/board/` is the **B2B board**: the project themes of every front (a swimlane per front) on the columns of the board, each column mapping to one of the ten
V4 stages. A card moves by drag or by its *Move to* menu; every move is one `move` event (from/to column and stage, who, the open gates, and a reason
when the move skips a stage of the theme's route or leaves it). **Gates** (the checklist of the standard, on each project theme) are ticked with an
evidence; an open gate warns on the card and never blocks. **Columns** are configurable (name in three languages, stage, optional WIP limit, order);
there are no admins until the sign-in phase, so for now anyone with a name can configure them.

Each theme page has an **Attachments** panel and `/attachments/` lists the attachments of every theme (latest editions, with filters: type, front, stage, who, text). An
attachment is a **file** (up to 50 MB, straight from the browser to the private Storage bucket; the row keeps the size and type Storage reports and a SHA-256
checksum), a **note** (Markdown) or a **link** (https). A new one can be an **edition** of another (the list shows the latest and keeps the earlier ones under
it), can be tied to a **stage** (it then shows in that stage's gate checklist) and to an execution item. Pictures, audio and video play in the page through a
signed address that expires after five minutes; everything else, and HTML always, is only offered as a download (`?download=` makes Storage answer with
`Content-Disposition: attachment`), so no attachment is ever rendered on the app's origin. Removing hides the row; the file stays in Storage. Notes are shown
as plain text for now. The pictures of the theme's RFC are listed in a group of their own.

**Slides and AI suggestions.** The three answers of a theme (problem, solution, success) have a state: *missing*, *suggested by the AI, not confirmed* or *confirmed*
(by a person, with who and when). The **Summary for the slides** panel of a theme runs **Suggest with AI**: the Edge Function
[`suggest-summary`](supabase/functions/suggest-summary/index.ts) reads the theme's RFC, notes, text attachments and the last weekly updates, asks a Cloudflare
Workers AI model (the account the translation already uses) for the three answers, and keeps an answer **only if a quotation it gives is found word for word in the
document it names**; anything else becomes *missing*, with a sentence saying what is missing. The page stores the suggestions with their sources; a suggestion
never replaces a confirmed answer or a text a person wrote, and writing or correcting the text in the theme form confirms it. `/slides/` exports a **.pptx** with one slide
per chosen theme (projects and standalone tasks): title, front, owner, status, estimate, Jira links and the three answers in the language chosen at export;
a missing answer reads "Not explained yet: …", an unconfirmed suggestion is marked. The slide look is neutral until the company's template file is received.
To turn the suggestion on: apply `20261130000000_theme_answers.sql`, then deploy the function with **both files** (`index.ts`, `suggest.ts`), JWT verification **off**
(the page calls it with the public key; it limits itself to 3 runs an hour per theme and 40 in all). It uses the secrets `CF_ACCOUNT_ID` and `CF_API_TOKEN` of
the translation (optional `CF_SUGGEST_MODEL`, default `@cf/meta/llama-3.3-70b-instruct-fp8-fast`). What is read and how the answer is checked is
[`suggest.ts`](supabase/functions/suggest-summary/suggest.ts), tested by `tests/test_suggest.py`.

**Sign-in** (phase 2, docs/spec/v2/login.md). `/login/` signs a person in with their `@phizchat.com` e-mail: one message with a link and a 6-digit code. The session lives in the browser (`localStorage`
`phiz-auth`) and `assets/auth.js` — loaded first on every page — wraps `fetch` so every request to Supabase carries the token; with a session the account (and *Sign out*) is in the menu, and the name
written on changes is the account's. Whether pages **require** sign-in is the switch `auth.required` of `site.config.json` (false today: nothing changes for anyone until the database is locked — slice 2 —
and the switch turned on together, slice 3). Before that, open `/login/` to try it; `localStorage["phiz-auth-required"] = "1"` makes only your own browser strict. Needs custom SMTP and the redirect URLs
in Supabase (the prerequisites of the spec). **The window of sign-in is long:** the access token (1 h) is renewed silently, before it is needed (when the tab comes back, when the network comes back, every 4 minutes in an open tab, one tab at a time), and the session ends only when Supabase says the refresh token is invalid, never for a network error or a `5xx`; on the Free plan refresh tokens do not expire, so a person stays signed in as long as they come back. Do not set a short time-box or inactivity timeout in Supabase (Authentication → Sessions).

`/roadmap/` is the **roadmap**: every theme over time, grouped by front, drawn from the theme's own dates (a bar from its start to its estimated
completion, a marker when only one of them is set) and from the execution items marked as milestones (diamonds, filled when done), with a line for today,
an *Overdue* flag on open themes whose estimate has passed, and the themes with no dates listed under it. It stores nothing: a date changed on a
theme shows on the next load. Filters: status, front, tag, owner.

`/metrics/` shows the **flow metrics**, all computed in the browser from the event log (nothing is typed by hand; times in calendar days): lead, delivery and cycle
time (median and 85th percentile), time in each stage with the WIP against the board's column limits, throughput per week, the cumulative flow diagram
(CFD), aging WIP against the 85th percentile of the finished themes, blocked time, moves with open gates and the triage rule (leave 01 within 2 business days),
plus the same for the execution items (lead, cycle, throughput, WIP per column, aging and the CFD of one project). Each block explains its definition and lists
the themes behind it. Filters: period, level (themes, items, both), front, tag, route, owner. Themes whose history was never recorded (the imported ones) are
*estimated* and left out of the times unless the box is ticked. The formulas are in [`apps/web/lib/metrics.ts`](apps/web/lib/metrics.ts) and are tested on
fixed histories in `tests/test_metrics.py`.

## The app (Next.js)

`apps/web` (plan in [`docs/spec/v2`](docs/spec/v2/README.md)). The pages of today are generated by TypeScript (`apps/web/server/site`, a port
of the old Python build); the page scripts run unchanged from `public/assets`, filled by `apps/web/scripts/prepare.ts` before every build
(assets, template and skill zip).

```bash
npm install          # once (Node 24+)
npm run dev          # http://localhost:3000
npm run build && npm start
```

## Tests

The page scripts have smoke tests that run in a real browser against the built site, with the Supabase API replaced by a small in-memory fake (`tests/fake_supabase.py`): languages and diagrams, versions, status change, comment and reply placement, delete, reactions, paragraph comments, and a database without the `para` column.

```bash
.venv/bin/pip install -r requirements-dev.txt
PW_CHANNEL=chrome .venv/bin/python tools/run_tests.py                       # the whole suite in parallel (builds once; --workers N)
PW_CHANNEL=chrome .venv/bin/python -m unittest discover -s tests -v   # the same tests one by one; uses your Chrome, CI installs Playwright's Chromium
SITE_URL=https://phiz-rfcs.vercel.app PW_CHANNEL=chrome .venv/bin/python -m unittest discover -s tests   # against a deployment (or a preview)
```

RFCs created on the site are covered by `tests/test_live.py` (new-RFC page, viewer, edit, index, hostile content); the migrations are parsed by `tests/test_sql.py`. The Python and JavaScript renderers are compared by `tests/test_parity.py`; `tests/test_render_js.py` covers the single-file reader and the sanitizer (including XSS vectors).

The page scripts live in `assets/js/` as ES modules (`main.js` is the entry; `state.js` holds the config and the only shared mutable state).

## Where the RFCs live

**In the database.** Each RFC is one file (a metadata block and the content in PT-BR, EN-US and 中文; [`docs/spec/rfc-bundle.md`](docs/spec/rfc-bundle.md), template [`templates/bundle/RFC.md`](templates/bundle/RFC.md)) stored as append-only revisions (`rfc_revisions`), with its pictures in `rfc_assets`. The site is static: the index (`/`), the page of an RFC (`/rfc/?id=PHZ-NNNN[&v=1.1]`), the new-RFC page (`/nova/`) and the comments page read the database in the browser and draw everything there (`assets/js/render/` is the renderer, with DOMPurify). Adding or changing an RFC needs no build and no pull request.

## Add an RFC, or a new version

Anyone can, with no account: **＋ Nova RFC** on the index (`/nova/`) walks through four steps: download the template (or the `phiz-rfc` skill), ask an AI to fill it in (the page shows a ready prompt), upload the file (checked in the browser, with a preview in the three languages; pictures and diagrams are attached on the same page) and publish with your name and the collaborators' names. The RFC gets the next `PHZ-NNNN`, shows in the index as a Draft, and anyone with the link can read it, comment on it and change its status.

A **new version** is made from the green **✎ New version** button in the header of the RFC (it opens `/nova/?edit=PHZ-NNNN` with the current text). Every publication is a version (1.0, 1.1…); nothing is overwritten. The version menu (`v1.1 ▾`) lists them with date, author and note, and any version opens read-only at `/rfc/?id=PHZ-NNNN&v=1.0`.

From the terminal (the same checks and calls as the page; images are read from the folder of the file):

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt     # once
.venv/bin/python tools/publish_rfc.py rfc.md --check
.venv/bin/python tools/publish_rfc.py rfc.md --by "Gleison"                            # a new RFC
.venv/bin/python tools/publish_rfc.py rfc.md --by "Gleison" --id PHZ-0003 --note "O que mudou"   # a new version
```

With Claude Code, the `phiz-rfc` skill ([`skills/phiz-rfc`](skills/phiz-rfc)) follows this workflow: it reads the documents you give it, fills the template, translates, checks and publishes.

1. **Database**: apply [`20261022000000_live_rfcs.sql`](supabase/migrations/20261022000000_live_rfcs.sql) (shared id sequence, revisions, the functions the page calls), [`20261023000000_rfc_assets.sql`](supabase/migrations/20261023000000_rfc_assets.sql) (pictures) and [`20261024000000_more_images.sql`](supabase/migrations/20261024000000_more_images.sql) (up to 160 pictures per RFC). Until then the page says it cannot publish.
2. **Take an RFC down**: **Table Editor → rfc_ids**, set `hidden = true` on the row (`false` brings it back).
3. **Pictures**: `![alt](asset:name.png)` in the text, PNG/JPEG/WebP, up to 160 per RFC and 1 MB each (the page shrinks bigger ones); an old version keeps the picture it had.

## The RFCs that came from the repository

PHZ-0001 and PHZ-0002 were first written as Markdown folders (`rfcs/<ID>/`); a one-off importer moved them to the database, rewriting their
raw HTML as the Markdown of the site, attaching their pictures and keeping version numbers, reviewers and dates. The folders, the importer
and the OpenAPI generator are gone from the repository (they are in the git history). What the database did not hold, the versions archived as HTML pages
(PHZ-0001 v1.0–v1.6, PHZ-0002 v1.0), the pictures they use, and the OpenAPI reference of PHZ-0001 (`openapi.{pt,en,zh}.yaml` and the Swagger page), is now
**attachments** of those two themes (the pages as self-contained HTML, the pictures in one ZIP, to be extracted next to them), and the repository holds no RFC
content. The version menu of the RFC page still lists the archived versions (from the attachments that carry `archive_version`) and each leads to the theme's
attachments. The old addresses `/rfcs/<ID>/`, `/rfcs/<ID>/v<version>.html`, `/rfcs/PHZ-0001/openapi/`… redirect: the first to the RFC page, the others to the theme's attachments.

## Status

A new RFC starts as `draft`; the status is changed from the badge in the header of the page (see above) and kept in Supabase. Allowed values:
`draft` · `in-review` · `approved` · `implemented` · `rejected` · `superseded`

## Pull requests and deploys

Every change follows three rules — **spec first (SDD), tests, no regression** — written in [`CLAUDE.md`](CLAUDE.md) and [`docs/spec/v2/guardrail.md`](docs/spec/v2/guardrail.md) and checked by `python3 tools/guardrail.py --base origin/main` (CI job `guardrail`, and a hook of Claude Code before `git push` / `gh pr create`).

Every pull request runs the build, the type check and the smoke tests (`.github/workflows/check.yml`) and gets a Vercel preview; `main` is
deployed by Vercel.

## Notes

- Every RFC is a single Markdown file in the database, drawn in the browser; nothing generated is committed. The versions archived before the Markdown format (PHZ-0001 v1.0–v1.6, PHZ-0002 v1.0) are attachments of their themes (see *The RFCs that came from the repository*).
- The OpenAPI of PHZ-0001 (`openapi.{pt,en,zh}.yaml` and the Swagger page) is an attachment of the theme; the address the RFC links to (`/rfcs/PHZ-0001/openapi/`) redirects to the attachments.
- The screens of PHZ-0001 sections 03 (WhatsApp reference) and 04 (PhizChat opt-in, boards P* and Q*, which also use `phiz.css`) come from `sources/PHZ-0001/whatsapp-design/` (English `.dc.html` files plus `i18n.json` with PT-BR and 中文). Render them with `python3 tools/render_wa_mocks.py sources/PHZ-0001/whatsapp-design rfcs/PHZ-0001/mocks` (needs playwright, beautifulsoup4 and a CJK font such as Noto Sans CJK SC).
- `.github/workflows/keepalive.yml` reads one row from Supabase every Monday and Thursday, because free projects are paused after about a week without activity (it fails, and GitHub emails you, if the project is already paused: restore it in the Supabase dashboard).
- Mermaid is bundled in `assets/` (v10.9.1), so diagrams do not depend on a CDN. Fonts and Swagger UI load from Google Fonts and jsDelivr.
- Reachability from mainland China is not guaranteed for vercel.app, Google Fonts, Supabase or giscus. If a reviewer there has trouble, send them the PDF/HTML of the RFC directly.
