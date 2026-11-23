# Spec v2: platform

Status: draft for review. Phases 1 and 2.

## Today, and why it has to change

A static site on GitHub Pages (Python build, about 9,000 lines of plain JavaScript and Python), with the browser talking to Supabase with the
public (publishable) key. Every rule lives in SQL functions and row security, because there is no server of ours.

That model reaches its limit with what is coming:

- **Nothing is private.** The repository is public (a free GitHub Pages site requires it), the key is in it, and anyone with the address can
  read every RFC, comment and picture through the API. The pictures of the first RFCs (32 MB) are in the public git history. Sign-in on the
  page alone would not change that: the data and the repository have to close too.
- **Secrets need a server.** The AI suggestions of the executive view need an API key; slide export builds files; neither can run in the
  browser with a public key.
- **Permissions need users.** Roles, "who moved this card", and the audit of gates need an authenticated user on every request.
- **The build already breaks on drafts.** Since 2026-11-20 every Pages deploy fails, because `rfcs/checkout-global/` (a draft written in the
  repository) has no `rfc.json`; the site serves the last good deploy (fixed separately from this spec).

## Target

```
 Browser ──► Vercel: Next.js app (TypeScript)
              ├─ pages (React, server-rendered shells + client islands for board, comments, editor)
              ├─ route handlers /api/* (the backend: domain services, AI, slide export, uploads)
              └─ middleware (session check, redirects of old addresses)
                    │
                    ▼
            Supabase: Postgres (row security, keyed to the signed-in user)
                      Auth (Microsoft / Entra ID, @phiz.com only)
                      Storage (attachments: private bucket, signed URLs)
                      Edge Function translate-comment (unchanged) + Cloudflare Workers AI
```

- **One deployable, two layers.** The frontend and the backend live in the same Next.js app on purpose: the team is small and a separate API
  service would double deploys, config and auth without a gain today. The split is in the code: UI in `app/` and `components/`, the
  backend in `server/` (services with no React), shared types and the renderer in packages. Moving `server/` behind its own service later is
  a refactor, not a rewrite.
- **Keep Supabase.** It already holds the data, the comment translation and the migrations, and gives Auth with Microsoft and Storage. Moving
  the database brings risk and no feature.
- **Vercel** builds every pull request into a preview address: that is where each phase is reviewed and tested before merge.

### Repository layout (phase 1)

```
apps/web/                 Next.js app
  app/                    routes: / , /rfc, /nova, /comments, (phase 3+) /items, /boards, /metrics
  components/             React components
  server/                 backend: db access, services (items, flow, metrics, export, ai), auth helpers; no React here
  middleware.ts           session and redirects
packages/render/          the RFC renderer, sanitizer and checks (today assets/js/render/, moved to TypeScript)
packages/spec-tests/      the compatibility suite (Playwright, TypeScript), runs against any base URL
supabase/                 migrations (numbered, as today) and functions
docs/spec/                specs
legacy/                   what only the old site needs while it lives (removed at the end of phase 1)
```

- Package manager: pnpm workspaces. Node 22 LTS. Tests: Vitest (units), Playwright (pages). Lint and types run in CI.
- The Python tools leave with the static site. `tools/import_rfcs.py` and `tools/publish_rfc.py` are replaced by `pnpm` scripts in phase 1
  (publishing from the terminal stays possible, see compatibility).
- The archived HTML pages of PHZ-0001 and PHZ-0002 and the OpenAPI page are copied as static files (`apps/web/public/rfcs/…`), so their
  addresses keep working.

### Rendering

The renderer (`assets/js/render/`) is already ES modules with no build step; it moves to `packages/render` in TypeScript with the same
output. The parity tests against the Python renderer become snapshot tests of the TypeScript renderer on the same fixtures (the repository
RFCs, `tests/fixtures/syntax.md`, the template), generated once from the current output, so phase 1 proves nothing changed.

## Authentication (phase 2)

- **Supabase Auth with the Azure provider**, single tenant (the company's Entra ID). The app registration in Entra ID is done by the tenant
  administrator (open question 7): client id, secret, redirect URL `https://<project>.supabase.co/auth/v1/callback`.
- **Only `@phiz.com`.** Three checks, so no single one is load-bearing: the Entra app is single-tenant; a database hook (`before user created`)
  refuses any e-mail outside the domain; row security requires the signed-in role (`authenticated`) plus a row in `profiles`.
- **No anonymous access.** Phase 2 revokes every grant to `anon` and replaces the policies with `authenticated` ones. The publishable key stays
  in the app, but without a session it reads nothing.
- **Sessions** are cookies set by `@supabase/ssr`; the middleware sends anyone without a session to `/login` and back to the address they
  asked for (deep links to a comment keep working after sign-in).
- **Names.** Today people type a name to comment, change a status or publish. After sign-in the name comes from the account; the typed name
  field goes away. Old rows keep the names they have.
- **Tools.** `publish` from the terminal uses a personal token (Supabase session from a device-code style sign-in, or a per-user API token
  created in the app), never the service key.

### Roles

| role | can |
|---|---|
| member (default for `@phiz.com`) | read everything, comment, react, create and edit items and RFCs, attach files, move cards, tick gates |
| admin | everything a member can, plus configure boards and columns, change roles, hide or restore anything, edit Jira base settings |

Stored in `profiles.role`; checked by row security in the database and by the route handlers. Open question 6: is a read-only role needed?

## Security

- Repository private from phase 1 (Vercel deploys private repositories of the organization). The public history keeps what was already
  pushed; if anything there is sensitive, it needs a history rewrite, which is a separate decision.
- Attachments in a **private** Storage bucket, served by signed URLs that expire; uploads checked for size (proposal: 50 MB) and stored with
  their real content type. HTML attachments are served as downloads (`Content-Disposition: attachment`), never rendered on the app's origin.
- Rendered RFC text keeps the current rules: no raw HTML, DOMPurify, https-only images.
- AI calls are server-side only, with the key in Vercel's encrypted environment; the prompt says to answer "not found" instead of guessing.
- Secrets live in Vercel and Supabase settings, never in the repository. The service-role key is used only by migrations and admin scripts.

## Acceptance (phase 1 and 2)

- Phase 1: the compatibility suite passes against the preview deployment; every old address listed in `compatibility.md` answers as
  specified; the Pages workflow is removed and the repository is private.
- Phase 2: a request without a session reads nothing from the API (tested with the publishable key directly); a non-`@phiz.com` account
  cannot be created; a member cannot change roles or board columns; the compatibility suite passes when signed in.
