"""Phase 9: the three slide answers with their states, "Suggest with AI" (the Edge Function is replaced by the fake; its own checks are in
tests/test_suggest.py) and the guarantee that a suggestion never replaces what a person wrote or confirmed."""
import sys
import unittest
from pathlib import Path

from playwright.sync_api import expect

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import SiteCase  # noqa: E402

SUGGESTION = {
    "suggestions": {
        "problem": {"text": "O merchant integra três APIs para enviar uma mensagem.", "sources": [{"label": "RFC — 1. Contexto", "quote": "integrar três APIs diferentes"}], "missing": None},
        "solution": {"text": None, "sources": [], "missing": "A RFC não descreve a solução."},
        "success": {"text": "Migrar 80% dos merchants em 6 meses.", "sources": [{"label": "Nota — Reunião", "quote": "migrar 80% dos merchants em 6 meses"}], "missing": None},
    },
    "sources": [{"id": "S1", "label": "RFC — 1. Contexto"}, {"id": "S2", "label": "Nota — Reunião"}],
}


class SummaryTest(SiteCase):
    def setUp(self):
        super().setUp()
        self.db.seed_theme("PHZ-0001", "api-platform", title={"pt": "Business Messaging API"}, owner="Gleisonc")
        self.db.suggest_response = SUGGESTION

    def theme(self, query=""):
        self.page.goto(self.base + f"/themes/PHZ-0001/{query}")
        expect(self.page.locator("h1")).to_be_visible()

    def sign(self, name="Ana"):
        self.prefs()
        self.page.get_by_label("Seu nome").fill(name)
        self.page.keyboard.press("Escape")

    def box(self):
        return self.page.get_by_role("region", name="Resumo para os slides")

    def answer(self, f):
        return self.box().locator(f'[data-answer="{f}"]')

    def suggest(self):
        self.box().get_by_role("button", name="Sugerir com IA").click()

    # -- states ------------------------------------------------------------------------------------------------------------
    def test_a_new_theme_has_three_unexplained_answers(self):
        self.theme()
        for f in ("problem", "solution", "success"):
            expect(self.answer(f)).to_have_attribute("data-state", "empty")
            expect(self.answer(f).locator('[data-k="missing"]')).to_have_text("Ainda não explicado")
        expect(self.box()).to_contain_text("Que problema estamos tratando com este tema?")

    def test_a_text_written_before_states_existed_counts_as_confirmed(self):
        self.db.themes["PHZ-0001"]["problem"] = {"pt": "Texto antigo"}
        self.theme()
        expect(self.answer("problem")).to_have_attribute("data-state", "confirmed")
        expect(self.answer("problem")).to_contain_text("Texto antigo")

    # -- suggesting --------------------------------------------------------------------------------------------------------
    def test_a_suggestion_is_stored_as_suggested_with_its_sources_and_missing_ones_say_what_is_missing(self):
        self.theme()
        self.sign()
        self.suggest()
        expect(self.box().get_by_role("status")).to_have_text("Sugestão pronta: revise e confirme.")
        self.assertEqual(self.db.suggest_calls, [{"theme": "PHZ-0001", "by": "Ana"}])
        expect(self.answer("problem")).to_have_attribute("data-state", "suggested")
        expect(self.answer("problem")).to_contain_text("O merchant integra três APIs")
        expect(self.answer("problem")).to_contain_text("Sugerida pela IA, ainda não confirmada")
        self.answer("problem").locator("summary").click()
        expect(self.answer("problem").locator("[data-source]")).to_have_text("RFC — 1. Contexto — “integrar três APIs diferentes”")
        expect(self.answer("solution")).to_have_attribute("data-state", "missing")
        expect(self.answer("solution").locator('[data-k="missing"]')).to_have_text("Ainda não explicado: A RFC não descreve a solução.")
        t = self.db.themes["PHZ-0001"]
        self.assertEqual((t["problem"], t["solution"]), ({"pt": "O merchant integra três APIs para enviar uma mensagem."}, {}))
        self.assertEqual(t["answers"]["problem"]["state"], "suggested")
        self.assertEqual([e["new_value"] for e in self.db.events if e["field"] == "answers_suggested"], [["problem", "solution", "success"]])

    def test_a_suggestion_needs_a_name(self):
        self.theme()
        self.suggest()
        expect(self.box().get_by_role("status")).to_have_text("Informe seu nome para salvar.")
        self.assertEqual(self.db.suggest_calls, [])

    def test_a_suggestion_never_replaces_a_confirmed_answer_or_a_text_a_person_wrote(self):
        t = self.db.themes["PHZ-0001"]
        t["problem"] = {"pt": "Escrito por pessoa"}                                               # no state: counts as confirmed
        t["success"] = {"pt": "Confirmado"}
        t["answers"]["success"] = {"state": "confirmed", "by": "Bo", "at": "2026-11-20T10:00:00+00:00", "sources": []}
        self.theme()
        self.sign()
        self.suggest()
        expect(self.answer("solution")).to_have_attribute("data-state", "missing")
        self.assertEqual((t["problem"], t["success"]), ({"pt": "Escrito por pessoa"}, {"pt": "Confirmado"}))
        expect(self.answer("problem")).to_contain_text("Escrito por pessoa")
        expect(self.answer("success")).to_have_attribute("data-state", "confirmed")
        expect(self.answer("success")).to_contain_text("Confirmada por Bo")

    def test_a_new_suggestion_replaces_an_earlier_unconfirmed_one(self):
        self.theme()
        self.sign()
        self.suggest()
        expect(self.answer("problem")).to_have_attribute("data-state", "suggested")
        self.db.suggest_response = {"suggestions": {"problem": {"text": "Outra versão.", "sources": [{"label": "Nota — X", "quote": "outra versão do texto"}], "missing": None},
                                                    "solution": {"text": None, "sources": [], "missing": "x"}, "success": {"text": None, "sources": [], "missing": "y"}}, "sources": []}
        self.suggest()
        expect(self.answer("problem")).to_contain_text("Outra versão.")
        self.assertEqual(self.db.themes["PHZ-0001"]["problem"], {"pt": "Outra versão."})

    def test_machine_translations_of_an_old_suggestion_are_dropped_with_it(self):
        self.theme()
        self.sign()
        self.suggest()
        expect(self.answer("problem")).to_have_attribute("data-state", "suggested")
        self.db.machine_translate("PHZ-0001", "problem", "en", "The merchant integrates three APIs.")
        self.db.suggest_response = {"suggestions": {"problem": {"text": "Nova.", "sources": [{"label": "Nota — X", "quote": "nova versão aqui"}], "missing": None}}, "sources": []}
        self.suggest()
        expect(self.answer("problem")).to_contain_text("Nova.")
        t = self.db.themes["PHZ-0001"]
        self.assertEqual((t["problem"], t["text_meta"].get("problem")), ({"pt": "Nova."}, None))

    def test_the_ai_failing_or_the_limit_shows_a_message_and_changes_nothing(self):
        self.theme()
        self.sign()
        self.db.suggest_status = 502
        self.suggest()
        expect(self.box().get_by_role("status")).to_have_text("A IA não respondeu agora. Tente de novo em instantes.")
        self.db.suggest_status = 429
        self.suggest()
        expect(self.box().get_by_role("status")).to_have_text("Muitas sugestões seguidas. Espere um pouco.")
        self.assertEqual(self.db.themes["PHZ-0001"]["answers"], {})

    # -- confirming ---------------------------------------------------------------------------------------------------------
    def test_confirming_a_suggestion_keeps_its_sources_and_records_who_and_when(self):
        self.theme()
        self.sign()
        self.suggest()
        self.sign("Bo")
        self.answer("problem").get_by_role("button", name="Confirmar").click()
        expect(self.answer("problem")).to_have_attribute("data-state", "confirmed")
        a = self.db.themes["PHZ-0001"]["answers"]["problem"]
        self.assertEqual((a["state"], a["by"], len(a["sources"])), ("confirmed", "Bo", 1))
        expect(self.answer("problem")).to_contain_text("Confirmada por Bo")
        expect(self.answer("problem").get_by_role("button", name="Confirmar")).to_have_count(0)

    def test_editing_the_text_in_the_form_confirms_it(self):
        self.theme()
        self.sign()
        self.suggest()
        expect(self.answer("problem")).to_have_attribute("data-state", "suggested")
        self.page.get_by_role("form", name="theme").get_by_label("Que problema estamos tratando com este tema?").fill("Problema corrigido por Ana")
        self.page.get_by_role("form", name="theme").get_by_role("button", name="Salvar").click()
        expect(self.answer("problem")).to_have_attribute("data-state", "confirmed")
        self.assertEqual(self.db.themes["PHZ-0001"]["answers"]["problem"]["by"], "Ana")
        self.assertEqual(len(self.db.themes["PHZ-0001"]["answers"]["problem"]["sources"]), 1)      # the citation of the suggestion stays

    def test_emptying_a_text_takes_it_out_of_the_states(self):
        self.db.themes["PHZ-0001"]["problem"] = {"pt": "x"}
        self.theme()
        self.sign()
        self.page.get_by_role("form", name="theme").get_by_label("Que problema estamos tratando com este tema?").fill("")
        self.page.get_by_role("form", name="theme").get_by_role("button", name="Salvar").click()
        expect(self.answer("problem")).to_have_attribute("data-state", "empty")

    def test_reader_mode_shows_the_states_without_controls(self):
        self.theme()
        self.sign()
        self.suggest()
        expect(self.answer("problem")).to_have_attribute("data-state", "suggested")
        self.theme("?mode=reader")
        expect(self.answer("problem")).to_contain_text("Sugerida pela IA")
        expect(self.box().get_by_role("button")).to_have_count(0)

    def test_the_history_records_the_ai_suggestion_and_the_confirmation(self):
        self.theme()
        self.sign()
        self.suggest()
        expect(self.answer("problem")).to_have_attribute("data-state", "suggested")
        self.answer("problem").get_by_role("button", name="Confirmar").click()
        expect(self.answer("problem")).to_have_attribute("data-state", "confirmed")
        self.page.reload()
        expect(self.page.locator(".history")).to_contain_text("respostas sugeridas pela IA")
        expect(self.page.locator(".history")).to_contain_text("resposta confirmada")


if __name__ == "__main__":
    unittest.main()
