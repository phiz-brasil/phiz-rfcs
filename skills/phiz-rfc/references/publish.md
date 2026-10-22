# Publish, verify, comments

## Publish

```bash
cd ~/Projetos/phiz-rfcs
git fetch -q && git status -sb          # pull --ff-only first if behind
git add sources/<ID> rfcs/<ID>
git commit -m "<ID>: <o que mudou>"      # Portuguese, plus the attribution line from the session reminder
git push origin main
```

The site is public. Before the first push of a new RFC, confirm with the user. Never commit secrets: the Supabase key in `site.config.json` is the *publishable* one and is public by design; secret/service-role keys never go in the repo.

Wait for the deploy:

```bash
H=$(git rev-parse --short=7 HEAD)
for i in $(seq 1 30); do r=$(gh run list --repo phiz-brasil/phiz-rfcs --limit 1 --json status,conclusion,headSha -q '.[0] | "\(.headSha[:7]) \(.status) \(.conclusion)"'); case "$r" in $H\ completed*) echo "$r"; break;; esac; sleep 6; done
```

If the run fails with `Failed to create deployment (status: 500)`, it is a GitHub Pages outage, not the build. `gh run rerun` needs admin rights on the repo; if the logged-in account lacks them, retrigger with `git commit --allow-empty -m "Reexecuta o deploy do Pages (erro 500 do GitHub)"` and push.

## Verify in the browser

Open `https://phiz-brasil.github.io/phiz-rfcs/rfcs/<ID>/?t=<random>#pt` in the built-in browser and run:

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
- Moderation: Supabase → Table Editor → `rfc_comments`: `hidden = true` hides a comment and its replies; deleting the row removes it.
- Comments are keyed by `rfc_id` + section id. Renaming a section id after review starts orphans its comments.
- Read comments for a summary: `curl -s "$URL/rest/v1/rfc_comments?select=section,author,body,quote,created_at&rfc_id=eq.<ID>&order=created_at" -H "apikey: $KEY"`.
