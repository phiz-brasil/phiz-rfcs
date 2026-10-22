# Mermaid diagrams

The site bundles Mermaid 10.9.1 (`assets/mermaid.min.js`), theme `neutral`/`dark`, `securityLevel: strict`, and renders only the active language. A syntax error does not break the page but shows a "Syntax error" box, so check every diagram on the live page.

## Patterns that worked

**Architecture today** — systems left to right, external parties as cylinders, config reads dashed:

```
flowchart LR
  APP["phiz-flutter<br/>app"] --> AS["microwd-appserver<br/>API do app"]
  AS --> CH["microwd-channel<br/>fala com os canais"]
  CH --> CP[("CredPay<br/>4 APIs")]
  DB[("route_cfg<br/>road_info")] -. "lê a rota" .-> AS
```

**Before / after** — two subgraphs joined by a thick arrow:

```
flowchart LR
  subgraph HOJE["Hoje"]
    direction TB
    A1["/AuthCredPay<br/>checkout"]
    A2["/oauth/token<br/>PIX"]
  end
  subgraph NOVO["API GruPag"]
    K["Authorization: Bearer gpk_…"]
  end
  HOJE ==> NOVO
```

Subgraph ids (`HOJE`, `NOVO`) can stay the same in every language; only the quoted label changes.

**Key flow** — sequence with numbered steps and a loop:

```
sequenceDiagram
  autonumber
  participant CH as channel
  participant G as API GruPag
  CH->>G: POST /transacional/pix/qrcode
  G-->>CH: transactionId
  loop até CONFIRMADO
    CH->>G: GET /transacional/pix/consulta/{id}
  end
```

**Lifecycle** — `stateDiagram-v2` with transition labels:

```
stateDiagram-v2
  [*] --> GERADO
  GERADO --> CONFIRMADO: pagamento
  CONFIRMADO --> DISPUTA: devolução após 24 h
```

**Cutover / rollback** — a decision node and a dashed operator edge:

```
flowchart LR
  BA["backapply"] --> RC{"route_cfg<br/>por comerciante"}
  RC -- "código antigo" --> OLD["Serviços atuais"]
  RC -- "código novo" --> NEW["Adaptador novo"]
  OP["Operador no painel"] -. "troca a linha" .-> RC
```

## Traps

- Quote every flowchart label that has spaces, accents, slashes, parentheses, `·` or Chinese: `A["…"]`, `-- "…" -->`, `-. "…" .->`. Use `<br/>` for line breaks inside quotes.
- In sequence messages avoid `;` and `#` (they end or comment the line); braces like `{id}` are fine.
- Node ids are ASCII without spaces (`APP`, `RC`). Do not use `end` as an id.
- Keep labels short: 2 lines of ~25 characters. Long labels shrink the whole diagram.
- One diagram, one idea. Five to eight nodes per flowchart, up to ~14 messages per sequence.
- Translate labels in all three files and keep the same number of diagrams; the build checks the count.
