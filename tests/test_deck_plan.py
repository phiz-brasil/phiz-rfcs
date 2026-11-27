"""Describe the material (docs/spec/v2/redesign.md, What PR 3 delivers): the deck plan the model answers is cleaned before it is shown
(apps/web/lib/deck-plan.ts) and the Edge Function plan-deck builds its prompt from the active themes only (supabase/functions/plan-deck/plan.ts).
Pure, so Node runs them. The point: nothing on a slide comes without a theme it can be traced to."""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(module, expr, data):
    code = (f"import * as M from './{module}'; import {{ readFileSync }} from 'node:fs';"
            f"const D = JSON.parse(readFileSync(0, 'utf8')); console.log(JSON.stringify({expr}));")
    out = subprocess.run(["node", "--input-type=module", "-e", code], input=json.dumps(data), cwd=ROOT, capture_output=True, text=True)
    if out.returncode:
        raise AssertionError(out.stderr)
    return json.loads(out.stdout)


def clean(plan, known=("PHZ-0001", "PHZ-0002")):
    return run("apps/web/lib/deck-plan.ts", "M.cleanPlan(D.plan, D.known)", {"plan": plan, "known": list(known)})


@unittest.skipUnless(shutil.which("node"), "node is not installed")
class CleanPlanTest(unittest.TestCase):
    def test_a_sentence_without_a_known_theme_is_dropped_and_counted(self):
        r = clean({"title": "Payments", "slides": [{"kind": "decisions", "title": "Decidir", "items": [
            {"theme": "PHZ-0001", "text": "Escolher o parceiro"}, {"theme": "PHZ-0999", "text": "Inventado"}, {"text": "Sem tema"}]}]})
        self.assertEqual(r["plan"]["slides"], [{"kind": "decisions", "title": "Decidir", "items": [{"theme": "PHZ-0001", "text": "Escolher o parceiro"}]}])
        self.assertEqual(r["dropped"], 2)

    def test_unknown_kinds_and_unknown_or_closed_themes_are_dropped_and_empty_slides_go(self):
        r = clean({"slides": [{"kind": "chart", "title": "x"}, {"kind": "theme", "theme": "PHZ-0003"}, {"kind": "theme", "theme": "phz-0002"},
                              {"kind": "roadmap", "title": "R", "themes": ["PHZ-0009"]}, {"kind": "numbers", "title": "N", "themes": ["PHZ-0001", "PHZ-0001", "PHZ-0002"]},
                              {"kind": "dates", "title": "D", "items": []}]})
        self.assertEqual(r["plan"]["slides"], [{"kind": "theme", "theme": "PHZ-0002"}, {"kind": "numbers", "title": "N", "themes": ["PHZ-0001", "PHZ-0002"]}])
        self.assertEqual(r["dropped"], 0)

    def test_the_cover_stays_and_takes_the_plan_title_when_it_has_none(self):
        r = clean({"title": "Status de Payments", "slides": [{"kind": "cover", "subtitle": "Para o Gustavo"}]})
        self.assertEqual(r["plan"], {"title": "Status de Payments", "slides": [{"kind": "cover", "title": "Status de Payments", "subtitle": "Para o Gustavo"}]})

    def test_texts_are_trimmed_and_the_slides_capped(self):
        r = clean({"title": "T" * 300, "slides": [{"kind": "dates", "title": "  Próximas \n datas ", "items": [{"theme": "PHZ-0001", "text": "x" * 400}]}] +
                   [{"kind": "theme", "theme": "PHZ-0001"}] * 40})
        self.assertEqual(len(r["plan"]["title"]), 120)
        self.assertEqual(r["plan"]["slides"][0]["title"], "Próximas datas")
        self.assertEqual(len(r["plan"]["slides"][0]["items"][0]["text"]), 280)
        self.assertEqual(len(r["plan"]["slides"]), 30)

    def test_anything_that_is_not_a_plan_gives_an_empty_one(self):
        for raw in (None, "texto", [1, 2], {"slides": "x"}):
            self.assertEqual(clean(raw), {"plan": {"title": "", "slides": []}, "dropped": 0})

    def test_the_themes_the_plan_needs_in_the_order_they_appear(self):
        plan = {"title": "", "slides": [{"kind": "dates", "title": "", "items": [{"theme": "PHZ-0002", "text": "a"}]}, {"kind": "theme", "theme": "PHZ-0001"},
                                        {"kind": "roadmap", "title": "", "themes": ["PHZ-0002", "PHZ-0003"]}, {"kind": "cover", "title": "c", "subtitle": ""}]}
        self.assertEqual(run("apps/web/lib/deck-plan.ts", "M.planThemeIds(D)", plan), ["PHZ-0002", "PHZ-0001", "PHZ-0003"])


CONTEXT = {
    "themes": [{"id": "PHZ-0001", "front": "payments", "title": {"pt": "Checkout global", "en": "Global checkout"}, "what_it_is": {"pt": "Um checkout"},
                "progress": {}, "status": "at_risk", "start_date": "2026-10-01", "due_date": "2026-12-15", "owner": "Luciana"}],
    "blockers": [{"theme_id": "PHZ-0001", "what": {"pt": "Contrato sem assinatura"}, "urgency": "urgent", "due_date": "2026-12-01"}],
    "decisions": [{"theme_id": "PHZ-0001", "what": {"pt": "Qual adquirente?"}, "urgency": "important", "due_date": None}],
    "milestones": [{"theme_id": "PHZ-0001", "title": "Go-live", "due_date": "2026-12-10"}],
}


@unittest.skipUnless(shutil.which("node"), "node is not installed")
class PlanDeckPromptTest(unittest.TestCase):
    MOD = "supabase/functions/plan-deck/plan.ts"

    def test_the_prompt_carries_the_request_and_each_theme_with_its_open_items(self):
        p = run(self.MOD, "M.buildPrompt(D.r, 'pt', D.c)", {"r": "Status de Payments para o Gustavo", "c": CONTEXT})
        self.assertIn("Request: Status de Payments para o Gustavo", p["user"])
        for want in ("[PHZ-0001] Checkout global", "status at_risk", "estimate 2026-12-15", "blocker (urgent, by 2026-12-01): Contrato sem assinatura",
                     "decision needed (important): Qual adquirente?", "milestone: Go-live on 2026-12-10", "what it is: Um checkout"):
            self.assertIn(want, p["user"])
        self.assertIn("never invent", p["system"])
        self.assertIn("Brazilian Portuguese", p["system"])

    def test_the_theme_texts_follow_the_language_of_the_deck(self):
        p = run(self.MOD, "M.buildPrompt('x', 'en', D)", CONTEXT)
        self.assertIn("[PHZ-0001] Global checkout", p["user"])
        self.assertIn("English", p["system"])

    def test_a_long_request_is_cut(self):
        p = run(self.MOD, "M.buildPrompt(D.r, 'pt', D.c)", {"r": "a" * 900, "c": CONTEXT})
        self.assertIn("Request: " + "a" * 600 + "\n", p["user"])
        self.assertNotIn("a" * 601, p["user"])

    def test_the_answer_of_the_model_is_read_with_or_without_fences(self):
        self.assertEqual(run(self.MOD, "M.parseModelJson(D)", 'Aqui está:\n```json\n{"title": "A", "slides": []}\n```'), {"title": "A", "slides": []})
        self.assertEqual(run(self.MOD, "M.parseModelJson(D)", 'texto {"title": "B"} fim'), {"title": "B"})
        self.assertIsNone(run(self.MOD, "M.parseModelJson(D)", "sem json"))


if __name__ == "__main__":
    unittest.main()
