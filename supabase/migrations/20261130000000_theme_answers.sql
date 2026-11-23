-- Estados das três respostas dos slides (fase 9): faltando, sugerida pela IA (ainda não confirmada) ou confirmada por uma pessoa, com as fontes.
-- Idempotente. themes.answers: {"problem": {"state": "suggested|confirmed|missing", "sources": [{"label", "quote"}], "missing": "…", "by": "…", "at": "…"}, …}.
-- Uma sugestão NUNCA sobrescreve uma resposta confirmada nem um texto que uma pessoa escreveu antes de existir este quadro.

alter table public.themes add column if not exists answers jsonb not null default '{}'::jsonb;

-- Guardar o que a IA sugeriu (a Edge Function suggest-summary só devolve; quem grava é esta função, chamada pela página) ----------------
create or replace function public.suggest_theme_answers(p_theme text, p jsonb, p_by text)
returns jsonb language plpgsql security definer set search_path = public, extensions as $$
declare t public.themes; f text; s jsonb; cur jsonb; txt text; ans jsonb; applied text[] := '{}'; has_text boolean; srcs jsonb;
begin
  perform public.theme_check_name(p_by);
  perform public.rfc_rate_limit(public.rfc_origin_hash(), 'theme', 120, 1000);
  select * into t from public.themes where id = p_theme and not hidden for update;
  if not found or t.kind is null then raise exception 'unknown theme' using errcode = '22023'; end if;
  ans := coalesce(t.answers, '{}'::jsonb);
  foreach f in array array['problem', 'solution', 'success'] loop
    continue when not (p ? f);
    s := p -> f;
    if jsonb_typeof(s) is distinct from 'object' then raise exception 'invalid answer' using errcode = '22023'; end if;
    cur := ans -> f;
    select exists (select 1 from jsonb_each_text(coalesce(to_jsonb(t) -> f, '{}'::jsonb)) x where btrim(x.value) <> '') into has_text;
    continue when (cur ->> 'state') = 'confirmed' or (has_text and cur is null);          -- a person's text is never replaced
    txt := nullif(btrim(coalesce(s ->> 'text', '')), '');
    srcs := coalesce(s -> 'sources', '[]'::jsonb);
    if jsonb_typeof(srcs) is distinct from 'array' or jsonb_array_length(srcs) > 6
       or exists (select 1 from jsonb_array_elements(srcs) e where jsonb_typeof(e) is distinct from 'object' or char_length(coalesce(e ->> 'label', '')) not between 1 and 200
                  or char_length(coalesce(e ->> 'quote', '')) not between 1 and 400) then
      raise exception 'invalid sources' using errcode = '22023';
    end if;
    if char_length(coalesce(s ->> 'missing', '')) > 300 then raise exception 'invalid missing' using errcode = '22023'; end if;
    if txt is not null then
      if char_length(txt) > 1200 or jsonb_array_length(srcs) = 0 then raise exception 'invalid answer' using errcode = '22023'; end if;
      update public.themes set
        problem  = case when f = 'problem' then jsonb_build_object('pt', txt) else problem end,
        solution = case when f = 'solution' then jsonb_build_object('pt', txt) else solution end,
        success  = case when f = 'success' then jsonb_build_object('pt', txt) else success end,
        text_meta = coalesce(text_meta, '{}'::jsonb) - f,
        updated_at = now()
        where id = p_theme;
      ans := jsonb_set(ans, array[f], jsonb_build_object('state', 'suggested', 'by', btrim(p_by), 'at', now(), 'sources', srcs), true);
    else
      update public.themes set
        problem  = case when f = 'problem' then '{}'::jsonb else problem end,
        solution = case when f = 'solution' then '{}'::jsonb else solution end,
        success  = case when f = 'success' then '{}'::jsonb else success end,
        text_meta = coalesce(text_meta, '{}'::jsonb) - f,
        updated_at = now()
        where id = p_theme;
      ans := jsonb_set(ans, array[f], jsonb_build_object('state', 'missing', 'by', btrim(p_by), 'at', now(), 'missing', coalesce(s ->> 'missing', '')), true);
    end if;
    applied := applied || f;
  end loop;
  update public.themes set answers = ans where id = p_theme;
  if array_length(applied, 1) > 0 then
    insert into public.theme_events (theme_id, edited_by, field, new_value) values (p_theme, btrim(p_by), 'answers_suggested', to_jsonb(applied));
  end if;
  return jsonb_build_object('applied', to_jsonb(applied));
end $$;

-- Confirmar respostas (a pessoa leu, e editou se quis) ---------------------------------------------------------------------------------
create or replace function public.confirm_theme_answers(p_theme text, p_fields text[], p_by text)
returns void language plpgsql security definer set search_path = public, extensions as $$
declare t public.themes; f text; ans jsonb; has_text boolean;
begin
  perform public.theme_check_name(p_by);
  perform public.rfc_rate_limit(public.rfc_origin_hash(), 'theme', 120, 1000);
  select * into t from public.themes where id = p_theme and not hidden for update;
  if not found then raise exception 'unknown theme' using errcode = '22023'; end if;
  ans := coalesce(t.answers, '{}'::jsonb);
  foreach f in array p_fields loop
    if f not in ('problem', 'solution', 'success') then raise exception 'invalid field' using errcode = '22023'; end if;
    select exists (select 1 from jsonb_each_text(coalesce(to_jsonb(t) -> f, '{}'::jsonb)) x where btrim(x.value) <> '') into has_text;
    if not has_text then raise exception 'nothing to confirm' using errcode = '22023'; end if;
    ans := jsonb_set(ans, array[f], jsonb_build_object('state', 'confirmed', 'by', btrim(p_by), 'at', now(), 'sources', coalesce(ans -> f -> 'sources', '[]'::jsonb)), true);
    insert into public.theme_events (theme_id, edited_by, field, new_value) values (p_theme, btrim(p_by), 'answer_confirmed', to_jsonb(f));
  end loop;
  update public.themes set answers = ans where id = p_theme;
end $$;

-- update_theme: o texto de uma resposta escrito por pessoa vira "confirmado" (o resto da função é o de 20261125000000_theme_translations) ---------------
create or replace function public.update_theme(p_id text, p jsonb, p_by text)
returns void language plpgsql security definer set search_path = public, extensions as $$
declare old_row jsonb; new_row jsonb; t public.themes; f text; lg text; meta jsonb; ans jsonb;
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
  -- uma resposta dos slides que uma pessoa escreveu ou corrigiu está confirmada (as fontes da sugestão ficam); vazia, sai do quadro de estados
  ans := coalesce(t.answers, '{}'::jsonb);
  foreach f in array array['problem', 'solution', 'success'] loop
    if p ? f and (old_row -> f) is distinct from (new_row -> f) then
      if exists (select 1 from jsonb_each_text(coalesce(new_row -> f, '{}'::jsonb)) x where btrim(x.value) <> '') then
        ans := jsonb_set(ans, array[f], jsonb_build_object('state', 'confirmed', 'by', btrim(p_by), 'at', now(), 'sources', coalesce(ans -> f -> 'sources', '[]'::jsonb)), true);
      else
        ans := ans - f;
      end if;
    end if;
  end loop;
  if ans is distinct from coalesce(t.answers, '{}'::jsonb) then update public.themes set answers = ans where id = p_id; end if;
  foreach f in array fields loop
    if old_row -> f is distinct from new_row -> f then
      insert into public.theme_events (theme_id, edited_by, field, old_value, new_value) values (p_id, btrim(p_by), f, old_row -> f, new_row -> f);
    end if;
  end loop;
end $$;

revoke all on function public.suggest_theme_answers(text, jsonb, text), public.confirm_theme_answers(text, text[], text), public.update_theme(text, jsonb, text) from public;
grant execute on function public.suggest_theme_answers(text, jsonb, text), public.confirm_theme_answers(text, text[], text), public.update_theme(text, jsonb, text) to anon, authenticated;
