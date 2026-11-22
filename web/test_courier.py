"""Phase 5: courier booking / tracking. The courier APIs are mocked (no network)."""

import json
from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings

from customers.models import SmsLog

from . import courier
from .models import District, Order, OrderItem, Product, SiteSettings, Thana


class FakeResponse:
    def __init__(self, payload):
        self.body = json.dumps(payload).encode()

    def read(self, *args):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def answer(*payloads):
    """urlopen stand-in returning the payloads in order; records the requests."""
    calls = []

    def fake(req, timeout=None):
        calls.append(req)
        return FakeResponse(payloads[min(len(calls), len(payloads)) - 1])

    fake.calls = calls
    return fake


class CourierTestBase(TestCase):
    def setUp(self):
        cache.clear()
        product = Product.objects.create(name="Test Lock", slug="test-lock", price=Decimal("2050"), stock=5)
        self.order = Order.objects.create(
            full_name="Rahim Uddin", phone="01712345678", address_line1="House 12, Road 5", city="Dhaka",
            thana="Dhanmondi", subtotal=Decimal("2050"), shipping=Decimal("60"), total=Decimal("2110"),
            payment_method="cod",
        )
        OrderItem.objects.create(order=self.order, product=product, quantity=1, price=Decimal("2050"))

    def use_steadfast(self, **extra):
        site = SiteSettings.load()
        site.courier_provider = "steadfast"
        site.steadfast_api_key = "key-123"
        site.steadfast_secret_key = "secret-456"
        for k, v in extra.items():
            setattr(site, k, v)
        site.save()
        return site


class SteadfastTests(CourierTestBase):
    BOOKED = {"status": 200, "message": "Consignment has been created successfully.",
              "consignment": {"consignment_id": 1424107, "invoice": "x", "tracking_code": "15BAEB8A", "status": "in_review"}}

    def test_book_sends_cod_and_saves_tracking(self):
        self.use_steadfast()
        fake = answer(self.BOOKED)
        with mock.patch("web.courier.urllib.request.urlopen", fake):
            courier.book(self.order)
        self.order.refresh_from_db()
        self.assertEqual((self.order.courier, self.order.courier_consignment_id, self.order.courier_tracking_code),
                         ("steadfast", "1424107", "15BAEB8A"))
        self.assertEqual(self.order.status, Order.STATUS_SHIPPED)
        self.assertIsNotNone(self.order.courier_sent_at)
        req = fake.calls[0]
        self.assertTrue(req.full_url.endswith("/create_order"))
        self.assertEqual(req.get_header("Api-key"), "key-123")
        sent = json.loads(req.data)
        self.assertEqual(sent["invoice"], self.order.order_number)
        self.assertEqual(sent["cod_amount"], 2110.0)
        self.assertIn("Dhanmondi", sent["recipient_address"])
        self.assertEqual(courier.tracking_url(self.order), "https://steadfast.com.bd/t/15BAEB8A")

    def test_paid_order_collects_nothing(self):
        self.use_steadfast()
        self.order.payment_status = Order.PAYMENT_PAID
        self.order.save()
        fake = answer(self.BOOKED)
        with mock.patch("web.courier.urllib.request.urlopen", fake):
            courier.book(self.order)
        self.assertEqual(json.loads(fake.calls[0].data)["cod_amount"], 0.0)

    def test_dispatch_sms_once_per_number_per_day(self):
        self.use_steadfast()
        with mock.patch("web.courier.urllib.request.urlopen", answer(self.BOOKED)):
            courier.book(self.order)
        sms = SmsLog.objects.get(purpose="dispatch")
        self.assertIn("15BAEB8A", sms.message)
        self.assertIn(self.order.order_number, sms.message)
        # Same number, same day: no second SMS.
        self.assertIsNone(courier.notify_customer(self.order))
        self.assertEqual(SmsLog.objects.filter(phone="01712345678").count(), 1)

    def test_no_sms_when_switched_off(self):
        self.use_steadfast(courier_sms_on_dispatch=False)
        with mock.patch("web.courier.urllib.request.urlopen", answer(self.BOOKED)):
            courier.book(self.order)
        self.assertFalse(SmsLog.objects.exists())

    def test_cannot_book_twice_or_without_keys(self):
        with self.assertRaisesMessage(courier.CourierError, "No courier is connected"):
            courier.book(self.order)
        self.use_steadfast(steadfast_secret_key="")
        with self.assertRaisesMessage(courier.CourierError, "secret key"):
            courier.book(self.order)
        self.use_steadfast()
        with mock.patch("web.courier.urllib.request.urlopen", answer(self.BOOKED)):
            courier.book(self.order)
        with self.assertRaisesMessage(courier.CourierError, "Already sent"):
            courier.book(self.order)

    def test_api_error_is_readable(self):
        self.use_steadfast()
        bad = {"status": 400, "message": "Validation error", "errors": {"recipient_phone": ["The recipient phone must be 11 digits."]}}
        with mock.patch("web.courier.urllib.request.urlopen", answer(bad)):
            with self.assertRaisesMessage(courier.CourierError, "recipient_phone: The recipient phone must be 11 digits."):
                courier.book(self.order)
        self.order.refresh_from_db()
        self.assertEqual(self.order.courier_consignment_id, "")

    def test_delivered_status_completes_cod_order(self):
        self.use_steadfast()
        with mock.patch("web.courier.urllib.request.urlopen", answer(self.BOOKED, {"status": 200, "delivery_status": "delivered"})):
            courier.book(self.order, notify=False)
            self.assertEqual(courier.refresh(self.order), "delivered")
        self.order.refresh_from_db()
        self.assertEqual((self.order.status, self.order.payment_status), (Order.STATUS_DELIVERED, Order.PAYMENT_PAID))


class PathaoTests(CourierTestBase):
    def use_pathao(self):
        site = SiteSettings.load()
        site.courier_provider = "pathao"
        site.pathao_client_id, site.pathao_client_secret = "cid", "csecret"
        site.pathao_username, site.pathao_password, site.pathao_store_id = "shop@example.com", "pw", "77"
        site.save()

    def test_needs_city_and_zone_numbers_then_books(self):
        self.use_pathao()
        with self.assertRaisesMessage(courier.CourierError, "No Pathao city number"):
            courier.book(self.order)
        District.objects.filter(name_en="Dhaka").update(pathao_city_id=1)
        Thana.objects.filter(district__name_en="Dhaka", name_en="Dhanmondi").update(pathao_zone_id=52)
        fake = answer({"access_token": "tok", "expires_in": 3600},
                      {"code": 200, "data": {"consignment_id": "DL121224VS8TTJ", "order_status": "Pending"}})
        with mock.patch("web.courier.urllib.request.urlopen", fake):
            courier.book(self.order, notify=False)
        sent = json.loads(fake.calls[1].data)
        self.assertEqual((sent["recipient_city"], sent["recipient_zone"], sent["store_id"]), (1, 52, 77))
        self.assertEqual(sent["amount_to_collect"], 2110)
        self.assertEqual(fake.calls[1].get_header("Authorization"), "Bearer tok")
        self.order.refresh_from_db()
        self.assertEqual(self.order.courier_consignment_id, "DL121224VS8TTJ")
        self.assertIn("consignment_id=DL121224VS8TTJ", courier.tracking_url(self.order))

    def test_match_locations_by_name_and_old_spelling(self):
        self.use_pathao()
        cities = {"data": {"data": [{"city_id": 1, "city_name": "Dhaka"}, {"city_id": 2, "city_name": "Chittagong"}]}}
        dhaka_zones = {"data": {"data": [{"zone_id": 52, "zone_name": "Dhanmondi"}, {"zone_id": 60, "zone_name": "Mirpur"}]}}
        ctg_zones = {"data": {"data": [{"zone_id": 300, "zone_name": "Panchlaish"}]}}

        def fake(req, timeout=None):
            url = req.full_url
            if url.endswith("issue-token"):
                return FakeResponse({"access_token": "tok", "expires_in": 3600})
            if url.endswith("city-list"):
                return FakeResponse(cities)
            if "/cities/1/" in url:
                return FakeResponse(dhaka_zones)
            if "/cities/2/" in url:
                return FakeResponse(ctg_zones)
            return FakeResponse({"data": {"data": []}})

        with mock.patch("web.courier.urllib.request.urlopen", fake):
            summary = courier.match_pathao_locations()
        self.assertEqual(District.objects.get(name_en="Chattogram").pathao_city_id, 2)
        self.assertEqual(Thana.objects.get(district__name_en="Dhaka", name_en="Dhanmondi").pathao_zone_id, 52)
        self.assertEqual(summary["districts"], 2)
        self.assertIn("Gazipur", summary["missing_districts"])


@override_settings(ALLOWED_HOSTS=["testserver", "localhost"])
class CourierAdminAndCustomerTests(CourierTestBase):
    def setUp(self):
        super().setUp()
        self.admin = get_user_model().objects.create_superuser(email="owner@example.com", password="x-test-only")
        self.client.force_login(self.admin)

    def test_order_page_offers_send_and_books(self):
        self.use_steadfast()
        url = f"/admin/web/order/{self.order.pk}/change/"
        self.assertContains(self.client.get(url), "Send to Steadfast")
        with mock.patch("web.courier.urllib.request.urlopen", answer(SteadfastTests.BOOKED)):
            r = self.client.post(f"/admin/web/order/{self.order.pk}/courier/send/")
        self.assertRedirects(r, url, fetch_redirect_response=False)
        page = self.client.get(url).content.decode()
        self.assertIn("15BAEB8A", page)
        self.assertIn("Refresh status", page)

    def test_order_page_save_keeps_hidden_fields(self):
        url = f"/admin/web/order/{self.order.pk}/change/"
        r = self.client.post(url, {
            "status": "shipped", "payment_status": "unpaid", "notes": "", "full_name": "Rahim Uddin",
            "email": "", "phone": "01712345678", "address_line1": "House 12, Road 5", "thana": "Dhanmondi",
            "city": "Dhaka", "postal_code": "", "courier": "RedX", "courier_tracking_code": "RX123",
            "courier_tracking_url": "https://redx.com.bd/track/RX123", "_save": "Save",
        })
        self.assertEqual(r.status_code, 302, r.content[:500])
        self.order.refresh_from_db()
        self.assertEqual((self.order.status, self.order.courier, self.order.payment_method, self.order.delivery_zone),
                         ("shipped", "RedX", "cod", "inside"))
        self.assertEqual(courier.tracking_url(self.order), "https://redx.com.bd/track/RX123")

    def test_customer_sees_tracking_code(self):
        Order.objects.filter(pk=self.order.pk).update(courier="steadfast", courier_consignment_id="1",
                                                      courier_tracking_code="15BAEB8A", status="shipped")
        self.client.logout()
        r = self.client.post("/track-order/", {"order_number": self.order.order_number, "phone": "01712345678"})
        self.assertContains(r, "15BAEB8A")
        self.assertContains(r, "https://steadfast.com.bd/t/15BAEB8A")

    def test_courier_settings_and_pathao_match_screens(self):
        SiteSettings.load()
        self.assertContains(self.client.get("/admin/web/sitesettings/1/change/"), "courier-test/")
        r = self.client.get("/admin/web/sitesettings/1/courier-test/", follow=True)
        self.assertContains(r, "No courier is connected")
        self.assertContains(self.client.get("/admin/web/district/"), "Match Pathao cities")
