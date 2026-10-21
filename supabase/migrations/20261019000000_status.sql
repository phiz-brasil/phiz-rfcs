-- Status das RFCs alterável pela página: log só de inserção e a view do status atual.
-- Idempotente: tem 'if not exists' / 'or replace', então é seguro rodar de novo no SQL Editor (ou com `supabase db push`).

-- Status das RFCs ------------------------------------------------------------------------------
-- O status mostrado no site vem daqui; o "status" de rfcs/<ID>/rfc.json vale só até alguém mudar.
-- Qualquer pessoa com o link pode mudar o status pela página (sem login). Cada mudança vira uma linha
-- nova em rfc_status_log, com o nome informado; ninguém edita nem apaga pela página.
-- Desfazer uma mudança indevida: no Table Editor, apague a linha em rfc_status_log (vale a anterior).

create table if not exists public.rfc_status_log (
  id          uuid primary key default gen_random_uuid(),
  rfc_id      text not null check (rfc_id ~ '^PHZ-[0-9]{4}$'),
  status      text not null check (status in ('draft', 'in-review', 'approved', 'implemented', 'rejected', 'superseded')),
  author      text not null check (char_length(btrim(author)) between 1 and 60),
  created_at  timestamptz not null default now(),
  ip_hash     text
);

create index if not exists rfc_status_log_rfc_idx on public.rfc_status_log (rfc_id, created_at desc);
create index if not exists rfc_status_log_ip_idx on public.rfc_status_log (ip_hash, created_at);

create or replace function public.rfc_status_log_before_insert()
returns trigger
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
  headers  json := coalesce(nullif(current_setting('request.headers', true), ''), '{}')::json;
  ip       text := coalesce(headers ->> 'cf-connecting-ip', split_part(headers ->> 'x-forwarded-for', ',', 1), 'unknown');
begin
  new.id         := gen_random_uuid();
  new.created_at := now();
  new.author     := btrim(new.author);
  new.ip_hash    := encode(digest(ip || ':phiz-rfc', 'sha256'), 'hex');

  -- Limite por origem: 10 por minuto e 100 por dia.
  if (select count(*) from public.rfc_status_log
        where ip_hash = new.ip_hash and created_at > now() - interval '1 minute') >= 10
     or (select count(*) from public.rfc_status_log
        where ip_hash = new.ip_hash and created_at > now() - interval '1 day') >= 100 then
    raise exception 'rate limit' using errcode = 'PT429';
  end if;

  return new;
end;
$$;

drop trigger if exists rfc_status_log_before_insert on public.rfc_status_log;
create trigger rfc_status_log_before_insert
  before insert on public.rfc_status_log
  for each row execute function public.rfc_status_log_before_insert();

alter table public.rfc_status_log enable row level security;

revoke all on public.rfc_status_log from anon, authenticated;
grant select (id, rfc_id, status, author, created_at) on public.rfc_status_log to anon, authenticated;
grant insert (rfc_id, status, author) on public.rfc_status_log to anon, authenticated;

drop policy if exists "read status log" on public.rfc_status_log;
create policy "read status log" on public.rfc_status_log for select to anon, authenticated using (true);

drop policy if exists "add status" on public.rfc_status_log;
create policy "add status" on public.rfc_status_log for insert to anon, authenticated with check (true);

-- Status atual de cada RFC: a linha mais recente do log.
create or replace view public.rfc_status_current as
  select distinct on (rfc_id) rfc_id, status, author, created_at
  from public.rfc_status_log
  order by rfc_id, created_at desc;

grant select on public.rfc_status_current to anon, authenticated;
