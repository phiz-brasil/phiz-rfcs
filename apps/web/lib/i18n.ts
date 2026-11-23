/* The three languages of the interface and the text people write in them. The language is the one the other pages use (localStorage
   "phiz-rfc-lang"); a text typed by a person is stored under the language it was written in, and shown in the reader's language when
   it exists, otherwise in the first language that has it. */
"use client";
import { useEffect, useState } from "react";

export const LANGS = ["pt", "en", "zh"] as const;
export type Lang = (typeof LANGS)[number];
export type Tri = Partial<Record<Lang, string>>;

const KEY = "phiz-rfc-lang";
const BCP: Record<Lang, string> = { pt: "pt-BR", en: "en", zh: "zh-CN" };

function read(): Lang {
  try {
    const s = localStorage.getItem(KEY);
    if (LANGS.includes(s as Lang)) return s as Lang;
  } catch { /* storage blocked */ }
  const n = (navigator.language || "pt").slice(0, 2);
  return LANGS.includes(n as Lang) ? (n as Lang) : "pt";
}

export function useLang(): [Lang, (l: Lang) => void] {
  const [lang, set] = useState<Lang>("pt");
  useEffect(() => {
    const l = read();
    set(l);
    document.documentElement.lang = BCP[l];
  }, []);
  return [lang, (l: Lang) => {
    set(l);
    document.documentElement.lang = BCP[l];
    try { localStorage.setItem(KEY, l); } catch { /* ignore */ }
  }];
}

/* A text in the reader's language, or the first language that has one. `fallbackOf` tells which language was used when it is not the reader's. */
export function pick(t: Tri | null | undefined, lang: Lang): { text: string; from: Lang | null } {
  if (!t) return { text: "", from: null };
  if (t[lang]?.trim()) return { text: t[lang]!, from: null };
  const other = LANGS.find(l => t[l]?.trim());
  return other ? { text: t[other]!, from: other } : { text: "", from: null };
}

export const text = (t: Tri | null | undefined, lang: Lang) => pick(t, lang).text;

type Dict = Record<string, Record<Lang, string>>;
export const T: Dict = {
  themes: { pt: "Temas", en: "Themes", zh: "主题" },
  rfcs: { pt: "RFCs", en: "RFCs", zh: "RFC" },
  newRfc: { pt: "Nova RFC", en: "New RFC", zh: "新建 RFC" },
  comments: { pt: "Comentários", en: "Comments", zh: "评论" },
  lead: { pt: "Acompanhe cada tema por frente: andamento, responsável, etapa e itens de execução.", en: "Follow each theme by front: progress, owner, stage and execution items.", zh: "按业务线跟进每个主题：进展、负责人、阶段和执行项。" },
  loading: { pt: "Carregando…", en: "Loading…", zh: "加载中…" },
  failed: { pt: "Não foi possível carregar. Tente de novo.", en: "Could not load. Please try again.", zh: "无法加载，请重试。" },
  yourName: { pt: "Seu nome", en: "Your name", zh: "你的名字" },
  needName: { pt: "Informe seu nome para salvar.", en: "Enter your name to save.", zh: "请填写名字后再保存。" },
  newTheme: { pt: "Novo tema", en: "New theme", zh: "新建主题" },
  editFronts: { pt: "Editar frentes", en: "Edit fronts", zh: "编辑业务线" },
  doneEditing: { pt: "Concluir edição", en: "Done editing", zh: "完成编辑" },
  all: { pt: "Todos", en: "All", zh: "全部" },
  project: { pt: "Projeto", en: "Project", zh: "项目" },
  task: { pt: "Tarefa avulsa", en: "Standalone task", zh: "独立任务" },
  kind: { pt: "Tipo", en: "Type", zh: "类型" },
  front: { pt: "Frente", en: "Front", zh: "业务线" },
  title: { pt: "Título", en: "Title", zh: "标题" },
  owner: { pt: "Responsável", en: "Owner", zh: "负责人" },
  status: { pt: "Status", en: "Status", zh: "状态" },
  stage: { pt: "Etapa", en: "Stage", zh: "阶段" },
  start: { pt: "Início", en: "Start", zh: "开始" },
  due: { pt: "Conclusão estimada", en: "Estimated completion", zh: "预计完成" },
  tags: { pt: "Etiquetas (separadas por vírgula)", en: "Tags (comma separated)", zh: "标签（逗号分隔）" },
  whatItIs: { pt: "O que é (uma frase)", en: "What it is (one sentence)", zh: "是什么（一句话）" },
  progress: { pt: "Andamento (uma frase)", en: "Progress (one sentence)", zh: "进展（一句话）" },
  problem: { pt: "Que problema estamos tratando com este tema?", en: "What problem are we addressing with this theme?", zh: "这个主题要解决什么问题？" },
  solution: { pt: "Qual é a solução proposta, em resumo?", en: "What is the proposed solution, in short?", zh: "拟议的解决方案是什么（简述）？" },
  success: { pt: "O que é sucesso e como saberemos que foi atingido?", en: "What does success look like and how will we know it was reached?", zh: "什么算成功？我们如何知道已达成？" },
  save: { pt: "Salvar", en: "Save", zh: "保存" },
  saved: { pt: "Salvo.", en: "Saved.", zh: "已保存。" },
  saving: { pt: "Salvando…", en: "Saving…", zh: "保存中…" },
  create: { pt: "Criar", en: "Create", zh: "创建" },
  cancel: { pt: "Cancelar", en: "Cancel", zh: "取消" },
  items: { pt: "Itens de execução", en: "Execution items", zh: "执行项" },
  addItem: { pt: "Adicionar item", en: "Add item", zh: "添加执行项" },
  itemTitle: { pt: "Novo item", en: "New item", zh: "新执行项" },
  jira: { pt: "Links do Jira", en: "Jira links", zh: "Jira 链接" },
  jiraUrl: { pt: "Endereço do item no Jira (https://…)", en: "Jira issue address (https://…)", zh: "Jira 事项地址（https://…）" },
  jiraLabel: { pt: "Rótulo (opcional)", en: "Label (optional)", zh: "标签（可选）" },
  add: { pt: "Adicionar", en: "Add", zh: "添加" },
  remove: { pt: "Remover", en: "Remove", zh: "移除" },
  open: { pt: "Abrir no Jira", en: "Open in Jira", zh: "在 Jira 中打开" },
  deps: { pt: "Dependências", en: "Dependencies", zh: "依赖" },
  depends_on: { pt: "depende de", en: "depends on", zh: "依赖于" },
  blocks: { pt: "bloqueia", en: "blocks", zh: "阻塞" },
  related: { pt: "relacionado a", en: "related to", zh: "相关" },
  otherTheme: { pt: "Outro tema (PHZ-0000)", en: "Other theme (PHZ-0000)", zh: "其他主题（PHZ-0000）" },
  history: { pt: "Histórico", en: "History", zh: "历史" },
  rfc: { pt: "RFC deste tema", en: "This theme's RFC", zh: "该主题的 RFC" },
  openRfc: { pt: "Abrir a RFC", en: "Open the RFC", zh: "打开 RFC" },
  noRfc: { pt: "Este tema ainda não tem RFC.", en: "This theme has no RFC yet.", zh: "该主题尚无 RFC。" },
  none: { pt: "Nada ainda.", en: "Nothing yet.", zh: "暂无。" },
  noThemes: { pt: "Nenhum tema nesta frente.", en: "No themes in this front.", zh: "该业务线暂无主题。" },
  notFound: { pt: "Tema não encontrado.", en: "Theme not found.", zh: "未找到该主题。" },
  back: { pt: "← Temas", en: "← Themes", zh: "← 主题" },
  fromLang: { pt: "texto em", en: "text in", zh: "文本语言：" },
  frontName: { pt: "Nome da frente", en: "Front name", zh: "业务线名称" },
  frontScope: { pt: "O que a frente cobre", en: "What the front covers", zh: "业务线范围" },
  frontOrder: { pt: "Ordem", en: "Order", zh: "顺序" },
  writtenIn: { pt: "Você escreve em", en: "You write in", zh: "你正在使用" },
  error: { pt: "Não foi possível salvar.", en: "Could not save.", zh: "无法保存。" },
  rate: { pt: "Muitas alterações seguidas. Espere um minuto.", en: "Too many changes in a row. Wait a minute.", zh: "更改过于频繁，请稍候。" },
  by: { pt: "por", en: "by", zh: "由" },
  "stage.1": { pt: "01 Solicitação", en: "01 Request", zh: "01 需求提出" },
  "stage.2": { pt: "02 Pesquisa", en: "02 Research", zh: "02 需求调研" },
  "stage.3": { pt: "03 Decisão", en: "03 Decision", zh: "03 立项决策" },
  "stage.4": { pt: "04 PRD e início", en: "04 PRD and kickoff", zh: "04 PRD 与启动" },
  "stage.5": { pt: "05 Revisão da solução", en: "05 Solution review", zh: "05 方案评审" },
  "stage.6": { pt: "06 Planejamento", en: "06 Planning", zh: "06 项目排期" },
  "stage.7": { pt: "07 Desenvolvimento", en: "07 Build", zh: "07 开发" },
  "stage.8": { pt: "08 Testes", en: "08 QA", zh: "08 测试验收" },
  "stage.9": { pt: "09 Publicação", en: "09 Release", zh: "09 发布准备" },
  "stage.10": { pt: "10 Lançamento", en: "10 Launch", zh: "10 上线收口" },
  "status.not_started": { pt: "Não iniciado", en: "Not started", zh: "未开始" },
  "status.on_track": { pt: "No prazo", en: "On track", zh: "按计划" },
  "status.at_risk": { pt: "Em risco", en: "At risk", zh: "有风险" },
  "status.blocked": { pt: "Bloqueado", en: "Blocked", zh: "受阻" },
  "status.paused": { pt: "Pausado", en: "Paused", zh: "已暂停" },
  "status.done": { pt: "Concluído", en: "Done", zh: "已完成" },
  "status.cancelled": { pt: "Cancelado", en: "Cancelled", zh: "已取消" },
  "col.todo": { pt: "A fazer", en: "To do", zh: "待办" },
  "col.doing": { pt: "Fazendo", en: "Doing", zh: "进行中" },
  "col.blocked": { pt: "Bloqueado", en: "Blocked", zh: "受阻" },
  "col.done": { pt: "Feito", en: "Done", zh: "完成" },
  "ev.created": { pt: "tema criado", en: "theme created", zh: "创建主题" },
  "ev.item_created": { pt: "item criado", en: "item created", zh: "创建执行项" },
  "ev.item_col": { pt: "item movido", en: "item moved", zh: "移动执行项" },
  "ev.jira_added": { pt: "link do Jira adicionado", en: "Jira link added", zh: "添加 Jira 链接" },
  "ev.jira_removed": { pt: "link do Jira removido", en: "Jira link removed", zh: "移除 Jira 链接" },
  "ev.link_added": { pt: "dependência adicionada", en: "dependency added", zh: "添加依赖" },
  "ev.link_removed": { pt: "dependência removida", en: "dependency removed", zh: "移除依赖" }
};

export const t = (key: string, lang: Lang) => T[key]?.[lang] ?? key;
export const STAGES = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];
export const STATUSES = ["not_started", "on_track", "at_risk", "blocked", "paused", "done", "cancelled"];
export const COLS = ["todo", "doing", "blocked", "done"];
