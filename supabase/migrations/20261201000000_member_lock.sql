-- O cadeado do banco (fase 2, fatia 2 — docs/spec/v2/login.md): só quem tem conta @phiz.com lê ou escreve.
-- NÃO aplicar antes da virada (fatia 3): ele fecha o acesso anônimo de uma vez. Idempotente: seguro rodar de novo.
-- Ordem da virada: SMTP e URLs prontos → interruptor auth.required ligado (as pessoas começam a entrar) → secret REQUIRE_MEMBER=1 e deploy de suggest-summary → ESTE arquivo.
--
-- Como funciona:
--  1. is_member() / is_admin(): quem é membro (JWT de role authenticated com e-mail @phiz.com) e quem é admin (app_admins; enquanto estiver vazia, todo membro é admin).
--  2. check_request(): o portão único da API REST (db_pre_request do PostgREST): service_role e /rpc/ping passam; anon leva 401; conta de outro domínio leva 403.
--  3. Defesa em profundidade: anon perde tudo no schema public (e nos padrões para objetos novos); cada tabela com RLS ganha a política restritiva members_only.
--  4. Storage: as políticas do bucket attachments passam a ser só de membros.
--  5. Admin: save_board_column e delete_board_column ganham UMA linha (is_admin()); o resto delas é igual ao de 20261127000000_board_columns.sql.
--  6. ping(): para o job de keep-alive. 7. O portão é ligado na ÚLTIMA instrução; o desfazer está no fim do arquivo.

-- 1. Quem é membro, quem é admin ---------------------------------------------------------------------------------------------------
create table if not exists public.app_admins (
  email      text primary key check (email = lower(email) and email ~ '^[^@]+@phiz\.com$'),
  created_at timestamptz not null default now()
);
alter table public.app_admins enable row level security;
revoke all on public.app_admins from anon, authenticated;

create or replace function public.is_member()
returns boolean language sql stable set search_path = '' as $$
  select coalesce(auth.jwt() ->> 'role', '') = 'authenticated'
     and coalesce(lower(auth.jwt() ->> 'email'), '') ~ '^[^@]+@phiz\.com$'
$$;

create or replace function public.is_admin()
returns boolean language sql stable security definer set search_path = public as $$
  select public.is_member()
     and (not exists (select 1 from public.app_admins)                                   -- ninguém nomeado ainda: todo membro é admin
          or exists (select 1 from public.app_admins a where a.email = lower(auth.jwt() ->> 'email')))
$$;

create or replace function public.ping()
returns boolean language sql stable set search_path = '' as $$ select true $$;

-- 2. O portão único da API ---------------------------------------------------------------------------------------------------------
create or replace function public.check_request()
returns void language plpgsql stable set search_path = public as $$
declare
  claims jsonb := coalesce(nullif(current_setting('request.jwt.claims', true), '')::jsonb, '{}'::jsonb);
  who text := coalesce(claims ->> 'role', current_user);
  path text := coalesce(current_setting('request.path', true), '');
begin
  if who = 'service_role' or current_user in ('postgres', 'supabase_admin', 'service_role') then return; end if;     -- funções de borda, webhooks, migrações
  if path = '/rpc/ping' then return; end if;                                                                         -- o keep-alive
  if who = 'anon' then raise sqlstate 'PT401' using message = 'sign in with a @phiz.com account'; end if;
  if not public.is_member() then raise sqlstate 'PT403' using message = 'only @phiz.com accounts have access'; end if;
end $$;

grant execute on function public.check_request(), public.ping(), public.is_member() to anon, authenticated;
grant execute on function public.is_admin() to authenticated;

-- 3. Defesa em profundidade -----------------------------------------------------------------------------------------------------
revoke all on all tables in schema public from anon;
revoke all on all functions in schema public from anon;
revoke all on all sequences in schema public from anon;
alter default privileges in schema public revoke all on tables from anon;
alter default privileges in schema public revoke all on functions from anon;
alter default privileges in schema public revoke all on sequences from anon;
grant execute on function public.check_request(), public.ping(), public.is_member() to anon;           -- o que o revoke acima tirou e o portão precisa

do $$
declare t record;
begin
  for t in select c.relname from pg_class c join pg_namespace n on n.oid = c.relnamespace
           where n.nspname = 'public' and c.relkind in ('r', 'p') and c.relrowsecurity loop
    execute format('drop policy if exists members_only on public.%I', t.relname);
    execute format('create policy members_only on public.%I as restrictive for all to authenticated using (public.is_member()) with check (public.is_member())', t.relname);
  end loop;
end $$;

-- 4. Storage: o bucket attachments só para membros ---------------------------------------------------------------------------------
drop policy if exists "attachments read" on storage.objects;
create policy "attachments read" on storage.objects for select to authenticated using (bucket_id = 'attachments' and public.is_member());
drop policy if exists "attachments upload" on storage.objects;
create policy "attachments upload" on storage.objects for insert to authenticated
  with check (bucket_id = 'attachments' and public.is_member()
              and name ~ '^PHZ-[0-9]{4}/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/[^/]{1,150}$');
drop policy if exists "attachments members only" on storage.objects;
create policy "attachments members only" on storage.objects as restrictive for all to authenticated
  using (bucket_id <> 'attachments' or public.is_member()) with check (bucket_id <> 'attachments' or public.is_member());

-- 5. Admin: configurar as colunas do quadro ----------------------------------------------------------------------------------------
create or replace function public.save_board_column(p_id uuid, p jsonb, p_by text)
returns jsonb language plpgsql security definer set search_path = public, extensions as $$
declare new_id uuid; c public.board_columns; wip integer;
begin
  if not public.is_admin() then raise exception 'only admins can configure the board' using errcode = '42501'; end if;
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
  if not public.is_admin() then raise exception 'only admins can configure the board' using errcode = '42501'; end if;
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

revoke all on function public.save_board_column(uuid, jsonb, text), public.delete_board_column(uuid, text) from public, anon;
grant execute on function public.save_board_column(uuid, jsonb, text), public.delete_board_column(uuid, text) to authenticated;

-- 7. O portão, por último -------------------------------------------------------------------------------------------------------
alter role authenticator set pgrst.db_pre_request = 'public.check_request';
notify pgrst, 'reload config';

-- DESFAZER (rodar no SQL Editor, que não passa pela API REST; volta a como era antes do portão):
--   alter role authenticator reset pgrst.db_pre_request;
--   notify pgrst, 'reload config';
-- (os revokes de anon não são desfeitos por isso: para reabrir tudo, volte também os grants das migrações anteriores)
