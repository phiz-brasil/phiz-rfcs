-- Tira do tema PHZ-0015 (Deeper Link) os dados que os testes de tradução e de FUP deixaram (docs/spec/v2/fup.md): uma decisão aberta e um bloqueio
-- abertos de "Claude (teste)" e as três atualizações da semana 2026-W48. O tema fica; o histórico de eventos (auditoria) não é mexido.
-- Idempotente: sem essas linhas, não faz nada.
delete from public.theme_decisions where theme_id = 'PHZ-0015' and created_by = 'Claude (teste)';
delete from public.theme_blockers  where theme_id = 'PHZ-0015' and created_by = 'Claude (teste)';
delete from public.theme_updates   where theme_id = 'PHZ-0015' and week = '2026-W48' and edited_by in ('Claude (teste)', 'Gleison Silva');
-- a frase de andamento do tema era uma dessas atualizações
update public.themes set progress = '{}'::jsonb, text_meta = coalesce(text_meta, '{}'::jsonb) - 'progress'
where id = 'PHZ-0015' and (progress ->> 'pt' like 'Tratado no FUP%' or progress ->> 'pt' like 'Teste autom%' or progress ->> 'en' like 'Discussed in the FUP%');
