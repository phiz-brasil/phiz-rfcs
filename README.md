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
   2. **SQL Editor → New query**, paste [`supabase/schema.sql`](supabase/schema.sql) and run it. It creates `rfc_comments`, the access rules and a rate limit (5 per minute, 50 per day per origin).
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

### Automatic translation of comments (DeepL)

Comments are shown in the language selected on the page (PT-BR, EN-US or 中文), with a *Machine translation · Show original* note. Translations are made once on the server and stored with the comment, so every reader sees the same text in any browser. Until this is set up, comments simply appear as written.

1. **Database**: in the Supabase **SQL Editor**, run [`supabase/schema.sql`](supabase/schema.sql) again (safe to re-run) or only its last block, “Tradução automática”. It adds the read-only columns `translations` and `src_lang`.
2. **DeepL key**: create an account at <https://www.deepl.com/pro-api> (the Free plan covers 500,000 characters a month) and copy the API key (Free keys end with `:fx`).
3. **Function**: deploy [`supabase/functions/translate-comment`](supabase/functions/translate-comment/index.ts) with JWT verification **off** (the webhook authenticates with a shared secret instead):

   ```bash
   supabase login
   supabase link --project-ref <project ref, from the Supabase URL>
   supabase secrets set DEEPL_API_KEY=<DeepL key> TRANSLATE_WEBHOOK_SECRET=<long random string>
   supabase functions deploy translate-comment --no-verify-jwt
   ```

   Without the CLI: **Edge Functions → Deploy a new function → Via editor**, name it `translate-comment`, paste the file, turn off *Verify JWT*, and add both secrets under **Edge Functions → Secrets**.
4. **Webhook**: **Database → Webhooks → Create a new hook**: table `rfc_comments`, event **Insert**, type **Supabase Edge Functions** → `translate-comment`, method `POST`, HTTP header `x-webhook-secret: <same secret>`.
5. **Existing comments**: translate the ones already posted (repeat until it returns `{"translated":0}`; 200 per call):

   ```bash
   curl -X POST "https://<project ref>.supabase.co/functions/v1/translate-comment" \
     -H "x-webhook-secret: <same secret>" -H "Content-Type: application/json" -d '{"backfill":true}'
   ```

A new comment shows in its original language for a second or two, then in translation on the next load. Check the function's **Logs** in Supabase if translations do not appear (wrong key, missing secret or DeepL quota).

## Add a new RFC

```bash
python3 tools/new_rfc.py --pt "Título" --en "Title" --zh "标题" --short "Short title" --author "Gleison"
```

This takes the next free `PHZ-NNNN`, copies `sources/_template/` (10 standard sections in PT-BR, EN-US and 中文, with examples of every component) to `sources/<ID>/`, creates `rfcs/<ID>/rfc.json` and builds `rfcs/<ID>/source.html`. Then:

1. Write `sources/<ID>/content_pt.html`, then translate to `content_en.html` and `content_zh.html` (same section ids and the same number of diagrams; the build refuses otherwise). Code samples shared by the three languages go in `code.json` and are placed with `{CODE:name}`.
2. Fill `summary`, `reviewers` and `status` in `rfcs/<ID>/rfc.json`.
3. Build: `cd sources/<ID> && python3 build_rfc.py && cd ../.. && python3 tools/build.py`.
4. `git add sources/<ID> rfcs/<ID> && git commit -m "<ID>: …" && git push`.

With Claude Code, the `phiz-rfc` skill follows this workflow, including research in the PHIZ repos, diagrams, translation and checking the published page.

Open it as a pull request if you want review before it appears in the index.

## Versions

Every RFC has a version (`MAJOR.MINOR`, in `rfc.json` → `version`) and a changelog. The page header shows it (`v1.1 ▾`); clicking it lists every version with its date and a note in the three languages. Old versions stay available as read-only pages at `/rfcs/<ID>/v<version>.html`, with a banner pointing to the current one (no new comments on them).

To publish a new version of an RFC that was already published:

```bash
python3 tools/new_version.py PHZ-0001 --note-pt "O que mudou" --note-en "What changed" --note-zh "变更内容"
```

Run it **before** editing, with the last published version committed. It archives `rfcs/<ID>/source.html` as it is in git HEAD into `rfcs/<ID>/versions/<current>/`, bumps the version (minor by default; `--major`, or `--set 2.0`) and adds the changelog entry. Then edit `sources/<ID>/`, rebuild and commit as usual. Typo fixes do not need a new version.

Notes: archived pages reuse the RFC's current `mocks/` and OpenAPI files. Comments are keyed by section id and shared by all versions, so keep section ids stable.

## Status

Change `status` in `rfc.json` and push. Allowed values:
`draft` · `in-review` · `approved` · `implemented` · `rejected` · `superseded`

## Preview locally

```bash
python3 tools/build.py
python3 -m http.server -d dist 8000   # http://localhost:8000
```

## Notes

- `rfcs/PHZ-0002/source.html` is generated from `sources/PHZ-0002/` (`python3 build_rfc.py` in that folder).
- `rfcs/PHZ-0001/source.html` is generated from `sources/PHZ-0001/` (needs `swagger-ui-dist@5.17.14` for its CSS and `pyyaml`); the OpenAPI YAMLs next to it are generated by `openapi_gen.py`.
- The WhatsApp reference screens of PHZ-0001 (section 03) come from `sources/PHZ-0001/whatsapp-design/` (English `.dc.html` files plus `i18n.json` with PT-BR and 中文). Render them with `python3 tools/render_wa_mocks.py sources/PHZ-0001/whatsapp-design rfcs/PHZ-0001/mocks` (needs playwright, beautifulsoup4 and a CJK font such as Noto Sans CJK SC).
- Mermaid is bundled in `assets/` (v10.9.1), so diagrams do not depend on a CDN. Fonts and Swagger UI load from Google Fonts and jsDelivr.
- Reachability from mainland China is not guaranteed for github.io, Google Fonts, Supabase or giscus. If a reviewer there has trouble, send them the PDF/HTML of the RFC directly.
- Prefer private hosting later? The same `dist/` folder works unchanged on Cloudflare Pages + Access or S3 + CloudFront.
