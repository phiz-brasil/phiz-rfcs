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
  app/                    routes: / , /rfc, /nova, /comments, (phase 3+) /themes, /executive, /board, /roadmap, /metrics
  components/             React components
  server/                 backend: db access, services (themes, updates, flow, metrics, export, ai, translation), auth helpers; no React here
  middleware.ts           session and redirects
packages/render/          the RFC renderer, sanitizer and checks (today assets/js/render/, moved to TypeScript)
packages/spec-tests/      the compatibility suite (Playwright, TypeScript), runs against any base URL
supabase/                 migrations (numbered, as today) and functions
docs/spec/                specs
legacy/                   what only the old site needs while it lives (removed at the end of phase 1)
```

- Package manager: npm workspaces (no extra tool to install). Node 24 or newer. Tests: Vitest (units), Playwright (pages). Types run in CI.
- The Python tools leave with the static site. `tools/import_rfcs.py` and `tools/publish_rfc.py` are replaced by `pnpm` scripts in phase 1
  (publishing from the terminal stays possible, see compatibility).
- The archived HTML pages of PHZ-0001 and PHZ-0002 and the OpenAPI page are copied as static files (`apps/web/public/rfcs/…`), so their
  addresses keep working.

### Rendering

The renderer (`assets/js/render/`) is already ES modules with no build step; it moves to `packages/render` in TypeScript with the same
output. The parity tests against the Python renderer become snapshot tests of the TypeScript renderer on the same fixtures (the repository
RFCs, `tests/fixtures/syntax.md`, the template), generated once from the current output, so phase 1 proves nothing changed.

## Access (phase 2)

- **Only `@phiz.com`.** First with **sign-in by e-mail link** (Supabase Auth magic link): it needs no company IT and nothing but the domain
  check. **Microsoft sign-in** (Supabase Auth, Azure provider, single tenant) is added when the administrator of the company's Microsoft tenant
  registers the app (client id, secret, redirect URL `https://<project>.supabase.co/auth/v1/callback`); both lead to the same account, keyed by
  e-mail (decision of 2026-11-23: Microsoft is secondary for now).
- **The domain is checked three times**, so no single check is load-bearing: the sign-in form; a database hook (`before user created`) that
  refuses any e-mail outside the domain; row security that requires a signed-in user with a row in `profiles`.
- **No anonymous access.** Phase 2 revokes every grant to `anon` and replaces the policies with `authenticated` ones. The publishable key stays
  in the app, but without a session it reads nothing.
- **Sessions** are cookies set by `@supabase/ssr`; the middleware sends anyone without a session to `/login` and back to the address they
  asked for (deep links to a comment keep working after sign-in).
- **Names.** Today people type a name to comment, change a status or publish. After sign-in the name comes from the account; the typed name
  field goes away. Old rows keep the names they have.
- **Tools.** Publishing from the terminal uses a personal token created in the app, never the service key.

### Roles and reader mode

- Everyone with `@phiz.com` is a **member** and can do everything: read, comment, create and edit themes, items, updates and RFCs, attach files,
  move cards (decision of 2026-11-23). An **admin** flag (by e-mail list) adds board configuration, moderation and role changes.
- **Reader mode** is a switch, not a role: it hides every create, edit and update control on the executive view, theme pages and roadmap, for
  people who only read (`domain.md`, Views).

## Security

- Repository private from phase 1 (Vercel deploys private repositories of the organization). The public history keeps what was already
  pushed; if anything there is sensitive, it needs a history rewrite, which is a separate decision.
- Attachments in a **private** Storage bucket, served by signed URLs that expire; uploads checked for size (proposal: 50 MB) and stored with
  their real content type. HTML attachments are served as downloads (`Content-Disposition: attachment`), never rendered on the app's origin.
- Rendered RFC text keeps the current rules: no raw HTML, DOMPurify, https-only images.
- AI calls are server-side only, with the key in Vercel's encrypted environment; the prompt says to answer "not found" instead of guessing.
- Secrets live in Vercel and Supabase settings, never in the repository. The service-role key is used only by migrations and admin scripts.

### How phase 1 is built

- The four pages of today (index, RFC, new RFC, comments) are route handlers that answer with the same HTML the old build wrote
  (`apps/web/server/site/pages.ts`, a port of the old `tools/build.py`); until the cutover a check proved them byte for byte the same. The page scripts keep running unchanged from `public/assets`. React pages start with the new features (phase 3 on).
- `apps/web/scripts/prepare.ts` fills `public/` before every build: the repository's `assets/`, the template, the skill zip, the files of
  `rfcs/` the archived pages use, and the archived pages themselves, frozen in `apps/web/legacy/` (rendered once by the old build).
- `/rfcs/PHZ-NNNN/` is a route that redirects to `/rfc/?id=…` with the rest of the query; `/rfcs/PHZ-0001/openapi/` is rewritten to its file.
- The compatibility suite stays the Python one for now: `tests/support.py` builds the Next.js app and runs `next start`, and the same 85 tests
  run against it (`SITE_URL=` against any deployment). Porting the suite to TypeScript is
  left for when the Python tools retire (phase 2), so phase 1 changes one thing at a time.
- The cutover (done): production on `https://phiz-rfcs.vercel.app` (Vercel team PhizChat, Root Directory `apps/web`); GitHub Pages only
  serves `pages-redirect/`, which sends every old address to the same path there; the old build is removed. Making the repository private is
  the step left (see below).

### Making the repository private

GitHub Pages works on private repositories only on paid GitHub plans. If the organization is on the free plan, keep the redirect alive by
moving it to a public repository of its own: rename this repository (for example `phiz-portal`; GitHub and Vercel follow the rename), make it
private, create a new public repository named `phiz-rfcs` with only `pages-redirect/` and `pages.yml`, and turn Pages on there. The old
address `https://phiz-brasil.github.io/phiz-rfcs/…` is then served by the new repository.

## Acceptance (phase 1 and 2)

- Phase 1: the compatibility suite passes against the preview deployment; every old address listed in `compatibility.md` answers as
  specified; the Pages workflow is removed and the repository is private.
- Phase 2: a request without a session reads nothing from the API (tested with the publishable key directly); a non-`@phiz.com` account
  cannot be created; a member who is not admin cannot change board columns; the compatibility suite passes when signed in.
