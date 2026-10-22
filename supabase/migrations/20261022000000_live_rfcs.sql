-- RFCs criadas pelo site: ids compartilhados com o repositório, revisões (só inserção) e as funções que a página usa.
-- Idempotente: tem 'if not exists' / 'or replace', então é seguro rodar de novo no SQL Editor (ou com `supabase db push`).
--
-- O conteúdo é o arquivo único da RFC (docs/spec/rfc-bundle.md) guardado como texto; a página o transforma em HTML no navegador.
-- Quem acessa: a chave pública só LÊ (tabela de revisões e as views) e CHAMA as funções create_rfc, add_rfc_revision e
-- reserve_rfc_id; não insere nem altera linhas direto. Editar é criar uma revisão nova; nada é sobrescrito.
-- Moderação: no Table Editor, marque hidden = true em rfc_ids para tirar uma RFC do ar (e false para voltar).

create extension if not exists pgcrypto with schema extensions;

-- Ids: uma sequência só para as RFCs do repositório e as do site, sem colisão ------------------------------------
create table if not exists public.rfc_ids (
  rfc_id      text primary key check (rfc_id ~ '^PHZ-[0-9]{4}$'),
  source      text not null check (source in ('site', 'repo')),
  reserved_by text check (reserved_by is null or char_length(reserved_by) <= 60),
  hidden      boolean not null default false,
  created_at  timestamptz not null default now()
);

insert into public.rfc_ids (rfc_id, source) values ('PHZ-0001', 'repo'), ('PHZ-0002', 'repo')
  on conflict (rfc_id) do nothing;

-- Revisões ----------------------------------------------------------------------------------------------------
create table if not exists public.rfc_revisions (
  id            uuid primary key default gen_random_uuid(),
  rfc_id        text not null references public.rfc_ids (rfc_id),
  rev           integer not null check (rev >= 1),
  version       text not null check (version ~ '^[0-9]+\.[0-9]+$'),
  meta          jsonb not null,                       -- {title:{pt,en,zh}, summary:{pt,en,zh}, systems:[…]}
  bundle        text not null check (char_length(bundle) between 1 and 600000),
  authors       jsonb not null,
  collaborators jsonb not null default '[]'::jsonb,
  edited_by     text not null check (char_length(btrim(edited_by)) between 1 and 60),
  note          text check (note is null or char_length(note) <= 300),
  created_at    timestamptz not null default now(),
  ip_hash       text,
  unique (rfc_id, rev)
);
create index if not exists rfc_revisions_rfc_idx on public.rfc_revisions (rfc_id, rev desc);

-- Limite de frequência por origem (compartilhado pelas funções abaixo)
create table if not exists public.rfc_live_actions (
  id         uuid primary key default gen_random_uuid(),
  ip_hash    text not null,
  action     text not null,
  created_at timestamptz not null default now()
);
create index if not exists rfc_live_actions_idx on public.rfc_live_actions (ip_hash, action, created_at);

alter table public.rfc_ids enable row level security;
alter table public.rfc_revisions enable row level security;
alter table public.rfc_live_actions enable row level security;

revoke all on public.rfc_ids, public.rfc_revisions, public.rfc_live_actions from anon, authenticated;
grant select (id, rfc_id, rev, version, meta, bundle, authors, collaborators, edited_by, note, created_at)
  on public.rfc_revisions to anon, authenticated;
grant select (rfc_id, source, hidden) on public.rfc_ids to anon, authenticated;     -- the policy below reads it as the caller

drop policy if exists "read ids" on public.rfc_ids;
create policy "read ids" on public.rfc_ids for select to anon, authenticated using (true);

drop policy if exists "read visible revisions" on public.rfc_revisions;
create policy "read visible revisions" on public.rfc_revisions for select to anon, authenticated
  using (exists (select 1 from public.rfc_ids i where i.rfc_id = rfc_revisions.rfc_id and not i.hidden));

-- Views: a revisão atual de cada RFC do site (sem o texto, para listas) e o histórico ---------------------------
create or replace view public.rfc_live_current as
  select distinct on (r.rfc_id)
         r.rfc_id, r.rev, r.version, r.meta, r.authors, r.collaborators, r.edited_by, r.created_at,
         (select min(x.created_at) from public.rfc_revisions x where x.rfc_id = r.rfc_id) as first_created_at
    from public.rfc_revisions r
    join public.rfc_ids i on i.rfc_id = r.rfc_id
   where not i.hidden
   order by r.rfc_id, r.rev desc;

create or replace view public.rfc_live_revisions as
  select r.rfc_id, r.rev, r.version, r.edited_by, r.note, r.created_at
    from public.rfc_revisions r
    join public.rfc_ids i on i.rfc_id = r.rfc_id
   where not i.hidden;

grant select on public.rfc_live_current, public.rfc_live_revisions to anon, authenticated;

-- Funções --------------------------------------------------------------------------------------------------------
create or replace function public.rfc_origin_hash()
returns text language plpgsql stable security definer set search_path = public, extensions as $$
declare
  headers json := coalesce(nullif(current_setting('request.headers', true), ''), '{}')::json;
  ip      text := coalesce(headers ->> 'cf-connecting-ip', split_part(headers ->> 'x-forwarded-for', ',', 1), 'unknown');
begin
  return encode(digest(ip || ':phiz-rfc', 'sha256'), 'hex');
end $$;

create or replace function public.rfc_rate_limit(p_hash text, p_action text, p_per_hour integer, p_per_day integer)
returns void language plpgsql security definer set search_path = public as $$
begin
  if (select count(*) from public.rfc_live_actions where ip_hash = p_hash and action = p_action and created_at > now() - interval '1 hour') >= p_per_hour
     or (select count(*) from public.rfc_live_actions where ip_hash = p_hash and action = p_action and created_at > now() - interval '1 day') >= p_per_day then
    raise exception 'rate limit' using errcode = 'PT429';
  end if;
  insert into public.rfc_live_actions (ip_hash, action) values (p_hash, p_action);
end $$;

-- O que uma RFC enviada precisa ter (a página já confere tudo; aqui é a barreira de quem chama a função direto)
create or replace function public.rfc_check_input(p_meta jsonb, p_bundle text, p_authors jsonb, p_collaborators jsonb, p_by text)
returns void language plpgsql immutable set search_path = public as $$
declare
  lang   text;
  key    text;
  item   jsonb;
  maxlen integer;
begin
  if p_meta is null or jsonb_typeof(p_meta) is distinct from 'object' then raise exception 'invalid meta' using errcode = '22023'; end if;
  foreach key in array array['title', 'summary'] loop
    if jsonb_typeof(p_meta -> key) is distinct from 'object' then raise exception 'invalid meta.%', key using errcode = '22023'; end if;
    maxlen := case when key = 'title' then 300 else 1000 end;
    foreach lang in array array['pt', 'en', 'zh'] loop
      if jsonb_typeof(p_meta -> key -> lang) is distinct from 'string'
         or char_length(btrim(p_meta -> key ->> lang)) not between 1 and maxlen then
        raise exception 'invalid meta.%.%', key, lang using errcode = '22023';
      end if;
    end loop;
  end loop;
  if (p_meta -> 'systems') is not null
     and (jsonb_typeof(p_meta -> 'systems') is distinct from 'array' or jsonb_array_length(p_meta -> 'systems') > 10) then
    raise exception 'invalid meta.systems' using errcode = '22023';
  end if;
  if p_bundle is null or char_length(p_bundle) not between 1 and 600000 then raise exception 'invalid bundle size' using errcode = '22023'; end if;
  foreach lang in array array['pt', 'en', 'zh'] loop
    if p_bundle !~ ('<!--\s*lang:\s*' || lang || '\s*-->') then raise exception 'bundle is missing the % section', lang using errcode = '22023'; end if;
  end loop;
  if p_authors is null or jsonb_typeof(p_authors) is distinct from 'array' or jsonb_array_length(p_authors) not between 1 and 10 then
    raise exception 'invalid authors' using errcode = '22023';
  end if;
  if p_collaborators is null or jsonb_typeof(p_collaborators) is distinct from 'array' or jsonb_array_length(p_collaborators) > 20 then
    raise exception 'invalid collaborators' using errcode = '22023';
  end if;
  for item in select * from jsonb_array_elements(p_authors || p_collaborators) loop
    if jsonb_typeof(item) is distinct from 'string' or char_length(btrim(item #>> '{}')) not between 1 and 80 then
      raise exception 'invalid person name' using errcode = '22023';
    end if;
  end loop;
  if p_by is null or char_length(btrim(p_by)) not between 1 and 60 then raise exception 'invalid name' using errcode = '22023'; end if;
end $$;

-- Próximo id livre, para as RFCs do site e para as que se criam no repositório
create or replace function public.rfc_allocate_id(p_source text, p_by text)
returns text language plpgsql security definer set search_path = public as $$
declare next_n integer; new_id text;
begin
  perform pg_advisory_xact_lock(7243001);
  select coalesce(max(substring(rfc_id from 5)::integer), 0) + 1 into next_n from public.rfc_ids;
  if next_n > 9999 then raise exception 'no ids left' using errcode = '22023'; end if;
  new_id := 'PHZ-' || lpad(next_n::text, 4, '0');
  insert into public.rfc_ids (rfc_id, source, reserved_by) values (new_id, p_source, left(btrim(p_by), 60));
  return new_id;
end $$;

-- tools/new_rfc.py pede o id por aqui, para não colidir com uma RFC criada no site ao mesmo tempo
create or replace function public.reserve_rfc_id(p_by text)
returns text language plpgsql security definer set search_path = public, extensions as $$
begin
  if p_by is null or char_length(btrim(p_by)) not between 1 and 60 then raise exception 'invalid name' using errcode = '22023'; end if;
  perform public.rfc_rate_limit(public.rfc_origin_hash(), 'reserve', 20, 60);
  return public.rfc_allocate_id('repo', p_by);
end $$;

create or replace function public.create_rfc(p_meta jsonb, p_bundle text, p_authors jsonb, p_collaborators jsonb, p_by text)
returns jsonb language plpgsql security definer set search_path = public, extensions as $$
declare h text := public.rfc_origin_hash(); new_id text;
begin
  perform public.rfc_check_input(p_meta, p_bundle, p_authors, coalesce(p_collaborators, '[]'::jsonb), p_by);
  perform public.rfc_rate_limit(h, 'create', 5, 20);     -- por origem: 5 por hora e 20 por dia
  new_id := public.rfc_allocate_id('site', p_by);
  insert into public.rfc_revisions (rfc_id, rev, version, meta, bundle, authors, collaborators, edited_by, ip_hash)
    values (new_id, 1, '1.0', p_meta, p_bundle, p_authors, coalesce(p_collaborators, '[]'::jsonb), btrim(p_by), h);
  return jsonb_build_object('rfc_id', new_id, 'version', '1.0');
end $$;

create or replace function public.add_rfc_revision(p_rfc_id text, p_meta jsonb, p_bundle text, p_authors jsonb, p_collaborators jsonb, p_by text, p_note text)
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
  return jsonb_build_object('rfc_id', p_rfc_id, 'version', v);
end $$;

-- Só as três funções da página/ferramenta ficam abertas à chave pública
revoke all on function public.rfc_origin_hash(), public.rfc_rate_limit(text, text, integer, integer),
  public.rfc_check_input(jsonb, text, jsonb, jsonb, text), public.rfc_allocate_id(text, text) from public, anon, authenticated;
revoke all on function public.reserve_rfc_id(text), public.create_rfc(jsonb, text, jsonb, jsonb, text),
  public.add_rfc_revision(text, jsonb, text, jsonb, jsonb, text, text) from public;
grant execute on function public.reserve_rfc_id(text), public.create_rfc(jsonb, text, jsonb, jsonb, text),
  public.add_rfc_revision(text, jsonb, text, jsonb, jsonb, text, text) to anon, authenticated;
