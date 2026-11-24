-- O domínio dos membros é phizchat.com (docs/spec/v2/login.md, "Decision 2026-11-24"). A migração 20261201000000_member_lock.sql já foi aplicada com
-- phiz.com e não é editada; esta troca só a regra de membro. check_request() e as políticas chamam is_member(), então não mudam. Idempotente.

create or replace function public.is_member()
returns boolean language sql stable set search_path = '' as $$
  select coalesce(auth.jwt() ->> 'role', '') = 'authenticated'
     and coalesce(lower(auth.jwt() ->> 'email'), '') ~ '^[^@]+@phizchat\.com$'
$$;

-- a lista de admins também só aceita o domínio novo (a tabela está vazia: todo membro é admin até alguém ser nomeado)
alter table public.app_admins drop constraint if exists app_admins_email_check;
alter table public.app_admins add constraint app_admins_email_check check (email = lower(email) and email ~ '^[^@]+@phizchat\.com$');
