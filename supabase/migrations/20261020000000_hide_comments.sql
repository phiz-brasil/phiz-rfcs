-- Excluir comentários pela página: a função esconde o comentário e as respostas (nada é apagado).
-- Idempotente: tem 'if not exists' / 'or replace', então é seguro rodar de novo no SQL Editor (ou com `supabase db push`).

-- Excluir comentários ----------------------------------------------------------------------------
-- Qualquer pessoa com o link pode excluir um comentário pela página (sem login). "Excluir" só esconde:
-- a função marca o comentário (e as respostas dele) com hidden = true, guarda quando e por quem
-- (hidden_at, hidden_by) e ninguém apaga linhas pela página.
-- Restaurar: Table Editor > rfc_comments, ponha hidden = false (as respostas escondidas junto
-- também precisam voltar a hidden = false).
alter table public.rfc_comments add column if not exists hidden_at timestamptz;
alter table public.rfc_comments add column if not exists hidden_by text;

create table if not exists public.rfc_comment_hides (
  id          uuid primary key default gen_random_uuid(),
  comment_id  uuid not null,
  ip_hash     text,
  created_at  timestamptz not null default now()
);
create index if not exists rfc_comment_hides_ip_idx on public.rfc_comment_hides (ip_hash, created_at);
alter table public.rfc_comment_hides enable row level security;
revoke all on public.rfc_comment_hides from anon, authenticated;   -- sem policies: só a função grava

create or replace function public.hide_rfc_comment(p_id uuid, p_by text default null)
returns void
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
  headers  json := coalesce(nullif(current_setting('request.headers', true), ''), '{}')::json;
  ip       text := coalesce(headers ->> 'cf-connecting-ip', split_part(headers ->> 'x-forwarded-for', ',', 1), 'unknown');
  h        text := encode(digest(ip || ':phiz-rfc', 'sha256'), 'hex');
begin
  -- Limite por origem: 10 por minuto e 100 por dia.
  if (select count(*) from public.rfc_comment_hides where ip_hash = h and created_at > now() - interval '1 minute') >= 10
     or (select count(*) from public.rfc_comment_hides where ip_hash = h and created_at > now() - interval '1 day') >= 100 then
    raise exception 'rate limit' using errcode = 'PT429';
  end if;
  insert into public.rfc_comment_hides (comment_id, ip_hash) values (p_id, h);

  update public.rfc_comments
     set hidden = true, hidden_at = now(), hidden_by = left(nullif(btrim(coalesce(p_by, '')), ''), 60)
   where (id = p_id or parent_id = p_id) and hidden = false;
end;
$$;

revoke all on function public.hide_rfc_comment(uuid, text) from public;
grant execute on function public.hide_rfc_comment(uuid, text) to anon, authenticated;
