-- Remove os dois FUPs criados para validar a escrita em produção (docs/spec/v2/fup.md). Por id e só se o título ainda começa com TESTE.
-- As atualizações da semana que eles escreveram no tema de teste PHZ-0015 ficam. Idempotente: sem os registros, não faz nada.
delete from public.fup_meetings
where id in ('1b345f9f-cf92-4e6a-923a-41af26a4744a', 'c00b76aa-cdae-4dd8-9a48-869977bb58d1')
  and title like 'TESTE%';
