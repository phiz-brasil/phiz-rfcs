"""templates/bundle/RFC.md (the single-file template) is the three repository templates side by side; they must not drift apart."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def strip_comments(text):
    return re.sub(r"<!--.*?-->\s*", "", text, flags=re.S).strip()


class TemplateSync(unittest.TestCase):
    def test_bundle_template_matches_the_repository_templates(self):
        bundle = (ROOT / "templates" / "bundle" / "RFC.md").read_text(encoding="utf-8")
        parts = re.split(r"^<!-- lang:(pt|en|zh) -->$", bundle, flags=re.M)
        sections = dict(zip(parts[1::2], parts[2::2]))
        self.assertEqual(sorted(sections), ["en", "pt", "zh"])
        for lang, text in sections.items():
            repo = (ROOT / "templates" / "rfc" / f"rfc.{lang}.md").read_text(encoding="utf-8")
            self.assertEqual(strip_comments(text), strip_comments(repo), f"{lang}: regenerate templates/bundle/RFC.md from templates/rfc")


if __name__ == "__main__":
    unittest.main()
