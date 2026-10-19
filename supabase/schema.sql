-- Comentários das RFCs, guardados no Supabase.
-- Rode este arquivo inteiro uma vez no SQL Editor do projeto (Supabase > SQL Editor > New query).
-- É seguro rodar de novo: tudo usa "if not exists" / "or replace".
--
-- Quem acessa: a página usa a chave pública (publishable/anon). Com ela, qualquer pessoa pode
-- LER comentários visíveis e CRIAR comentários novos. Ninguém edita nem apaga pela página.
-- Moderação: no Table Editor, marque "hidden = true" no comentário (ou apague a linha).

create extension if not exists pgcrypto with schema extensions;

create table if not exists public.rfc_comments (
  id          uuid primary key default gen_random_uuid(),
  rfc_id      text not null check (rfc_id ~ '^PHZ-[0-9]{4}$'),
  section     text not null check (section ~ '^[a-z0-9-]{1,80}$'),
  parent_id   uuid references public.rfc_comments (id) on delete cascade,
  author      text not null check (char_length(btrim(author)) between 1 and 60),
  body        text not null check (char_length(btrim(body)) between 1 and 4000),
  quote       text check (quote is null or char_length(quote) <= 500),
  lang        text not null default 'pt' check (lang in ('pt', 'en', 'zh')),
  created_at  timestamptz not null default now(),
  hidden      boolean not null default false,
  ip_hash     text
);

create index if not exists rfc_comments_rfc_idx on public.rfc_comments (rfc_id, created_at);
create index if not exists rfc_comments_ip_idx on public.rfc_comments (ip_hash, created_at);

-- Antes de gravar: fixa os campos que o visitante não controla, valida respostas e limita a frequência.
create or replace function public.rfc_comments_before_insert()
returns trigger
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
  headers  json := coalesce(nullif(current_setting('request.headers', true), ''), '{}')::json;
  ip       text := coalesce(headers ->> 'cf-connecting-ip', split_part(headers ->> 'x-forwarded-for', ',', 1), 'unknown');
  parent   public.rfc_comments%rowtype;
begin
  new.id         := gen_random_uuid();
  new.created_at := now();
  new.hidden     := false;
  new.author     := btrim(new.author);
  new.body       := btrim(new.body);
  new.quote      := nullif(btrim(coalesce(new.quote, '')), '');
  new.ip_hash    := encode(digest(ip || ':phiz-rfc', 'sha256'), 'hex');

  -- Respostas têm um nível só e ficam na mesma RFC e seção do comentário original.
  if new.parent_id is not null then
    select * into parent from public.rfc_comments where id = new.parent_id;
    if not found or parent.hidden or parent.parent_id is not null
       or parent.rfc_id <> new.rfc_id or parent.section <> new.section then
      raise exception 'invalid parent' using errcode = '22023';
    end if;
  end if;

  -- Limite por origem: 5 por minuto e 50 por dia.
  if (select count(*) from public.rfc_comments
        where ip_hash = new.ip_hash and created_at > now() - interval '1 minute') >= 5
     or (select count(*) from public.rfc_comments
        where ip_hash = new.ip_hash and created_at > now() - interval '1 day') >= 50 then
    raise exception 'rate limit' using errcode = 'PT429';
  end if;

  return new;
end;
$$;

drop trigger if exists rfc_comments_before_insert on public.rfc_comments;
create trigger rfc_comments_before_insert
  before insert on public.rfc_comments
  for each row execute function public.rfc_comments_before_insert();

-- Permissões: a chave pública só lê colunas públicas e só insere os campos do formulário.
alter table public.rfc_comments enable row level security;

revoke all on public.rfc_comments from anon, authenticated;
grant select (id, rfc_id, section, parent_id, author, body, quote, lang, created_at)
  on public.rfc_comments to anon, authenticated;
grant insert (rfc_id, section, parent_id, author, body, quote, lang)
  on public.rfc_comments to anon, authenticated;

drop policy if exists "read visible comments" on public.rfc_comments;
create policy "read visible comments" on public.rfc_comments
  for select to anon, authenticated
  using (hidden = false);

drop policy if exists "add comments" on public.rfc_comments;
create policy "add comments" on public.rfc_comments
  for insert to anon, authenticated
  with check (hidden = false);

-- Tradução automática (DeepL) ------------------------------------------------------------
-- A Edge Function supabase/functions/translate-comment preenche estas colunas depois de cada
-- comentário novo: {"pt": {"body": …, "quote": …}, "en": {…}, "zh": {…}} e o idioma detectado.
-- A página só LÊ estas colunas; a chave pública não pode gravá-las (o insert continua limitado
-- aos campos do formulário acima).
alter table public.rfc_comments add column if not exists translations jsonb;
alter table public.rfc_comments add column if not exists src_lang text
  check (src_lang is null or src_lang in ('pt', 'en', 'zh'));

grant select (translations, src_lang) on public.rfc_comments to anon, authenticated;
