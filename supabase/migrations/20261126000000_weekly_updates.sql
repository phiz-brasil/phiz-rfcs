-- Atualização semanal, bloqueios e decisões dos temas (fase 4 do plano em docs/spec/v2).
-- Idempotente: 'if not exists' / 'or replace'; seguro rodar de novo no SQL Editor.
--
-- Uma atualização semanal é um registro que nunca é sobrescrito: o tema mostra a última e o histórico guarda as outras. Postar uma atualização
-- também atualiza o tema (a frase de andamento, o status e a data estimada), com os eventos de sempre em theme_events.
-- Bloqueios e decisões são registros próprios, ligados ao tema e, quando for o caso, a um item; os marcados "exige a liderança" aparecem em
-- destaque na visão executiva. Os textos têm {pt, en, zh} e text_meta, como os do tema: a tradução automática (webhook + translate-comment)
-- vale para as três tabelas novas; texto de pessoa nunca é sobrescrito.
-- Quem acessa: a chave pública LÊ e escreve só pelas funções abaixo (limite por origem, nome obrigatório). Sem login por enquanto.

create table if not exists public.theme_updates (
  id          uuid primary key default gen_random_uuid(),
  theme_id    text not null references public.themes (id),
  week        text not null check (week ~ '^[0-9]{4}-W[0-9]{2}$'),     -- semana ISO em que foi postada
  edited_by   text not null,
  created_at  timestamptz not null default now(),
  progress    jsonb not null default '{}'::jsonb,                      -- a frase de andamento
  advanced    jsonb not null default '{}'::jsonb,                      -- o que avançou
  next_step   jsonb not null default '{}'::jsonb,
  status_from text,
  status_to   text,                                                    -- só quando o status mudou
  due_from    date,
  due_to      date,                                                    -- só quando a data estimada mudou
  due_reason  text check (due_reason is null or char_length(due_reason) <= 300),
  text_meta   jsonb not null default '{}'::jsonb
);
create index if not exists theme_updates_theme_idx on public.theme_updates (theme_id, created_at desc);

create table if not exists public.theme_blockers (
  id               uuid primary key default gen_random_uuid(),
  theme_id         text not null references public.themes (id),
  item_id          uuid references public.theme_items (id),
  what             jsonb not null,
  owner            text check (owner is null or char_length(owner) <= 80),
  due_date         date,
  needs_leadership boolean not null default false,
  state            text not null default 'open' check (state in ('open', 'resolved')),
  how_resolved     jsonb not null default '{}'::jsonb,
  resolved_at      timestamptz,
  resolved_by      text,
  created_at       timestamptz not null default now(),
  created_by       text not null,
  text_meta        jsonb not null default '{}'::jsonb
);
create index if not exists theme_blockers_theme_idx on public.theme_blockers (theme_id, state);

create table if not exists public.theme_decisions (
  id               uuid primary key default gen_random_uuid(),
  theme_id         text not null references public.themes (id),
  item_id          uuid references public.theme_items (id),
  what             jsonb not null,                                     -- o que precisa ser decidido
  decider          text check (decider is null or char_length(decider) <= 80),
  due_date         date,
  needs_leadership boolean not null default false,
  state            text not null default 'open' check (state in ('open', 'decided', 'dropped')),
  decision         jsonb not null default '{}'::jsonb,
  decided_at       timestamptz,
  decided_by       text,
  created_at       timestamptz not null default now(),
  created_by       text not null,
  text_meta        jsonb not null default '{}'::jsonb
);
create index if not exists theme_decisions_theme_idx on public.theme_decisions (theme_id, state);

alter table public.theme_updates enable row level security;
alter table public.theme_blockers enable row level security;
alter table public.theme_decisions enable row level security;
revoke all on public.theme_updates, public.theme_blockers, public.theme_decisions from anon, authenticated;
grant select on public.theme_updates, public.theme_blockers, public.theme_decisions to anon, authenticated;
drop policy if exists "read theme updates" on public.theme_updates;
create policy "read theme updates" on public.theme_updates for select to anon, authenticated
  using (exists (select 1 from public.themes t where t.id = theme_updates.theme_id and not t.hidden));
drop policy if exists "read theme blockers" on public.theme_blockers;
create policy "read theme blockers" on public.theme_blockers for select to anon, authenticated
  using (exists (select 1 from public.themes t where t.id = theme_blockers.theme_id and not t.hidden));
drop policy if exists "read theme decisions" on public.theme_decisions;
create policy "read theme decisions" on public.theme_decisions for select to anon, authenticated
  using (exists (select 1 from public.themes t where t.id = theme_decisions.theme_id and not t.hidden));

-- Um idioma que uma pessoa mexeu deixa de ser tradução automática: tira-o das listas de text_meta dos campos de texto que mudaram
create or replace function public.theme_text_meta_after(p_old jsonb, p_new jsonb, p_meta jsonb, p_fields text[])
returns jsonb language plpgsql immutable set search_path = public as $$
declare f text; lg text; meta jsonb := coalesce(p_meta, '{}'::jsonb);
begin
  foreach f in array p_fields loop
    foreach lg in array array['pt', 'en', 'zh'] loop
      if (p_old -> f -> lg) is distinct from (p_new -> f -> lg) then
        meta := jsonb_set(meta, array[f], coalesce(meta -> f, '[]'::jsonb) - lg, true);
      end if;
    end loop;
  end loop;
  return meta;
end $$;

-- Posta a atualização semanal de um tema; atualiza a frase de andamento, o status e a data estimada do tema
create or replace function public.post_theme_update(p_theme text, p jsonb, p_by text)
returns jsonb language plpgsql security definer set search_path = public, extensions as $$
declare t public.themes; new_id uuid; st text := p ->> 'status'; due date; due_set boolean := p ? 'due_date';
  wk text := to_char(now() at time zone 'utc', 'IYYY"-W"IW');
begin
  perform public.theme_check_name(p_by);
  perform public.rfc_rate_limit(public.rfc_origin_hash(), 'theme', 120, 1000);
  select * into t from public.themes where id = p_theme and not hidden for update;
  if not found then raise exception 'unknown theme' using errcode = '22023'; end if;
  perform public.theme_check_i18n(coalesce(p -> 'progress', '{}'::jsonb), 1200, true);
  perform public.theme_check_i18n(coalesce(p -> 'advanced', '{}'::jsonb), 2000, false);
  perform public.theme_check_i18n(coalesce(p -> 'next_step', '{}'::jsonb), 2000, false);
  if st is not null and st not in ('not_started', 'on_track', 'at_risk', 'blocked', 'paused', 'done', 'cancelled') then
    raise exception 'invalid status' using errcode = '22023';
  end if;
  if char_length(coalesce(p ->> 'due_reason', '')) > 300 then raise exception 'invalid reason' using errcode = '22023'; end if;
  if due_set then due := nullif(p ->> 'due_date', '')::date; end if;
  insert into public.theme_updates (theme_id, week, edited_by, progress, advanced, next_step, status_from, status_to, due_from, due_to, due_reason)
    values (p_theme, wk, btrim(p_by), p -> 'progress', coalesce(p -> 'advanced', '{}'::jsonb), coalesce(p -> 'next_step', '{}'::jsonb),
            case when st is not null and st <> t.status then t.status end, case when st is not null and st <> t.status then st end,
            case when due_set and due is distinct from t.due_date then t.due_date end, case when due_set and due is distinct from t.due_date then due end,
            nullif(btrim(coalesce(p ->> 'due_reason', '')), ''))
    returning id into new_id;
  update public.themes set
    progress   = p -> 'progress',
    text_meta  = coalesce(t.text_meta, '{}'::jsonb) - 'progress',                   -- a frase nova é de pessoa; as traduções antigas saem com ela
    status     = coalesce(st, status),
    due_date   = case when due_set then due else due_date end,
    updated_at = now()
  where id = p_theme;
  insert into public.theme_events (theme_id, edited_by, field, old_value, new_value) values (p_theme, btrim(p_by), 'update_posted', null, to_jsonb(wk));
  if st is not null and st <> t.status then
    insert into public.theme_events (theme_id, edited_by, field, old_value, new_value) values (p_theme, btrim(p_by), 'status', to_jsonb(t.status), to_jsonb(st));
  end if;
  if due_set and due is distinct from t.due_date then
    insert into public.theme_events (theme_id, edited_by, field, old_value, new_value) values (p_theme, btrim(p_by), 'due_date', to_jsonb(t.due_date), to_jsonb(due));
  end if;
  return jsonb_build_object('id', new_id, 'week', wk);
end $$;

-- Bloqueios: cria (p_id nulo) ou altera
create or replace function public.save_theme_blocker(p_theme text, p_id uuid, p jsonb, p_by text)
returns jsonb language plpgsql security definer set search_path = public, extensions as $$
declare b public.theme_blockers; new_id uuid; item uuid := nullif(p ->> 'item_id', '')::uuid;
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
    insert into public.theme_blockers (theme_id, item_id, what, owner, due_date, needs_leadership, created_by)
      values (p_theme, item, p -> 'what', nullif(btrim(coalesce(p ->> 'owner', '')), ''), nullif(p ->> 'due_date', '')::date,
              coalesce((p ->> 'needs_leadership')::boolean, false), btrim(p_by)) returning id into new_id;
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
    text_meta        = public.theme_text_meta_after(to_jsonb(b), jsonb_build_object('what', coalesce(p -> 'what', b.what)), b.text_meta, array['what'])
  where id = p_id;
  return jsonb_build_object('id', p_id);
end $$;

create or replace function public.resolve_theme_blocker(p_id uuid, p_how jsonb, p_by text)
returns void language plpgsql security definer set search_path = public, extensions as $$
declare b public.theme_blockers;
begin
  perform public.theme_check_name(p_by);
  perform public.rfc_rate_limit(public.rfc_origin_hash(), 'theme', 120, 1000);
  select * into b from public.theme_blockers where id = p_id for update;
  if not found or b.state <> 'open' then raise exception 'unknown blocker' using errcode = '22023'; end if;
  perform public.theme_check_i18n(coalesce(p_how, '{}'::jsonb), 1200, false);
  update public.theme_blockers set state = 'resolved', how_resolved = coalesce(p_how, '{}'::jsonb), resolved_at = now(), resolved_by = btrim(p_by) where id = p_id;
  insert into public.theme_events (theme_id, item_id, edited_by, field, old_value) values (b.theme_id, b.item_id, btrim(p_by), 'blocker_resolved', b.what);
end $$;

-- Decisões: cria (p_id nulo) ou altera
create or replace function public.save_theme_decision(p_theme text, p_id uuid, p jsonb, p_by text)
returns jsonb language plpgsql security definer set search_path = public, extensions as $$
declare d public.theme_decisions; new_id uuid; item uuid := nullif(p ->> 'item_id', '')::uuid;
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
    insert into public.theme_decisions (theme_id, item_id, what, decider, due_date, needs_leadership, created_by)
      values (p_theme, item, p -> 'what', nullif(btrim(coalesce(p ->> 'decider', '')), ''), nullif(p ->> 'due_date', '')::date,
              coalesce((p ->> 'needs_leadership')::boolean, false), btrim(p_by)) returning id into new_id;
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
    text_meta        = public.theme_text_meta_after(to_jsonb(d), jsonb_build_object('what', coalesce(p -> 'what', d.what)), d.text_meta, array['what'])
  where id = p_id;
  return jsonb_build_object('id', p_id);
end $$;

-- Fecha uma decisão: decidida (com o texto da decisão) ou descartada
create or replace function public.decide_theme_decision(p_id uuid, p_state text, p_decision jsonb, p_by text)
returns void language plpgsql security definer set search_path = public, extensions as $$
declare d public.theme_decisions;
begin
  perform public.theme_check_name(p_by);
  perform public.rfc_rate_limit(public.rfc_origin_hash(), 'theme', 120, 1000);
  if p_state not in ('decided', 'dropped') then raise exception 'invalid state' using errcode = '22023'; end if;
  select * into d from public.theme_decisions where id = p_id for update;
  if not found or d.state <> 'open' then raise exception 'unknown decision' using errcode = '22023'; end if;
  perform public.theme_check_i18n(coalesce(p_decision, '{}'::jsonb), 1200, p_state = 'decided');
  update public.theme_decisions set state = p_state, decision = coalesce(p_decision, '{}'::jsonb), decided_at = now(), decided_by = btrim(p_by) where id = p_id;
  insert into public.theme_events (theme_id, item_id, edited_by, field, old_value, new_value) values (d.theme_id, d.item_id, btrim(p_by), 'decision_' || p_state, d.what, p_decision);
end $$;

revoke all on function public.theme_text_meta_after(jsonb, jsonb, jsonb, text[]) from public, anon, authenticated;
revoke all on function public.post_theme_update(text, jsonb, text), public.save_theme_blocker(text, uuid, jsonb, text),
  public.resolve_theme_blocker(uuid, jsonb, text), public.save_theme_decision(text, uuid, jsonb, text),
  public.decide_theme_decision(uuid, text, jsonb, text) from public;
grant execute on function public.post_theme_update(text, jsonb, text), public.save_theme_blocker(text, uuid, jsonb, text),
  public.resolve_theme_blocker(uuid, jsonb, text), public.save_theme_decision(text, uuid, jsonb, text),
  public.decide_theme_decision(uuid, text, jsonb, text) to anon, authenticated;
