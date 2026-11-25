-- Hook "Before User Created" do Supabase Auth (docs/spec/v2/login.md, "Sign-up of other domains"): só cria usuário quem tem e-mail @phizchat.com.
-- Esta migração só CRIA a função; ligá-la é uma configuração do painel (Authentication → Auth Hooks → Before User Created → Postgres function). Idempotente.
-- Quem já existe não é afetado (o hook roda só na criação). O padrão é o mesmo de public.is_member() (20261202000000_member_domain.sql).

create or replace function public.hook_before_user_created(event jsonb)
returns jsonb language plpgsql stable set search_path = '' as $$
begin
  if coalesce(lower(event -> 'user' ->> 'email'), '') ~ '^[^@]+@phizchat\.com$' then
    return '{}'::jsonb;
  end if;
  return jsonb_build_object('error', jsonb_build_object('http_code', 403, 'message', 'only @phizchat.com accounts can sign up'));
end $$;

grant execute on function public.hook_before_user_created(jsonb) to supabase_auth_admin;
revoke execute on function public.hook_before_user_created(jsonb) from public, anon, authenticated;
