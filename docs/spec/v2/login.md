# Spec v2: sign-in (phase 2)

Status: decided 2026-11-24 (owner: "Sim, login"). Replaces what `platform.md` says about `@supabase/ssr` cookies and a middleware (see *Decisions*). Built in three slices so that
nothing changes for anyone until the owner flips the switch.

## Goal

Only people with a `@phiz.com` account read or write anything. Today the publishable key is in every page, so anyone with the address can read and edit everything.

## Decisions

1. **Supabase Auth, e-mail first.** A person types their `@phiz.com` address; Supabase sends one message with a **link** and a **6-digit code**; either signs them in. Microsoft sign-in comes later
   (it needs the administrator of the company's Microsoft tenant, `README.md` open question 2). Everyone with the domain is a *member*; no profiles yet.
2. **Three locks, the last one is the real one.** (a) the sign-in page refuses other domains before sending anything; (b) the Supabase hook *before user created* (when the plan allows) refuses them
   at the source; (c) **the database**: every table, function and Storage policy requires a verified e-mail that ends in `@phiz.com`, so a non-member who got an account still reads nothing.
3. **The session is in the browser, not in cookies.** The pages are static shells; the data is behind the API, so the protection is in the database and a server-side middleware would add nothing.
   The session (`access_token`, `refresh_token`, `expires_at`, `user`) is kept in `localStorage` under `phiz-auth`; the access token is refreshed a minute before it expires; every request to Supabase sends the
   publishable key as `apikey` and the access token as `Authorization: Bearer`. A refresh that fails ends the session. (`@supabase/ssr` is not used.)
4. **The switch.** `site.config.json` → `auth.required` (false until go-live). When true, a page without a session sends the visitor to `/login/?next=<where they were>` and brings them back after sign-in
   (deep links to a comment keep working). `/login/` always works, so the sign-in can be tried before the switch. A person can also make *their own* browser strict with `localStorage["phiz-auth-required"] = "1"`
   (it only adds strictness; the tests use it).
5. **Names.** With a session, "your name" is the account's: `user_metadata.name`, else the part of the e-mail before `@` with `.`, `_` and `-` turned into spaces and capitalised (`ana.souza@phiz.com` → `Ana Souza`).
   The typed-name field disappears from Preferences; the account (e-mail and *Sign out*) takes its place. The functions keep their `p_by` argument and the client sends the account name there.
   Without a session (before go-live) nothing changes: the typed name stays.
6. **Where the code lives.** The same small module twice, because the old pages are plain scripts and the new ones are React: `assets/auth.js` (a classic script that defines `window.PHIZ_AUTH`, loaded first on every old page)
   and `apps/web/lib/auth.ts`. Both read and write the same `localStorage` entry and behave the same; `tests/` drive both through the real pages.

## Slices

| slice | what | reaches production how |
|---|---|---|
| 1 | the sign-in page, the session, the token on every request, the account in the menu, the guard behind the switch (`auth.required` false) | an ordinary PR; nobody notices, `/login/` can be tried |
| 2 | the database lock: `is_member()`, policies and grants moved from `anon` to members, membership checked inside every function and Storage policy, a `ping()` for the keep-alive job, the Edge Function `suggest-summary` checking the token | a migration written and tested, **applied only when the owner says**, after the prerequisites below |
| 3 | go-live: `auth.required` true, the migration applied, the checks of the acceptance run against production | one planned moment, with the owner |

## Prerequisites (owner, outside the code)

1. **Custom SMTP.** Supabase's built-in mailer only writes to members of the Supabase organization and at 2 messages an hour, so colleagues would not receive the link. A provider (Resend, SendGrid, the company's) and the sender's domain records (SPF/DKIM) are needed.
2. **Auth settings** (Authentication → URL configuration): *Site URL* `https://phiz-rfcs.vercel.app`, and in the redirect list `https://phiz-rfcs.vercel.app/login/` and `http://localhost:3000/login/`. Template *Magic Link* with both `{{ .ConfirmationURL }}` and `{{ .Token }}`.
3. **Who are the admins** (the e-mails that will configure board columns and moderate): a list for slice 2.

## What the sign-in page does (`/login/`)

- A field for the e-mail and a button. An address that is not `@phiz.com` is refused on the page with a message and **nothing is sent**.
- Sending calls Supabase (`/auth/v1/otp`, `create_user: true`) and shows "we sent a link and a code to …", with a field for the code and a *Send again* button (not before 30 s).
- Typing the code calls `/auth/v1/verify` (`type: email`); the link brings the visitor back to `/login/` with the tokens in the address (`#access_token=…`), which the page reads, fetches the user, saves the session
  and removes from the address. Either way the visitor goes to `next` (only paths of this site; default `/overview/`).
- A session whose e-mail is not `@phiz.com` is ended with a message. An invalid or expired code shows an error and keeps the form.
- Texts in pt-BR, en and zh-Hans.

## Acceptance (slice 1)

- `/login/` refuses a non-`@phiz.com` address without any request; with a `@phiz.com` address it asks Supabase for a link and a code; a correct code, or the tokens in the address, make a session and lead to `next`.
- With a session every request to the REST API of the React pages **and** of the old pages carries `Authorization: Bearer <access token>`; without one none does (nothing changes before the switch).
- An expiring access token is refreshed before the request; a refresh that fails clears the session.
- *Sign out* clears the session; the menu shows the account.
- With `auth.required` (or the browser's own strict flag) a page without a session goes to `/login/?next=…`, with a session stays, and `/login/` never redirects; `next` outside this site is ignored.
- With a session, writes carry the account name (`Ana Souza`), and the typed-name field is not shown.
- The whole suite passes as before (no session, switch off) — and the part of it that writes passes with a session too.

## Acceptance (slices 2 and 3)

- A request with the publishable key alone (no session) reads nothing from any table and cannot call any function except `ping()`; a non-`@phiz.com` account reads nothing and cannot write; a member can do everything they could before;
  a member who is not admin cannot change board columns; a non-`@phiz.com` address cannot be created.
- The keep-alive workflow still succeeds (`ping()`); the Edge Function `suggest-summary` refuses a call without a member's token.
- The compatibility suite passes against production while signed in.
