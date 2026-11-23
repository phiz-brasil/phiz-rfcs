/* The pages of the RFC site, as HTML text: the index, the RFC viewer, the new-RFC page and the comments page.
   A port of tools/build.py (the static build); the page scripts in public/assets fill them in from the database. */
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { COMMENTS_CSS, INDEX_COUNTS_JS, INDEX_CSS, INDEX_JS, T_COMMENTS, T_NEW } from "./constants.ts";
import { CFG, REPO_ROOT, esc, liveConfig, pyJson, spans, type Tri } from "./html.ts";

export function indexPage(): string {
  const fl = '<button type="button" data-filter="all" aria-pressed="true">' + spans({ pt: "Todas", en: "All", zh: "全部" }) + "</button>";
  return `<!doctype html><html lang="pt-BR" data-lang="pt"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>${esc(CFG.title)}</title><meta name="robots" content="noindex">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Schibsted+Grotesk:wght@700;800&family=IBM+Plex+Sans:wght@400;500;600&family=JetBrains+Mono:wght@600&display=swap">
<style>${INDEX_CSS}</style></head><body>
<header><div class="wrap"><div class="brand"><span class="logo" aria-hidden="true">P</span><span>PHIZCHAT</span></div>
<div class="hright"><a class="navc" href="themes/">${spans({ pt: "Temas", en: "Themes", zh: "主题" })}</a><a class="navc" href="board/">${spans({ pt: "Quadro B2B", en: "B2B board", zh: "B2B 看板" })}</a><a class="navc" href="roadmap/">Roadmap</a><a class="navc" href="metrics/">${spans({ pt: "Métricas", en: "Metrics", zh: "指标" })}</a><a class="navc" href="executive/">${spans({ pt: "Visão executiva", en: "Executive view", zh: "管理层视图" })}</a><a class="navc newrfc" href="nova/">＋ ${spans(T_NEW)}</a><a class="navc" href="comments/">💬 ${spans(T_COMMENTS)}<span class="ccount" hidden></span><span class="cnewb" hidden></span></a>
<div class="langs" role="group" aria-label="Language"><button type="button" data-set-lang="pt">PT-BR</button><button type="button" data-set-lang="en">EN-US</button><button type="button" data-set-lang="zh">中文</button></div></div></div></header>
<main class="wrap"><h1>RFCs</h1>
<p class="lead">${spans({"pt": "Propostas técnicas da plataforma, com status e comentários por seção.", "en": "Platform technical proposals, with status and per-section comments.", "zh": "平台技术提案，含状态与分节评论。"})}</p>
<div class="filters" role="group">${fl}</div>
<ul class="list"></ul></main><script>window.PHIZ_CMT=${pyJson(CFG.comments ?? {})};window.PHIZ_SITE=${pyJson({ comments: CFG.comments ?? {} })};${INDEX_JS}${INDEX_COUNTS_JS}window.PHIZ_STATUS_INDEX=true;</script>
<script src="assets/status.js"></script>
<script type="module" src="assets/js/index-live.js"></script></body></html>`;
}

export function commentsPage(): string {
  const data = pyJson({ cfg: CFG.comments ?? {}, rfcs: [] }, false).replaceAll("</", "<\\/");
  const lead: Tri = {
    pt: "Todos os comentários das RFCs em um só lugar. Filtre por RFC, veja o que está sem resposta ou o que chegou desde sua última visita, e abra o comentário na RFC para responder.",
    en: "Every RFC comment in one place. Filter by RFC, see what is unanswered or new since your last visit, and open a comment in its RFC to reply.",
    zh: "所有 RFC 评论集中在一处。可按 RFC 筛选，查看未回复或自上次访问以来的新评论，并在 RFC 中打开评论进行回复。"
  };
  return `<!doctype html><html lang="pt-BR" data-lang="pt"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>${esc(T_COMMENTS.pt)} · ${esc(CFG.title)}</title><meta name="robots" content="noindex">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Schibsted+Grotesk:wght@700;800&family=IBM+Plex+Sans:wght@400;500;600&family=JetBrains+Mono:wght@600&display=swap">
<style>${INDEX_CSS}${COMMENTS_CSS}</style></head><body>
<header><div class="wrap"><div class="brand"><span class="logo" aria-hidden="true">P</span><span>PHIZCHAT</span><a class="back" href="../">← RFCs</a></div>
<div class="langs" role="group" aria-label="Language"><button type="button" data-set-lang="pt">PT-BR</button><button type="button" data-set-lang="en">EN-US</button><button type="button" data-set-lang="zh">中文</button></div></div></header>
<main class="wrap"><h1>${spans(T_COMMENTS)}</h1><p class="lead">${spans(lead)}</p><div id="cmt-root"></div></main>
<script>window.PHIZ_COMMENTS=${data};${INDEX_JS}</script>
<script src="../assets/comments-page.js"></script></body></html>`;
}

/* A page that starts with <title>… (the shell is a fragment) needs the document skeleton around it. */
export function wrapFragment(page: string): string {
  if (page.trimStart().toLowerCase().startsWith("<!doctype")) return page;
  const head = '<!doctype html>\n<html lang="pt-BR">\n<head>\n<meta charset="utf-8">\n' +
    '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n';
  const m = /<header|<body|<main|<h1/.exec(page);
  const i = m ? m.index : page.length;
  return head + page.slice(0, i) + "\n</head>\n<body>\n" + page.slice(i) + "\n</body>\n</html>\n";
}

export function viewerPage(): string {
  const shell = readFileSync(join(REPO_ROOT, "templates", "shell.html"), "utf-8");
  const css = readFileSync(join(REPO_ROOT, "templates", "page.css"), "utf-8");
  const loading: Tri = { pt: "Carregando a RFC…", en: "Loading the RFC…", zh: "正在加载 RFC…" };
  let page = shell.replace(/<title>[\s\S]*?<\/title>/, "<title>RFC</title>");
  page = page.replaceAll("RFC {{ID}}", "RFC").replaceAll("/*CSS*/", () => css)
    .replaceAll("<!--CONTENT-->", `<p class="live-state">${spans(loading)}</p>`).replaceAll("<!--TOC-->", "");
  page = wrapFragment(page);
  page = page.replace('<span class="rfcno">', '<a class="back" href="../">← RFCs</a><span class="rfcno">');
  page = page.replace("</title>", '</title>\n<link rel="stylesheet" href="../assets/rfc-site.css">');
  const inject = `<script>window.PHIZ_SITE=${pyJson(liveConfig())};</script>\n<script src="../assets/mermaid.min.js"></script>\n` +
    '<script src="../assets/vendor/markdown-it.min.js"></script>\n<script src="../assets/vendor/markdown-it-container.min.js"></script>\n' +
    '<script src="../assets/vendor/purify.min.js"></script>\n<script type="module" src="../assets/js/live.js"></script>\n</body>';
  return page.replace("</body>", () => inject);
}

export function newRfcPage(): string {
  const S = (pt: string, en: string, zh: string) => spans({ pt, en, zh });
  return `<!doctype html><html lang="pt-BR" data-lang="pt"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>${esc(CFG.title)} · Nova RFC</title><meta name="robots" content="noindex">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Schibsted+Grotesk:wght@700;800&family=IBM+Plex+Sans:wght@400;500;600&family=JetBrains+Mono:wght@600&display=swap">
<style>${INDEX_CSS}</style><link rel="stylesheet" href="../assets/nova.css"></head><body>
<header><div class="wrap"><div class="brand"><span class="logo" aria-hidden="true">P</span><span>PHIZCHAT</span></div>
<div class="hright"><a class="navc" href="../">← RFCs</a>
<div class="langs" role="group" aria-label="Language"><button type="button" data-set-lang="pt">PT-BR</button><button type="button" data-set-lang="en">EN-US</button><button type="button" data-set-lang="zh">中文</button></div></div></div></header>
<main class="wrap nova">
<h1 id="nova-title"><span class="only-new">${S("Nova RFC", "New RFC", "新建 RFC")}</span><span class="only-edit" hidden>${S("Nova versão de", "New version of", "新版本：")} <span id="edit-id"></span></span></h1>
<p class="lead">${S("Monte a sua RFC em quatro passos. Não precisa de conta nem de código: o arquivo que você enviar vira uma página do site, com comentários, status e histórico de versões.",
                    "Build your RFC in four steps. No account and no code needed: the file you upload becomes a page of the site, with comments, status and version history.",
                    "四步完成你的 RFC。无需账号，也无需代码：你上传的文件会变成站点上的一个页面，带有评论、状态和版本历史。")}</p>
<ol class="steps">
<li><h2>1. ${S("Baixe o modelo", "Download the template", "下载模板")}</h2>
<p class="only-new">${S("É um arquivo só, com português, inglês e chinês. Cada ponto a preencher está marcado com TODO:.", "It is a single file with Portuguese, English and Chinese. Every spot to fill is marked TODO:.", "这是一个同时包含葡萄牙语、英语和中文的单一文件。每个待填写处都标有 TODO:。")}</p>
<p class="only-edit" hidden>${S("O arquivo da versão atual já está abaixo, no passo 3. Você também pode baixá-lo para editar no seu computador.", "The current version's file is already in step 3. You can also download it to edit on your computer.", "当前版本的文件已在第 3 步中。你也可以下载后在自己的电脑上编辑。")}</p>
<p><a class="btn" id="dl-template" href="../assets/templates/RFC.md" download="RFC.md">${S("Baixar o modelo (RFC.md)", "Download the template (RFC.md)", "下载模板 (RFC.md)")}</a>
<a class="btn" id="dl-current" href="#" download="RFC.md" hidden>${S("Baixar a versão atual", "Download the current version", "下载当前版本")}</a></p></li>
<li><h2>2. ${S("Peça a uma IA para preencher", "Ask an AI to fill it in", "请 AI 帮忙填写")}</h2>
<p>${S("Abra a IA de sua preferência (Claude, ChatGPT…), cole o texto abaixo, anexe o modelo e os seus documentos. Com o Claude Code, a skill phiz-rfc faz isso direto no repositório.",
      "Open the AI you prefer (Claude, ChatGPT…), paste the text below and attach the template and your documents. With Claude Code, the phiz-rfc skill does this in the repository.",
      "打开你喜欢的 AI（Claude、ChatGPT 等），粘贴下面的文字，并附上模板和你的文档。使用 Claude Code 时，phiz-rfc skill 可直接在仓库中完成。")}</p>
<textarea id="prompt" rows="8" readonly aria-label="Prompt"></textarea>
<p><button type="button" class="btn" id="copy-prompt">${S("Copiar o texto", "Copy the text", "复制文字")}</button> <span id="copied" class="note" aria-live="polite"></span></p>
<details class="skillbox" id="skillbox"><summary>${S("Prefere uma skill? Baixe ou copie a skill phiz-rfc", "Prefer a skill? Download or copy the phiz-rfc skill", "更喜欢 skill？下载或复制 phiz-rfc skill")}</summary>
<p>${S("A skill ensina a IA a preencher o modelo do jeito certo (estrutura, tradução, diagramas) e a conferir o resultado antes de entregar o arquivo. Ela já traz o modelo dentro.",
      "The skill teaches the AI to fill in the template the right way (structure, translation, diagrams) and to check the result before handing over the file. It already contains the template.",
      "该 skill 教 AI 以正确的方式填写模板（结构、翻译、图表），并在交付文件前检查结果。模板已包含在内。")}</p>
<p><a class="btn" id="dl-skill" href="../assets/skill/phiz-rfc.zip" download="phiz-rfc.zip">${S("Baixar a skill (.zip)", "Download the skill (.zip)", "下载 skill (.zip)")}</a>
<button type="button" class="btn" id="copy-skill">${S("Copiar o texto completo da skill", "Copy the full text of the skill", "复制 skill 全文")}</button> <span id="skill-copied" class="note" aria-live="polite"></span></p>
<ul class="how">
<li><b>Claude Code:</b> ${S("descompacte em ~/.claude/skills e peça: “use a skill phiz-rfc para preencher o RFC.md com estes documentos”.", "unzip into ~/.claude/skills and ask: “use the phiz-rfc skill to fill in RFC.md from these documents”.", "解压到 ~/.claude/skills，然后说：“用 phiz-rfc skill，根据这些文档填写 RFC.md”。")}
<pre class="cmd">mkdir -p ~/.claude/skills &amp;&amp; unzip -o ~/Downloads/phiz-rfc.zip -d ~/.claude/skills</pre></li>
<li><b>Claude (claude.ai / app):</b> ${S("na tela de Skills das configurações, envie o arquivo .zip e depois peça o mesmo.", "in the Skills screen of the settings, upload the .zip file and then ask the same.", "在设置的 Skills 页面上传 .zip 文件，然后提出同样的请求。")}</li>
<li><b>${S("Outras IAs", "Other AIs", "其他 AI")}:</b> ${S("use o texto acima, ou copie o texto completo da skill e cole como instruções junto com os seus documentos.", "use the text above, or copy the full text of the skill and paste it as instructions together with your documents.", "使用上面的文字，或复制 skill 全文，连同你的文档一起作为指令粘贴。")}</li>
</ul></details></li>
<li><h2>3. ${S("Envie o arquivo preenchido", "Upload the filled file", "上传填写好的文件")}</h2>
<p><label class="btn" for="file">${S("Escolher arquivo (.md)", "Choose a file (.md)", "选择文件 (.md)")}</label><input type="file" id="file" accept=".md,.markdown,.txt,text/markdown,text/plain" hidden>
 <span class="note">${S("ou cole o conteúdo abaixo", "or paste the content below", "或在下方粘贴内容")}</span></p>
<textarea id="text" rows="10" spellcheck="false" aria-label="RFC.md"></textarea>
<div class="assetsbox">
<h3>${S("Imagens e diagramas (opcional)", "Images and diagrams (optional)", "图片和图表（可选）")}</h3>
<p>${S("Diagramas em texto (Mermaid) já funcionam direto no arquivo. Para prints e diagramas feitos em outra ferramenta (draw.io, Excalidraw…), exporte em PNG, anexe aqui e cite no texto com o trecho que aparece em cada imagem. Aceitamos PNG, JPEG e WebP; cada imagem é reduzida para até 1 MB, e o limite é de 160 imagens. Se a imagem muda por idioma (telas traduzidas), anexe uma por idioma.",
      "Text diagrams (Mermaid) already work straight in the file. For screenshots and diagrams made in another tool (draw.io, Excalidraw…), export as PNG, attach them here and cite them in the text with the snippet shown for each image. We accept PNG, JPEG and WebP; each image is reduced to at most 1 MB, and the limit is 160 images. If the picture changes by language (translated screens), attach one per language.",
      "文本图表（Mermaid）可直接写在文件中。对于截图以及用其他工具（draw.io、Excalidraw 等）制作的图表，请导出为 PNG，在此附加，并使用每张图片旁显示的片段在正文中引用。支持 PNG、JPEG 和 WebP；每张图片会被缩小到最多 1 MB，上限为 160 张。如果图片因语言而异（翻译后的截图），请为每种语言各附加一张。")}</p>
<p><label class="btn" for="imgs">${S("Anexar imagens", "Attach images", "附加图片")}</label><input type="file" id="imgs" accept="image/png,image/jpeg,image/webp" multiple hidden>
<span id="imgs-note" class="note" aria-live="polite"></span></p>
<ul id="assets" class="assets"></ul>
</div>
<div id="result" aria-live="polite"></div>
<p id="preview-bar" hidden><button type="button" class="btn" id="preview-toggle">${S("Ver prévia", "Preview", "预览")}</button>
<span class="langs" role="group" id="preview-langs" hidden><button type="button" data-pl="pt" aria-pressed="true">PT-BR</button><button type="button" data-pl="en" aria-pressed="false">EN-US</button><button type="button" data-pl="zh" aria-pressed="false">中文</button></span></p>
<iframe id="preview" title="Preview" sandbox="allow-scripts" hidden></iframe></li>
<li><h2>4. ${S("Quem escreveu", "Who wrote it", "作者")}</h2>
<div class="fields">
<label><span>${S("Seu nome", "Your name", "你的名字")} <span class="req">*</span></span><input id="by" maxlength="60" autocomplete="name"></label>
<label class="only-new">${S("Frente (o tema da RFC)", "Front (the RFC's theme)", "业务线（RFC 的主题）")}<select id="front"></select></label>
<label class="only-edit" hidden>${S("Autores (um por linha)", "Authors (one per line)", "作者（每行一位）")}<textarea id="authors" rows="2"></textarea></label>
<label>${S("Colaboradores (um por linha ou separados por vírgula)", "Collaborators (one per line or comma separated)", "协作者（每行一位或用逗号分隔）")}<textarea id="collabs" rows="2"></textarea></label>
<label class="only-edit" hidden>${S("O que mudou (opcional)", "What changed (optional)", "改动说明（可选）")}<input id="note" maxlength="300"></label>
</div>
<p class="note">${S("Ao publicar, a RFC aparece no índice como Rascunho. Qualquer pessoa com o link pode ler, comentar e enviar novas versões; o histórico fica guardado e nada é sobrescrito.",
                   "When you publish, the RFC shows in the index as a Draft. Anyone with the link can read it, comment and upload new versions; the history is kept and nothing is overwritten.",
                   "发布后，RFC 会以草稿状态出现在索引中。任何持有链接的人都可以阅读、评论并上传新版本；历史会被保留，不会覆盖任何内容。")}</p>
<p><button type="button" class="btn primary" id="publish" disabled><span class="only-new">${S("Publicar RFC", "Publish RFC", "发布 RFC")}</span><span class="only-edit" hidden>${S("Publicar nova versão", "Publish new version", "发布新版本")}</span></button>
<span id="publish-note" class="note" aria-live="polite"></span></p></li>
</ol></main>
<script>window.PHIZ_SITE=${pyJson(liveConfig())};</script>
<script src="../assets/vendor/markdown-it.min.js"></script><script src="../assets/vendor/markdown-it-container.min.js"></script><script src="../assets/vendor/purify.min.js"></script>
<script type="module" src="../assets/js/nova.js"></script></body></html>`;
}
