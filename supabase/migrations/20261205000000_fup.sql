-- O modo FUP (docs/spec/v2/fup.md): a reunião de acompanhamento guarda só a pauta, os registros feitos nela e a foto ao fechar.
-- O que se registra vai direto para os temas pelas funções que já existem (decisões, itens, status); ao fechar, cada tema com registro
-- ganha uma atualização da semana. Idempotente: seguro rodar de novo.

create table if not exists public.fup_meetings (
  id         uuid primary key default gen_random_uuid(),
  title      text not null check (char_length(btrim(title)) between 1 and 120),
  held_on    date not null default (now() at time zone 'utc')::date,
  agenda     jsonb not null default '[]'::jsonb check (jsonb_typeof(agenda) = 'array'),
  log        jsonb not null default '[]'::jsonb check (jsonb_typeof(log) = 'array'),
  closed_at  timestamptz,
  snapshot   jsonb,
  created_by text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists fup_meetings_held_idx on public.fup_meetings (held_on desc);

alter table public.fup_meetings enable row level security;
revoke all on public.fup_meetings from anon, authenticated;
grant select on public.fup_meetings to authenticated;
drop policy if exists "read fups" on public.fup_meetings;
create policy "read fups" on public.fup_meetings for select to authenticated using (true);
drop policy if exists members_only on public.fup_meetings;
create policy members_only on public.fup_meetings as restrictive for all to authenticated using (public.is_member()) with check (public.is_member());

-- A pauta: [{theme, kind: inform|discuss|decide, on, star}]
create or replace function public.fup_check_agenda(p jsonb)
returns void language plpgsql immutable set search_path = public as $$
declare x jsonb;
begin
  if jsonb_typeof(p) is distinct from 'array' or jsonb_array_length(p) > 300 then raise exception 'invalid agenda' using errcode = '22023'; end if;
  for x in select * from jsonb_array_elements(p) loop
    if jsonb_typeof(x) is distinct from 'object' or coalesce(x ->> 'theme', '') !~ '^PHZ-[0-9]{4}$'
       or coalesce(x ->> 'kind', '') not in ('inform', 'discuss', 'decide')
       or jsonb_typeof(x -> 'on') is distinct from 'boolean' or jsonb_typeof(x -> 'star') is distinct from 'boolean' then
      raise exception 'invalid agenda' using errcode = '22023';
    end if;
  end loop;
end $$;

-- Os registros: [{theme, type: note|decision|action, text, progress: todo|doing|done, due, ref}]
create or replace function public.fup_check_log(p jsonb)
returns void language plpgsql immutable set search_path = public as $$
declare x jsonb;
begin
  if jsonb_typeof(p) is distinct from 'array' or jsonb_array_length(p) > 500 then raise exception 'invalid log' using errcode = '22023'; end if;
  for x in select * from jsonb_array_elements(p) loop
    if jsonb_typeof(x) is distinct from 'object' or coalesce(x ->> 'theme', '') !~ '^PHZ-[0-9]{4}$'
       or coalesce(x ->> 'type', '') not in ('note', 'decision', 'action')
       or char_length(btrim(coalesce(x ->> 'text', ''))) not between 1 and 1200
       or coalesce(x ->> 'progress', '') not in ('todo', 'doing', 'done')
       or (x ->> 'due' is not null and x ->> 'due' !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$')
       or (x ->> 'ref' is not null and x ->> 'ref' !~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$') then
      raise exception 'invalid log' using errcode = '22023';
    end if;
  end loop;
end $$;

-- Cria (p_id nulo) ou altera um FUP aberto: só vão as chaves presentes em p (title, held_on, agenda, log)
create or replace function public.save_fup(p_id uuid, p jsonb, p_by text)
returns jsonb language plpgsql security definer set search_path = public, extensions as $$
declare f public.fup_meetings; new_id uuid;
begin
  perform public.theme_check_name(p_by);
  perform public.rfc_rate_limit(public.rfc_origin_hash(), 'fup', 600, 5000);
  if p ? 'title' and char_length(btrim(coalesce(p ->> 'title', ''))) not between 1 and 120 then raise exception 'invalid title' using errcode = '22023'; end if;
  if p ? 'held_on' and coalesce(p ->> 'held_on', '') !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' then raise exception 'invalid date' using errcode = '22023'; end if;
  if p ? 'agenda' then perform public.fup_check_agenda(p -> 'agenda'); end if;
  if p ? 'log' then perform public.fup_check_log(p -> 'log'); end if;
  if p_id is null then
    if char_length(btrim(coalesce(p ->> 'title', ''))) = 0 then raise exception 'invalid title' using errcode = '22023'; end if;
    insert into public.fup_meetings (title, held_on, agenda, log, created_by)
      values (btrim(p ->> 'title'), coalesce((p ->> 'held_on')::date, (now() at time zone 'utc')::date), coalesce(p -> 'agenda', '[]'::jsonb),
              coalesce(p -> 'log', '[]'::jsonb), btrim(p_by))
      returning id into new_id;
    return jsonb_build_object('id', new_id);
  end if;
  select * into f from public.fup_meetings where id = p_id for update;
  if not found then raise exception 'unknown fup' using errcode = '22023'; end if;
  if f.closed_at is not null then raise exception 'fup closed' using errcode = '22023'; end if;
  update public.fup_meetings set
    title      = case when p ? 'title' then btrim(p ->> 'title') else title end,
    held_on    = case when p ? 'held_on' then (p ->> 'held_on')::date else held_on end,
    agenda     = case when p ? 'agenda' then p -> 'agenda' else agenda end,
    log        = case when p ? 'log' then p -> 'log' else log end,
    updated_at = now()
  where id = p_id;
  return jsonb_build_object('id', p_id);
end $$;

-- Fecha o FUP: congela a foto e escreve uma atualização da semana em cada tema que teve registro
create or replace function public.close_fup(p_id uuid, p_by text)
returns jsonb language plpgsql security definer set search_path = public, extensions as $$
declare f public.fup_meetings; tid text; notes text; nexts text; day text; statuses jsonb := '{}'::jsonb; n integer := 0;
begin
  perform public.theme_check_name(p_by);
  select * into f from public.fup_meetings where id = p_id for update;
  if not found then raise exception 'unknown fup' using errcode = '22023'; end if;
  if f.closed_at is not null then raise exception 'fup closed' using errcode = '22023'; end if;
  day := to_char(f.held_on, 'DD/MM/YYYY');
  for tid in select distinct x ->> 'theme' from jsonb_array_elements(f.log) x loop
    perform 1 from public.themes where id = tid and not hidden;
    if not found then continue; end if;
    select string_agg(case when x ->> 'type' = 'decision' then 'Decidido: ' || (x ->> 'text') else x ->> 'text' end, E'\n')
      into notes from jsonb_array_elements(f.log) x where x ->> 'theme' = tid and x ->> 'type' in ('note', 'decision');
    select string_agg((x ->> 'text') || coalesce(' (até ' || to_char((x ->> 'due')::date, 'DD/MM') || ')', ''), E'\n')
      into nexts from jsonb_array_elements(f.log) x where x ->> 'theme' = tid and x ->> 'type' = 'action';
    perform public.post_theme_update(tid, jsonb_strip_nulls(jsonb_build_object(
      'progress', jsonb_build_object('pt', 'Tratado no FUP de ' || day || '.'),
      'advanced', case when notes is not null then jsonb_build_object('pt', left(notes, 2000)) end,
      'next_step', case when nexts is not null then jsonb_build_object('pt', left(nexts, 2000)) end)), p_by);
    n := n + 1;
  end loop;
  select coalesce(jsonb_object_agg(t.id, t.status), '{}'::jsonb) into statuses
    from public.themes t where t.id in (select x ->> 'theme' from jsonb_array_elements(f.agenda) x where (x ->> 'on')::boolean);
  update public.fup_meetings set closed_at = now(), updated_at = now(),
    snapshot = jsonb_build_object('agenda', f.agenda, 'log', f.log, 'statuses', statuses, 'closed_by', btrim(p_by))
  where id = p_id;
  return jsonb_build_object('id', p_id, 'updates', n);
end $$;

revoke all on function public.fup_check_agenda(jsonb), public.fup_check_log(jsonb) from public, anon, authenticated;
revoke all on function public.save_fup(uuid, jsonb, text), public.close_fup(uuid, text) from public, anon;
grant execute on function public.save_fup(uuid, jsonb, text), public.close_fup(uuid, text) to authenticated;
