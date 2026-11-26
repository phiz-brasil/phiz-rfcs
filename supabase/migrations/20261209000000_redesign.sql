-- Redesenho, PR 1 (docs/spec/v2/redesign.md, "Data"): as entregas (itens de execução) ganham data de início, para terem um período na linha do tempo;
-- bloqueios e decisões ganham urgência (urgent, important, info), mostrada no Painel. Idempotente.

-- 1. Período das entregas ------------------------------------------------------------------------------------------------------------------
alter table public.theme_items add column if not exists start_date date;
do $$ begin
  if not exists (select 1 from pg_constraint where conname = 'theme_items_period_check') then
    alter table public.theme_items add constraint theme_items_period_check check (start_date is null or due_date is null or start_date <= due_date);
  end if;
end $$;

create or replace function public.save_theme_item(p_theme text, p_item uuid, p jsonb, p_by text)
returns jsonb language plpgsql security definer set search_path = public, extensions as $$
declare t public.themes; it public.theme_items; new_id uuid; c text := p ->> 'col'; s date; d date;
begin
  perform public.theme_check_name(p_by);
  perform public.rfc_rate_limit(public.rfc_origin_hash(), 'theme', 120, 1000);
  select * into t from public.themes where id = p_theme and not hidden;
  if not found or t.kind <> 'project' then raise exception 'unknown project' using errcode = '22023'; end if;
  if c is not null and c not in ('todo', 'doing', 'blocked', 'done') then raise exception 'invalid column' using errcode = '22023'; end if;
  if p ? 'title' and char_length(btrim(coalesce(p ->> 'title', ''))) not between 1 and 200 then raise exception 'invalid title' using errcode = '22023'; end if;
  if p_item is null then
    s := nullif(p ->> 'start_date', '')::date;
    d := nullif(p ->> 'due_date', '')::date;
    if s is not null and d is not null and s > d then raise exception 'invalid period' using errcode = '22023'; end if;
    insert into public.theme_items (theme_id, title, owner, col, start_date, due_date, milestone, created_by)
      values (p_theme, btrim(p ->> 'title'), nullif(left(btrim(coalesce(p ->> 'owner', '')), 80), ''), coalesce(c, 'todo'),
              s, d, coalesce((p ->> 'milestone')::boolean, false), btrim(p_by))
      returning id into new_id;
    insert into public.theme_events (theme_id, item_id, edited_by, field, new_value) values (p_theme, new_id, btrim(p_by), 'item_created', to_jsonb(btrim(p ->> 'title')));
    return jsonb_build_object('id', new_id);
  end if;
  select * into it from public.theme_items where id = p_item and theme_id = p_theme for update;
  if not found then raise exception 'unknown item' using errcode = '22023'; end if;
  s := case when p ? 'start_date' then nullif(p ->> 'start_date', '')::date else it.start_date end;
  d := case when p ? 'due_date' then nullif(p ->> 'due_date', '')::date else it.due_date end;
  if s is not null and d is not null and s > d then raise exception 'invalid period' using errcode = '22023'; end if;
  update public.theme_items set
    title      = case when p ? 'title' then btrim(p ->> 'title') else title end,
    owner      = case when p ? 'owner' then nullif(left(btrim(coalesce(p ->> 'owner', '')), 80), '') else owner end,
    col        = coalesce(c, col),
    start_date = s,
    due_date   = d,
    milestone  = case when p ? 'milestone' then (p ->> 'milestone')::boolean else milestone end,
    updated_at = now()
  where id = p_item;
  if c is not null and c <> it.col then
    insert into public.theme_events (theme_id, item_id, edited_by, field, old_value, new_value) values (p_theme, p_item, btrim(p_by), 'item_col', to_jsonb(it.col), to_jsonb(c));
  end if;
  if s is distinct from it.start_date or d is distinct from it.due_date then
    insert into public.theme_events (theme_id, item_id, edited_by, field, old_value, new_value)
      values (p_theme, p_item, btrim(p_by), 'item_period', jsonb_build_object('start_date', it.start_date, 'due_date', it.due_date), jsonb_build_object('start_date', s, 'due_date', d));
  end if;
  return jsonb_build_object('id', p_item);
end $$;

-- 2. Urgência de bloqueios e decisões ------------------------------------------------------------------------------------------------------
alter table public.theme_blockers add column if not exists urgency text not null default 'info';
alter table public.theme_decisions add column if not exists urgency text not null default 'info';
do $$ begin
  if not exists (select 1 from pg_constraint where conname = 'theme_blockers_urgency_check') then
    alter table public.theme_blockers add constraint theme_blockers_urgency_check check (urgency in ('urgent', 'important', 'info'));
    update public.theme_blockers set urgency = 'important' where needs_leadership and urgency = 'info';     -- só na primeira vez (a restrição ainda não existia)
  end if;
  if not exists (select 1 from pg_constraint where conname = 'theme_decisions_urgency_check') then
    alter table public.theme_decisions add constraint theme_decisions_urgency_check check (urgency in ('urgent', 'important', 'info'));
    update public.theme_decisions set urgency = 'important' where needs_leadership and urgency = 'info';
  end if;
end $$;

create or replace function public.theme_urgency(p jsonb, lead boolean)
returns text language plpgsql immutable set search_path = public as $$
begin
  if p ? 'urgency' then
    if p ->> 'urgency' is null or p ->> 'urgency' not in ('urgent', 'important', 'info') then raise exception 'invalid urgency' using errcode = '22023'; end if;
    return p ->> 'urgency';
  end if;
  return case when lead then 'important' else 'info' end;
end $$;
revoke all on function public.theme_urgency(jsonb, boolean) from public, anon, authenticated;

create or replace function public.save_theme_blocker(p_theme text, p_id uuid, p jsonb, p_by text)
returns jsonb language plpgsql security definer set search_path = public, extensions as $$
declare b public.theme_blockers; new_id uuid; item uuid := nullif(p ->> 'item_id', '')::uuid; lead boolean;
begin
  perform public.theme_check_name(p_by);
  perform public.rfc_rate_limit(public.rfc_origin_hash(), 'theme', 120, 1000);
  perform 1 from public.themes where id = p_theme and not hidden;
  if not found then raise exception 'unknown theme' using errcode = '22023'; end if;
  if item is not null then
    perform 1 from public.theme_items where id = item and theme_id = p_theme;
    if not found then raise exception 'unknown item' using errcode = '22023'; end if;
  end if;
  if p ? 'what' then perform public.theme_check_i18n(p -> 'what', 1200, true); end if;
  if char_length(coalesce(p ->> 'owner', '')) > 80 then raise exception 'invalid owner' using errcode = '22023'; end if;
  if p_id is null then
    perform public.theme_check_i18n(coalesce(p -> 'what', '{}'::jsonb), 1200, true);
    lead := coalesce((p ->> 'needs_leadership')::boolean, false);
    insert into public.theme_blockers (theme_id, item_id, what, owner, due_date, needs_leadership, urgency, created_by)
      values (p_theme, item, p -> 'what', nullif(btrim(coalesce(p ->> 'owner', '')), ''), nullif(p ->> 'due_date', '')::date,
              lead, public.theme_urgency(p, lead), btrim(p_by)) returning id into new_id;
    insert into public.theme_events (theme_id, item_id, edited_by, field, new_value) values (p_theme, item, btrim(p_by), 'blocker_added', p -> 'what');
    return jsonb_build_object('id', new_id);
  end if;
  select * into b from public.theme_blockers where id = p_id and theme_id = p_theme for update;
  if not found then raise exception 'unknown blocker' using errcode = '22023'; end if;
  update public.theme_blockers set
    what             = case when p ? 'what' then p -> 'what' else what end,
    owner            = case when p ? 'owner' then nullif(btrim(coalesce(p ->> 'owner', '')), '') else owner end,
    due_date         = case when p ? 'due_date' then nullif(p ->> 'due_date', '')::date else due_date end,
    needs_leadership = case when p ? 'needs_leadership' then (p ->> 'needs_leadership')::boolean else needs_leadership end,
    urgency          = case when p ? 'urgency' then public.theme_urgency(p, false) else urgency end,
    text_meta        = public.theme_text_meta_after(to_jsonb(b), jsonb_build_object('what', coalesce(p -> 'what', b.what)), b.text_meta, array['what'])
  where id = p_id;
  return jsonb_build_object('id', p_id);
end $$;

create or replace function public.save_theme_decision(p_theme text, p_id uuid, p jsonb, p_by text)
returns jsonb language plpgsql security definer set search_path = public, extensions as $$
declare d public.theme_decisions; new_id uuid; item uuid := nullif(p ->> 'item_id', '')::uuid; lead boolean;
begin
  perform public.theme_check_name(p_by);
  perform public.rfc_rate_limit(public.rfc_origin_hash(), 'theme', 120, 1000);
  perform 1 from public.themes where id = p_theme and not hidden;
  if not found then raise exception 'unknown theme' using errcode = '22023'; end if;
  if item is not null then
    perform 1 from public.theme_items where id = item and theme_id = p_theme;
    if not found then raise exception 'unknown item' using errcode = '22023'; end if;
  end if;
  if p ? 'what' then perform public.theme_check_i18n(p -> 'what', 1200, true); end if;
  if char_length(coalesce(p ->> 'decider', '')) > 80 then raise exception 'invalid decider' using errcode = '22023'; end if;
  if p_id is null then
    perform public.theme_check_i18n(coalesce(p -> 'what', '{}'::jsonb), 1200, true);
    lead := coalesce((p ->> 'needs_leadership')::boolean, false);
    insert into public.theme_decisions (theme_id, item_id, what, decider, due_date, needs_leadership, urgency, created_by)
      values (p_theme, item, p -> 'what', nullif(btrim(coalesce(p ->> 'decider', '')), ''), nullif(p ->> 'due_date', '')::date,
              lead, public.theme_urgency(p, lead), btrim(p_by)) returning id into new_id;
    insert into public.theme_events (theme_id, item_id, edited_by, field, new_value) values (p_theme, item, btrim(p_by), 'decision_added', p -> 'what');
    return jsonb_build_object('id', new_id);
  end if;
  select * into d from public.theme_decisions where id = p_id and theme_id = p_theme for update;
  if not found then raise exception 'unknown decision' using errcode = '22023'; end if;
  update public.theme_decisions set
    what             = case when p ? 'what' then p -> 'what' else what end,
    decider          = case when p ? 'decider' then nullif(btrim(coalesce(p ->> 'decider', '')), '') else decider end,
    due_date         = case when p ? 'due_date' then nullif(p ->> 'due_date', '')::date else due_date end,
    needs_leadership = case when p ? 'needs_leadership' then (p ->> 'needs_leadership')::boolean else needs_leadership end,
    urgency          = case when p ? 'urgency' then public.theme_urgency(p, false) else urgency end,
    text_meta        = public.theme_text_meta_after(to_jsonb(d), jsonb_build_object('what', coalesce(p -> 'what', d.what)), d.text_meta, array['what'])
  where id = p_id;
  return jsonb_build_object('id', p_id);
end $$;
