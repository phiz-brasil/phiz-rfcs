-- Anexos que são a página arquivada de uma versão antiga de RFC (fase 8, segunda parte: o arquivo congelado entra no banco).
-- Idempotente (create or replace). add_attachment passa a aceitar archive_version ("1.6"), archive_date e archive_note ({pt, en, zh}) em arquivos:
-- a página da RFC lista essas versões antigas, e cada uma leva ao painel de anexos do tema.

create or replace function public.add_attachment(p_theme text, p jsonb, p_by text)
returns jsonb language plpgsql security definer set search_path = public, extensions as $$
declare k text := p ->> 'kind'; nm text := btrim(coalesce(p ->> 'name', '')); ds text := coalesce(p ->> 'description', '');
  item uuid := nullif(p ->> 'item_id', '')::uuid; st integer := nullif(p ->> 'stage', '')::integer; rep uuid := nullif(p ->> 'replaces', '')::uuid;
  path text := p ->> 'path'; obj record; new_id uuid; av text := nullif(p ->> 'archive_version', ''); ad date := nullif(p ->> 'archive_date', '')::date;
  an jsonb := p -> 'archive_note'; chk text := nullif(p ->> 'checksum', '');
begin
  perform public.theme_check_name(p_by);
  perform public.rfc_rate_limit(public.rfc_origin_hash(), 'theme', 120, 1000);
  perform 1 from public.themes where id = p_theme and not hidden;
  if not found then raise exception 'unknown theme' using errcode = '22023'; end if;
  if k not in ('file', 'note', 'link') then raise exception 'invalid kind' using errcode = '22023'; end if;
  if char_length(nm) not between 1 and 200 then raise exception 'invalid name' using errcode = '22023'; end if;
  if char_length(ds) > 1000 then raise exception 'invalid description' using errcode = '22023'; end if;
  if st is not null and st not between 1 and 10 then raise exception 'invalid stage' using errcode = '22023'; end if;
  if item is not null then
    perform 1 from public.theme_items where id = item and theme_id = p_theme;
    if not found then raise exception 'unknown item' using errcode = '22023'; end if;
  end if;
  if rep is not null then
    perform 1 from public.attachments where id = rep and theme_id = p_theme and not hidden;
    if not found then raise exception 'unknown attachment' using errcode = '22023'; end if;
  end if;
  if chk is not null and chk !~ '^[0-9a-f]{64}$' then raise exception 'invalid checksum' using errcode = '22023'; end if;
  if av is not null and (k <> 'file' or av !~ '^[0-9]{1,3}\.[0-9]{1,3}$') then raise exception 'invalid archive version' using errcode = '22023'; end if;
  if an is not null then perform public.theme_check_i18n(an, 1200, false); end if;
  if k = 'file' then
    if path is null or path !~ ('^' || p_theme || '/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/[^/]{1,150}$') then
      raise exception 'invalid path' using errcode = '22023';
    end if;
    select o.name, (o.metadata ->> 'size')::bigint as size, o.metadata ->> 'mimetype' as mime into obj
      from storage.objects o where o.bucket_id = 'attachments' and o.name = path;
    if not found then raise exception 'file not uploaded' using errcode = '22023'; end if;
    insert into public.attachments (theme_id, item_id, kind, name, description, storage_path, content_type, size, checksum, stage, replaces, created_by, archive_version, archive_date, archive_note)
      values (p_theme, item, k, nm, ds, path, obj.mime, obj.size, chk, st, rep, btrim(p_by), av, ad, case when av is not null then an end) returning id into new_id;
  elsif k = 'note' then
    if char_length(coalesce(p ->> 'body', '')) not between 1 and 50000 then raise exception 'invalid note' using errcode = '22023'; end if;
    insert into public.attachments (theme_id, item_id, kind, name, description, body, stage, replaces, created_by)
      values (p_theme, item, k, nm, ds, p ->> 'body', st, rep, btrim(p_by)) returning id into new_id;
  else
    if coalesce(p ->> 'url', '') !~ '^https://[^ ]{4,500}$' then raise exception 'invalid url' using errcode = '22023'; end if;
    insert into public.attachments (theme_id, item_id, kind, name, description, url, stage, replaces, created_by)
      values (p_theme, item, k, nm, ds, p ->> 'url', st, rep, btrim(p_by)) returning id into new_id;
  end if;
  insert into public.theme_events (theme_id, item_id, edited_by, field, new_value) values (p_theme, item, btrim(p_by), 'attachment_added', to_jsonb(nm));
  return jsonb_build_object('id', new_id);
end $$;

revoke all on function public.add_attachment(text, jsonb, text) from public;
grant execute on function public.add_attachment(text, jsonb, text) to anon, authenticated;
