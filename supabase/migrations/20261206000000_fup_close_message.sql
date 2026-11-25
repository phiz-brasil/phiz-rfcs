-- FUP: a frase fixa do fechamento vai escrita nos três idiomas (docs/spec/v2/fup.md). A tradução automática tinha feito "Tratado no FUP" virar
-- "Treaty on the FUP". Só recria close_fup; a migração 20261205000000 já foi aplicada e não se edita. Idempotente.

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
      'progress', jsonb_build_object('pt', 'Tratado no FUP de ' || day || '.', 'en', 'Discussed in the FUP of ' || day || '.', 'zh', '已在 ' || day || ' 的 FUP 会议上讨论。'),
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

revoke all on function public.close_fup(uuid, text) from public, anon;
grant execute on function public.close_fup(uuid, text) to authenticated;
