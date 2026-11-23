-- Hub de anexos dos temas (fase 8 do plano em docs/spec/v2): arquivos, notas em Markdown e links, com edições (um anexo que substitui outro).
-- Idempotente: seguro rodar de novo no SQL Editor.
--
-- Os arquivos vão do navegador direto para o Storage (bucket privado 'attachments', até 50 MB, caminho <tema>/<uuid>/<nome>); a linha desta tabela só é
-- criada por add_attachment, que confere no próprio Storage que o arquivo existe e grava o tamanho e o tipo REAIS dele. Quem lê: a chave pública lê
-- as linhas e pede endereços assinados que expiram; quem escreve: só as funções abaixo. Sem login por enquanto (a fase 2, por último, fecha o acesso).
-- HTML nunca é aberto na origem do app: a página só o oferece para baixar.

insert into storage.buckets (id, name, public, file_size_limit)
values ('attachments', 'attachments', false, 52428800)
on conflict (id) do update set public = false, file_size_limit = 52428800;

drop policy if exists "attachments read" on storage.objects;
create policy "attachments read" on storage.objects for select to anon, authenticated using (bucket_id = 'attachments');
drop policy if exists "attachments upload" on storage.objects;
create policy "attachments upload" on storage.objects for insert to anon, authenticated
  with check (bucket_id = 'attachments' and name ~ '^PHZ-[0-9]{4}/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/[^/]{1,150}$');

create table if not exists public.attachments (
  id           uuid primary key default gen_random_uuid(),
  theme_id     text not null references public.themes (id),
  item_id      uuid references public.theme_items (id),
  kind         text not null check (kind in ('file', 'note', 'link')),
  name         text not null check (char_length(btrim(name)) between 1 and 200),
  description  text not null default '' check (char_length(description) <= 1000),
  storage_path text unique,
  content_type text,
  size         bigint check (size is null or size >= 0),
  checksum     text check (checksum is null or checksum ~ '^[0-9a-f]{64}$'),
  body         text check (body is null or char_length(body) <= 50000),
  url          text check (url is null or url ~ '^https://[^ ]{4,500}$'),
  stage        integer check (stage between 1 and 10),
  replaces     uuid references public.attachments (id),
  archive_version text,                                  -- só para a página arquivada de uma versão antiga de RFC (fase 8, arquivo congelado)
  archive_date    date,
  archive_note    jsonb,
  hidden       boolean not null default false,
  created_at   timestamptz not null default now(),
  created_by   text not null,
  check ((kind = 'file' and storage_path is not null) or (kind = 'note' and body is not null) or (kind = 'link' and url is not null))
);
create index if not exists attachments_theme_idx on public.attachments (theme_id, created_at desc);

alter table public.attachments enable row level security;
revoke all on public.attachments from anon, authenticated;
grant select on public.attachments to anon, authenticated;
drop policy if exists "read attachments" on public.attachments;
create policy "read attachments" on public.attachments for select to anon, authenticated
  using (not hidden and exists (select 1 from public.themes t where t.id = attachments.theme_id and not t.hidden));

-- Registrar um anexo --------------------------------------------------------------------------------------------------
create or replace function public.add_attachment(p_theme text, p jsonb, p_by text)
returns jsonb language plpgsql security definer set search_path = public, extensions as $$
declare k text := p ->> 'kind'; nm text := btrim(coalesce(p ->> 'name', '')); ds text := coalesce(p ->> 'description', '');
  item uuid := nullif(p ->> 'item_id', '')::uuid; st integer := nullif(p ->> 'stage', '')::integer; rep uuid := nullif(p ->> 'replaces', '')::uuid;
  path text := p ->> 'path'; obj record; new_id uuid; chk text := nullif(p ->> 'checksum', '');
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
  if k = 'file' then
    if path is null or path !~ ('^' || p_theme || '/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/[^/]{1,150}$') then
      raise exception 'invalid path' using errcode = '22023';
    end if;
    select o.name, (o.metadata ->> 'size')::bigint as size, o.metadata ->> 'mimetype' as mime into obj
      from storage.objects o where o.bucket_id = 'attachments' and o.name = path;
    if not found then raise exception 'file not uploaded' using errcode = '22023'; end if;
    insert into public.attachments (theme_id, item_id, kind, name, description, storage_path, content_type, size, checksum, stage, replaces, created_by)
      values (p_theme, item, k, nm, ds, path, obj.mime, obj.size, chk, st, rep, btrim(p_by)) returning id into new_id;
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

-- Tirar um anexo da lista (o arquivo fica no Storage; a lista deixa de mostrá-lo) -------------------------------------------
create or replace function public.hide_attachment(p_id uuid, p_by text)
returns void language plpgsql security definer set search_path = public, extensions as $$
declare a public.attachments;
begin
  perform public.theme_check_name(p_by);
  perform public.rfc_rate_limit(public.rfc_origin_hash(), 'theme', 120, 1000);
  select * into a from public.attachments where id = p_id and not hidden for update;
  if not found then raise exception 'unknown attachment' using errcode = '22023'; end if;
  update public.attachments set hidden = true where id = p_id;
  insert into public.theme_events (theme_id, item_id, edited_by, field, old_value) values (a.theme_id, a.item_id, btrim(p_by), 'attachment_removed', to_jsonb(a.name));
end $$;

revoke all on function public.add_attachment(text, jsonb, text), public.hide_attachment(uuid, text) from public;
grant execute on function public.add_attachment(text, jsonb, text), public.hide_attachment(uuid, text) to anon, authenticated;
