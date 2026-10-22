# Components (HTML)

This is the HTML each block renders to, and what you can write as raw HTML inside a Markdown RFC when no Markdown form exists. Write the Markdown forms of `markdown.md` by default.

All classes come from `page.css` (copied into each RFC). Colors are tokens with dark-mode variants, so never hardcode colors in content.

## Section

```html
<section>
<h2 id="§context"><span class="n">02</span>Contexto: como funciona hoje</h2>
…
</section>
```

`h3` for sub-blocks, `h4` for small labels (e.g. "Objetivos" / "Fora do escopo"). Internal links: `<a href="#§questions">…</a>` (the build rewrites `§` to the language prefix).

## Stats row (summary)

```html
<div class="stats">
  <div class="stat"><b>8</b><span>integrações hoje</span></div>
  <div class="stat"><b>4 → 1</b><span>formas de autenticação</span></div>
</div>
```

## Tables

```html
<div class="tbl"><table><thead><tr><th>…</th></tr></thead><tbody>
<tr><td>…</td></tr>
</tbody></table></div>
```

Variants: `tbl changes` (4 wide columns, today/why/proposal/use case), `tbl num` (mono first column), `tbl map` (route mapping, below). Inline verdicts: `<span class="yes">`, `<span class="part">`, `<span class="no">`.

### Mapping table with status chips (migrations)

```html
<div class="legend"><span><span class="st eq">equivalente</span> mesma operação</span><span><span class="st ch">muda</span> regra diferente</span><span><span class="st new">novo</span> não existia</span><span><span class="st gap">sem equivalente</span> fica no antigo</span></div>
<div class="tbl map"><table><thead><tr><th>Hoje</th><th>API nova</th><th>Situação</th><th>O que muda</th></tr></thead><tbody>
<tr><td>POST /Tokenizacao/Pagar<br>B21</td><td>POST /v1/pagamento</td><td><span class="st ch">muda</span></td><td>…</td></tr>
</tbody></table></div>
```

First two columns render in monospace. EN chips: equivalent / changes / new / no equivalent. ZH: 对应 / 变化 / 新增 / 无对应.

## Endpoint list

```html
<div class="eps">
  <div class="ep"><span class="m m-post">POST</span><code class="p">/v1/pagamento</code><span class="d">Cobra o cartão</span></div>
</div>
```

Methods: `m-get`, `m-post`, `m-put`, `m-patch`, `m-delete`.

## Note boxes

```html
<div class="note-box decision"><span class="lbl">Decisão</span><p>…</p></div>
<div class="note-box risk"><span class="lbl">A confirmar</span><p>…</p></div>
<div class="note-box"><span class="lbl">Nota</span><p>…</p></div>
```

`decision` (green) for choices made, `risk` (red) for pending confirmations and impacts.

## Diagram

```html
<div class="diagram"><pre class="mermaid">
flowchart LR
  A["…"] --> B["…"]
</pre></div>
<p class="cap">Uma frase explicando o diagrama.</p>
```

## Phases

```html
<div class="phases">
  <div class="phase first"><span class="tag">FASE 0</span><h5>Preparação</h5><ul><li>…</li></ul></div>
  <div class="phase"><span class="tag">FASE 1</span><h5>PIX</h5><ul><li>…</li></ul></div>
</div>
```

Tags: `FASE N` / `PHASE N` / `第 N 阶段`.

## Open questions

```html
<ol class="qs">
  <li><strong>Tokens.</strong> Pergunta…</li>
</ol>
```

## Code samples

Put samples in `code.json` and reference them with `{CODE:name}` on its own line in each language:

```json
{
  "auth_new": ["bash", "curl -X GET \"https://…\" \\\n  -H \"Authorization: Bearer $KEY\""],
  "pay_new": ["json", {"orderId": "PED-4711", "amount": "15000"}]
}
```

Languages with highlighting: `json`, `bash`, `http`, `python`, `yaml`, `java`, `javascript`, `typescript`, `dart`, `kotlin`, `go`. Use realistic but fake values; never real keys, tokens, documents or customer data. Comments in English.

## Hero

```html
<header class="hero">
  <div class="eyebrow">RFC PHZ-0003 · Rascunho para revisão</div>
  <h1>Título</h1>
  <p class="lede">…</p>
  <dl class="meta">
    <div><dt>Status</dt><dd><span class="pill">Rascunho</span></dd></div>
    <div><dt>Autor</dt><dd>Gleison (Engenharia PHIZ)</dd></div>
    <div><dt>Data</dt><dd>16/10/2026</dd></div>
    <div><dt>Revisores</dt><dd>Pedro Bettani (Brasil)<br>Richard Liang (China)</dd></div>
    <div><dt>Sistemas</dt><dd>channel · card-vault · backapply</dd></div>
  </dl>
</header>
```

Dates: `16/10/2026` in PT, `2026-10-16` in EN and ZH.
