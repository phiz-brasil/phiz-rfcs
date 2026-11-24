# Spec v2: sign-in (phase 2)

Status: slice 1 built on 2026-11-24 (`assets/auth.js`, `/login/`, the account in the menu, the guard; `auth.required` false); slices 2 and 3 pending. Decided 2026-11-24 (owner: "Sim, login"). Replaces what `platform.md` says about `@supabase/ssr` cookies and a middleware (see *Decisions*). Built in three slices so that
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
   On the React pages the typed-name field leaves Preferences and the account (e-mail and *Sign out*) takes its place; the functions keep their `p_by` argument and the client sends the account name there. The old
   pages (RFC, new RFC, comments, index) keep their name field, **filled in with the account name** (they read the name remembered under `phiz-rfc-author`, which the session overwrites); the server trusts
   `p_by` as it does today, all members being trusted. Without a session (before go-live) nothing changes: the typed name stays.
6. **One script does it all: `assets/auth.js`.** A classic script, loaded first on every page (old and React) with the Supabase address, the publishable key and the switch in `data-` attributes. It defines
   `window.PHIZ_AUTH` (session, name, member check, send link, verify code, sign out), keeps the session fresh, and **wraps `window.fetch`**: any request to the Supabase address (REST, Storage, Edge Functions; never
   `/auth/v1/`) leaves with `Authorization: Bearer <access token>` when there is a session. Because of the wrapper no request site of the old or the new pages needs to change. It also runs the guard (decision 4).

## A long window of sign-in (decision of 2026-11-24: "garanta que o login tenha uma janela longa")

Signing in should be rare: the person signs in once and stays in for as long as they keep coming back, and even after weeks away. Two parts, the code and Supabase's settings.

**In the code** (`assets/auth.js`)
1. The access token is short (Supabase's default, 1 h) and is renewed **silently**; the refresh token is what makes the window long, and the client never throws it away for a reason that is not final.
   The session ends **only** when Supabase answers the refresh with *invalid* (HTTP 400, 401 or 403). A network error, `429` or any `5xx` keeps the session and tries again later.
2. A session that was not used for a long time (the access token expired weeks ago) renews on the first request and carries on, as long as Supabase still accepts the refresh token.
3. The token is renewed **before** it is needed: when the tab becomes visible again, when the network comes back, and every 4 minutes in a tab that stays open, whenever less than 5 minutes are left.
4. Several tabs renew **one at a time** (the Web Locks API, `phiz-auth-refresh`): a tab that waited for the lock reads the session the other one saved and does not call Supabase again (no spent refresh token, no spurious sign-out).

**In Supabase** (owner; Authentication → Sessions, and Project Settings → JWT)
- Do **not** set a *time-box* or an *inactivity timeout* shorter than the window wanted. On the Free plan these options do not exist and refresh tokens do not expire, which is the longest window there is; on a paid plan
  set the inactivity timeout to 30 days or more and leave the time-box off (or 90 days or more).
- Keep *Refresh token reuse detection* on (default) and the JWT expiry at 3600 s: a longer access token only lengthens what a stolen token can do and adds nothing to the window.
- Anyone can end their own session with *Sign out*; a member who leaves the company is cut off by the database lock (slice 2) — their e-mail stops being valid — and not by the session length.

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
- With a session, writes carry the account name (`Ana Souza`); on the React pages the typed-name field is not shown, on the old pages it is filled in with the account name.
- The whole suite passes as before (no session, switch off) — and the part of it that writes passes with a session too.

## Acceptance (the long window)

- A refresh answered with `500` or `429`, or that does not arrive, keeps the session; one answered with `400` ends it.
- A session whose access token expired 30 days ago renews on the first request and works.
- When the tab becomes visible again with less than 5 minutes left, the token is renewed without any page request; in a tab that stays open it is renewed by itself before it expires.
- Two tabs that need a new token at the same moment make **one** call to Supabase.

## Acceptance (slices 2 and 3)

- A request with the publishable key alone (no session) reads nothing from any table and cannot call any function except `ping()`; a non-`@phiz.com` account reads nothing and cannot write; a member can do everything they could before;
  a member who is not admin cannot change board columns; a non-`@phiz.com` address cannot be created.
- The keep-alive workflow still succeeds (`ping()`); the Edge Function `suggest-summary` refuses a call without a member's token.
- The compatibility suite passes against production while signed in.
