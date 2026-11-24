-- As mensagens do portão citam o domínio certo (docs/spec/v2/login.md, "Decision 2026-11-24: the gate's messages"). A lógica é idêntica à de 20261201000000_member_lock.sql;
-- só os dois textos mudam. Idempotente. O portão já está ligado: a função nova entra em vigor assim que for criada.

create or replace function public.check_request()
returns void language plpgsql stable set search_path = public as $$
declare
  claims jsonb := coalesce(nullif(current_setting('request.jwt.claims', true), '')::jsonb, '{}'::jsonb);
  who text := coalesce(claims ->> 'role', current_user);
  path text := coalesce(current_setting('request.path', true), '');
begin
  if who = 'service_role' or current_user in ('postgres', 'supabase_admin', 'service_role') then return; end if;     -- funções de borda, webhooks, migrações
  if path = '/rpc/ping' then return; end if;                                                                         -- o keep-alive
  if who = 'anon' then raise sqlstate 'PT401' using message = 'sign in with a @phizchat.com account'; end if;
  if not public.is_member() then raise sqlstate 'PT403' using message = 'only @phizchat.com accounts have access'; end if;
end $$;
