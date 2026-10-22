"""Images and diagrams attached to an RFC created on the site: attaching, the checks, the preview, publishing (staged, then created
together with the RFC), reading them back, and editing. Supabase is tests/fake_supabase.py."""
import re
import sys
import unittest
from pathlib import Path

from playwright.sync_api import expect

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import ROOT, SiteCase, png_bytes  # noqa: E402

BUNDLE = (ROOT / "tests" / "fixtures" / "valid_bundle.md").read_text(encoding="utf-8")
META = {"title": {"pt": "Integração de teste", "en": "Test integration", "zh": "测试集成"},
        "summary": {"pt": "Resumo", "en": "Summary", "zh": "摘要"}, "systems": []}


def with_image(name="diagram.png"):
    out = BUNDLE.replace("O problema em uma frase.", f"O problema em uma frase.\n\n![Arquitetura](asset:{name})", 1)
    out = out.replace("The problem in one sentence.", f"The problem in one sentence.\n\n![Architecture](asset:{name})", 1)
    return out.replace("一句话说明问题。", f"一句话说明问题。\n\n![架构](asset:{name})", 1)


def file(name="diagram.png", data=None, mime="image/png"):
    return {"name": name, "mimeType": mime, "buffer": data or png_bytes(3, 3)}


class ImagesTest(SiteCase):
    def nova(self, edit=None):
        self.page.goto(self.base + "/nova/" + (f"?edit={edit}" if edit else ""))
        return self.page

    def attach(self, *files):
        self.page.locator("#imgs").set_input_files(list(files))

    def images_loaded(self, expected=1):
        """The images of the language on screen are loaded (the other languages' are lazy and off screen)."""
        self.page.wait_for_function(
            "(n) => { const imgs = [...document.querySelectorAll('.lang.active img[data-asset]')]; return imgs.length === n && imgs.every(i => i.complete && i.naturalWidth > 0); }",
            arg=expected)

    # -- attaching -----------------------------------------------------------
    def test_an_attached_image_gets_a_name_and_a_snippet_to_insert(self):
        page = self.nova()
        self.attach(file("Arquitetura Final.PNG"))
        item = page.locator("#assets li")
        expect(item).to_have_count(1)
        self.assertEqual(item.locator("input").input_value(), "arquitetura-final.png")
        expect(item.locator("code")).to_have_text("![descrição](asset:arquitetura-final.png)")
        page.locator("#text").fill("## Resumo {#summary}\n\nTexto.\n")
        item.get_by_role("button", name="Inserir no texto").click()
        self.assertIn("![descrição](asset:arquitetura-final.png)", page.locator("#text").input_value())
        expect(page.locator("#imgs-note")).to_have_text("1/160")

    def test_only_png_jpeg_and_webp_are_accepted(self):
        page = self.nova()
        self.attach({"name": "anim.gif", "mimeType": "image/gif", "buffer": b"GIF89a"})
        expect(page.locator("#imgs-note")).to_contain_text("não é PNG, JPEG ou WebP")
        self.attach({"name": "d.svg", "mimeType": "image/svg+xml", "buffer": b"<svg xmlns='http://www.w3.org/2000/svg'/>"})
        expect(page.locator("#imgs-note")).to_contain_text("não é PNG, JPEG ou WebP")
        self.attach({"name": "broken.png", "mimeType": "image/png", "buffer": b"not really a png"})
        expect(page.locator("#imgs-note")).to_contain_text("Não foi possível ler")
        expect(page.locator("#assets li")).to_have_count(0)

    def test_at_most_160_images(self):
        page = self.nova()
        self.attach(*[file(f"img{i}.png") for i in range(162)])
        expect(page.locator("#assets li")).to_have_count(160)
        expect(page.locator("#imgs-note")).to_contain_text("No máximo 160")

    def test_same_file_name_twice_gets_a_distinct_name(self):
        page = self.nova()
        self.attach(file("a.png"), file("a.png"))
        expect(page.locator("#assets li")).to_have_count(2)
        names = page.locator("#assets li input").evaluate_all("els => els.map(e => e.value)")
        self.assertEqual(names, ["a.png", "a-2.png"])

    def test_a_big_image_is_reduced_in_the_browser(self):
        page = self.nova()
        result = page.evaluate("""async () => {
          const m = await import('/assets/js/images.js');
          const c = document.createElement('canvas'); c.width = 2400; c.height = 1800;
          const ctx = c.getContext('2d'); const d = ctx.createImageData(2400, 1800);
          for (let i = 0; i < d.data.length; i += 4) { d.data[i] = Math.random() * 255; d.data[i+1] = Math.random() * 255; d.data[i+2] = Math.random() * 255; d.data[i+3] = 255; }
          ctx.putImageData(d, 0, 0);
          const blob = await new Promise(r => c.toBlob(r, 'image/png'));
          const out = await m.shrinkImage(new File([blob], 'noise.png', { type: 'image/png' }));
          return { before: blob.size, after: out.blob.size, width: out.width, mime: out.mime, limit: m.MAX_BYTES };
        }""")
        self.assertGreater(result["before"], 5_000_000)
        self.assertLessEqual(result["after"], result["limit"])
        self.assertLessEqual(result["width"], 1600)

    # -- the checks ------------------------------------------------------------
    def test_a_cited_image_must_be_attached_and_an_unused_one_is_flagged(self):
        page = self.nova()
        page.locator("#text").fill(with_image("diagram.png"))
        expect(page.locator("#result .issues")).to_contain_text('uses the image "diagram.png" but it is not attached')
        self.attach(file("diagram.png"))
        expect(page.locator("#result .ok")).to_be_visible()
        self.attach(file("unused.png"))
        expect(page.locator("#result .warn")).to_contain_text("unused.png")

    def test_renaming_an_attachment_updates_the_text(self):
        page = self.nova()
        self.attach(file("diagram.png"))
        page.locator("#text").fill(with_image("diagram.png"))
        expect(page.locator("#result .ok")).to_be_visible()
        page.locator("#assets li input").fill("arch.png")
        page.locator("#assets li input").press("Enter")
        page.wait_for_function("document.getElementById('text').value.includes('asset:arch.png')")
        self.assertNotIn("asset:diagram.png", page.locator("#text").input_value())
        expect(page.locator("#result .ok")).to_be_visible()

    def test_the_preview_shows_the_attached_images(self):
        page = self.nova()
        self.attach(file("diagram.png"))
        page.locator("#text").fill(with_image())
        expect(page.locator("#result .ok")).to_be_visible()
        page.locator("#preview-toggle").click()
        img = page.frame_locator("#preview").locator("img[data-asset]")
        for _ in range(40):                                           # the frame can still be reloading: retry
            try:
                if img.evaluate("i => i.complete && i.naturalWidth > 0"):
                    break
            except Exception:
                pass
            page.wait_for_timeout(250)
        else:
            self.fail("the preview did not show the attached image")

    # -- publishing and reading --------------------------------------------------
    def test_publishing_sends_the_images_first_and_the_viewer_shows_them(self):
        page = self.nova()
        self.attach(file("diagram.png", png_bytes(3, 3)))
        page.locator("#text").fill(with_image())
        expect(page.locator("#result .ok")).to_be_visible()
        page.locator("#by").fill("Ana")
        page.locator("#publish").click()
        page.wait_for_url(re.compile(r"/rfc/\?id=PHZ-0003"))
        self.assertEqual([c[0] for c in self.db.calls], ["stage_rfc_asset", "create_rfc"])
        stage, create = self.db.calls[0][1], self.db.calls[1][1]
        self.assertEqual(stage["p_name"], "diagram.png")
        self.assertEqual(stage["p_mime"], "image/png")
        self.assertEqual(stage["p_token"], create["p_token"])
        self.assertEqual([(a["rfc_id"], a["name"], a["rev"]) for a in self.db.assets], [("PHZ-0003", "diagram.png", 1)])
        self.images_loaded()

    def test_an_unused_attachment_is_not_sent(self):
        page = self.nova()
        self.attach(file("unused.png"))
        page.locator("#text").fill(BUNDLE)
        page.locator("#by").fill("Ana")
        page.locator("#publish").click()
        page.wait_for_url(re.compile(r"/rfc/\?id=PHZ-0003"))
        self.assertEqual([c[0] for c in self.db.calls], ["create_rfc"])
        self.assertEqual(self.db.assets, [])

    def test_an_image_the_server_refuses_stops_the_publication(self):
        page = self.nova()
        # PNG headers are checked by the server: a JPEG sent as PNG is refused (here forced from the test)
        self.attach(file("diagram.png"))
        page.locator("#text").fill(with_image())
        page.locator("#by").fill("Ana")
        original = self.db.MAGIC["image/png"]
        self.db.MAGIC["image/png"] = lambda b: False
        try:
            page.locator("#publish").click()
            expect(page.locator("#publish-note")).to_contain_text("O servidor recusou")
        finally:
            self.db.MAGIC["image/png"] = original
        self.assertEqual(self.db.revisions, [])                       # nothing was created

    # -- editing and history ------------------------------------------------------
    def test_a_new_version_keeps_the_images_and_old_versions_show_theirs(self):
        rid = self.db.seed_rfc(with_image(), META, images={"diagram.png": png_bytes(2, 2, (200, 30, 30))})
        page = self.nova(edit=rid)
        expect(page.locator("#result .ok")).to_be_visible()
        expect(page.locator("#assets li")).to_have_count(1)
        expect(page.locator("#assets li .note")).to_have_text("já enviada")
        # a text-only edit reuses the stored image
        page.locator("#text").fill(page.locator("#text").input_value().replace("Another sentence.", "A changed sentence."))
        page.locator("#by").fill("Eli")
        page.locator("#publish").click()
        page.wait_for_url(re.compile(rf"/rfc/\?id={rid}"))
        self.assertEqual([c[0] for c in self.db.calls], ["add_rfc_revision"])
        self.images_loaded()
        # replace the image in a third version: the first one must keep showing the first picture
        page = self.nova(edit=rid)
        expect(page.locator("#result .ok")).to_be_visible()
        self.attach(file("diagram.png", png_bytes(5, 5, (10, 10, 200))))
        expect(page.locator("#assets li")).to_have_count(2)         # the stored name and the new attachment
        names = page.locator("#assets li input").evaluate_all("els => els.map(e => e.value)")
        self.assertEqual(names, ["diagram-2.png", "diagram.png"])    # the new file was renamed: the stored name is taken
        page.locator("#text").fill(page.locator("#text").input_value().replace("asset:diagram.png", "asset:diagram-2.png"))
        page.locator("#by").fill("Eli")
        page.locator("#publish").click()
        page.wait_for_url(re.compile(rf"/rfc/\?id={rid}"))
        self.images_loaded()
        widths = self.page.evaluate("[...document.querySelectorAll('.lang[data-lang=pt] img[data-asset]')].map(i => i.naturalWidth)")
        self.assertEqual(widths, [5])                                 # the new version shows the new picture
        self.page.goto(self.base + f"/rfc/?id={rid}&v=1.0")
        self.images_loaded()
        self.assertEqual(self.page.evaluate("[...document.querySelectorAll('.lang[data-lang=pt] img[data-asset]')].map(i => i.naturalWidth)"), [2])

    def test_a_missing_image_is_shown_as_such(self):
        rid = self.db.seed_rfc(with_image("gone.png"), META)            # the text cites an image that was never stored
        self.page.goto(self.base + f"/rfc/?id={rid}")
        self.page.wait_for_selector("img.missing")
        self.assertEqual(self.page.locator("img.missing").count(), 3)

    def test_clicking_an_image_opens_it_full_size(self):
        rid = self.db.seed_rfc(with_image(), META, images={"diagram.png": png_bytes(4, 4)})
        self.page.goto(self.base + f"/rfc/?id={rid}")
        self.images_loaded()
        with self.context.expect_page() as popup:
            self.page.locator('.lang.active img[data-asset]').click()
        self.assertTrue(popup.value.url.startswith("blob:"))


if __name__ == "__main__":
    unittest.main()
