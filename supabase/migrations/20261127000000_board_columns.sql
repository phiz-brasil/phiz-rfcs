-- Quadro B2B: colunas configuráveis, checklist de gates e movimentação de cards (fase 5 do plano em docs/spec/v2).
-- Idempotente: seguro rodar de novo no SQL Editor (o seed só insere o que falta).
--
-- Os temas de tipo projeto andam pelas dez etapas da norma V4. O quadro tem colunas configuráveis: cada coluna aponta para UMA etapa (várias colunas
-- podem apontar para a mesma). Mover um card grava um evento 'move' em theme_events com colunas e etapas de origem e destino, quem moveu, o motivo
-- (obrigatório ao pular etapas da rota ou sair dela) e os gates que estavam abertos. Gate aberto avisa, não bloqueia.
-- Ainda não há login: qualquer pessoa com nome configura as colunas; quando houver, isso passa a ser só de admin.

-- Gates da norma (dados, não código: uma mudança do piloto é uma mudança de linha) ------------------------------------
create table if not exists public.stage_gates (
  key          text primary key check (key ~ '^[0-9]{2}-[a-z0-9-]{2,30}$'),
  stage        integer not null check (stage between 1 and 10),
  position     integer not null,
  title        jsonb not null,                          -- {pt, en, zh}
  owner_role   text,                                    -- quem confirma (texto livre)
  non_waivable boolean not null default false           -- piso inegociável da norma: só avisa, mas em vermelho
);

-- Colunas do quadro --------------------------------------------------------------------------------------------------
create table if not exists public.board_columns (
  id         uuid primary key default gen_random_uuid(),
  board      text not null default 'b2b' check (board = 'b2b'),
  name       jsonb not null,                            -- {pt, en, zh}
  position   integer not null,
  stage      integer not null check (stage between 1 and 10),
  wip_limit  integer check (wip_limit is null or wip_limit > 0),
  created_at timestamptz not null default now()
);

alter table public.themes add column if not exists board_column uuid references public.board_columns (id) on delete set null;

-- Gate marcado por uma pessoa, com a evidência (link, anexo, chave do Jira, seção da RFC) ---------------------------------
create table if not exists public.theme_gate_checks (
  theme_id   text not null references public.themes (id),
  gate_key   text not null references public.stage_gates (key),
  evidence   text not null check (char_length(btrim(evidence)) between 1 and 500),
  checked_by text not null,
  checked_at timestamptz not null default now(),
  primary key (theme_id, gate_key)
);

alter table public.stage_gates enable row level security;
alter table public.board_columns enable row level security;
alter table public.theme_gate_checks enable row level security;
revoke all on public.stage_gates, public.board_columns, public.theme_gate_checks from anon, authenticated;
grant select on public.stage_gates, public.board_columns, public.theme_gate_checks to anon, authenticated;
drop policy if exists "read stage gates" on public.stage_gates;
create policy "read stage gates" on public.stage_gates for select to anon, authenticated using (true);
drop policy if exists "read board columns" on public.board_columns;
create policy "read board columns" on public.board_columns for select to anon, authenticated using (true);
drop policy if exists "read gate checks" on public.theme_gate_checks;
create policy "read gate checks" on public.theme_gate_checks for select to anon, authenticated
  using (exists (select 1 from public.themes t where t.id = theme_gate_checks.theme_id and not t.hidden));

-- Seed: os gates da norma V4 e as dez colunas padrão --------------------------------------------------------------------
insert into public.stage_gates (key, stage, position, title, owner_role, non_waivable) values
  ('01-triage',     1, 1, '{"pt":"Informações obrigatórias completas e impacto verificável","en":"Required information complete and impact verifiable","zh":"必填信息完整且影响可验证"}', 'Product (triagem)', false),
  ('01-owner',      1, 2, '{"pt":"Um responsável (Path Owner ou Product Owner) definido","en":"One Path Owner or Product Owner assigned","zh":"已指定一位 Path Owner 或 Product Owner"}', 'Business Owner', false),
  ('02-evidence',   2, 1, '{"pt":"Evidências sustentam problema, escala e custo de não agir","en":"Evidence supports the problem, its scale and the cost of inaction","zh":"证据支持问题、规模与不作为的代价"}', 'Product Owner', false),
  ('02-input',      2, 2, '{"pt":"Engenharia e QA deram parecer","en":"Engineering and QA gave input","zh":"工程与 QA 已给出意见"}', 'Leads de Engenharia e QA', false),
  ('03-approved',   3, 1, '{"pt":"Seguir adiante aprovado explicitamente, com escopo e pré-requisitos","en":"Proceed explicitly approved, with scope and prerequisites","zh":"明确批准继续，并确定范围与前置条件"}', 'Product/Path Owner', false),
  ('04-prd',        4, 1, '{"pt":"PRD no padrão","en":"PRD follows the standard","zh":"PRD 符合标准"}', 'Product Owner', false),
  ('04-acceptance', 4, 2, '{"pt":"Todo requisito tem aceite testável","en":"Every requirement has testable acceptance","zh":"每条需求都有可测试的验收标准"}', 'QA', false),
  ('04-boundaries', 4, 3, '{"pt":"Fronteiras entre capacidades claras","en":"Boundaries between capabilities are clear","zh":"能力边界清晰"}', 'Capability Owners', false),
  ('04-signoffs',   4, 4, '{"pt":"Aprovações de alto risco (Segurança, DPO, Jurídico, Financeiro)","en":"High-risk sign-offs (Security, DPO, Legal, Finance)","zh":"高风险签核（安全、DPO、法务、财务）"}', 'Segurança, DPO, Jurídico, Financeiro', true),
  ('04-jira',       4, 5, '{"pt":"Issue do Jira liga a RFC e o PRD","en":"Jira issue links the RFC and the PRD","zh":"Jira 单关联 RFC 与 PRD"}', 'Product Owner', false),
  ('05-conclusions',5, 1, '{"pt":"Quatro conclusões registradas e aprovadas (ou aprovadas com condições)","en":"Four conclusions recorded and approved (or conditionally approved)","zh":"四项结论已记录并获批（或附条件批准）"}', 'Project Manager', false),
  ('05-blockers',   5, 2, '{"pt":"Bloqueios fechados; condições com responsável e data","en":"Blockers closed; conditions with owner and date","zh":"阻塞已关闭；条件有负责人和日期"}', 'Project Manager', false),
  ('06-milestones', 6, 1, '{"pt":"Prioridades e quatro marcos com responsáveis e evidências","en":"Priorities and four milestones with owners and evidence","zh":"优先级与四个里程碑已有负责人和证据"}', 'Project Manager', false),
  ('06-deps',       6, 2, '{"pt":"Dependências externas acordadas por escrito","en":"External dependencies committed in writing","zh":"外部依赖已书面承诺"}', 'Project Manager', false),
  ('06-dates',      6, 3, '{"pt":"Engenharia e QA confirmaram as datas","en":"Engineering and QA confirmed the dates","zh":"工程与 QA 已确认日期"}', 'Leads de Engenharia e QA', false),
  ('07-pipeline',   7, 1, '{"pt":"Pipeline dentro do padrão","en":"Pipeline meets the standard","zh":"流水线符合标准"}', 'Engineering Capability Owner', false),
  ('07-contracts',  7, 2, '{"pt":"Contratos conferem com os documentos","en":"Contracts match the documents","zh":"接口契约与文档一致"}', 'Engineering Capability Owner', false),
  ('07-selftest',   7, 3, '{"pt":"Autoteste cobre os ids de requisito e as exceções","en":"Self-test covers requirement ids and exceptions","zh":"自测覆盖需求编号与异常"}', 'Engineering Capability Owner', false),
  ('07-registry',   7, 4, '{"pt":"Flags, migrações e valores fixos registrados","en":"Flags, migrations and hard-coded values registered","zh":"开关、迁移与硬编码值已登记"}', 'Engineering Capability Owner', false),
  ('08-floors',     8, 1, '{"pt":"Itens inegociáveis passam (consistência financeira, segurança de autorização, dados pessoais)","en":"Non-waivable items pass (financial consistency, authorization security, personal data)","zh":"不可豁免项通过（资金一致性、授权安全、个人数据）"}', 'QA', true),
  ('08-acceptance', 8, 2, '{"pt":"Aceite de negócio completo","en":"Business acceptance complete","zh":"业务验收完成"}', 'Business', true),
  ('08-residual',   8, 3, '{"pt":"Pendências residuais com responsável e data","en":"Residual issues owned and dated","zh":"遗留问题有负责人和日期"}', 'QA', false),
  ('08-signoffs',   8, 4, '{"pt":"Aprovações de finanças, privacidade e permissões","en":"Finance, privacy and permission sign-offs","zh":"财务、隐私与权限签核"}', 'Finanças, DPO, Segurança', true),
  ('09-frozen',     9, 1, '{"pt":"Pacote congelado","en":"Package frozen","zh":"发布包已冻结"}', 'Launch Owner', false),
  ('09-rollback',   9, 2, '{"pt":"Rollback executado fora da produção","en":"Rollback executed outside production","zh":"已在生产外演练回滚"}', 'Engenharia', true),
  ('09-monitoring', 9, 3, '{"pt":"Monitoramento e plantão ativos","en":"Monitoring and duty active","zh":"监控与值守已就绪"}', 'Launch Owner', false),
  ('09-ready',      9, 4, '{"pt":"Suporte, comunicação e conciliação prontos","en":"Support, communication and reconciliation ready","zh":"客服、沟通与对账已就绪"}', 'Launch Owner', false),
  ('10-metrics',   10, 1, '{"pt":"Métricas dentro dos limites ou rollback seguro","en":"Metrics within thresholds or safe rollback","zh":"指标在阈值内或已安全回滚"}', 'Project Manager', false),
  ('10-reconcile', 10, 2, '{"pt":"Primeira conciliação financeira fecha","en":"First financial reconciliation balances","zh":"首次资金对账一致"}', 'Finanças', true),
  ('10-summary',   10, 3, '{"pt":"Resumo do projeto e ações registrados","en":"Project summary and actions recorded","zh":"项目总结与行动项已记录"}', 'Project Manager', false),
  ('10-value',     10, 4, '{"pt":"Revisão de valor agendada","en":"Value review scheduled","zh":"已安排价值复盘"}', 'Path Owner', false)
on conflict (key) do nothing;

insert into public.board_columns (name, position, stage)
select n.name, n.stage, n.stage from (values
  (1,  '{"pt":"01 Solicitação","en":"01 Request","zh":"01 需求提出"}'::jsonb),
  (2,  '{"pt":"02 Pesquisa","en":"02 Research","zh":"02 需求调研"}'::jsonb),
  (3,  '{"pt":"03 Decisão","en":"03 Decision","zh":"03 立项决策"}'::jsonb),
  (4,  '{"pt":"04 PRD e início","en":"04 PRD and kickoff","zh":"04 PRD 与启动"}'::jsonb),
  (5,  '{"pt":"05 Revisão da solução","en":"05 Solution review","zh":"05 方案评审"}'::jsonb),
  (6,  '{"pt":"06 Planejamento","en":"06 Planning","zh":"06 项目排期"}'::jsonb),
  (7,  '{"pt":"07 Desenvolvimento","en":"07 Build","zh":"07 开发"}'::jsonb),
  (8,  '{"pt":"08 Testes","en":"08 QA","zh":"08 测试验收"}'::jsonb),
  (9,  '{"pt":"09 Publicação","en":"09 Release","zh":"09 发布准备"}'::jsonb),
  (10, '{"pt":"10 Lançamento","en":"10 Launch","zh":"10 上线收口"}'::jsonb)
) as n(stage, name)
where not exists (select 1 from public.board_columns);

-- As etapas que a rota percorre: full/supplement/tech 1–10, bug 6–10, p0 7–10 ------------------------------------------------
create or replace function public.route_stages(p_route text)
returns integer[] language sql immutable as $$
  select case p_route when 'bug' then array[6,7,8,9,10] when 'p0' then array[7,8,9,10] else array[1,2,3,4,5,6,7,8,9,10] end
$$;

-- Mover um card ----------------------------------------------------------------------------------------------------------
create or replace function public.move_theme_card(p_theme text, p_column uuid, p_by text, p_reason text default null)
returns jsonb language plpgsql security definer set search_path = public, extensions as $$
declare t public.themes; dest public.board_columns; cur public.board_columns; from_stage integer; rstages integer[]; skipped boolean; off_route boolean;
  open_gates jsonb := '[]'::jsonb; ev jsonb;
begin
  perform public.theme_check_name(p_by);
  perform public.rfc_rate_limit(public.rfc_origin_hash(), 'theme', 120, 1000);
  select * into t from public.themes where id = p_theme and not hidden for update;
  if not found or t.kind <> 'project' then raise exception 'unknown theme' using errcode = '22023'; end if;
  select * into dest from public.board_columns where id = p_column;
  if not found then raise exception 'unknown column' using errcode = '22023'; end if;
  if char_length(coalesce(p_reason, '')) > 300 then raise exception 'invalid reason' using errcode = '22023'; end if;
  -- a coluna de hoje: a gravada, se ainda aponta para a etapa do tema; senão a primeira coluna da etapa
  select * into cur from public.board_columns c where c.id = t.board_column and c.stage = t.stage;
  if not found and t.stage is not null then
    select * into cur from public.board_columns c where c.stage = t.stage order by c.position, c.created_at limit 1;
  end if;
  if cur.id = dest.id then return jsonb_build_object('moved', false); end if;
  from_stage := t.stage;
  rstages := public.route_stages(t.route);
  skipped := dest.stage > coalesce(from_stage, 0) and exists (select 1 from unnest(rstages) s where s > coalesce(from_stage, 0) and s < dest.stage);
  off_route := not (dest.stage = any (rstages));
  if (skipped or off_route) and char_length(btrim(coalesce(p_reason, ''))) = 0 then raise exception 'reason required' using errcode = '22023'; end if;
  if from_stage is not null and dest.stage > from_stage then
    select coalesce(jsonb_agg(g.key order by g.position), '[]'::jsonb) into open_gates
      from public.stage_gates g
      where g.stage = from_stage
        and not exists (select 1 from public.theme_gate_checks k where k.theme_id = p_theme and k.gate_key = g.key);
  end if;
  update public.themes set stage = dest.stage, board_column = dest.id, updated_at = now() where id = p_theme;
  ev := jsonb_build_object('from_column', cur.id, 'to_column', dest.id, 'from_stage', from_stage, 'to_stage', dest.stage, 'open_gates', open_gates,
                           'reason', nullif(btrim(coalesce(p_reason, '')), ''));
  insert into public.theme_events (theme_id, edited_by, field, old_value, new_value)
    values (p_theme, btrim(p_by), 'move', null, ev);
  return jsonb_build_object('moved', true, 'open_gates', open_gates);
end $$;

-- Marcar ou desmarcar um gate --------------------------------------------------------------------------------------------
create or replace function public.set_theme_gate(p_theme text, p_gate text, p_evidence text, p_by text)
returns void language plpgsql security definer set search_path = public, extensions as $$
declare t public.themes;
begin
  perform public.theme_check_name(p_by);
  perform public.rfc_rate_limit(public.rfc_origin_hash(), 'theme', 120, 1000);
  select * into t from public.themes where id = p_theme and not hidden;
  if not found or t.kind <> 'project' then raise exception 'unknown theme' using errcode = '22023'; end if;
  perform 1 from public.stage_gates where key = p_gate;
  if not found then raise exception 'unknown gate' using errcode = '22023'; end if;
  if p_evidence is null or char_length(btrim(p_evidence)) = 0 then
    delete from public.theme_gate_checks where theme_id = p_theme and gate_key = p_gate;
    insert into public.theme_events (theme_id, edited_by, field, new_value) values (p_theme, btrim(p_by), 'gate_unchecked', to_jsonb(p_gate));
    return;
  end if;
  if char_length(btrim(p_evidence)) > 500 then raise exception 'invalid evidence' using errcode = '22023'; end if;
  insert into public.theme_gate_checks (theme_id, gate_key, evidence, checked_by) values (p_theme, p_gate, btrim(p_evidence), btrim(p_by))
    on conflict (theme_id, gate_key) do update set evidence = excluded.evidence, checked_by = excluded.checked_by, checked_at = now();
  insert into public.theme_events (theme_id, edited_by, field, new_value) values (p_theme, btrim(p_by), 'gate_checked', to_jsonb(p_gate));
end $$;

-- Configurar colunas ----------------------------------------------------------------------------------------------------
create or replace function public.save_board_column(p_id uuid, p jsonb, p_by text)
returns jsonb language plpgsql security definer set search_path = public, extensions as $$
declare new_id uuid; c public.board_columns; wip integer;
begin
  perform public.theme_check_name(p_by);
  perform public.rfc_rate_limit(public.rfc_origin_hash(), 'theme', 120, 1000);
  if p ? 'name' then perform public.theme_check_i18n(p -> 'name', 60, true); end if;
  if p ? 'stage' and (p ->> 'stage')::integer not between 1 and 10 then raise exception 'invalid stage' using errcode = '22023'; end if;
  if p ? 'position' and (p ->> 'position')::integer not between 1 and 100 then raise exception 'invalid position' using errcode = '22023'; end if;
  if p ? 'wip_limit' then
    wip := nullif(p ->> 'wip_limit', '')::integer;
    if wip is not null and wip < 1 then raise exception 'invalid limit' using errcode = '22023'; end if;
  end if;
  if p_id is null then
    if not (p ? 'name' and p ? 'stage') then raise exception 'name and stage required' using errcode = '22023'; end if;
    insert into public.board_columns (name, position, stage, wip_limit)
      values (p -> 'name', coalesce((p ->> 'position')::integer, (select coalesce(max(position), 0) + 1 from public.board_columns)),
              (p ->> 'stage')::integer, nullif(p ->> 'wip_limit', '')::integer) returning id into new_id;
    return jsonb_build_object('id', new_id);
  end if;
  select * into c from public.board_columns where id = p_id for update;
  if not found then raise exception 'unknown column' using errcode = '22023'; end if;
  -- mudar a etapa de uma coluna não pode deixar uma etapa com cards sem coluna
  if p ? 'stage' and (p ->> 'stage')::integer <> c.stage
     and not exists (select 1 from public.board_columns o where o.stage = c.stage and o.id <> c.id)
     and exists (select 1 from public.themes t where t.stage = c.stage and t.kind = 'project' and not t.hidden and t.resolution is null) then
    raise exception 'stage in use' using errcode = '22023';
  end if;
  update public.board_columns set
    name      = case when p ? 'name' then p -> 'name' else name end,
    position  = case when p ? 'position' then (p ->> 'position')::integer else position end,
    stage     = case when p ? 'stage' then (p ->> 'stage')::integer else stage end,
    wip_limit = case when p ? 'wip_limit' then nullif(p ->> 'wip_limit', '')::integer else wip_limit end
  where id = p_id;
  return jsonb_build_object('id', p_id);
end $$;

create or replace function public.delete_board_column(p_id uuid, p_by text)
returns void language plpgsql security definer set search_path = public, extensions as $$
declare c public.board_columns;
begin
  perform public.theme_check_name(p_by);
  perform public.rfc_rate_limit(public.rfc_origin_hash(), 'theme', 120, 1000);
  select * into c from public.board_columns where id = p_id for update;
  if not found then raise exception 'unknown column' using errcode = '22023'; end if;
  if not exists (select 1 from public.board_columns o where o.stage = c.stage and o.id <> c.id)
     and exists (select 1 from public.themes t where t.stage = c.stage and t.kind = 'project' and not t.hidden and t.resolution is null) then
    raise exception 'stage in use' using errcode = '22023';
  end if;
  delete from public.board_columns where id = p_id;       -- themes.board_column vira null e o card cai na primeira coluna da etapa
end $$;

revoke all on function public.route_stages(text), public.move_theme_card(text, uuid, text, text), public.set_theme_gate(text, text, text, text),
  public.save_board_column(uuid, jsonb, text), public.delete_board_column(uuid, text) from public;
grant execute on function public.move_theme_card(text, uuid, text, text), public.set_theme_gate(text, text, text, text),
  public.save_board_column(uuid, jsonb, text), public.delete_board_column(uuid, text) to anon, authenticated;
