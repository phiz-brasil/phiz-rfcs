-- Tradução automática dos comentários: colunas que a Edge Function translate-comment preenche.
-- Idempotente: tem 'if not exists' / 'or replace', então é seguro rodar de novo no SQL Editor (ou com `supabase db push`).

-- Tradução automática (Cloudflare Workers AI) ------------------------------------------------------------
-- A Edge Function supabase/functions/translate-comment preenche estas colunas depois de cada
-- comentário novo: {"pt": {"body": …, "quote": …}, "en": {…}, "zh": {…}} e o idioma detectado.
-- A página só LÊ estas colunas; a chave pública não pode gravá-las (o insert continua limitado
-- aos campos do formulário acima).
alter table public.rfc_comments add column if not exists translations jsonb;
alter table public.rfc_comments add column if not exists src_lang text
  check (src_lang is null or src_lang in ('pt', 'en', 'zh'));

grant select (translations, src_lang) on public.rfc_comments to anon, authenticated;
