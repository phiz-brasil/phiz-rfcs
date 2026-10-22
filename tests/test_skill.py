"""The skill people download from the new-RFC page: its zip, the text to copy, and the box on the page."""
import io
import re
import sys
import unittest
import zipfile
from pathlib import Path

from playwright.sync_api import expect

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import ROOT, SiteCase  # noqa: E402


class SkillDownload(SiteCase):
    def zip(self):
        data = self.page.request.get(self.base + "/assets/skill/phiz-rfc.zip").body()
        return zipfile.ZipFile(io.BytesIO(data))

    def test_the_zip_is_a_self_contained_skill(self):
        z = self.zip()
        names = set(z.namelist())
        self.assertEqual(names, {"phiz-rfc/SKILL.md", "phiz-rfc/assets/RFC.md", "phiz-rfc/references/structure.md",
                                 "phiz-rfc/references/markdown.md", "phiz-rfc/references/mermaid.md"})
        skill = z.read("phiz-rfc/SKILL.md").decode("utf-8")
        self.assertRegex(skill, r"(?s)^---\nname: phiz-rfc\ndescription: .+?\n---\n")
        self.assertEqual(z.read("phiz-rfc/assets/RFC.md").decode("utf-8"), (ROOT / "templates" / "bundle" / "RFC.md").read_text(encoding="utf-8"))
        # everything the skill points to is in the zip, and nothing points at repository-only files
        for ref in re.findall(r"`((?:references|assets)/[A-Za-z.]+)`", skill):
            self.assertIn(f"phiz-rfc/{ref}", names, ref)
        for text in [skill] + [z.read(n).decode("utf-8") for n in names if n.endswith(".md")]:
            self.assertNotIn("new_rfc.py", text)
            self.assertNotIn("~/Projetos", text)
        self.assertNotIn("rfc.json (repository", z.read("phiz-rfc/references/structure.md").decode("utf-8"))

    def test_the_zip_is_the_same_every_build(self):
        a = self.page.request.get(self.base + "/assets/skill/phiz-rfc.zip").body()
        self.assertEqual(zipfile.ZipFile(io.BytesIO(a)).testzip(), None)
        info = zipfile.ZipFile(io.BytesIO(a)).infolist()[0]
        self.assertEqual(info.date_time, (2026, 1, 1, 0, 0, 0))

    def test_the_text_to_copy_has_the_skill_and_the_template(self):
        text = self.page.request.get(self.base + "/assets/skill/phiz-rfc-skill.md").text()
        self.assertTrue(text.startswith("---\nname: phiz-rfc"))
        for part in ("# File: references/markdown.md", "# File: references/mermaid.md", "# File: assets/RFC.md", "<!-- lang:zh -->"):
            self.assertIn(part, text)

    def test_the_page_offers_both(self):
        self.context.grant_permissions(["clipboard-read", "clipboard-write"], origin=self.base)
        page = self.page
        page.goto(self.base + "/nova/")
        page.locator("#skillbox summary").click()
        self.assertEqual(page.locator("#dl-skill").get_attribute("href"), "../assets/skill/phiz-rfc.zip")
        expect(page.locator("#skillbox")).to_contain_text("Claude Code")
        page.locator("#copy-skill").click()
        expect(page.locator("#skill-copied")).to_have_text("Copiado.")
        copied = page.evaluate("navigator.clipboard.readText()")
        self.assertTrue(copied.startswith("---\nname: phiz-rfc"))
        self.assertIn("# File: assets/RFC.md", copied)


if __name__ == "__main__":
    unittest.main()
