Você vai montar uma RFC (proposta técnica) preenchendo o MODELO anexo (arquivo RFC.md) com base nos meus documentos.

Regras:
1. Devolva o arquivo COMPLETO, do primeiro `<!--` ao último parágrafo, em um único bloco de código Markdown, sem comentários seus fora dele.
2. Mantenha a estrutura do modelo: o bloco de metadados no topo, os três marcadores `<!-- lang:pt -->`, `<!-- lang:en -->`, `<!-- lang:zh -->`
   e as seções `## Título {#id}`. Pode acrescentar, dividir ou remover seções, mas com os MESMOS ids, na mesma ordem e com os mesmos
   parágrafos, itens de lista, tabelas, diagramas e blocos de código nos três idiomas (os comentários por parágrafo usam essa numeração).
3. Escreva primeiro em português; depois traduza para inglês e chinês simplificado. Traduza também os rótulos dentro dos diagramas, mas
   mantenha nomes técnicos (endpoints, classes, códigos de status). Blocos de código são idênticos nos três idiomas (comentários em inglês).
4. Troque TODO marcador `TODO:` por conteúdo. Se uma informação não está nos meus documentos, não invente: escreva "a confirmar" e
   coloque a dúvida na seção de perguntas em aberto, endereçada a alguém.
5. Frases curtas e concretas. Tabelas para comparações ("hoje x depois"). Cite arquivos, classes e documentos usados.
6. Só Markdown: sem HTML, sem scripts, sem imagens que não sejam links https. Nunca coloque senhas, tokens, chaves ou dados de clientes.
7. Componentes que o modelo mostra e você pode usar: tabelas, `::: note|decision|risk Rótulo`, `::: stats`, `::: phases`
   (`##### FASE 1: Nome`), `::: questions`, `::: endpoints`, blocos ```json / bash / http / python …, e diagramas
   ```mermaid Legenda de uma frase (se a legenda tiver crases, abra o bloco com ~~~mermaid).
8. Antes de responder, confira: mesmos ids nos três idiomas, mesmo número de parágrafos por seção, nenhum `TODO:` sobrando.

Meus documentos estão abaixo / anexados.
