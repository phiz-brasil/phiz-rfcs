/* Which parts of an RFC section get a comment button, and how they are numbered. The page numbers them at run time
   (panels.js) and the checks count them before an RFC is published, so both use this one definition; tools/rfc_md.py keeps a
   Python copy (class _Blocks) that tests/test_parity.py compares with this one. */

// paragraphs are numbered per section (0, 1, 2…) in document order, the same in the three languages
export const PARA_SEL = "p:not(.cap), li, .tbl, .diagram, figure.code";

export function paraBlocks(sec) {
  return [...sec.querySelectorAll(PARA_SEL)].filter(e =>
    !e.closest(".cmt-panel") && !(e.parentElement && e.parentElement.closest(".tbl, .diagram, figure, .eps-wrap")) &&
    !(e.matches("p") && e.parentElement.matches("li")));
}

/* The structure of a rendered body (what the three languages must share): commentable blocks per section, number of
   diagrams, and the text of each code figure. */
export function structure(bodyHtml) {
  const doc = new DOMParser().parseFromString(`<body>${bodyHtml}</body>`, "text/html");
  return {
    blocks: [...doc.body.querySelectorAll("section")].map(s => paraBlocks(s).length),
    diagrams: doc.body.querySelectorAll(".diagram").length,
    code: [...doc.body.querySelectorAll("figure.code")].map(f => f.textContent)
  };
}
