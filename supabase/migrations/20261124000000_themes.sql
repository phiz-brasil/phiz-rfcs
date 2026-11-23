-- Frentes, temas e itens de execução (fase 3 do plano em docs/spec/v2).
-- Idempotente: tem 'if not exists' / 'or replace' e o seed só insere o que falta; seguro rodar de novo no SQL Editor.
--
-- Frente → Tema → Item de execução. Um tema é um projeto (anda pelas etapas da norma V4) ou uma tarefa avulsa. Todo id de tema é um PHZ-NNNN da
-- mesma sequência das RFCs (rfc_ids): a RFC de um tema é a RFC com o mesmo id, e as RFCs já publicadas viram temas aqui.
-- Quem acessa: a chave pública LÊ tudo e escreve só pelas funções abaixo (com limite por origem e o nome de quem mexeu); cada mudança de
-- um tema vira uma linha em theme_events. Sem login por enquanto (a fase 2 do plano, por último, fecha o acesso).

-- rfc_ids passa a aceitar ids de temas que não têm RFC
alter table public.rfc_ids drop constraint if exists rfc_ids_source_check;
alter table public.rfc_ids add constraint rfc_ids_source_check check (source in ('site', 'repo', 'theme'));

-- Frentes ------------------------------------------------------------------------------------------------------------
create table if not exists public.fronts (
  key      text primary key check (key ~ '^[a-z0-9-]{2,30}$'),
  name     jsonb not null,                              -- {pt, en, zh}
  scope    jsonb not null default '{}'::jsonb,          -- {pt, en, zh}: o que a frente cobre
  ord      integer not null,
  is_other boolean not null default false               -- "Outros": permanente, sempre por último
);

-- Temas --------------------------------------------------------------------------------------------------------------
create table if not exists public.themes (
  id          text primary key references public.rfc_ids (rfc_id),
  kind        text not null check (kind in ('project', 'task')),
  front       text not null references public.fronts (key),
  title       jsonb not null,                           -- {pt, en, zh}: ao menos um idioma preenchido
  owner       text check (owner is null or char_length(owner) <= 80),
  status      text not null default 'not_started'
              check (status in ('not_started', 'on_track', 'at_risk', 'blocked', 'paused', 'done', 'cancelled')),
  stage       integer check (stage between 1 and 10),   -- só projetos: etapa da norma V4
  route       text not null default 'full' check (route in ('full', 'bug', 'p0')),
  what_it_is  jsonb not null default '{}'::jsonb,       -- uma frase: o que é (estável)
  progress    jsonb not null default '{}'::jsonb,       -- uma frase: como vai agora (semanal)
  problem     jsonb not null default '{}'::jsonb,       -- as três respostas do slide
  solution    jsonb not null default '{}'::jsonb,
  success     jsonb not null default '{}'::jsonb,
  start_date  date,
  due_date    date,
  tags        text[] not null default '{}',
  resolution  text check (resolution in ('done', 'declined', 'deferred', 'merged', 'cancelled')),
  hidden      boolean not null default false,
  created_at  timestamptz not null default now(),
  created_by  text,
  updated_at  timestamptz not null default now(),
  check (kind = 'project' or stage is null)
);
create index if not exists themes_front_idx on public.themes (front);

-- Itens de execução (projetos) ----------------------------------------------------------------------------------------
create table if not exists public.theme_items (
  id         uuid primary key default gen_random_uuid(),
  theme_id   text not null references public.themes (id),
  title      text not null check (char_length(btrim(title)) between 1 and 200),
  owner      text check (owner is null or char_length(owner) <= 80),
  col        text not null default 'todo' check (col in ('todo', 'doing', 'blocked', 'done')),
  due_date   date,
  milestone  boolean not null default false,
  created_at timestamptz not null default now(),
  created_by text,
  updated_at timestamptz not null default now()
);
create index if not exists theme_items_theme_idx on public.theme_items (theme_id);

-- Dependências entre temas (de frentes diferentes, sem copiar o tema) -------------------------------------------------
create table if not exists public.theme_links (
  theme_id text not null references public.themes (id),
  to_theme text not null references public.themes (id),
  kind     text not null check (kind in ('depends_on', 'blocks', 'related')),
  primary key (theme_id, to_theme, kind),
  check (theme_id <> to_theme)
);

-- Links para o Jira: só o endereço; a página mostra a chave lida dele e abre o Jira em outra aba -------------------------
create table if not exists public.theme_jira (
  id         uuid primary key default gen_random_uuid(),
  theme_id   text not null references public.themes (id),
  item_id    uuid references public.theme_items (id),
  url        text not null check (url ~ '^https://[^ ]{4,500}$'),
  label      text check (label is null or char_length(label) <= 80),
  issue_key  text,
  created_at timestamptz not null default now(),
  created_by text
);
create index if not exists theme_jira_theme_idx on public.theme_jira (theme_id);

-- Histórico: toda mudança, com quem e quando; as mudanças de etapa alimentam as métricas ------------------------------
create table if not exists public.theme_events (
  id        uuid primary key default gen_random_uuid(),
  theme_id  text not null references public.themes (id),
  item_id   uuid,
  at        timestamptz not null default now(),
  edited_by text not null,
  field     text not null,
  old_value jsonb,
  new_value jsonb
);
create index if not exists theme_events_theme_idx on public.theme_events (theme_id, at desc);

alter table public.fronts enable row level security;
alter table public.themes enable row level security;
alter table public.theme_items enable row level security;
alter table public.theme_links enable row level security;
alter table public.theme_jira enable row level security;
alter table public.theme_events enable row level security;
revoke all on public.fronts, public.themes, public.theme_items, public.theme_links, public.theme_jira, public.theme_events from anon, authenticated;
grant select on public.fronts, public.themes, public.theme_items, public.theme_links, public.theme_jira, public.theme_events to anon, authenticated;

drop policy if exists "read fronts" on public.fronts;
create policy "read fronts" on public.fronts for select to anon, authenticated using (true);
drop policy if exists "read themes" on public.themes;
create policy "read themes" on public.themes for select to anon, authenticated using (not hidden);
drop policy if exists "read theme items" on public.theme_items;
create policy "read theme items" on public.theme_items for select to anon, authenticated
  using (exists (select 1 from public.themes t where t.id = theme_items.theme_id and not t.hidden));
drop policy if exists "read theme links" on public.theme_links;
create policy "read theme links" on public.theme_links for select to anon, authenticated
  using (exists (select 1 from public.themes t where t.id = theme_links.theme_id and not t.hidden));
drop policy if exists "read theme jira" on public.theme_jira;
create policy "read theme jira" on public.theme_jira for select to anon, authenticated
  using (exists (select 1 from public.themes t where t.id = theme_jira.theme_id and not t.hidden));
drop policy if exists "read theme events" on public.theme_events;
create policy "read theme events" on public.theme_events for select to anon, authenticated
  using (exists (select 1 from public.themes t where t.id = theme_events.theme_id and not t.hidden));

-- Frentes oficiais -----------------------------------------------------------------------------------------------------
insert into public.fronts (key, name, scope, ord, is_other) values
  ('pop', '{"pt":"POP","en":"POP","zh":"POP"}',
   '{"pt":"PhizChat Open Platform: o portal onde as empresas clientes administram suas contas e atividades. Contas comerciais, acesso de parceiros a várias contas, permissões, verificação, KYB no portal e o portal de conteúdo e social acessado a partir da POP.",
     "en":"PhizChat Open Platform: the portal where business customers manage their accounts and activity. Business accounts, partner access to several accounts, permissions, verification, KYB in the portal and the content and social portal reached from POP.",
     "zh":"PhizChat Open Platform：企业客户管理账户和业务的门户。包括商业账户、合作伙伴多账户访问、权限、认证、门户中的 KYB，以及从 POP 进入的内容与社交门户。"}', 1, false),
  ('api-platform', '{"pt":"API Platform","en":"API Platform","zh":"API Platform"}',
   '{"pt":"Tudo sobre APIs: Single Message API, Outbound API, migração da API antiga usada pelo CRM, regras de recontato e bloqueios, endereçamento por hash ou telefone, APIs de grupos e a investigação de bots para grupos.",
     "en":"Everything about APIs: Single Message API, Outbound API, migration of the old API used by the CRM, recontact rules and blocks, addressing by hash or phone, group APIs and the investigation of bots for groups.",
     "zh":"所有与 API 相关的内容：Single Message API、Outbound API、CRM 所用旧 API 的迁移、再触达规则与屏蔽、按哈希或手机号寻址、群组 API，以及群组机器人调查。"}', 2, false),
  ('mini-apps', '{"pt":"Mini-Apps","en":"Mini-Apps","zh":"Mini-Apps"}',
   '{"pt":"Tudo sobre mini-apps: saneamento, organização da vitrine com a UX atual, fábrica de mini-apps, estratégia e próximos passos, benchmarks e iniciativas no México.",
     "en":"Everything about mini-apps: clean-up, organizing the showcase with the current UX, the mini-app factory, strategy and next steps, benchmarks and initiatives in Mexico.",
     "zh":"所有与 mini-app 相关的内容：整治、基于现有 UX 的展示页整理、mini-app 工厂、策略与后续步骤、对标研究以及墨西哥的举措。"}', 3, false),
  ('payments', '{"pt":"Payments","en":"Payments","zh":"Payments"}',
   '{"pt":"Global Checkout, arquitetura de pagamentos e seu handoff, pagamentos para influenciadores e alinhamento sobre BaaS e Sub no PicPay.",
     "en":"Global Checkout, payments architecture and its handoff, payments to influencers and alignment on BaaS and Sub at PicPay.",
     "zh":"Global Checkout、支付架构及其交接、面向网红的支付，以及与 PicPay 在 BaaS 和 Sub 上的对齐。"}', 4, false),
  ('product-center', '{"pt":"Product Center","en":"Product Center","zh":"Product Center"}',
   '{"pt":"PDLC, metodologias, OKRs, processo de roadmap, alinhamento semanal B2C–B2B, acompanhamento consolidado das POCs enquanto seu vínculo estiver em aberto e revisão dos desenhos do Henry. A plataforma de testes A/B começa aqui se for compartilhada entre times.",
     "en":"PDLC, methodologies, OKRs, the roadmap process, the weekly B2C–B2B alignment, consolidated follow-up of POCs while their front is open and the review of Henry''s designs. The A/B testing platform starts here if it is shared across teams.",
     "zh":"PDLC、方法论、OKR、路线图流程、每周 B2C–B2B 对齐、在归属未定期间对 POC 的汇总跟进，以及 Henry 设计稿的评审。若 A/B 测试平台为多团队共用，则从这里开始。"}', 5, false),
  ('outros', '{"pt":"Outros","en":"Others","zh":"其他"}',
   '{"pt":"Temas em descoberta, transversais ou fora do escopo das frentes. Podem ser movidos para uma frente quando o escopo ficar claro, preservando o histórico.",
     "en":"Themes in discovery, cross-cutting or outside the fronts. They can move to a front once the scope is clear, keeping their history.",
     "zh":"处于探索阶段、跨领域或不属于各业务线的主题。范围明确后可移入某一业务线，历史记录保留。"}', 99, true)
on conflict (key) do nothing;

-- Funções de escrita ---------------------------------------------------------------------------------------------------
-- {pt,en,zh}: um objeto com textos (cada um de até p_max caracteres); chaves fora desses idiomas são recusadas
create or replace function public.theme_check_i18n(p jsonb, p_max integer, p_required boolean)
returns void language plpgsql immutable set search_path = public as $$
declare k text; v jsonb; filled boolean := false;
begin
  if p is null or jsonb_typeof(p) is distinct from 'object' then raise exception 'invalid text' using errcode = '22023'; end if;
  for k, v in select * from jsonb_each(p) loop
    if k not in ('pt', 'en', 'zh') or jsonb_typeof(v) is distinct from 'string' or char_length(v #>> '{}') > p_max then
      raise exception 'invalid text' using errcode = '22023';
    end if;
    if char_length(btrim(v #>> '{}')) > 0 then filled := true; end if;
  end loop;
  if p_required and not filled then raise exception 'text required' using errcode = '22023'; end if;
end $$;

create or replace function public.theme_check_name(p_by text)
returns void language plpgsql immutable set search_path = public as $$
begin
  if p_by is null or char_length(btrim(p_by)) not between 1 and 60 then raise exception 'invalid name' using errcode = '22023'; end if;
end $$;

-- Cria um tema novo (ou promove a tema uma RFC que ainda não é: p->>'id')
create or replace function public.create_theme(p jsonb, p_by text)
returns jsonb language plpgsql security definer set search_path = public, extensions as $$
declare new_id text; k text := coalesce(p ->> 'kind', 'task'); f text := p ->> 'front'; ti jsonb := coalesce(p -> 'title', '{}'::jsonb);
begin
  perform public.theme_check_name(p_by);
  perform public.rfc_rate_limit(public.rfc_origin_hash(), 'theme', 30, 200);
  if k not in ('project', 'task') then raise exception 'invalid kind' using errcode = '22023'; end if;
  perform 1 from public.fronts where key = f;
  if not found then raise exception 'invalid front' using errcode = '22023'; end if;
  perform public.theme_check_i18n(ti, 200, true);
  if p ->> 'id' is not null then
    new_id := p ->> 'id';
    perform 1 from public.rfc_ids where rfc_id = new_id and not hidden;
    if not found then raise exception 'unknown RFC' using errcode = '22023'; end if;
    perform 1 from public.themes where id = new_id;
    if found then raise exception 'theme exists' using errcode = '22023'; end if;
  else
    new_id := public.rfc_allocate_id('theme', p_by);
  end if;
  insert into public.themes (id, kind, front, title, owner, stage, created_by)
    values (new_id, k, f, ti, nullif(left(btrim(coalesce(p ->> 'owner', '')), 80), ''), case when k = 'project' then 1 end, btrim(p_by));
  insert into public.theme_events (theme_id, edited_by, field, old_value, new_value) values (new_id, btrim(p_by), 'created', null, to_jsonb(k));
  return jsonb_build_object('id', new_id);
end $$;

-- Altera campos de um tema: só vão as chaves presentes em p; cada campo que mudou vira um evento
create or replace function public.update_theme(p_id text, p jsonb, p_by text)
returns void language plpgsql security definer set search_path = public, extensions as $$
declare old_row jsonb; new_row jsonb; t public.themes; f text;
  fields text[] := array['front', 'title', 'owner', 'status', 'stage', 'route', 'what_it_is', 'progress', 'problem', 'solution', 'success',
                         'start_date', 'due_date', 'tags', 'resolution'];
begin
  perform public.theme_check_name(p_by);
  perform public.rfc_rate_limit(public.rfc_origin_hash(), 'theme', 120, 1000);
  select * into t from public.themes where id = p_id and not hidden for update;
  if not found then raise exception 'unknown theme' using errcode = '22023'; end if;
  old_row := to_jsonb(t);
  if p ? 'front' then
    perform 1 from public.fronts where key = p ->> 'front';
    if not found then raise exception 'invalid front' using errcode = '22023'; end if;
  end if;
  if p ? 'title' then perform public.theme_check_i18n(p -> 'title', 200, true); end if;
  foreach f in array array['what_it_is', 'progress', 'problem', 'solution', 'success'] loop
    if p ? f then perform public.theme_check_i18n(p -> f, 1200, false); end if;
  end loop;
  if p ? 'status' and p ->> 'status' not in ('not_started', 'on_track', 'at_risk', 'blocked', 'paused', 'done', 'cancelled') then
    raise exception 'invalid status' using errcode = '22023';
  end if;
  if p ? 'route' and p ->> 'route' not in ('full', 'bug', 'p0') then raise exception 'invalid route' using errcode = '22023'; end if;
  if p ? 'resolution' and p ->> 'resolution' is not null
     and p ->> 'resolution' not in ('done', 'declined', 'deferred', 'merged', 'cancelled') then
    raise exception 'invalid resolution' using errcode = '22023';
  end if;
  if p ? 'stage' and p ->> 'stage' is not null then
    if t.kind <> 'project' or (p ->> 'stage')::integer not between 1 and 10 then raise exception 'invalid stage' using errcode = '22023'; end if;
  end if;
  if p ? 'tags' and (jsonb_typeof(p -> 'tags') is distinct from 'array' or jsonb_array_length(p -> 'tags') > 20
     or exists (select 1 from jsonb_array_elements(p -> 'tags') x where jsonb_typeof(x) is distinct from 'string' or char_length(x #>> '{}') not between 1 and 40)) then
    raise exception 'invalid tags' using errcode = '22023';
  end if;
  if p ? 'owner' and char_length(coalesce(p ->> 'owner', '')) > 80 then raise exception 'invalid owner' using errcode = '22023'; end if;
  update public.themes set
    front      = case when p ? 'front' then p ->> 'front' else front end,
    title      = case when p ? 'title' then p -> 'title' else title end,
    owner      = case when p ? 'owner' then nullif(btrim(coalesce(p ->> 'owner', '')), '') else owner end,
    status     = case when p ? 'status' then p ->> 'status' else status end,
    stage      = case when p ? 'stage' then nullif(p ->> 'stage', '')::integer else stage end,
    route      = case when p ? 'route' then p ->> 'route' else route end,
    what_it_is = case when p ? 'what_it_is' then p -> 'what_it_is' else what_it_is end,
    progress   = case when p ? 'progress' then p -> 'progress' else progress end,
    problem    = case when p ? 'problem' then p -> 'problem' else problem end,
    solution   = case when p ? 'solution' then p -> 'solution' else solution end,
    success    = case when p ? 'success' then p -> 'success' else success end,
    start_date = case when p ? 'start_date' then nullif(p ->> 'start_date', '')::date else start_date end,
    due_date   = case when p ? 'due_date' then nullif(p ->> 'due_date', '')::date else due_date end,
    tags       = case when p ? 'tags' then array(select jsonb_array_elements_text(p -> 'tags')) else tags end,
    resolution = case when p ? 'resolution' then nullif(p ->> 'resolution', '') else resolution end,
    updated_at = now()
  where id = p_id;
  select to_jsonb(x) into new_row from public.themes x where x.id = p_id;
  foreach f in array fields loop
    if old_row -> f is distinct from new_row -> f then
      insert into public.theme_events (theme_id, edited_by, field, old_value, new_value) values (p_id, btrim(p_by), f, old_row -> f, new_row -> f);
    end if;
  end loop;
end $$;

-- Edita uma frente: nome, texto do escopo e ordem (Outros fica sempre por último)
create or replace function public.update_front(p_key text, p jsonb, p_by text)
returns void language plpgsql security definer set search_path = public, extensions as $$
declare fr public.fronts;
begin
  perform public.theme_check_name(p_by);
  perform public.rfc_rate_limit(public.rfc_origin_hash(), 'theme', 120, 1000);
  select * into fr from public.fronts where key = p_key for update;
  if not found then raise exception 'unknown front' using errcode = '22023'; end if;
  if p ? 'name' then perform public.theme_check_i18n(p -> 'name', 60, true); end if;
  if p ? 'scope' then perform public.theme_check_i18n(p -> 'scope', 1200, false); end if;
  if p ? 'ord' and (fr.is_other or (p ->> 'ord')::integer not between 1 and 50) then raise exception 'invalid order' using errcode = '22023'; end if;
  update public.fronts set
    name  = case when p ? 'name' then p -> 'name' else name end,
    scope = case when p ? 'scope' then p -> 'scope' else scope end,
    ord   = case when p ? 'ord' then (p ->> 'ord')::integer else ord end
  where key = p_key;
end $$;

-- Itens de execução: cria (p_item nulo) ou altera; cada mudança de coluna vira um evento
create or replace function public.save_theme_item(p_theme text, p_item uuid, p jsonb, p_by text)
returns jsonb language plpgsql security definer set search_path = public, extensions as $$
declare t public.themes; it public.theme_items; new_id uuid; c text := p ->> 'col';
begin
  perform public.theme_check_name(p_by);
  perform public.rfc_rate_limit(public.rfc_origin_hash(), 'theme', 120, 1000);
  select * into t from public.themes where id = p_theme and not hidden;
  if not found or t.kind <> 'project' then raise exception 'unknown project' using errcode = '22023'; end if;
  if c is not null and c not in ('todo', 'doing', 'blocked', 'done') then raise exception 'invalid column' using errcode = '22023'; end if;
  if p ? 'title' and char_length(btrim(coalesce(p ->> 'title', ''))) not between 1 and 200 then raise exception 'invalid title' using errcode = '22023'; end if;
  if p_item is null then
    insert into public.theme_items (theme_id, title, owner, col, due_date, milestone, created_by)
      values (p_theme, btrim(p ->> 'title'), nullif(left(btrim(coalesce(p ->> 'owner', '')), 80), ''), coalesce(c, 'todo'),
              nullif(p ->> 'due_date', '')::date, coalesce((p ->> 'milestone')::boolean, false), btrim(p_by))
      returning id into new_id;
    insert into public.theme_events (theme_id, item_id, edited_by, field, new_value) values (p_theme, new_id, btrim(p_by), 'item_created', to_jsonb(btrim(p ->> 'title')));
    return jsonb_build_object('id', new_id);
  end if;
  select * into it from public.theme_items where id = p_item and theme_id = p_theme for update;
  if not found then raise exception 'unknown item' using errcode = '22023'; end if;
  update public.theme_items set
    title     = case when p ? 'title' then btrim(p ->> 'title') else title end,
    owner     = case when p ? 'owner' then nullif(left(btrim(coalesce(p ->> 'owner', '')), 80), '') else owner end,
    col       = coalesce(c, col),
    due_date  = case when p ? 'due_date' then nullif(p ->> 'due_date', '')::date else due_date end,
    milestone = case when p ? 'milestone' then (p ->> 'milestone')::boolean else milestone end,
    updated_at = now()
  where id = p_item;
  if c is not null and c <> it.col then
    insert into public.theme_events (theme_id, item_id, edited_by, field, old_value, new_value) values (p_theme, p_item, btrim(p_by), 'item_col', to_jsonb(it.col), to_jsonb(c));
  end if;
  return jsonb_build_object('id', p_item);
end $$;

-- Links do Jira: só o endereço (a chave vem dele)
create or replace function public.add_theme_jira(p_theme text, p_item uuid, p_url text, p_label text, p_by text)
returns jsonb language plpgsql security definer set search_path = public, extensions as $$
declare new_id uuid; k text;
begin
  perform public.theme_check_name(p_by);
  perform public.rfc_rate_limit(public.rfc_origin_hash(), 'theme', 120, 1000);
  perform 1 from public.themes where id = p_theme and not hidden;
  if not found then raise exception 'unknown theme' using errcode = '22023'; end if;
  if p_item is not null then
    perform 1 from public.theme_items where id = p_item and theme_id = p_theme;
    if not found then raise exception 'unknown item' using errcode = '22023'; end if;
  end if;
  if p_url is null or btrim(p_url) !~ '^https://[^ ]{4,500}$' then raise exception 'invalid url' using errcode = '22023'; end if;
  if p_label is not null and char_length(p_label) > 80 then raise exception 'invalid label' using errcode = '22023'; end if;
  k := substring(p_url from '([A-Z][A-Z0-9]+-[0-9]+)');
  insert into public.theme_jira (theme_id, item_id, url, label, issue_key, created_by)
    values (p_theme, p_item, btrim(p_url), nullif(btrim(coalesce(p_label, '')), ''), k, btrim(p_by)) returning id into new_id;
  insert into public.theme_events (theme_id, item_id, edited_by, field, new_value) values (p_theme, p_item, btrim(p_by), 'jira_added', to_jsonb(btrim(p_url)));
  return jsonb_build_object('id', new_id, 'issue_key', k);
end $$;

create or replace function public.remove_theme_jira(p_id uuid, p_by text)
returns void language plpgsql security definer set search_path = public, extensions as $$
declare j public.theme_jira;
begin
  perform public.theme_check_name(p_by);
  perform public.rfc_rate_limit(public.rfc_origin_hash(), 'theme', 120, 1000);
  select * into j from public.theme_jira where id = p_id;
  if not found then return; end if;
  delete from public.theme_jira where id = p_id;
  insert into public.theme_events (theme_id, item_id, edited_by, field, old_value) values (j.theme_id, j.item_id, btrim(p_by), 'jira_removed', to_jsonb(j.url));
end $$;

-- Dependências entre temas: liga ou desliga
create or replace function public.set_theme_link(p_theme text, p_to text, p_kind text, p_on boolean, p_by text)
returns void language plpgsql security definer set search_path = public, extensions as $$
begin
  perform public.theme_check_name(p_by);
  perform public.rfc_rate_limit(public.rfc_origin_hash(), 'theme', 120, 1000);
  if p_kind not in ('depends_on', 'blocks', 'related') or p_theme = p_to then raise exception 'invalid link' using errcode = '22023'; end if;
  perform 1 from public.themes where id = p_theme and not hidden;
  if not found then raise exception 'unknown theme' using errcode = '22023'; end if;
  perform 1 from public.themes where id = p_to and not hidden;
  if not found then raise exception 'unknown theme' using errcode = '22023'; end if;
  if p_on then
    insert into public.theme_links (theme_id, to_theme, kind) values (p_theme, p_to, p_kind) on conflict do nothing;
    insert into public.theme_events (theme_id, edited_by, field, new_value) values (p_theme, btrim(p_by), 'link_added', jsonb_build_object('to', p_to, 'kind', p_kind));
  else
    delete from public.theme_links where theme_id = p_theme and to_theme = p_to and kind = p_kind;
    insert into public.theme_events (theme_id, edited_by, field, old_value) values (p_theme, btrim(p_by), 'link_removed', jsonb_build_object('to', p_to, 'kind', p_kind));
  end if;
end $$;

-- Só as funções da página ficam abertas à chave pública; as auxiliares ficam fechadas
revoke all on function public.theme_check_i18n(jsonb, integer, boolean), public.theme_check_name(text) from public, anon, authenticated;
revoke all on function public.create_theme(jsonb, text), public.update_theme(text, jsonb, text), public.update_front(text, jsonb, text),
  public.save_theme_item(text, uuid, jsonb, text), public.add_theme_jira(text, uuid, text, text, text), public.remove_theme_jira(uuid, text),
  public.set_theme_link(text, text, text, boolean, text) from public;
grant execute on function public.create_theme(jsonb, text), public.update_theme(text, jsonb, text), public.update_front(text, jsonb, text),
  public.save_theme_item(text, uuid, jsonb, text), public.add_theme_jira(text, uuid, text, text, text), public.remove_theme_jira(uuid, text),
  public.set_theme_link(text, text, text, boolean, text) to anon, authenticated;

-- As RFCs já publicadas viram temas de projeto (frente confirmada em 2026-11-23; etapa e status a partir do status que a RFC tinha) ---
insert into public.themes (id, kind, front, title, owner, status, stage, resolution, created_at, created_by)
select m.id, 'project', m.front,
       coalesce(r.meta -> 'title', jsonb_build_object('pt', m.id)),
       nullif(left(btrim(coalesce(r.authors ->> 0, '')), 80), ''),
       case coalesce(s.status, 'draft') when 'draft' then 'not_started' when 'in-review' then 'on_track' when 'approved' then 'on_track'
            when 'implemented' then 'done' when 'rejected' then 'cancelled' else 'cancelled' end,
       case coalesce(s.status, 'draft') when 'draft' then 1 when 'in-review' then 3 when 'approved' then 4 when 'implemented' then 10 when 'rejected' then 3 else 3 end,
       case coalesce(s.status, 'draft') when 'implemented' then 'done' when 'rejected' then 'declined' when 'superseded' then 'cancelled' end,
       coalesce(r.created_at, now()), 'importação'
  from (values ('PHZ-0001', 'api-platform'), ('PHZ-0002', 'payments'), ('PHZ-0003', 'payments'), ('PHZ-0004', 'pop'),
               ('PHZ-0005', 'api-platform'), ('PHZ-0006', 'payments'), ('PHZ-0007', 'payments'), ('PHZ-0008', 'mini-apps')) as m(id, front)
  join public.rfc_ids i on i.rfc_id = m.id
  left join lateral (select x.meta, x.authors, x.created_at from public.rfc_revisions x where x.rfc_id = m.id order by x.rev desc limit 1) r on true
  left join public.rfc_status_current s on s.rfc_id = m.id
 where not exists (select 1 from public.themes t where t.id = m.id);

-- Temas iniciais de Outros, só com o nome (os PMs completam)
do $$
declare nm text;
begin
  foreach nm in array array['PhizShop e vendas via live', 'Merchant Golden Silver', 'Diagnóstico de Estopim', 'Ingoo e Café',
                            'Revisão de acessos ao PhizAdmin', 'Game Center', 'Deeper Link'] loop
    if not exists (select 1 from public.themes where front = 'outros' and title ->> 'pt' = nm) then
      insert into public.themes (id, kind, front, title, stage, created_by)
        values (public.rfc_allocate_id('theme', 'importação'), 'project', 'outros', jsonb_build_object('pt', nm, 'en', nm, 'zh', nm), 1, 'importação');
    end if;
  end loop;
end $$;
