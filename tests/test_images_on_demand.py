"""Phase 10 (docs/spec/v2/quota.md): the images of an RFC are read only when they are about to be seen, and are remembered by the browser. What the fake counts is
every read that carries the bytes of an image (`asset_reads`): that is what costs egress."""
import re
import sys
import unittest
from pathlib import Path

from playwright.sync_api import expect

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import ROOT, SiteCase, png_bytes  # noqa: E402

BUNDLE = (ROOT / "tests" / "fixtures" / "valid_bundle.md").read_text(encoding="utf-8")
META = {"title": {"pt": "Imagens sob demanda", "en": "Images on demand", "zh": "按需图片"}, "summary": {"pt": "R", "en": "S", "zh": "摘"}, "systems": []}
FILLER = "\n\n".join(f"Parágrafo de enchimento número {i} para empurrar a próxima imagem para fora da tela." for i in range(60))


def bundle(pt, en="a-en.png", zh="a-zh.png"):
    """The valid bundle with images cited in each language; `pt` is a list of names, each followed by a screen and a half of text."""
    block = "\n\n".join(f"![img {n}](asset:{n})\n\n{FILLER}" for n in pt)
    out = BUNDLE.replace("O problema em uma frase.", f"O problema em uma frase.\n\n{block}", 1)
    out = out.replace("The problem in one sentence.", f"The problem in one sentence.\n\n![img](asset:{en})", 1)
    return out.replace("一句话说明问题。", f"一句话说明问题。\n\n![img](asset:{zh})", 1)


class OnDemandTest(SiteCase):
    def rfc(self, pt=("a-pt.png",), **kw):
        names = list(pt) + [kw.get("en", "a-en.png"), kw.get("zh", "a-zh.png")]
        rid = self.db.seed_rfc(bundle(list(pt), **kw), META, images={n: png_bytes(2, 2, (i * 40 % 255, 60, 90)) for i, n in enumerate(names)})
        return rid

    def reads(self):
        return [name for _, name, _ in self.db.asset_reads]

    def shown(self):
        self.page.wait_for_function("() => [...document.querySelectorAll('.lang.active img[data-asset]')].some(i => i.complete && i.naturalWidth > 0)")

    def test_only_the_images_of_the_language_on_screen_are_read_until_another_is_chosen(self):
        rid = self.rfc()
        self.page.goto(self.base + f"/rfc/?id={rid}")
        self.shown()
        self.assertEqual(self.reads(), ["a-pt.png"])
        self.page.click("#btn-en")
        self.page.wait_for_function("() => [...document.querySelectorAll('.lang.active img[data-asset]')].every(i => i.complete && i.naturalWidth > 0)")
        self.assertEqual(sorted(self.reads()), ["a-en.png", "a-pt.png"])
        self.page.click("#btn-zh")
        self.page.wait_for_function("() => [...document.querySelectorAll('.lang.active img[data-asset]')].every(i => i.complete && i.naturalWidth > 0)")
        self.assertEqual(sorted(self.reads()), ["a-en.png", "a-pt.png", "a-zh.png"])
        self.page.click("#btn-pt")                                                    # going back reads nothing again
        self.page.wait_for_timeout(300)
        self.assertEqual(len(self.reads()), 3)

    def test_images_below_the_screen_wait_until_the_reader_scrolls_near_them(self):
        names = [f"p{i}.png" for i in range(6)]
        rid = self.rfc(pt=names)
        self.page.goto(self.base + f"/rfc/?id={rid}")
        self.shown()
        first = len(self.reads())
        self.assertGreaterEqual(first, 1)
        self.assertLess(first, 6, "the images far below the first screen must not be read yet")
        self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        self.page.wait_for_function("() => [...document.querySelectorAll('.lang.active img[data-asset]')].every(i => i.complete && i.naturalWidth > 0)")
        self.assertEqual(sorted(self.reads()), sorted(names))
        self.assertEqual(len(self.reads()), 6, "each image is read once")

    def test_an_image_read_once_is_remembered_by_the_browser(self):
        rid = self.rfc()
        self.page.goto(self.base + f"/rfc/?id={rid}")
        self.shown()
        self.assertEqual(self.reads(), ["a-pt.png"])
        self.page.reload()
        self.shown()
        self.assertEqual(self.reads(), ["a-pt.png"], "the reload read nothing")
        self.assertEqual(self.page.locator(".lang.active img[data-asset]").evaluate("i => i.naturalWidth"), 2)

    def test_another_version_that_uses_the_same_row_reads_nothing_and_a_new_row_is_read(self):
        rid = self.rfc()
        self.db.add_revision(rid, bundle(["a-pt.png"]), META, ("Ana",))                # revision 2: same text, same image rows (rev 1)
        self.page.goto(self.base + f"/rfc/?id={rid}&v=1.1")                            # revision 2 answers with the row of rev 1
        self.shown()
        self.assertEqual(self.reads(), ["a-pt.png"])
        self.page.goto(self.base + f"/rfc/?id={rid}&v=1.0")                            # revision 1: the same row, so no new read
        self.shown()
        self.assertEqual(self.reads(), ["a-pt.png"])
        self.db.add_asset(rid, "a-pt.png", 3, png_bytes(5, 5, (1, 2, 3)))              # revision 3 replaces the picture: a new row, a new read
        self.db.add_revision(rid, bundle(["a-pt.png"]), META, ("Ana",))
        self.page.goto(self.base + f"/rfc/?id={rid}")
        self.shown()
        self.assertEqual(self.reads(), ["a-pt.png", "a-pt.png"])
        self.assertEqual(self.page.locator(".lang.active img[data-asset]").evaluate("i => i.naturalWidth"), 5)
        self.page.goto(self.base + f"/rfc/?id={rid}&v=1.0")                            # and the old version still shows its own picture, from the browser
        self.shown()
        self.assertEqual(self.page.locator(".lang.active img[data-asset]").evaluate("i => i.naturalWidth"), 2)
        self.assertEqual(len(self.reads()), 2)

    def test_without_a_working_browser_cache_every_image_is_still_shown(self):
        rid = self.rfc()
        self.page.add_init_script("Object.defineProperty(window, 'caches', { get() { throw new Error('no cache here'); } })")
        self.page.goto(self.base + f"/rfc/?id={rid}")
        self.shown()
        self.assertEqual(self.page.locator(".lang.active img[data-asset]").evaluate("i => i.naturalWidth"), 2)
        self.page.reload()
        self.shown()
        self.assertEqual(self.reads(), ["a-pt.png", "a-pt.png"])                       # nothing remembered, but nothing broken

    def test_a_missing_image_is_marked_without_reading_any_bytes_and_a_click_opens_a_found_one(self):
        rid = self.db.seed_rfc(bundle(["ghost.png"]), META, images={"a-en.png": png_bytes(), "a-zh.png": png_bytes()})
        self.page.goto(self.base + f"/rfc/?id={rid}")
        self.page.wait_for_selector(".lang.active img.missing")
        self.assertEqual(self.reads(), [])
        rid2 = self.rfc()
        self.page.goto(self.base + f"/rfc/?id={rid2}")
        self.shown()
        with self.context.expect_page() as popup:
            self.page.locator(".lang.active img[data-asset]").click()
        popup.value.wait_for_url(re.compile(r"^blob:"))

    def test_printing_reads_the_images_of_the_language_on_screen_that_were_not_read_yet(self):
        names = [f"p{i}.png" for i in range(6)]
        rid = self.rfc(pt=names)
        self.page.goto(self.base + f"/rfc/?id={rid}")
        self.shown()
        self.assertLess(len(self.reads()), 6)
        self.page.evaluate("window.dispatchEvent(new Event('beforeprint'))")
        self.page.wait_for_function("() => [...document.querySelectorAll('.lang.active img[data-asset]')].every(i => i.complete && i.naturalWidth > 0)")
        self.assertEqual(sorted(self.reads()), sorted(names))                           # all of pt, none of en and zh
        self.assertEqual(len(self.reads()), 6)

    def test_the_list_of_images_is_read_once_per_page_and_carries_no_bytes(self):
        rid = self.rfc(pt=["p0.png", "p1.png"])
        sizes = []
        self.page.on("response", lambda r: sizes.append(len(r.body())) if "rfc_assets" in r.url and "select=name" in r.url else None)
        self.page.goto(self.base + f"/rfc/?id={rid}")
        self.shown()
        self.page.wait_for_timeout(300)
        self.assertEqual(len(sizes), 1)
        self.assertLess(sizes[0], 2000)


if __name__ == "__main__":
    unittest.main()
