-- Comentário por parágrafo e reações com emoji.
-- Idempotente: tem 'if not exists' / 'or replace', então é seguro rodar de novo no SQL Editor (ou com `supabase db push`).

-- Comentário por parágrafo e reações ------------------------------------------------------------
-- para = número do parágrafo dentro da seção (0, 1, 2…, na ordem do documento, igual nos três idiomas);
-- vazio = comentário da seção. Respostas herdam o para do comentário original (trigger acima).
-- Uma reação é uma resposta que contém só emoji; ela conta como resposta ("respondido").
alter table public.rfc_comments add column if not exists para integer
  check (para is null or para between 0 and 999);

grant select (para) on public.rfc_comments to anon, authenticated;
grant insert (para) on public.rfc_comments to anon, authenticated;

-- Respostas herdam o `para` do comentário original e o limite sobe para 15 por minuto e 150 por dia (reações contam).
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

  -- Respostas têm um nível só e ficam na mesma RFC, seção e parágrafo do comentário original.
  if new.parent_id is not null then
    select * into parent from public.rfc_comments where id = new.parent_id;
    if not found or parent.hidden or parent.parent_id is not null
       or parent.rfc_id <> new.rfc_id or parent.section <> new.section then
      raise exception 'invalid parent' using errcode = '22023';
    end if;
    new.para := parent.para;
  end if;

  -- Limite por origem: 15 por minuto e 150 por dia (reações com emoji também contam).
  if (select count(*) from public.rfc_comments
        where ip_hash = new.ip_hash and created_at > now() - interval '1 minute') >= 15
     or (select count(*) from public.rfc_comments
        where ip_hash = new.ip_hash and created_at > now() - interval '1 day') >= 150 then
    raise exception 'rate limit' using errcode = 'PT429';
  end if;

  return new;
end;
$$;
