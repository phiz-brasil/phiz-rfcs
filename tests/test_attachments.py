"""Phase 8: the attachments hub (files in private Storage, notes, links, editions) on the theme page and the cross-theme page, against tests/fake_themes.py."""
import hashlib
import os
import sys
import tempfile
import unittest
from pathlib import Path

from playwright.sync_api import expect

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import SiteCase  # noqa: E402

PNG = bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154789c6360f8cfc0f01f0005000201e221bc330000000049454e44ae426082")


class AttachmentsTest(SiteCase):
    def setUp(self):
        super().setUp()
        db = self.db
        db.seed_theme("PHZ-0001", "api-platform", title={"pt": "Business Messaging API"}, stage=4, owner="Gleison")
        db.seed_theme("PHZ-0002", "payments", title={"pt": "Migração CredPay"}, owner="Ana")

    def theme(self, tid="PHZ-0001", query=""):
        self.page.goto(self.base + f"/themes/{tid}/{query}")
        expect(self.page.locator("h1")).to_be_visible()

    def sign(self, name="Ana"):
        self.prefs()
        self.page.get_by_label("Seu nome").fill(name)
        self.page.keyboard.press("Escape")

    def box(self):
        return self.page.get_by_role("region", name="Anexos")

    def form(self):
        return self.page.get_by_role("form", name="Adicionar anexo")

    def row(self, name):
        return self.box().locator(f'tr[data-name="{name}"]')

    def add_file(self, name, data, mime, label=None):
        self.form().locator('input[type=file]').set_input_files(files=[{"name": name, "mimeType": mime, "buffer": data}])
        if label:
            self.form().get_by_label("Nome").fill(label)
        self.form().get_by_role("button", name="Anexar").click()

    # -- adding ----------------------------------------------------------------------------------------------
    def test_a_theme_with_no_attachments_says_so(self):
        self.theme()
        expect(self.box()).to_contain_text("Nenhum anexo ainda.")

    def test_a_file_goes_to_storage_and_the_row_keeps_the_real_size_type_and_checksum(self):
        self.theme()
        self.sign()
        self.add_file("Relatório final (v2).pdf", b"%PDF-1.4 conteudo", "application/pdf")
        expect(self.form().get_by_role("status")).to_have_text("Anexo adicionado.")
        (path, obj), = self.db.storage.items()
        self.assertRegex(path, r"^PHZ-0001/[0-9a-f-]{36}/Relatorio_final_v2_\.pdf$")
        self.assertEqual((obj["size"], obj["mimetype"]), (17, "application/pdf"))
        row = self.db.attachments[0]
        self.assertEqual((row["kind"], row["name"], row["storage_path"], row["size"], row["content_type"], row["created_by"]),
                         ("file", "Relatório final (v2).pdf", path, 17, "application/pdf", "Ana"))
        self.assertEqual(row["checksum"], hashlib.sha256(b"%PDF-1.4 conteudo").hexdigest())
        expect(self.row("Relatório final (v2).pdf")).to_contain_text("17 B")
        expect(self.row("Relatório final (v2).pdf")).to_contain_text("Ana")
        self.assertTrue([e for e in self.db.events if e["field"] == "attachment_added"])

    def test_the_name_defaults_to_the_file_name_and_can_be_changed(self):
        self.theme()
        self.sign()
        self.add_file("a.txt", b"x", "text/plain", label="Ata da reunião")
        expect(self.row("Ata da reunião")).to_be_visible()
        self.add_file("b.txt", b"yy", "text/plain")
        expect(self.row("b.txt")).to_be_visible()

    def test_a_note_is_stored_as_markdown_and_read_in_the_page(self):
        self.theme()
        self.sign()
        self.form().get_by_label("Tipo de anexo").select_option(label="Nota")
        self.form().get_by_label("Nome").fill("Decisões da reunião")
        self.form().get_by_label("Nota (Markdown)").fill("# Reunião\n\n- Aprovado o escopo")
        self.form().get_by_role("button", name="Anexar").click()
        expect(self.row("Decisões da reunião")).to_be_visible()
        self.assertEqual(self.db.attachments[0]["body"], "# Reunião\n\n- Aprovado o escopo")
        self.row("Decisões da reunião").get_by_role("button", name="Abrir").click()
        expect(self.box().locator("pre.notebody")).to_have_text("# Reunião\n\n- Aprovado o escopo")

    def test_a_link_is_listed_and_opens_in_another_tab(self):
        self.theme()
        self.sign()
        self.form().get_by_label("Tipo de anexo").select_option(label="Link")
        self.form().get_by_label("Nome").fill("Protótipo no Figma")
        self.form().get_by_label("Endereço (https)").fill("https://www.figma.com/file/abc")
        self.form().get_by_role("button", name="Anexar").click()
        expect(self.row("Protótipo no Figma")).to_be_visible()
        self.context.route("https://www.figma.com/**", lambda r: r.fulfill(status=200, content_type="text/html", body="figma"))
        with self.context.expect_page() as popup:
            self.row("Protótipo no Figma").get_by_role("button", name="Abrir").click()
        popup.value.wait_for_load_state()
        self.assertEqual(popup.value.url, "https://www.figma.com/file/abc")

    def test_a_link_that_is_not_https_is_refused(self):
        self.theme()
        self.sign()
        self.form().get_by_label("Tipo de anexo").select_option(label="Link")
        self.form().get_by_label("Nome").fill("Inseguro")
        self.form().get_by_label("Endereço (https)").fill("http://example.com/x")
        self.form().get_by_role("button", name="Anexar").click()
        expect(self.form().get_by_role("status")).to_have_text("Não foi possível salvar.")
        self.assertEqual(self.db.attachments, [])

    def test_a_name_and_a_file_are_needed(self):
        self.theme()
        self.form().get_by_role("button", name="Anexar").click()
        expect(self.form().get_by_role("status")).to_have_text("Informe seu nome para salvar.")
        self.sign()
        self.form().get_by_role("button", name="Anexar").click()
        expect(self.form().get_by_role("status")).to_have_text("Dê um nome ao anexo.")
        self.form().get_by_label("Nome").fill("x")
        self.form().get_by_role("button", name="Anexar").click()
        expect(self.form().get_by_role("status")).to_have_text("Escolha um arquivo.")
        self.assertEqual(self.db.storage, {})

    def test_a_file_over_50_mb_is_refused_before_uploading(self):
        self.theme()
        self.sign()
        with tempfile.TemporaryDirectory() as d:
            big = os.path.join(d, "grande.bin")
            with open(big, "wb") as fh:
                fh.truncate(51 * 1024 * 1024)                                              # a sparse file: no real disk used
            self.form().locator('input[type=file]').set_input_files(big)
            self.form().get_by_role("button", name="Anexar").click()
            expect(self.form().get_by_role("status")).to_have_text("O arquivo passa de 50 MB.")
        self.assertEqual((self.db.storage, self.db.storage_calls), ({}, []))

    # -- reading ------------------------------------------------------------------------------------------
    def test_a_picture_is_shown_in_the_page_through_a_signed_address(self):
        a = self.db.seed_attachment("PHZ-0001", "tela.png", content_type="image/png", data=PNG)
        self.theme()
        self.row("tela.png").get_by_role("button", name="Abrir").click()
        img = self.box().locator("tr[data-preview-of] img")
        expect(img).to_be_visible()
        self.assertRegex(img.get_attribute("src"), r"/storage/v1/object/sign/attachments/PHZ-0001/.+/tela\.png\?token=")
        self.assertNotIn("download=", img.get_attribute("src"))
        expect(img).to_have_js_property("naturalWidth", 1)
        self.assertEqual(self.db.downloads[0][0], a["storage_path"])

    def test_audio_and_video_play_in_the_page(self):
        self.db.seed_attachment("PHZ-0001", "reuniao.mp3", content_type="audio/mpeg", data=b"ID3")
        self.db.seed_attachment("PHZ-0001", "demo.mp4", content_type="video/mp4", data=b"\x00\x00\x00\x18ftypmp42")
        self.theme()
        self.row("reuniao.mp3").get_by_role("button", name="Abrir").click()
        expect(self.box().locator("audio[controls]")).to_have_count(1)
        self.row("demo.mp4").get_by_role("button", name="Abrir").click()
        expect(self.box().locator("video[controls]")).to_have_count(1)

    def test_html_is_only_a_download_and_is_never_shown_on_the_app_origin(self):
        self.db.seed_attachment("PHZ-0001", "export.html", content_type="text/html", data=b"<script>alert(1)</script>")
        self.theme()
        expect(self.row("export.html")).to_contain_text("HTML só é oferecido para baixar.")
        with self.page.expect_download() as dl:
            self.row("export.html").get_by_role("button", name="Baixar").click()
        self.assertEqual(dl.value.suggested_filename, "export.html")
        self.assertEqual(self.db.downloads[0][1].get("download"), ["export.html"])        # the address asks for Content-Disposition: attachment
        self.assertEqual(len(self.page.context.pages), 1)                                  # nothing opened to show it
        expect(self.box().locator("iframe")).to_have_count(0)

    def test_other_files_are_a_download_too(self):
        self.db.seed_attachment("PHZ-0001", "planilha.xlsx", content_type="application/vnd.ms-excel")
        self.theme()
        with self.page.expect_download() as dl:
            self.row("planilha.xlsx").get_by_role("button", name="Baixar").click()
        self.assertEqual(dl.value.suggested_filename, "planilha.xlsx")

    # -- editions, stages, removing ----------------------------------------------------------------------------
    def test_a_new_edition_replaces_the_old_one_in_the_list_and_keeps_it_under_it(self):
        v1 = self.db.seed_attachment("PHZ-0001", "plano.pdf", content_type="application/pdf", created_at="2026-11-01T10:00:00+00:00")
        self.theme()
        self.sign()
        self.row("plano.pdf").get_by_role("button", name="Nova edição").click()
        expect(self.form().get_by_label("Nova edição de")).to_have_value(v1["id"])
        self.add_file("plano-v2.pdf", b"v2", "application/pdf")
        expect(self.row("plano-v2.pdf")).to_be_visible()
        self.assertEqual(self.db.attachments[1]["replaces"], v1["id"])
        expect(self.box().locator('tr[data-name="plano.pdf"]')).to_have_count(0)                    # only the latest edition is listed...
        self.row("plano-v2.pdf").get_by_role("button", name="1 edições anteriores").click()
        expect(self.box().locator('tr[data-name="plano.pdf"][data-earlier="1"]')).to_have_count(1)  # ...with the earlier one under it

    def test_a_chain_of_three_editions(self):
        a = self.db.seed_attachment("PHZ-0001", "v1.pdf", content_type="application/pdf", created_at="2026-11-01T00:00:00+00:00")
        b = self.db.seed_attachment("PHZ-0001", "v2.pdf", content_type="application/pdf", replaces=a["id"], created_at="2026-11-02T00:00:00+00:00")
        self.db.seed_attachment("PHZ-0001", "v3.pdf", content_type="application/pdf", replaces=b["id"], created_at="2026-11-03T00:00:00+00:00")
        self.theme()
        self.assertEqual(self.box().locator("tr[data-attachment]").evaluate_all("els => els.map(e => e.dataset.name)"), ["v3.pdf"])
        self.row("v3.pdf").get_by_role("button", name="2 edições anteriores").click()
        self.assertEqual(self.box().locator("tr[data-attachment]").evaluate_all("els => els.map(e => e.dataset.name)"), ["v3.pdf", "v2.pdf", "v1.pdf"])

    def test_an_attachment_can_be_tied_to_a_stage_and_shows_in_the_gate_checklist(self):
        self.theme()
        self.sign()
        self.form().get_by_label("Tipo de anexo").select_option(label="Nota")
        self.form().get_by_label("Nome").fill("PRD aprovado")
        self.form().get_by_label("Nota (Markdown)").fill("ok")
        self.form().get_by_label("Etapa que ele comprova").select_option(label="04 PRD e início")
        self.form().get_by_role("button", name="Anexar").click()
        expect(self.row("PRD aprovado")).to_contain_text("04 PRD e início")
        self.assertEqual(self.db.attachments[0]["stage"], 4)
        self.page.reload()
        expect(self.page.locator('[data-stage-files="4"]')).to_have_text("Anexos desta etapa: PRD aprovado")

    def test_removing_takes_it_off_the_list_and_is_recorded(self):
        self.db.seed_attachment("PHZ-0001", "velho.pdf", content_type="application/pdf")
        self.theme()
        self.sign("Bo")
        self.row("velho.pdf").get_by_role("button", name="Remover").click()
        expect(self.row("velho.pdf")).to_have_count(0)
        self.assertTrue(self.db.attachments[0]["hidden"])
        self.assertEqual([e["edited_by"] for e in self.db.events if e["field"] == "attachment_removed"], ["Bo"])

    def test_the_history_of_the_theme_shows_attachments_added(self):
        self.theme()
        self.sign()
        self.add_file("a.txt", b"x", "text/plain")
        expect(self.row("a.txt")).to_be_visible()
        self.page.reload()
        expect(self.page.locator(".history")).to_contain_text("anexo adicionado")

    def test_the_pictures_of_the_rfc_are_listed_in_a_group_of_their_own(self):
        self.db.assets.append({"rfc_id": "PHZ-0001", "name": "fluxo.png", "rev": 1, "mime": "image/png", "size": 2048, "data": "x", "uploaded_by": "Ana", "created_at": "2026-11-01T00:00:00Z"})
        self.theme()
        group = self.box().locator('details[data-group="rfc-pictures"]')
        expect(group).to_contain_text("Imagens da RFC (1)")
        group.locator("summary").click()
        expect(group).to_contain_text("fluxo.png · 2.0 KB")

    def test_attachments_of_other_themes_do_not_show_here_and_an_item_can_be_tied(self):
        self.db.seed_attachment("PHZ-0002", "outro.pdf", content_type="application/pdf")
        self.db.items.append({"id": "i1", "theme_id": "PHZ-0001", "title": "Contrato", "owner": None, "col": "todo", "due_date": None, "milestone": False, "created_at": "x"})
        self.theme()
        self.sign()
        expect(self.box().locator("tr[data-attachment]")).to_have_count(0)
        self.form().get_by_label("Tipo de anexo").select_option(label="Nota")
        self.form().get_by_label("Nome").fill("Minuta")
        self.form().get_by_label("Nota (Markdown)").fill("texto")
        self.form().get_by_label("Item (opcional)").select_option(label="Contrato")
        self.form().get_by_role("button", name="Anexar").click()
        expect(self.row("Minuta")).to_contain_text("Contrato")
        self.assertEqual(self.db.attachments[-1]["item_id"], "i1")

    def test_reader_mode_lists_and_opens_but_has_no_controls_to_add_or_change(self):
        self.db.seed_attachment("PHZ-0001", "tela.png", content_type="image/png", data=PNG)
        self.theme(query="?mode=reader")
        expect(self.row("tela.png")).to_be_visible()
        expect(self.form()).to_have_count(0)
        expect(self.box().get_by_role("button", name="Remover")).to_have_count(0)
        expect(self.box().get_by_role("button", name="Nova edição")).to_have_count(0)
        self.row("tela.png").get_by_role("button", name="Abrir").click()
        expect(self.box().locator("tr[data-preview-of] img")).to_be_visible()

    # -- the cross-theme page ------------------------------------------------------------------------------------------
    def all_page(self):
        self.page.goto(self.base + "/attachments/")
        expect(self.page.locator("h1")).to_have_text("Anexos")
        expect(self.page.locator("tr[data-attachment]").first).to_be_visible()

    def names(self):
        return sorted(self.page.locator("tr[data-attachment]").evaluate_all("els => els.map(e => e.dataset.name)"))

    def test_the_page_lists_the_latest_attachments_of_every_theme_with_filters(self):
        a = self.db.seed_attachment("PHZ-0001", "plano.pdf", content_type="application/pdf")
        self.db.seed_attachment("PHZ-0001", "plano-v2.pdf", content_type="application/pdf", replaces=a["id"], stage=4)
        self.db.seed_attachment("PHZ-0002", "contrato.docx", content_type="application/msword", created_by="Bo", description="minuta jurídica")
        self.db.seed_attachment("PHZ-0002", "ata", kind="note", body="x", created_by="Bo")
        self.db.seed_attachment("PHZ-0002", "Jira board", kind="link", url="https://jira.example.com/b", created_by="Bo")
        self.all_page()
        self.assertEqual(self.names(), ["Jira board", "ata", "contrato.docx", "plano-v2.pdf"])        # the old edition is not a row of its own
        self.page.get_by_label("Tipo de anexo").select_option(label="Nota")
        self.assertEqual(self.names(), ["ata"])
        self.page.get_by_label("Tipo de anexo").select_option(index=0)
        self.page.get_by_label("Frente").select_option(label="API Platform")
        self.assertEqual(self.names(), ["plano-v2.pdf"])
        self.page.get_by_label("Frente").select_option(label="Todos")
        self.page.locator("label.field", has_text="Etapa").locator("select").select_option(label="04 PRD e início")
        self.assertEqual(self.names(), ["plano-v2.pdf"])
        self.page.locator("label.field", has_text="Etapa").locator("select").select_option(label="Todos")
        self.page.get_by_label("Quem").select_option(label="Bo")
        self.assertEqual(self.names(), ["Jira board", "ata", "contrato.docx"])
        self.page.get_by_label("Quem").select_option(label="Todos")
        self.page.get_by_label("Buscar").fill("jurídica")
        self.assertEqual(self.names(), ["contrato.docx"])

    def test_each_row_links_to_the_attachments_of_its_theme(self):
        self.db.seed_attachment("PHZ-0002", "contrato.docx", content_type="application/msword")
        self.all_page()
        link = self.page.locator('tr[data-name="contrato.docx"] a').first
        self.assertEqual(link.get_attribute("href"), "/themes/PHZ-0002/#attachments")
        expect(self.page.locator('tr[data-name="contrato.docx"]')).to_contain_text("Migração CredPay")

    def test_the_header_links_to_the_attachments_and_an_empty_hub_still_loads(self):
        self.page.goto(self.base + "/themes/")
        self.page.get_by_role("button", name="Documentos").click()                      # the documents are grouped in a menu of the top bar
        self.page.get_by_role("link", name="Anexos").click()
        expect(self.page).to_have_url(self.base + "/attachments/")
        expect(self.page.get_by_text("Nenhum anexo ainda.")).to_be_visible()


if __name__ == "__main__":
    unittest.main()
