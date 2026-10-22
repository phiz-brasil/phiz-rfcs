-- Até 160 imagens por RFC (telas de uma RFC grande) e um limite de envio por origem maior, para caber essas imagens.
-- Idempotente ('or replace'): seguro rodar de novo no SQL Editor (ou com `supabase db push`).
--
-- A importação das RFCs do repositório (tools/import_rfcs.py) não passa por aqui: usa a chave service_role e insere
-- direto em rfc_revisions / rfc_assets. Este arquivo vale para quem envia imagens pela página Nova RFC.

-- Recebe uma imagem na área temporária ------------------------------------------------------------------------------
create or replace function public.stage_rfc_asset(p_token uuid, p_name text, p_mime text, p_data text, p_by text)
returns void language plpgsql security definer set search_path = public, extensions as $$
declare h text := public.rfc_origin_hash(); raw bytea; n integer;
begin
  if p_token is null then raise exception 'invalid token' using errcode = '22023'; end if;
  if p_name is null or p_name !~ '^[a-z0-9][a-z0-9._-]{0,59}$' then raise exception 'invalid image name' using errcode = '22023'; end if;
  if p_mime is null or p_mime not in ('image/png', 'image/jpeg', 'image/webp') then raise exception 'invalid image type' using errcode = '22023'; end if;
  if p_by is null or char_length(btrim(p_by)) not between 1 and 60 then raise exception 'invalid name' using errcode = '22023'; end if;
  if p_data is null or char_length(p_data) not between 1 and 1400000 then raise exception 'invalid image size' using errcode = '22023'; end if;
  begin
    raw := decode(p_data, 'base64');
  exception when others then
    raise exception 'invalid image data' using errcode = '22023';
  end;
  if octet_length(raw) not between 1 and 1048576 then raise exception 'invalid image size' using errcode = '22023'; end if;
  -- o arquivo tem que começar como o tipo declarado (PNG, JPEG ou WebP de verdade)
  if not (
       (p_mime = 'image/png'  and substring(raw from 1 for 8) = '\x89504e470d0a1a0a'::bytea)
    or (p_mime = 'image/jpeg' and substring(raw from 1 for 3) = '\xffd8ff'::bytea)
    or (p_mime = 'image/webp' and substring(raw from 1 for 4) = '\x52494646'::bytea and substring(raw from 9 for 4) = '\x57454250'::bytea)
  ) then
    raise exception 'file is not a valid %', p_mime using errcode = '22023';
  end if;
  perform public.rfc_rate_limit(h, 'asset', 200, 1000);           -- por origem: 200 por hora e 1000 por dia
  delete from public.rfc_asset_staging where created_at < now() - interval '1 day';
  select count(*) into n from public.rfc_asset_staging where token = p_token and name <> p_name;
  if n >= 160 then raise exception 'too many images' using errcode = '22023'; end if;
  insert into public.rfc_asset_staging (token, name, mime, size, data, uploaded_by, ip_hash)
    values (p_token, p_name, p_mime, octet_length(raw), p_data, btrim(p_by), h)
    on conflict (token, name) do update
      set mime = excluded.mime, size = excluded.size, data = excluded.data, uploaded_by = excluded.uploaded_by, created_at = now();
end $$;
