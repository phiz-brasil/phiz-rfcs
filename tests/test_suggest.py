"""supabase/functions/suggest-summary/suggest.ts: which documents the AI reads and how its answer is checked. Pure, so Node runs it.
The point of these tests: a suggestion is kept only with a quotation found word for word in the document it names; nothing is invented."""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(expr, data=None):
    code = ("import * as S from './supabase/functions/suggest-summary/suggest.ts'; import { readFileSync } from 'node:fs';"
            f"const D = JSON.parse(readFileSync(0, 'utf8')); console.log(JSON.stringify({expr}));")
    out = subprocess.run(["node", "--input-type=module", "-e", code], input=json.dumps(data or {}), cwd=ROOT, capture_output=True, text=True)
    if out.returncode:
        raise AssertionError(out.stderr)
    return json.loads(out.stdout)


BUNDLE = """---
title_pt: x
---
<!-- lang:pt -->
Texto antes de qualquer seção.

## 1. Contexto
Hoje o merchant precisa integrar três APIs diferentes para enviar uma mensagem.

## 2. Solução
Uma única API de mensagens comerciais, com webhook de entrega.

## 3. Métricas
Sucesso é migrar 80% dos merchants em 6 meses.
<!-- lang:en -->
## 1. Context
English text that must not be used when Portuguese exists.
"""
SOURCES = [{"id": "S1", "label": "RFC — Contexto", "text": "Hoje o merchant precisa integrar **três APIs** diferentes para enviar uma mensagem."},
           {"id": "S2", "label": "Nota — Reunião", "text": "Decidimos migrar 80% dos merchants em 6 meses."}]


@unittest.skipUnless(shutil.which("node"), "node is not installed")
class SuggestTest(unittest.TestCase):
    def test_an_rfc_is_split_into_sections_of_its_portuguese_text(self):
        s = run("S.rfcSections(D.b)", {"b": BUNDLE})
        self.assertEqual([x["heading"] for x in s], ["Introdução", "1. Contexto", "2. Solução", "3. Métricas"])
        self.assertNotIn("English", json.dumps(s))

    def test_the_anchor_id_of_a_heading_is_not_part_of_its_label(self):
        s = run("S.rfcSections(D.b)", {"b": "<!-- lang:pt -->\n## Resumo {summary}\nTexto.\n\n## **Plano** de entrega {plan}\nMais."})
        self.assertEqual([x["heading"] for x in s], ["Resumo", "Plano de entrega"])

    def test_the_english_text_is_used_when_there_is_no_portuguese(self):
        s = run("S.rfcSections(D.b)", {"b": "<!-- lang:en -->\n## Goal\nBuild the thing."})
        self.assertEqual(s, [{"heading": "Goal", "text": "Build the thing."}])

    def test_sources_are_numbered_labelled_and_cover_every_kind_of_document(self):
        raw = {"rfcBundle": BUNDLE, "notes": [{"name": "Ata", "body": "Decidimos X."}], "files": [{"name": "plano.md", "text": "Plano."}],
               "updates": [{"week": "2026-W47", "progress": {"pt": "No prazo"}, "advanced": {"en": "Contract signed"}}],
               "theme": {"what_it_is": {"pt": "Uma API"}, "progress": {}}}
        s = run("S.buildSources(D)", raw)
        self.assertEqual([x["id"] for x in s], [f"S{i}" for i in range(1, len(s) + 1)])
        labels = [x["label"] for x in s]
        self.assertIn("RFC — 1. Contexto", labels)
        self.assertIn("Nota — Ata", labels)
        self.assertIn("Anexo — plano.md", labels)
        self.assertIn("Atualização semanal 2026-W47", labels)
        self.assertIn("Tema — o que é e andamento", labels)

    def test_empty_documents_are_left_out_and_long_ones_are_cut_to_their_share(self):
        s = run("S.buildSources(D)", {"notes": [{"name": "vazia", "body": "  "}, {"name": "longa", "body": "x" * 50000}], "files": [], "updates": [], "theme": {}})
        self.assertEqual([x["label"] for x in s], ["Nota — longa"])
        self.assertEqual(len(s[0]["text"]), 7000)                      # the notes' whole share, but no more than one source may take (8000)

    def test_everything_the_model_reads_fits_its_context_window_whatever_the_documents(self):
        big = "palavra " * 5000
        raw = {"rfcBundle": "<!-- lang:pt -->\n" + "\n".join(f"## Seção {i}\n{big}" for i in range(25)),
               "notes": [{"name": f"n{i}", "body": big} for i in range(10)], "files": [{"name": f"f{i}.md", "text": big} for i in range(10)],
               "updates": [{"week": f"2026-W{i:02d}", "progress": {"pt": big}} for i in range(6)], "theme": {"what_it_is": {"pt": big}}}
        s = run("S.buildSources(D)", raw)
        self.assertLessEqual(sum(len(x["text"]) for x in s), 36000)
        self.assertLessEqual(len(s), 42)
        labels = [x["label"] for x in s]
        self.assertTrue(any(l.startswith("RFC") for l in labels) and any(l.startswith("Nota") for l in labels) and any(l.startswith("Anexo") for l in labels)
                        and any(l.startswith("Atualização") for l in labels))                  # a long RFC does not push the other documents out

    def test_a_long_rfc_shares_its_budget_between_its_sections(self):
        raw = {"rfcBundle": "<!-- lang:pt -->\n" + "\n".join(f"## Seção {i}\n{'a ' * 4000}" for i in range(10)), "notes": [], "files": [], "updates": [], "theme": {}}
        s = run("S.buildSources(D)", raw)
        self.assertEqual(len(s), 10)
        self.assertTrue(all(len(x["text"]) == 1800 for x in s))        # 18 000 / 10

    def test_the_prompt_forbids_inventing_and_carries_every_source(self):
        p = run("S.buildPrompt('Business API', D.s)", {"s": SOURCES})
        self.assertIn("SOMENTE", p["system"])
        self.assertIn("COPIADAS LITERALMENTE", p["system"])
        self.assertIn("### S2 · Nota — Reunião", p["user"])
        self.assertIn("Business API", p["user"])

    # -- reading the model's answer ----------------------------------------------------------------------------------------
    def test_the_json_is_found_inside_prose_and_code_fences(self):
        self.assertEqual(run("S.parseModelJson(D.t)", {"t": 'Claro!\n```json\n{"a": {"b": "}"}}\n```\nPronto.'}), {"a": {"b": "}"}})

    def test_text_without_json_is_null(self):
        self.assertIsNone(run("S.parseModelJson(D.t)", {"t": "não sei"}))

    # -- the check that keeps the AI honest ------------------------------------------------------------------------------------
    def answer(self, **fields):
        base = {f: {"text": None, "quotes": [], "missing": None} for f in ("problem", "solution", "success")}
        base.update(fields)
        return run("S.validate(D.p, D.s)", {"p": base, "s": SOURCES})

    def test_an_answer_with_a_quotation_found_in_its_source_is_kept_with_the_citation(self):
        r = self.answer(problem={"text": "O merchant integra várias APIs.", "quotes": [{"source": "S1", "quote": "integrar três APIs diferentes"}], "missing": None})
        self.assertEqual(r["problem"], {"text": "O merchant integra várias APIs.", "sources": [{"label": "RFC — Contexto", "quote": "integrar três APIs diferentes"}], "missing": None})

    def test_the_quotation_check_ignores_case_markdown_and_spacing(self):
        r = self.answer(problem={"text": "ok", "quotes": [{"source": "S1", "quote": "INTEGRAR  três   apis diferentes"}], "missing": None})
        self.assertEqual(r["problem"]["text"], "ok")

    def test_an_invented_quotation_drops_the_answer_and_says_why(self):
        r = self.answer(problem={"text": "O custo é de R$ 2 milhões.", "quotes": [{"source": "S1", "quote": "o custo anual passa de dois milhões"}], "missing": None})
        self.assertIsNone(r["problem"]["text"])
        self.assertEqual(r["problem"]["sources"], [])
        self.assertIn("citação verificável", r["problem"]["missing"])

    def test_a_quotation_taken_from_another_document_does_not_count(self):
        r = self.answer(success={"text": "Migrar 80%.", "quotes": [{"source": "S1", "quote": "migrar 80% dos merchants em 6 meses"}], "missing": None})
        self.assertIsNone(r["success"]["text"])            # that sentence is in S2, not in S1
        r = self.answer(success={"text": "Migrar 80%.", "quotes": [{"source": "S2", "quote": "migrar 80% dos merchants em 6 meses"}], "missing": None})
        self.assertEqual(r["success"]["sources"][0]["label"], "Nota — Reunião")

    def test_an_unknown_source_or_a_too_short_quotation_is_dropped(self):
        r = self.answer(problem={"text": "x", "quotes": [{"source": "S9", "quote": "integrar três APIs diferentes"}, {"source": "S1", "quote": "APIs"}], "missing": None})
        self.assertIsNone(r["problem"]["text"])

    def test_a_missing_answer_keeps_the_models_sentence_or_the_default(self):
        r = self.answer(solution={"text": None, "quotes": [], "missing": "A RFC não descreve a solução."})
        self.assertEqual(r["solution"], {"text": None, "sources": [], "missing": "A RFC não descreve a solução."})
        self.assertEqual(r["success"]["missing"], "Os documentos não dizem como o sucesso será medido.")

    def test_only_valid_quotations_are_kept_and_at_most_three(self):
        q = [{"source": "S1", "quote": "integrar três APIs diferentes"}, {"source": "S1", "quote": "frase que não existe aqui"}, {"source": "S1", "quote": "enviar uma mensagem"},
             {"source": "S2", "quote": "Decidimos migrar 80%"}, {"source": "S2", "quote": "dos merchants em 6 meses"}]
        r = self.answer(problem={"text": "ok", "quotes": q, "missing": None})
        self.assertEqual([c["quote"] for c in r["problem"]["sources"]], ["integrar três APIs diferentes", "enviar uma mensagem", "Decidimos migrar 80%"])

    def test_a_long_text_is_cut_and_garbage_answers_become_missing(self):
        r = self.answer(problem={"text": "a" * 900, "quotes": [{"source": "S1", "quote": "integrar três APIs diferentes"}], "missing": None})
        self.assertEqual(len(r["problem"]["text"]), 500)
        r = run("S.validate(D.p, D.s)", {"p": "lixo", "s": SOURCES})
        self.assertEqual([r[f]["text"] for f in ("problem", "solution", "success")], [None, None, None])
        r = run("S.validate(D.p, D.s)", {"p": {"problem": {"text": 7, "quotes": "x", "missing": {"a": 1}}}, "s": SOURCES})
        self.assertIsNone(r["problem"]["text"])


if __name__ == "__main__":
    unittest.main()
