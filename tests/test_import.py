"""The RFCs that came from the repository (PHZ-0001, PHZ-0002), as the importer left them in the database (tests/fixtures/imported/):
the pages show their galleries, screens and pictures, they pass the checks of the new-RFC page, and a new version follows their numbering."""
import re
import sys
import unittest
from pathlib import Path

from playwright.sync_api import expect

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import SiteCase, import_rfc, imported  # noqa: E402


class ImportedPages(SiteCase):
    def test_the_revision_keeps_the_number_reviewers_and_date_of_the_repository(self):
        rev = imported("PHZ-0001")[0]
        self.assertEqual((rev["rev"], rev["version"]), (8, "1.7"))          # the next version made on the site followed from 1.8
        self.assertEqual(rev["meta"]["reviewers"][0], {"name": "Pedro Bettani", "country": "BR"})
        self.assertEqual(rev["meta"]["created"], "2026-10-15")
        self.assertEqual(len(rev["assets"]), 138)


    def test_the_big_rfc_shows_its_galleries_and_screens_from_the_database(self):
        import_rfc(self.db, "PHZ-0001")
        self.page.goto(self.base + "/rfc/?id=PHZ-0001")
        self.page.wait_for_selector(".lang.active h2")
        self.assertGreater(self.page.locator(".lang.active .shots .shot").count(), 10)
        self.assertGreater(self.page.locator(".lang.active .screens .screen").count(), 5)
        self.assertGreaterEqual(self.page.locator(".lang.active .eps .ep").count(), 3)
        self.page.locator(".lang.active .shots img").first.scroll_into_view_if_needed()
        self.page.wait_for_function("document.querySelector('.lang.active .shots img').src.startsWith('blob:')")
        header = self.page.locator(".lang.active .hero").inner_text()
        self.assertIn("Pedro Bettani (Brasil)", header)
        self.assertIn("2026-10-15".split("-")[2], header)                    # the original date, not the day it was imported
        expect(self.page.locator(".rfcno.ver")).to_have_text("v1.7")

    def test_the_big_rfc_passes_the_checks_of_the_new_rfc_page(self):
        import_rfc(self.db, "PHZ-0001")
        self.page.goto(self.base + "/nova/?edit=PHZ-0001")
        expect(self.page.locator("#result .ok")).to_be_visible()
        expect(self.page.locator("#assets li")).to_have_count(138)

    def test_a_new_version_of_an_imported_rfc_is_the_next_number(self):
        import_rfc(self.db, "PHZ-0002")
        self.page.goto(self.base + "/nova/?edit=PHZ-0002")
        expect(self.page.locator("#result .ok")).to_be_visible()
        self.page.locator("#by").fill("Eli")
        self.page.locator("#publish").click()
        self.page.wait_for_url(re.compile(r"/rfc/\?id=PHZ-0002"))
        self.assertEqual(self.db.revisions[-1]["version"], "1.2")
        self.assertEqual(self.db.revisions[-1]["meta"]["reviewers"][0]["name"], "Pedro Bettani")      # reviewers are kept in the file


if __name__ == "__main__":
    unittest.main()
