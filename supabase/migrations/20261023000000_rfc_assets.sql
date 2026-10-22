-- Imagens e diagramas anexados às RFCs criadas pelo site.
-- Idempotente: tem 'if not exists' / 'or replace', então é seguro rodar de novo no SQL Editor (ou com `supabase db push`).
--
-- A pessoa anexa PNG, JPEG ou WebP (a página reduz cada um para até 1 MB) e os cita no arquivo da RFC como ![descrição](asset:nome.png).
-- No envio, cada imagem vai primeiro para uma área temporária (stage_rfc_asset) e só é efetivada junto com a RFC ou com a nova versão:
-- se alguma imagem citada faltar, nada é criado. Uma versão nova herda as imagens das anteriores; a versão antiga continua mostrando
-- a imagem que tinha (a página pede "a imagem mais recente com rev <= a da versão").
-- Quem acessa: a chave pública só LÊ as imagens e chama stage_rfc_asset, create_rfc e add_rfc_revision.

-- Área temporária: nada aqui é público; linhas com mais de um dia são apagadas quando alguém envia outra imagem ----
create table if not exists public.rfc_asset_staging (
  token       uuid not null,
  name        text not null check (name ~ '^[a-z0-9][a-z0-9._-]{0,59}$'),
  mime        text not null check (mime in ('image/png', 'image/jpeg', 'image/webp')),
  size        integer not null check (size between 1 and 1048576),
  data        text not null check (char_length(data) between 1 and 1400000),     -- base64
  uploaded_by text not null check (char_length(btrim(uploaded_by)) between 1 and 60),
  ip_hash     text,
  created_at  timestamptz not null default now(),
  primary key (token, name)
);

-- Imagens das RFCs --------------------------------------------------------------------------------------------------
create table if not exists public.rfc_assets (
  id          uuid primary key default gen_random_uuid(),
  rfc_id      text not null references public.rfc_ids (rfc_id),
  name        text not null check (name ~ '^[a-z0-9][a-z0-9._-]{0,59}$'),
  rev         integer not null check (rev >= 1),
  mime        text not null check (mime in ('image/png', 'image/jpeg', 'image/webp')),
  size        integer not null check (size between 1 and 1048576),
  data        text not null check (char_length(data) between 1 and 1400000),     -- base64
  uploaded_by text not null,
  created_at  timestamptz not null default now(),
  unique (rfc_id, name, rev)
);
create index if not exists rfc_assets_lookup_idx on public.rfc_assets (rfc_id, name, rev desc);

alter table public.rfc_asset_staging enable row level security;
alter table public.rfc_assets enable row level security;
revoke all on public.rfc_asset_staging, public.rfc_assets from anon, authenticated;
grant select (rfc_id, name, rev, mime, size, data, uploaded_by, created_at) on public.rfc_assets to anon, authenticated;

drop policy if exists "read visible assets" on public.rfc_assets;
create policy "read visible assets" on public.rfc_assets for select to anon, authenticated
  using (exists (select 1 from public.rfc_ids i where i.rfc_id = rfc_assets.rfc_id and not i.hidden));

-- Nomes de imagem citados no arquivo da RFC (só a sintaxe de imagem do Markdown) ------------------------------------
create or replace function public.rfc_asset_names(p_bundle text)
returns text[] language sql immutable set search_path = public as $$
  select coalesce(array_agg(distinct t.x[1]), '{}'::text[])
    from regexp_matches(p_bundle, '!\[[^\]]*\]\(asset:([a-z0-9][a-z0-9._-]{0,59})', 'g') as t(x)
$$;

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
  perform public.rfc_rate_limit(h, 'asset', 60, 300);             -- por origem: 60 por hora e 300 por dia
  delete from public.rfc_asset_staging where created_at < now() - interval '1 day';
  select count(*) into n from public.rfc_asset_staging where token = p_token and name <> p_name;
  if n >= 20 then raise exception 'too many images' using errcode = '22023'; end if;
  insert into public.rfc_asset_staging (token, name, mime, size, data, uploaded_by, ip_hash)
    values (p_token, p_name, p_mime, octet_length(raw), p_data, btrim(p_by), h)
    on conflict (token, name) do update
      set mime = excluded.mime, size = excluded.size, data = excluded.data, uploaded_by = excluded.uploaded_by, created_at = now();
end $$;

-- Efetiva as imagens junto com a revisão: toda imagem citada tem que estar na área temporária ou numa revisão anterior -----
create or replace function public.rfc_asset_finalize(p_rfc_id text, p_rev integer, p_bundle text, p_token uuid)
returns void language plpgsql security definer set search_path = public as $$
declare nm text;
begin
  foreach nm in array public.rfc_asset_names(p_bundle) loop
    if p_token is not null and exists (select 1 from public.rfc_asset_staging where token = p_token and name = nm) then
      insert into public.rfc_assets (rfc_id, name, rev, mime, size, data, uploaded_by)
        select p_rfc_id, s.name, p_rev, s.mime, s.size, s.data, s.uploaded_by
          from public.rfc_asset_staging s where s.token = p_token and s.name = nm;
    elsif not exists (select 1 from public.rfc_assets a where a.rfc_id = p_rfc_id and a.name = nm and a.rev < p_rev) then
      raise exception 'missing image %', nm using errcode = '22023';
    end if;
  end loop;
  if p_token is not null then delete from public.rfc_asset_staging where token = p_token; end if;
end $$;

-- create_rfc e add_rfc_revision ganham o token das imagens (as versões antigas das funções saem) ---------------------
drop function if exists public.create_rfc(jsonb, text, jsonb, jsonb, text);
drop function if exists public.add_rfc_revision(text, jsonb, text, jsonb, jsonb, text, text);

create or replace function public.create_rfc(p_meta jsonb, p_bundle text, p_authors jsonb, p_collaborators jsonb, p_by text, p_token uuid default null)
returns jsonb language plpgsql security definer set search_path = public, extensions as $$
declare h text := public.rfc_origin_hash(); new_id text;
begin
  perform public.rfc_check_input(p_meta, p_bundle, p_authors, coalesce(p_collaborators, '[]'::jsonb), p_by);
  perform public.rfc_rate_limit(h, 'create', 5, 20);     -- por origem: 5 por hora e 20 por dia
  new_id := public.rfc_allocate_id('site', p_by);
  insert into public.rfc_revisions (rfc_id, rev, version, meta, bundle, authors, collaborators, edited_by, ip_hash)
    values (new_id, 1, '1.0', p_meta, p_bundle, p_authors, coalesce(p_collaborators, '[]'::jsonb), btrim(p_by), h);
  perform public.rfc_asset_finalize(new_id, 1, p_bundle, p_token);
  return jsonb_build_object('rfc_id', new_id, 'version', '1.0');
end $$;

create or replace function public.add_rfc_revision(p_rfc_id text, p_meta jsonb, p_bundle text, p_authors jsonb, p_collaborators jsonb, p_by text, p_note text, p_token uuid default null)
returns jsonb language plpgsql security definer set search_path = public, extensions as $$
declare h text := public.rfc_origin_hash(); n integer; v text;
begin
  perform public.rfc_check_input(p_meta, p_bundle, p_authors, coalesce(p_collaborators, '[]'::jsonb), p_by);
  if p_note is not null and char_length(p_note) > 300 then raise exception 'invalid note' using errcode = '22023'; end if;
  perform public.rfc_rate_limit(h, 'revise', 30, 200);   -- por origem: 30 por hora e 200 por dia
  perform 1 from public.rfc_ids where rfc_id = p_rfc_id and source = 'site' and not hidden for update;
  if not found then raise exception 'unknown RFC' using errcode = '22023'; end if;
  select coalesce(max(rev), 0) + 1 into n from public.rfc_revisions where rfc_id = p_rfc_id;
  v := '1.' || (n - 1);
  insert into public.rfc_revisions (rfc_id, rev, version, meta, bundle, authors, collaborators, edited_by, note, ip_hash)
    values (p_rfc_id, n, v, p_meta, p_bundle, p_authors, coalesce(p_collaborators, '[]'::jsonb), btrim(p_by), nullif(btrim(coalesce(p_note, '')), ''), h);
  perform public.rfc_asset_finalize(p_rfc_id, n, p_bundle, p_token);
  return jsonb_build_object('rfc_id', p_rfc_id, 'version', v);
end $$;

-- Permissões: a chave pública chama só as três funções da página; as auxiliares ficam fechadas ------------------------
revoke all on function public.rfc_asset_names(text), public.rfc_asset_finalize(text, integer, text, uuid) from public, anon, authenticated;
revoke all on function public.stage_rfc_asset(uuid, text, text, text, text), public.create_rfc(jsonb, text, jsonb, jsonb, text, uuid),
  public.add_rfc_revision(text, jsonb, text, jsonb, jsonb, text, text, uuid) from public;
grant execute on function public.stage_rfc_asset(uuid, text, text, text, text), public.create_rfc(jsonb, text, jsonb, jsonb, text, uuid),
  public.add_rfc_revision(text, jsonb, text, jsonb, jsonb, text, text, uuid) to anon, authenticated;
