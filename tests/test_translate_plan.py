"""supabase/functions/translate-comment/themes.ts: what the translation webhook does when a theme changes. The module is pure, so Node runs it."""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def plan(old, rec, table="themes"):
    code = ("import { translationPlan, TABLE_FIELDS } from './supabase/functions/translate-comment/themes.ts';"
            "const [o, r, t] = JSON.parse(process.argv[1]); console.log(JSON.stringify(translationPlan(o, r, TABLE_FIELDS[t])));")
    out = subprocess.run(["node", "--input-type=module", "-e", code, json.dumps([old, rec, table])], cwd=ROOT, capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


@unittest.skipUnless(shutil.which("node"), "node is not installed")
class TranslationPlan(unittest.TestCase):
    def test_a_text_typed_in_one_language_is_translated_into_the_empty_ones(self):
        jobs = plan({"progress": {}}, {"progress": {"pt": "Contrato fechado"}, "text_meta": {}})
        self.assertEqual(jobs, [{"field": "progress", "src": "pt", "text": "Contrato fechado", "targets": ["en", "zh"]}])

    def test_a_new_theme_title_is_translated(self):
        jobs = plan(None, {"title": {"en": "Game Center"}, "text_meta": {}})
        self.assertEqual(jobs[0]["targets"], ["pt", "zh"])

    def test_what_a_person_typed_is_never_overwritten(self):
        jobs = plan({"progress": {"pt": "A", "en": "B"}}, {"progress": {"pt": "A2", "en": "B"}, "text_meta": {}})
        self.assertEqual(jobs, [{"field": "progress", "src": "pt", "text": "A2", "targets": ["zh"]}])        # en was typed by a person: kept

    def test_machine_translations_follow_the_source_when_it_changes(self):
        rec = {"progress": {"pt": "Novo texto", "en": "Old", "zh": "旧"}, "text_meta": {"progress": ["en", "zh"]}}
        jobs = plan({"progress": {"pt": "Texto", "en": "Old", "zh": "旧"}}, rec)
        self.assertEqual(jobs[0]["targets"], ["en", "zh"])

    def test_the_functions_own_write_triggers_nothing(self):
        before = {"progress": {"pt": "Texto"}}
        after = {"progress": {"pt": "Texto", "en": "Text", "zh": "文本"}, "text_meta": {"progress": ["en", "zh"]}}
        self.assertEqual(plan(before, after), [])

    def test_correcting_a_machine_translation_makes_it_a_source(self):
        # a person fixed the English: it is no longer machine (update_theme removed it from text_meta), so the Chinese follows it
        rec = {"progress": {"pt": "Texto", "en": "Corrected", "zh": "文本"}, "text_meta": {"progress": ["zh"]}}
        jobs = plan({"progress": {"pt": "Texto", "en": "Text", "zh": "文本"}}, rec)
        self.assertEqual(jobs, [{"field": "progress", "src": "en", "text": "Corrected", "targets": ["zh"]}])

    def test_weekly_updates_blockers_and_decisions_are_translated_too(self):
        jobs = plan(None, {"progress": {"pt": "Vai bem"}, "advanced": {"pt": "Contrato"}, "next_step": {}, "text_meta": {}}, "theme_updates")
        self.assertEqual([(j["field"], j["targets"]) for j in jobs], [("progress", ["en", "zh"]), ("advanced", ["en", "zh"])])
        jobs = plan({"what": {"pt": "Bloqueio"}, "how_resolved": {}}, {"what": {"pt": "Bloqueio"}, "how_resolved": {"en": "Fixed"}, "text_meta": {}}, "theme_blockers")
        self.assertEqual(jobs, [{"field": "how_resolved", "src": "en", "text": "Fixed", "targets": ["pt", "zh"]}])
        jobs = plan(None, {"what": {"zh": "决定什么"}, "decision": {}, "text_meta": {}}, "theme_decisions")
        self.assertEqual(jobs[0]["targets"], ["pt", "en"])
        self.assertEqual(plan(None, {"what": {"pt": "x"}, "text_meta": {}}, "themes"), [])       # `what` is not a field of themes

    def test_clearing_a_text_or_changing_other_fields_translates_nothing(self):
        self.assertEqual(plan({"progress": {"pt": "A"}}, {"progress": {"pt": ""}, "text_meta": {}}), [])
        self.assertEqual(plan({"status": "a", "progress": {"pt": "A"}}, {"status": "b", "progress": {"pt": "A"}, "text_meta": {}}), [])


if __name__ == "__main__":
    unittest.main()
