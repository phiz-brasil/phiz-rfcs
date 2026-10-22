# Publish, verify, comments

## Publish

An RFC is a row in the database, not a file of the repository: publishing does not touch git. Write the single file (`templates/bundle/RFC.md`), check it, then send it:

```bash
cd ~/Projetos/phiz-rfcs
.venv/bin/python tools/publish_rfc.py rfc.md --check                                   # the checks of the page; nothing is sent
.venv/bin/python tools/publish_rfc.py rfc.md --by "Gleison" --collaborators "Ana, Bo"   # a new RFC: prints PHZ-NNNN and its address
.venv/bin/python tools/publish_rfc.py rfc.md --by "Gleison" --id PHZ-0003 --note "O que mudou"     # a new version of PHZ-0003
```

Images (`![…](asset:nome.png)`) are read from the folder of the file (or `--images DIR`) and sent first. Editing an existing RFC: download its current file from **＋ Nova RFC** (`/nova/?edit=PHZ-NNNN` loads it), change it, and publish with `--id`. Every publication is a new version (1.0, 1.1…); nothing is overwritten.

The RFC is public: anyone with the link can read, comment and publish a new version. Before the first publication, confirm with the user and say plainly that internal service names and partner details will be readable by anyone with the link. Never put secrets in the file. The Supabase key in `site.config.json` is the *publishable* one and is public by design; the service-role key never goes in the repository (only `tools/import_rfcs.py` uses it, from an environment variable).

## Verify in the browser

Open `https://phiz-brasil.github.io/phiz-rfcs/rfc/?id=<ID>#pt` in the built-in browser and run:

```js
const check=()=>{const a=[...document.querySelectorAll('.lang.active pre.mermaid')];return {lang:document.documentElement.dataset.lang,total:a.length,svg:a.filter(p=>p.querySelector('svg')).length,bad:a.filter(p=>/syntax error|parse error/i.test(p.textContent)).length,h2:document.querySelectorAll('.lang.active h2').length,toc:document.querySelectorAll('.toc-list.active li').length,title:document.querySelector('.lang.active h1')?.textContent}};
await new Promise(r=>setTimeout(r,2500));
const out=[check()];
for (const l of ['en','zh']) { document.querySelector(`[data-set-lang="${l}"]`).click(); await new Promise(r=>setTimeout(r,2500)); out.push(check()); }
out
```

Pass when, for each language, `svg === total`, `bad === 0` and `h2 === toc`. Then take one screenshot of the hero and one of a diagram to check layout (e.g. long meta values wrapping). Scrolling with `scrollIntoView` may not move the pane; navigate to `#pt-<section>` instead.

## Comments (Supabase)

`assets/js/` (entry `main.js`) renders comments on the page when `site.config.json` has `comments.supabaseUrl` and `comments.supabaseKey` (publishable). Readers comment on a section or select a passage ("Comentar trecho"); passages are highlighted in the language they were written in; replies are one level deep. Without config it falls back to giscus, then to a pre-filled GitHub issue.

- Schema, access rules and rate limits (15/min, 150/day per origin): the numbered files in `supabase/migrations`, applied in order in the Supabase SQL Editor (all idempotent; add a new file for a change, never edit an applied one). The publishable key can only read visible comments and insert new ones.
- Moderation: Supabase → Table Editor → `rfc_comments`: `hidden = true` hides a comment and its replies; deleting the row removes it. To take a whole RFC off the site, set `hidden = true` on its row in `rfc_ids`.
- Comments are keyed by `rfc_id` + section id. Renaming a section id after review starts orphans its comments.
- Read comments for a summary: `curl -s "$URL/rest/v1/rfc_comments?select=section,author,body,quote,created_at&rfc_id=eq.<ID>&order=created_at" -H "apikey: $KEY"`.
