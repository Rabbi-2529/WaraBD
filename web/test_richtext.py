"""CKEditor text: sanitising, rendering on the site, picture upload."""

import io
import shutil
import tempfile
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from . import richtext
from .models import Page, Product


class SanitizeTests(TestCase):
    def test_keeps_formatting_drops_scripts(self):
        out = richtext.rich('<h2>Specs</h2><p onclick="x()">Hi <strong>there</strong><script>alert(1)</script></p>'
                            '<a href="javascript:alert(1)">bad</a><a href="https://warabd.com">ok</a>')
        self.assertIn("<h2>Specs</h2>", out)
        self.assertIn("<strong>there</strong>", out)
        self.assertNotIn("script", out)
        self.assertNotIn("onclick", out)
        self.assertNotIn("javascript:", out)
        self.assertIn('href="https://warabd.com"', out)

    def test_old_plain_text_still_becomes_paragraphs(self):
        self.assertEqual(richtext.rich("One\n\nTwo & three"), "<p>One</p>\n\n<p>Two &amp; three</p>")

    def test_inline_and_plain(self):
        self.assertEqual(richtext.rich_inline("<p>Line <em>one</em></p><p>Line two</p>"), "Line <em>one</em><br>Line two")
        self.assertEqual(richtext.plain("<p>A &amp; B</p><ul><li>One</li></ul>"), "A & B\n\n- One")


@override_settings(ALLOWED_HOSTS=["testserver", "localhost"])
class RichPagesTests(TestCase):
    def test_product_description_html_is_shown_cleanly(self):
        Product.objects.create(name="Lock", slug="lock-1", price=Decimal("1000"), stock=3,
                               description='<h2>Why this lock</h2><ul><li>Keyless</li></ul><img src="x" onerror="alert(1)">')
        body = self.client.get("/lock-1").content.decode()
        self.assertIn("<h2>Why this lock</h2>", body)
        self.assertIn("<li>Keyless</li>", body)
        self.assertNotIn("onerror", body)

    def test_policy_and_faq_pages_from_editor(self):
        Page.objects.create(slug="terms", title="Terms", body="<h2>Orders</h2><p>We ship <strong>fast</strong>.</p>")
        Page.objects.create(slug="faq", title="FAQ", kind=Page.KIND_FAQ,
                            body="<p>Q: Do you deliver?</p><p>A: Yes, <strong>all over</strong> Bangladesh.</p>")
        terms = self.client.get("/page/terms/").content.decode()
        self.assertIn("<h2>Orders</h2>", terms)
        self.assertIn("<strong>fast</strong>", terms)
        faq = self.client.get("/page/faq/").content.decode()
        self.assertIn("Do you deliver?", faq)
        self.assertIn("Yes, all over Bangladesh.", faq)


class EditorUploadTests(TestCase):
    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)
        self.staff = get_user_model().objects.create_superuser(email="owner@example.com", password="x-test-only")

    def png(self):
        from PIL import Image

        buf = io.BytesIO()
        Image.new("RGB", (4, 4), "red").save(buf, "PNG")
        return SimpleUploadedFile("photo.png", buf.getvalue(), content_type="image/png")

    def test_staff_can_upload_pictures_only(self):
        with override_settings(MEDIA_ROOT=self.media):
            self.client.force_login(self.staff)
            r = self.client.post("/admin/editor-upload/", {"upload": self.png()})
            self.assertEqual(r.status_code, 200, r.content)
            self.assertRegex(r.json()["url"], r"/editor/\d{4}/\d{2}/[0-9a-f]{32}\.png$")
            fake = SimpleUploadedFile("evil.png", b"<script>alert(1)</script>", content_type="image/png")
            r = self.client.post("/admin/editor-upload/", {"upload": fake})
            self.assertEqual(r.status_code, 400)

    def test_visitors_cannot_upload(self):
        with override_settings(MEDIA_ROOT=self.media):
            r = self.client.post("/admin/editor-upload/", {"upload": self.png()})
            self.assertNotEqual(r.status_code, 200)

    @override_settings(ALLOWED_HOSTS=["testserver", "localhost"])
    def test_admin_forms_use_the_editor(self):
        self.client.force_login(self.staff)
        r = self.client.get("/admin/web/product/add/")
        self.assertContains(r, 'data-rich-editor="full"', count=2)
        self.assertContains(r, "ckeditor5/41.4.2/classic/ckeditor.js")
        self.assertContains(r, "wara-editor.js")
        self.assertContains(r, 'id="pf-status"')
        self.assertContains(self.client.get("/admin/web/page/add/"), 'data-rich-editor="full"', count=2)
        self.assertContains(self.client.get("/admin/web/usecase/add/"), 'data-rich-editor="compact"')
