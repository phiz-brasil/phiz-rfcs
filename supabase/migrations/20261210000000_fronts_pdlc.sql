-- Redesign, PR 4 (docs/spec/v2/redesign.md, What PR 4 delivers): the fronts the owner named on 2026-11-26.
--   POP (API Platform joins it) · Payments · Mini-Apps · Parcerias e POCs (new) · Novos negócios (new) · Outros. Product Center leaves.
-- The themes of API Platform move to POP, each with a 'front' event in its history; a front is removed only when no theme points at it.
-- Idempotent: running it twice changes nothing more.

-- the two new fronts
insert into public.fronts (key, name, scope, ord, is_other) values
  ('parcerias-pocs', '{"pt":"Parcerias e POCs","en":"Partnerships and POCs","zh":"合作与 POC"}',
   '{"pt":"Parcerias com outras empresas e as provas de conceito (POCs) em andamento ou em negociação, enquanto não viram produto de uma frente.",
     "en":"Partnerships with other companies and the proofs of concept (POCs) running or being negotiated, until they become a product of a front.",
     "zh":"与其他公司的合作，以及正在进行或洽谈中的概念验证（POC），直至其成为某一业务线的产品。"}', 4, false),
  ('novos-negocios', '{"pt":"Novos negócios","en":"New business","zh":"新业务"}',
   '{"pt":"Oportunidades de negócio novas, ainda fora das frentes existentes: descoberta, casos de negócio e primeiros testes.",
     "en":"New business opportunities still outside the existing fronts: discovery, business cases and first tests.",
     "zh":"尚不属于现有业务线的新业务机会：探索、商业论证和初步测试。"}', 5, false)
on conflict (key) do nothing;

-- POP now covers the APIs too
update public.fronts set scope = '{"pt":"PhizChat Open Platform: o portal onde as empresas clientes administram suas contas e atividades (contas comerciais, acesso de parceiros, permissões, verificação, KYB, portal de conteúdo e social) e as APIs para empresas (Business Messaging, Single Message e Outbound API, migração da API antiga, regras de recontato, endereçamento, APIs de grupos e bots).",
  "en":"PhizChat Open Platform: the portal where business customers manage their accounts and activity (business accounts, partner access, permissions, verification, KYB, the content and social portal) and the APIs for businesses (Business Messaging, Single Message and Outbound API, migration of the old API, recontact rules, addressing, group APIs and bots).",
  "zh":"PhizChat Open Platform：企业客户管理账户和业务的门户（商业账户、合作伙伴访问、权限、认证、KYB、内容与社交门户），以及面向企业的 API（Business Messaging、Single Message 与 Outbound API、旧 API 迁移、再触达规则、寻址、群组 API 与机器人）。"}'
where key = 'pop' and scope ->> 'pt' not like '%APIs para empresas%';

-- the order the owner gave
update public.fronts set ord = 1 where key = 'pop';
update public.fronts set ord = 2 where key = 'payments';
update public.fronts set ord = 3 where key = 'mini-apps';
update public.fronts set ord = 4 where key = 'parcerias-pocs';
update public.fronts set ord = 5 where key = 'novos-negocios';

-- the themes of API Platform go to POP, and their history says so
insert into public.theme_events (theme_id, edited_by, field, old_value, new_value)
select id, 'Redesenho (PR 4)', 'front', to_jsonb('api-platform'::text), to_jsonb('pop'::text) from public.themes where front = 'api-platform';
update public.themes set front = 'pop', updated_at = now() where front = 'api-platform';

-- a front leaves only when nothing points at it
delete from public.fronts f where f.key in ('api-platform', 'product-center') and not exists (select 1 from public.themes t where t.front = f.key);
