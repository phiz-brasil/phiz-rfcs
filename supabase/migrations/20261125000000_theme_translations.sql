-- Tradução automática dos textos dos temas (fase 3, segunda parte).
-- Idempotente: seguro rodar de novo no SQL Editor.
--
-- text_meta guarda, por campo de texto, os idiomas que são tradução automática: {"progress": ["en", "zh"]}. Quem escreve é a Edge Function
-- translate-comment (webhook na tabela themes); update_theme tira um idioma dessa lista quando uma pessoa mexe nele, então um texto escrito ou
-- corrigido por uma pessoa nunca é sobrescrito por tradução, e o que ela escreve vira a origem das traduções dos idiomas que ainda são
-- automáticos ou estão vazios.

alter table public.themes add column if not exists text_meta jsonb not null default '{}'::jsonb;

create or replace function public.update_theme(p_id text, p jsonb, p_by text)
returns void language plpgsql security definer set search_path = public, extensions as $$
declare old_row jsonb; new_row jsonb; t public.themes; f text; lg text; meta jsonb;
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
  -- um texto que uma pessoa mexeu deixa de ser tradução automática (e será a origem das traduções dos outros idiomas)
  meta := coalesce(t.text_meta, '{}'::jsonb);
  foreach f in array array['title', 'what_it_is', 'progress', 'problem', 'solution', 'success'] loop
    if p ? f then
      foreach lg in array array['pt', 'en', 'zh'] loop
        if (old_row -> f -> lg) is distinct from (new_row -> f -> lg) then
          meta := jsonb_set(meta, array[f], coalesce(meta -> f, '[]'::jsonb) - lg, true);
        end if;
      end loop;
    end if;
  end loop;
  if meta is distinct from coalesce(t.text_meta, '{}'::jsonb) then update public.themes set text_meta = meta where id = p_id; end if;
  foreach f in array fields loop
    if old_row -> f is distinct from new_row -> f then
      insert into public.theme_events (theme_id, edited_by, field, old_value, new_value) values (p_id, btrim(p_by), f, old_row -> f, new_row -> f);
    end if;
  end loop;
end $$;

revoke all on function public.update_theme(text, jsonb, text) from public;
grant execute on function public.update_theme(text, jsonb, text) to anon, authenticated;
