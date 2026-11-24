"""Phase 9: the slide export. The model of a slide (apps/web/lib/slide-model.ts) is tested from Node; the page downloads a real .pptx, which is opened here as a ZIP
and read slide by slide."""
import json
import re
import shutil
import subprocess
import sys
import unittest
import zipfile
from pathlib import Path

from playwright.sync_api import expect

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import SiteCase  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def model(theme, jira, fronts, lang):
    code = ("import * as M from './apps/web/lib/slide-model.ts'; const [t, j, f, l] = JSON.parse(process.argv[1]); console.log(JSON.stringify(M.slideOf(t, j, f, l)));")
    out = subprocess.run(["node", "--input-type=module", "-e", code, json.dumps([theme, jira, fronts, lang])], cwd=ROOT, capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


FRONTS = [{"key": "payments", "name": {"pt": "Pagamentos", "en": "Payments"}}]


def theme(**extra):
    base = {"id": "PHZ-0001", "kind": "project", "front": "payments", "title": {"pt": "Checkout global", "en": "Global checkout"}, "owner": "Ana", "status": "on_track",
            "due_date": "2026-12-15", "problem": {}, "solution": {}, "success": {}, "answers": {}}
    base.update(extra)
    return base


@unittest.skipUnless(shutil.which("node"), "node is not installed")
class SlideModelTest(unittest.TestCase):
    def test_the_slide_carries_the_title_front_owner_status_estimate_and_jira_links(self):
        s = model(theme(problem={"pt": "P"}), [{"theme_id": "PHZ-0001", "url": "https://j.example/browse/PHZ-7", "issue_key": "PHZ-7", "label": None},
                                               {"theme_id": "PHZ-0002", "url": "https://j.example/browse/X-1", "issue_key": "X-1", "label": None}], FRONTS, "pt")
        self.assertEqual(s["title"], "Checkout global")
        self.assertEqual(s["meta"], [{"label": "Frente", "value": "Pagamentos"}, {"label": "Responsável", "value": "Ana"}, {"label": "Status", "value": "No prazo"},
                                     {"label": "Conclusão estimada", "value": "2026-12-15"}])
        self.assertEqual(s["jira"], [{"key": "PHZ-7", "url": "https://j.example/browse/PHZ-7"}])

    def test_the_questions_are_the_three_of_the_spec_in_the_chosen_language(self):
        en = model(theme(), [], FRONTS, "en")
        self.assertEqual([a["question"] for a in en["answers"]], ["What problem are we addressing with this theme?", "What is the proposed solution, in short?",
                                                                  "What does success look like for this theme and how will we know it was reached?"])
        zh = model(theme(), [], FRONTS, "zh")
        self.assertTrue(all(re.search(r"[一-鿿]", a["question"]) for a in zh["answers"]))

    def test_a_missing_answer_is_written_as_not_explained_yet_with_what_is_missing(self):
        s = model(theme(success={}, answers={"success": {"state": "missing", "missing": "A RFC não diz como medir."}}), [], FRONTS, "pt")
        self.assertEqual(s["answers"][2], {"question": s["answers"][2]["question"], "text": "Ainda não explicado: A RFC não diz como medir.", "missing": True, "unconfirmed": False, "note": ""})
        self.assertEqual(s["answers"][0]["text"], "Ainda não explicado")                       # no state at all: just "not explained yet"
        self.assertEqual(model(theme(), [], FRONTS, "en")["answers"][0]["text"], "Not explained yet")
        self.assertEqual(model(theme(answers={"problem": {"state": "missing", "missing": "x"}}), [], FRONTS, "zh")["answers"][0]["text"], "尚未说明：x")

    def test_an_answer_is_in_the_chosen_language_or_the_first_one_that_exists(self):
        t = theme(problem={"pt": "Problema em português", "en": "Problem in English"}, solution={"pt": "Só em português"})
        self.assertEqual([a["text"] for a in model(t, [], FRONTS, "en")["answers"][:2]], ["Problem in English", "Só em português"])
        self.assertEqual(model(t, [], FRONTS, "en")["meta"][0]["value"], "Payments")
        self.assertEqual(model(t, [], FRONTS, "zh")["meta"][0]["value"], "Pagamentos")      # the front has no Chinese name: the first language that has one

    def test_an_unconfirmed_ai_suggestion_is_marked_and_a_confirmed_one_is_not(self):
        s = model(theme(problem={"pt": "A"}, solution={"pt": "B"}, answers={"problem": {"state": "suggested"}, "solution": {"state": "confirmed"}}), [], FRONTS, "pt")
        self.assertEqual([(a["unconfirmed"], a["note"]) for a in s["answers"][:2]], [(True, "Sugestão da IA, ainda não confirmada"), (False, "")])

    def test_a_theme_with_no_owner_date_or_front_still_makes_a_slide(self):
        s = model(theme(owner=None, due_date=None, front="outros", title={}), [], FRONTS, "pt")
        self.assertEqual((s["title"], s["meta"][0]["value"], s["meta"][1]["value"], s["meta"][3]["value"]), ("PHZ-0001", "outros", "—", "—"))


def read_pptx(path):
    """The text of each slide of a .pptx, in slide order."""
    with zipfile.ZipFile(path) as z:
        names = sorted((n for n in z.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)), key=lambda n: int(re.findall(r"\d+", n)[0]))
        out = []
        for n in names:
            xml = z.read(n).decode("utf8")
            out.append(" | ".join(re.findall(r"<a:t>([^<]*)</a:t>", xml)))
        links = []
        for n in z.namelist():
            if n.startswith("ppt/slides/_rels/"):
                links += re.findall(r'Target="(https?://[^"]+)"', z.read(n).decode("utf8"))
    return out, links


def summary(slides, lang):
    code = ("import * as M from './apps/web/lib/slide-model.ts'; const [s, l] = JSON.parse(process.argv[1]); console.log(JSON.stringify(M.summaryOf(s, l)));")
    out = subprocess.run(["node", "--input-type=module", "-e", code, json.dumps([slides, lang])], cwd=ROOT, capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


@unittest.skipUnless(shutil.which("node"), "node is not installed")
class SummaryTest(unittest.TestCase):
    """docs/spec/v2/slides.md: the overview, the big number and "what is missing" are computed from the slides (pure, Node-tested)."""

    def slides(self, lang="pt"):
        full = {"pt": "Texto"}
        ok = model(theme(id="PHZ-0001", title={"pt": "A"}, status="on_track", problem=full, solution=full, success=full,
                         answers={k: {"state": "confirmed"} for k in ("problem", "solution", "success")}), [], FRONTS, lang)
        risk = model(theme(id="PHZ-0002", title={"pt": "B"}, status="at_risk", problem=full, solution={}, success=full,
                           answers={"problem": {"state": "confirmed"}, "success": {"state": "confirmed"}}), [], FRONTS, lang)
        blocked = model(theme(id="PHZ-0003", title={"pt": "C"}, status="blocked", problem=full, solution=full, success=full,
                              answers={"problem": {"state": "confirmed"}, "solution": {"state": "confirmed"}, "success": {"state": "suggested"}}), [], FRONTS, lang)
        return [ok, risk, blocked]

    def test_it_counts_the_themes_by_status_and_the_ones_at_risk_or_blocked(self):
        r = summary(self.slides(), "pt")
        self.assertEqual((r["total"], r["risky"]), (3, 2))
        self.assertEqual([(b["status"], b["count"]) for b in r["byStatus"]], [("on_track", 1), ("at_risk", 1), ("blocked", 1)])
        self.assertEqual([b["label"] for b in r["byStatus"]], ["No prazo", "Em risco", "Bloqueado"])

    def test_the_rows_carry_what_the_overview_table_shows(self):
        r = summary(self.slides(), "pt")
        self.assertEqual([x["id"] for x in r["rows"]], ["PHZ-0001", "PHZ-0002", "PHZ-0003"])
        self.assertEqual(r["rows"][1], {"id": "PHZ-0002", "title": "B", "front": "Pagamentos", "status": "at_risk", "statusLabel": "Em risco", "due": "2026-12-15", "answers": "2/3"})
        self.assertEqual(r["rows"][2]["answers"], "2/3")                                   # a suggestion nobody confirmed is not counted as an answer

    def test_what_is_missing_lists_missing_and_unconfirmed_and_skips_the_complete_theme(self):
        r = summary(self.slides(), "pt")
        self.assertEqual([g["id"] for g in r["gaps"]], ["PHZ-0002", "PHZ-0003"])
        self.assertEqual((r["gaps"][0]["missing"], r["gaps"][0]["unconfirmed"]), (["solução"], []))
        self.assertEqual((r["gaps"][1]["missing"], r["gaps"][1]["unconfirmed"]), ([], ["sucesso"]))

    def test_the_labels_exist_in_the_three_languages(self):
        for lang, word in (("pt", "O que falta"), ("en", "What is missing"), ("zh", "还缺什么")):
            r = summary(self.slides(lang), lang)
            self.assertEqual(r["labels"]["gaps"], word)
            self.assertTrue(all(r["labels"][k] for k in ("cover", "coverTitle", "overview", "risky", "gapsNone", "theme", "answers", "asOf", "themes")), lang)

    def test_nothing_missing_gives_no_gaps(self):
        r = summary(self.slides()[:1], "en")
        self.assertEqual((r["gaps"], r["risky"]), ([], 0))


class SlidesPageTest(SiteCase):
    def setUp(self):
        super().setUp()
        db = self.db
        db.seed_theme("PHZ-0001", "api-platform", title={"pt": "Business Messaging API", "en": "Business Messaging API"}, owner="Gleisonc", status="on_track", due_date="2026-12-15",
                      problem={"pt": "Três APIs para enviar uma mensagem."}, solution={"pt": "Uma API única."}, success={"pt": "80% migrados."},
                      answers={"problem": {"state": "confirmed"}, "solution": {"state": "suggested", "sources": []}, "success": {"state": "confirmed"}})
        db.seed_theme("PHZ-0002", "payments", title={"pt": "Migração CredPay"}, owner="Ana", problem={"pt": "Só o problema"})
        db.seed_theme("PHZ-0010", "outros", kind="task", title={"pt": "Game Center"})
        db.jira.append({"id": "j1", "theme_id": "PHZ-0001", "item_id": None, "url": "https://jira.example.com/browse/PHZ-77", "label": None, "issue_key": "PHZ-77", "created_at": "x"})

    def slides(self, query=""):
        self.page.goto(self.base + "/slides/" + query)
        expect(self.page.locator("h1")).to_have_text("Slides")
        expect(self.page.locator("li[data-theme]").first).to_be_visible()

    def export(self, tmp):
        with self.page.expect_download() as dl:
            self.page.get_by_role("button", name="Exportar .pptx").click()
        path = Path(tmp) / dl.value.suggested_filename
        dl.value.save_as(path)
        return path

    def pick(self, *ids):
        for i in ids:
            self.page.get_by_label(i, exact=True).check()

    def test_one_theme_exports_one_slide_with_the_three_answers(self):
        import tempfile
        self.slides()
        self.pick("PHZ-0001")
        with tempfile.TemporaryDirectory() as d:
            path = self.export(d)
            self.assertRegex(path.name, r"^PHIZ-slides-\d{4}-\d{2}-\d{2}\.pptx$")
            slides, links = read_pptx(path)
        self.assertEqual(len(slides), 1)
        text = slides[0]
        for want in ("Business Messaging API", "Frente: API Platform", "Responsável: Gleisonc", "Status: No prazo", "Conclusão estimada: 2026-12-15", "PHZ-77",
                     "Que problema estamos tratando com este tema?", "Três APIs para enviar uma mensagem.", "Uma API única.", "80% migrados."):
            self.assertIn(want, text)
        self.assertIn("Sugestão da IA, ainda não confirmada", text)                       # the solution was suggested and nobody confirmed it
        self.assertEqual(links, ["https://jira.example.com/browse/PHZ-77"])

    def test_many_themes_make_many_slides_in_the_order_of_the_list_and_a_missing_answer_is_written_as_such(self):
        import tempfile
        self.slides()
        self.pick("PHZ-0010", "PHZ-0002")
        with tempfile.TemporaryDirectory() as d:
            slides, _ = read_pptx(self.export(d))
        self.assertEqual(len(slides), 2)
        self.assertIn("Game Center", slides[0])                                            # the slides follow the order of the list (newest first), not the order of picking
        self.assertIn("Migração CredPay", slides[1])
        both = " ".join(slides)
        self.assertEqual(both.count("Ainda não explicado"), 5)                             # PHZ-0002 lacks solution and success, the task lacks all three

    def test_the_language_of_the_slide_is_chosen_at_export(self):
        import tempfile
        self.slides()
        self.pick("PHZ-0001")
        self.page.get_by_label("Idioma do slide").select_option(label="EN-US")
        with tempfile.TemporaryDirectory() as d:
            slides, _ = read_pptx(self.export(d))
        self.assertIn("What problem are we addressing with this theme?", slides[0])
        self.assertIn("Owner: Gleisonc", slides[0])
        self.assertIn("Status: On track", slides[0])
        self.slides()
        self.pick("PHZ-0002")
        self.page.get_by_label("Idioma do slide").select_option(label="中文")
        with tempfile.TemporaryDirectory() as d:
            slides, _ = read_pptx(self.export(d))
        self.assertIn("这个主题要解决什么问题？", slides[0])
        self.assertIn("尚未说明", slides[0])

    def test_exporting_with_nothing_picked_says_so(self):
        self.slides()
        self.page.get_by_role("button", name="Exportar .pptx").click()
        expect(self.page.get_by_role("status")).to_have_text("Escolha ao menos um tema.")

    def test_a_link_from_the_theme_page_opens_the_export_with_that_theme_picked(self):
        self.page.goto(self.base + "/themes/PHZ-0001/")
        self.page.get_by_role("link", name="Exportar .pptx").click()
        expect(self.page).to_have_url(self.base + "/slides/?theme=PHZ-0001")
        expect(self.page.get_by_label("PHZ-0001", exact=True)).to_be_checked()
        expect(self.page.get_by_role("button", name="Exportar .pptx (1)")).to_be_visible()

    def test_filters_and_select_all_shown(self):
        self.slides()
        self.page.get_by_label("Tipo").select_option(label="Tarefa avulsa")
        self.assertEqual(self.page.locator("li[data-theme]").evaluate_all("els => els.map(e => e.dataset.theme)"), ["PHZ-0010"])
        self.page.get_by_label("Tipo").select_option(label="Todos")
        self.page.get_by_label("Frente").select_option(label="Payments")
        self.page.get_by_role("button", name="Selecionar todos os exibidos").click()
        expect(self.page.get_by_role("button", name="Exportar .pptx (1)")).to_be_visible()
        self.page.get_by_role("button", name="Limpar seleção").click()
        expect(self.page.get_by_role("button", name="Exportar .pptx (0)")).to_be_visible()

    def test_the_list_shows_the_state_of_the_three_answers_of_each_theme(self):
        self.slides()
        row = self.page.locator('li[data-theme="PHZ-0001"]')
        self.assertEqual(row.locator("[data-answer]").evaluate_all("els => els.map(e => e.dataset.state)"), ["confirmed", "suggested", "confirmed"])
        self.assertEqual(self.page.locator('li[data-theme="PHZ-0010"] [data-answer]').evaluate_all("els => els.map(e => e.dataset.state)"), ["empty", "empty", "empty"])

    def test_the_header_links_to_the_slides(self):
        self.page.goto(self.base + "/themes/")
        self.page.get_by_role("button", name="Portfólio").click()                      # grouped in a menu of the top bar
        self.page.get_by_role("link", name="Slides").click()
        expect(self.page).to_have_url(self.base + "/slides/")


if __name__ == "__main__":
    unittest.main()

    def test_the_deck_with_cover_has_cover_overview_number_the_themes_and_what_is_missing(self):
        import tempfile
        self.slides()
        self.pick("PHZ-0010", "PHZ-0002", "PHZ-0001")
        self.page.get_by_label("Incluir capa e visão geral").check()
        with tempfile.TemporaryDirectory() as d:
            slides, links = read_pptx(self.export(d))
        self.assertEqual(len(slides), 3 + 3 + 1)                                            # cover, overview, the number, the themes, what is missing
        self.assertIn("PORTFÓLIO", slides[0])
        self.assertIn("Acompanhamento de temas", slides[0])
        self.assertIn("Onde estamos", slides[1])
        self.assertIn("Migração CredPay", slides[1])
        self.assertIn("3", slides[2])
        self.assertIn("temas", slides[2])
        self.assertIn("Game Center", slides[3])                                             # the themes keep the order of the list
        self.assertIn("Migração CredPay", slides[4])
        self.assertIn("Business Messaging API", slides[5])
        self.assertIn("O que falta", slides[6])
        self.assertIn("PHZ-0002", slides[6])
        self.assertEqual(links, ["https://jira.example.com/browse/PHZ-77"])

    def test_the_plain_export_has_no_cover_unless_asked(self):
        import tempfile
        self.slides()
        self.pick("PHZ-0001", "PHZ-0002")
        with tempfile.TemporaryDirectory() as d:
            slides, _ = read_pptx(self.export(d))
        self.assertEqual(len(slides), 2)
        self.assertFalse(any("PORTFÓLIO" in x or "O que falta" in x for x in slides))

    def test_the_deck_is_written_in_the_chosen_language(self):
        import tempfile
        self.slides()
        self.pick("PHZ-0001")
        self.page.get_by_label("Idioma do slide").select_option(label="EN-US")
        self.page.get_by_label("Include cover and overview" if False else "Incluir capa e visão geral").check()
        with tempfile.TemporaryDirectory() as d:
            slides, _ = read_pptx(self.export(d))
        self.assertIn("PORTFOLIO", slides[0])
        self.assertIn("What is missing", slides[-1])


class PaletteTest(unittest.TestCase):
    """docs/spec/v2/slides.md: no colour outside the table of the spec."""

    def test_every_colour_of_the_builder_is_in_the_spec_table(self):
        spec = (ROOT / "docs" / "spec" / "v2" / "slides.md").read_text(encoding="utf-8")
        allowed = set(re.findall(r"`([0-9A-F]{6})`", spec)) | {"FFFFFF"}
        used = set(re.findall(r'"([0-9A-F]{6})"', (ROOT / "apps" / "web" / "lib" / "slides.ts").read_text(encoding="utf-8")))
        self.assertTrue(used, "no colour found in slides.ts")
        self.assertEqual(sorted(used - allowed), [])
