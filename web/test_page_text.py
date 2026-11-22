"""Admin → Website → Page text: the side-by-side English / Bangla editor."""

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from .models import ContentBlock


@override_settings(ALLOWED_HOSTS=["testserver", "localhost"])
class PageTextEditorTests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_superuser(email="owner@example.com", password="x-test-only")
        self.block = ContentBlock.objects.create(key="home.hero.title", page="home", label="Hero · title",
                                                 value_en="Keyless security", value_bn="চাবিহীন নিরাপত্তা")
        ContentBlock.objects.create(key="about.banner.text", page="about", label="Banner · text", value_en="About us")
        self.url = f"/admin/web/contentblock/{self.block.pk}/quick-save/"

    def test_editor_lists_every_text_by_page(self):
        self.client.force_login(self.staff)
        page = self.client.get("/admin/web/contentblock/").content.decode()
        for text in ('class="pt"', 'data-page="home"', 'data-page="about"', "Keyless security", "চাবিহীন নিরাপত্তা",
                     "1 without বাংলা", self.url):
            self.assertIn(text, page)

    def test_quick_save_changes_the_text(self):
        self.client.force_login(self.staff)
        r = self.client.post(self.url, {"value_en": "  Smart locks  ", "value_bn": ""})
        self.assertEqual(r.json()["changed"], ["value_en", "value_bn"])
        self.block.refresh_from_db()
        self.assertEqual((self.block.value_en, self.block.value_bn), ("Smart locks", ""))
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_visitors_cannot_save(self):
        r = self.client.post(self.url, {"value_en": "Hacked"})
        self.assertNotEqual(r.status_code, 200)
        self.block.refresh_from_db()
        self.assertEqual(self.block.value_en, "Keyless security")


@override_settings(ALLOWED_HOSTS=["testserver", "localhost"])
class SiteMessageColourTests(TestCase):
    def test_success_is_green_and_errors_red(self):
        r = self.client.post("/account/logout/", follow=True)
        body = r.content.decode()
        self.assertIn('class="form-alert show msg-success"', body)   # "You have been logged out."
        self.assertNotIn("msg-error", body)
        r = self.client.post("/account/verify/change-number/", follow=True)   # no code pending → login page
        self.assertEqual(r.status_code, 200)
