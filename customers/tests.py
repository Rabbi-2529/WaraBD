"""Phase 4: phone login / registration with SMS codes, OTP rules, order OTP, My Account."""

import json
import re
import urllib.parse
from datetime import timedelta
from decimal import Decimal
from unittest import mock

from django.test import Client, TestCase, override_settings
from django.utils import timezone

from web.models import Order, Product, SiteSettings

from .models import Customer, CustomerAddress, OtpCode, SmsLog


class FakeResponse:
    def __init__(self, body='{"status":"success"}', status=200):
        self.body, self.status = body.encode(), status

    def read(self, *args):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@override_settings(ALLOWED_HOSTS=["testserver", "localhost"])
class OtpTestCase(TestCase):
    """Base: live gateway configured, real HTTP call replaced by a fake that records requests."""

    def setUp(self):
        site = SiteSettings.load()
        site.sms_enabled = True
        site.sms_api_key = "test-key"
        site.sms_sender_id = "WaRaBD"
        site.sms_daily_limit_per_number = 3
        site.sms_daily_limit_per_ip = 10
        site.otp_resend_seconds = 60
        site.save()
        self.sent = []
        patcher = mock.patch("customers.sms.urllib.request.urlopen", side_effect=self._fake_urlopen)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.gateway_body = '{"status":"success"}'

    def _fake_urlopen(self, request, timeout=None):
        parts = urllib.parse.urlsplit(request.full_url)
        self.sent.append({"url": f"{parts.scheme}://{parts.netloc}{parts.path}", "method": request.get_method(),
                          **dict(urllib.parse.parse_qsl(parts.query))})
        return FakeResponse(self.gateway_body)

    def last_code(self):
        return re.search(r"\b(\d{6})\b", self.sent[-1]["msg"]).group(1)

    def age_last_sms(self, seconds=120):
        SmsLog.objects.update(created_at=timezone.now() - timedelta(seconds=seconds))


class GatewayTests(OtpTestCase):
    def test_register_sends_sms_through_igl_api_with_admin_settings(self):
        r = self.client.post("/account/register/", {"name": "Rahim Uddin", "phone": "01712345678"})
        self.assertRedirects(r, "/account/verify/", fetch_redirect_response=False)
        call = self.sent[0]
        self.assertEqual(call["url"], "http://sms.iglweb.com/api/v1/send")
        self.assertEqual(call["method"], "GET")  # the values travel in the URL, as the gateway reads them
        self.assertEqual(call["api_key"], "test-key")
        self.assertEqual(call["senderid"], "WaRaBD")
        self.assertEqual(call["contacts"], "8801712345678")
        self.assertIn("is your WaRa BD verification code", call["msg"])
        log = SmsLog.objects.get()
        self.assertEqual(log.status, SmsLog.STATUS_SENT)
        self.assertNotIn(self.last_code(), log.message)  # code hidden in the log
        self.assertNotIn(self.last_code(), OtpCode.objects.get().code_hash)

    def test_number_format_01(self):
        SiteSettings.objects.update(sms_number_format="0")
        self.client.post("/account/register/", {"name": "Rahim Uddin", "phone": "+8801712345678"})
        self.assertEqual(self.sent[0]["contacts"], "01712345678")

    def test_igl_error_code_counts_as_failed(self):
        self.gateway_body = '{"code":"445010","message":"Missing api key"}'
        r = self.client.post("/account/register/", {"name": "Rahim Uddin", "phone": "01712345678"})
        self.assertContains(r, "We couldn&#x27;t send the SMS")
        self.assertEqual(SmsLog.objects.get().status, SmsLog.STATUS_FAILED)

    def test_gateway_error_is_reported_and_not_counted(self):
        self.gateway_body = '{"status":"error","message":"Invalid API key"}'
        r = self.client.post("/account/register/", {"name": "Rahim Uddin", "phone": "01712345678"})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "We couldn&#x27;t send the SMS")
        self.assertEqual(SmsLog.objects.get().status, SmsLog.STATUS_FAILED)
        self.assertTrue(OtpCode.objects.get().cancelled)

    @override_settings(DEBUG=False)
    def test_without_gateway_and_debug_off_codes_are_unavailable(self):
        SiteSettings.objects.update(sms_enabled=False)
        r = self.client.post("/account/register/", {"name": "Rahim Uddin", "phone": "01712345678"})
        self.assertContains(r, "SMS codes are not available right now")
        self.assertEqual(self.sent, [])

    @override_settings(DEBUG=True)
    def test_test_mode_shows_code_on_page_and_sends_nothing(self):
        SiteSettings.objects.update(sms_enabled=False)
        self.client.post("/account/register/", {"name": "Rahim Uddin", "phone": "01712345678"})
        page = self.client.get("/account/verify/").content.decode()
        code = re.search(r"Your code is <strong>(\d{6})</strong>", page).group(1)
        self.assertEqual(self.sent, [])
        self.assertEqual(SmsLog.objects.get().status, SmsLog.STATUS_TEST)
        r = self.client.post("/account/verify/", {"code": code})
        self.assertRedirects(r, "/account/", fetch_redirect_response=False)


class LoginRegisterTests(OtpTestCase):
    def test_register_verify_creates_account_and_logs_in(self):
        self.client.post("/account/register/", {"name": "Rahim Uddin", "phone": "01712345678", "email": "r@example.com"})
        r = self.client.post("/account/verify/", {"code": self.last_code()})
        self.assertRedirects(r, "/account/", fetch_redirect_response=False)
        customer = Customer.objects.get(phone="01712345678")
        self.assertEqual((customer.name, customer.email), ("Rahim Uddin", "r@example.com"))
        self.assertContains(self.client.get("/account/"), "Rahim Uddin")

    def test_bangla_digits_and_code(self):
        self.client.post("/bn/account/register/", {"name": "রহিম", "phone": "০১৭১২৩৪৫৬৭৮"})
        bangla_code = self.last_code().translate(str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯"))
        r = self.client.post("/bn/account/verify/", {"code": bangla_code})
        self.assertEqual(r.status_code, 302)
        self.assertTrue(Customer.objects.filter(phone="01712345678").exists())

    def test_login_existing_customer(self):
        Customer.objects.create(phone="01712345678", name="Rahim")
        r = self.client.post("/account/login/", {"phone": "01712345678"})
        self.assertRedirects(r, "/account/verify/", fetch_redirect_response=False)
        self.client.post("/account/verify/", {"code": self.last_code()})
        self.assertEqual(self.client.get("/account/").status_code, 200)

    def test_login_unknown_number_and_register_existing_number(self):
        r = self.client.post("/account/login/", {"phone": "01712345678"})
        self.assertContains(r, "No account uses this number yet")
        Customer.objects.create(phone="01812345678", name="Karim")
        r = self.client.post("/account/register/", {"name": "Karim", "phone": "01812345678"})
        self.assertContains(r, "This number already has an account")
        self.assertEqual(self.sent, [])

    def test_wrong_codes_lock_after_max_attempts(self):
        SiteSettings.objects.update(otp_max_attempts=3)
        self.client.post("/account/register/", {"name": "Rahim Uddin", "phone": "01712345678"})
        good = self.last_code()
        bad = "111111" if good != "111111" else "222222"
        self.assertContains(self.client.post("/account/verify/", {"code": bad}), "Wrong code. 2 tries left.")
        self.assertContains(self.client.post("/account/verify/", {"code": bad}), "Wrong code. 1 try left.")
        self.assertContains(self.client.post("/account/verify/", {"code": bad}), "Too many wrong codes")
        self.assertContains(self.client.post("/account/verify/", {"code": good}), "Too many wrong codes")
        self.assertFalse(Customer.objects.exists())

    def test_expired_code(self):
        self.client.post("/account/register/", {"name": "Rahim Uddin", "phone": "01712345678"})
        OtpCode.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertContains(self.client.post("/account/verify/", {"code": self.last_code()}), "This code has expired")

    def test_change_number_cancels_code_and_keeps_the_form(self):
        self.client.post("/account/register/", {"name": "Rahim Uddin", "phone": "01712345678", "email": "r@example.com"})
        r = self.client.post("/account/verify/change-number/")
        self.assertRedirects(r, "/account/register/?change=phone", fetch_redirect_response=False)
        self.assertTrue(OtpCode.objects.get().cancelled)
        page = self.client.get("/account/register/?change=phone").content.decode()
        self.assertIn('value="Rahim Uddin"', page)
        self.assertIn('value="01712345678"', page)
        self.assertIn('value="r@example.com"', page)
        # the old code no longer works
        self.assertRedirects(self.client.get("/account/verify/"), "/account/login/", fetch_redirect_response=False)

    def test_logout(self):
        customer = Customer.objects.create(phone="01712345678", name="Rahim")
        self.client.post("/account/login/", {"phone": customer.phone})
        self.client.post("/account/verify/", {"code": self.last_code()})
        self.client.post("/account/logout/")
        self.assertRedirects(self.client.get("/account/"), "/account/login/?next=/account/", fetch_redirect_response=False)


class SmsLimitTests(OtpTestCase):
    def test_resend_waits_for_cooldown(self):
        self.client.post("/account/register/", {"name": "Rahim Uddin", "phone": "01712345678"})
        r = self.client.post("/account/verify/resend/", follow=True)
        self.assertContains(r, "seconds before asking for a new code")
        self.assertEqual(len(self.sent), 1)
        self.age_last_sms()
        r = self.client.post("/account/verify/resend/", follow=True)
        self.assertContains(r, "A new code has been sent.")
        self.assertEqual(len(self.sent), 2)

    def test_daily_limit_per_number(self):
        SiteSettings.objects.update(sms_daily_limit_per_number=1)
        self.client.post("/account/register/", {"name": "Rahim Uddin", "phone": "01712345678"})
        self.age_last_sms()
        r = self.client.post("/account/verify/resend/", follow=True)
        self.assertContains(r, "reached today&#x27;s SMS limit")
        self.assertEqual(len(self.sent), 1)

    def test_yesterdays_sms_do_not_count(self):
        SiteSettings.objects.update(sms_daily_limit_per_number=1)
        self.client.post("/account/register/", {"name": "Rahim Uddin", "phone": "01712345678"})
        self.age_last_sms(seconds=26 * 3600)
        self.client.post("/account/verify/resend/")
        self.assertEqual(len(self.sent), 2)

    def test_daily_limit_per_ip(self):
        SiteSettings.objects.update(sms_daily_limit_per_ip=2)
        for i in range(3):
            self.client.post("/account/register/", {"name": "Someone", "phone": f"0171234567{i}"})
        self.assertEqual(len(self.sent), 2)
        r = self.client.post("/account/register/", {"name": "Someone", "phone": "01712345679"})
        self.assertContains(r, "Too many SMS codes were requested from this connection")


class CheckoutOtpTests(OtpTestCase):
    def setUp(self):
        super().setUp()
        Product.objects.create(name="Test Lock", slug="test-lock", price=Decimal("1000"), stock=10)

    def checkout(self, client=None, phone="01912345678"):
        data = {"name": "Guest Buyer", "phone": phone, "district": "Dhaka", "thana": "Dhanmondi", "address": "House 12, Road 5, Dhanmondi",
                "zone": "inside", "payment": "cod", "lines": [{"id": "test-lock", "qty": 1}]}
        return (client or self.client).post("/api/checkout/", json.dumps(data), content_type="application/json")

    def test_guest_order_needs_code_then_is_placed(self):
        r = self.checkout().json()
        self.assertEqual(r, {"success": False, "otp_required": True, "redirect": "/account/verify/"})
        self.assertFalse(Order.objects.exists())
        page = self.client.get("/account/verify/").content.decode()
        self.assertIn("Confirm & place order", page)
        r = self.client.post("/account/verify/", {"code": self.last_code()})
        order = Order.objects.get()
        self.assertRedirects(r, f"/order/success/{order.order_number}/?placed=1", fetch_redirect_response=False)
        self.assertEqual(order.total, Decimal("1060"))

    def test_same_number_needs_a_new_code_for_every_order(self):
        self.checkout()
        first_code = self.last_code()
        self.client.post("/account/verify/", {"code": first_code})
        r = self.checkout().json()                       # same number, same browser, right away
        self.assertTrue(r["otp_required"])
        self.assertEqual(Order.objects.count(), 1)        # not placed until the new code is entered
        self.assertEqual(len(self.sent), 2)
        self.assertContains(self.client.post("/account/verify/", {"code": first_code}), "Wrong code")
        self.client.post("/account/verify/", {"code": self.last_code()})
        self.assertEqual(Order.objects.count(), 2)

    def test_unused_code_still_has_the_resend_wait(self):
        self.checkout()
        r = self.checkout()                               # first code not entered yet
        self.assertEqual(r.status_code, 429)
        self.assertIn("Please wait", r.json()["errors"]["phone"])
        self.assertEqual(len(self.sent), 1)

    def test_second_tap_after_the_order_shows_the_order(self):
        self.checkout()
        code = self.last_code()
        stale = OtpCode.objects.get()                     # what a second, simultaneous tap would hold
        self.client.post("/account/verify/", {"code": code})
        order = Order.objects.get()
        r = self.client.post("/account/verify/", {"code": code})   # auto-submit + button tap
        self.assertRedirects(r, f"/order/success/{order.order_number}/?placed=1", fetch_redirect_response=False)
        from .otp import OtpError, verify_otp

        with self.assertRaises(OtpError):                 # the same code can never be used twice
            verify_otp(None, stale, code)
        self.assertEqual(Order.objects.count(), 1)

    def test_other_browser_still_needs_a_code(self):
        self.checkout()
        self.client.post("/account/verify/", {"code": self.last_code()})
        self.age_last_sms()
        self.assertTrue(self.checkout(client=Client(HTTP_HOST="localhost")).json()["otp_required"])

    def test_logged_in_customer_skips_code_and_order_is_linked(self):
        customer = Customer.objects.create(phone="01712345678", name="Rahim")
        self.client.post("/account/login/", {"phone": customer.phone})
        self.client.post("/account/verify/", {"code": self.last_code()})
        r = self.checkout(phone="01912345678").json()  # even for another receiver number
        self.assertTrue(r["success"])
        order = Order.objects.get()
        self.assertEqual(order.customer, customer)
        self.assertEqual(len(self.sent), 1)
        self.assertEqual(customer.addresses.get().district, "Dhaka")  # first address saved

    def test_verified_guest_order_links_to_existing_account(self):
        customer = Customer.objects.create(phone="01912345678", name="Guest Buyer")
        self.checkout()
        self.client.post("/account/verify/", {"code": self.last_code()})
        self.assertEqual(Order.objects.get().customer, customer)

    def test_change_number_from_checkout_returns_to_checkout(self):
        self.checkout()
        r = self.client.post("/account/verify/change-number/")
        self.assertRedirects(r, "/checkout/?change=phone", fetch_redirect_response=False)

    def test_otp_for_orders_can_be_switched_off(self):
        SiteSettings.objects.update(otp_for_orders=False)
        self.assertTrue(self.checkout().json()["success"])
        self.assertEqual(self.sent, [])


class AccountPagesTests(OtpTestCase):
    def setUp(self):
        super().setUp()
        self.customer = Customer.objects.create(phone="01712345678", name="Rahim")
        self.client.post("/account/login/", {"phone": self.customer.phone})
        self.client.post("/account/verify/", {"code": self.last_code()})
        product = Product.objects.create(name="Test Lock", slug="test-lock", price=Decimal("1000"), stock=10)
        self.order = Order.objects.create(full_name="Rahim", phone=self.customer.phone, address_line1="House 1",
                                          city="Dhaka", total=Decimal("1060"), customer=self.customer)
        self.other = Order.objects.create(full_name="Other", phone="01812345678", address_line1="House 2",
                                          city="Sylhet", total=Decimal("500"))
        self.order.items.create(product=product, quantity=1, price=Decimal("1000"))

    def test_pages_and_own_orders_only(self):
        for url in ["/account/", "/account/orders/", "/account/profile/", "/account/addresses/",
                    "/account/addresses/new/", f"/account/orders/{self.order.order_number}/",
                    "/bn/account/", "/bn/account/orders/"]:
            self.assertEqual(self.client.get(url).status_code, 200, url)
        self.assertEqual(self.client.get(f"/account/orders/{self.other.order_number}/").status_code, 404)

    def test_addresses_default_switching(self):
        data = {"label": "Home", "name": "Rahim", "phone": "01712345678", "district": "Dhaka",
                "thana": "Dhanmondi", "address": "House 1, Road 2", "is_default": "on"}
        self.client.post("/account/addresses/new/", data)
        self.client.post("/account/addresses/new/", {**data, "label": "Office", "district": "Gazipur", "thana": "Tongi"})
        self.assertEqual(self.customer.addresses.get(is_default=True).label, "Office")
        home = self.customer.addresses.get(label="Home")
        self.client.post(f"/account/addresses/{home.pk}/default/")
        self.assertEqual(self.customer.addresses.get(is_default=True).label, "Home")
        self.client.post(f"/account/addresses/{home.pk}/delete/")
        self.assertTrue(self.customer.addresses.get().is_default)

    def test_checkout_is_prefilled_from_default_address(self):
        CustomerAddress.objects.create(customer=self.customer, name="Rahim", phone="01712345678",
                                       district="Sylhet", thana="Zindabazar", address="House 9", is_default=True)
        page = self.client.get("/checkout/").content.decode()
        self.assertIn('data-selected="Sylhet"', page)
        self.assertIn('data-selected="Zindabazar"', page)        # thana is its own dropdown now
        self.assertIn('value="House 9"', page)
        self.assertIn("no SMS code needed", page)

    def test_change_phone_with_code_to_new_number(self):
        self.age_last_sms()
        r = self.client.post("/account/profile/", {"form": "phone", "phone": "01999999999"})
        self.assertRedirects(r, "/account/verify/", fetch_redirect_response=False)
        self.assertEqual(self.sent[-1]["contacts"], "8801999999999")
        self.client.post("/account/verify/", {"code": self.last_code()})
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.phone, "01999999999")

    def test_admin_screens(self):
        from django.contrib.auth import get_user_model

        admin_user = get_user_model().objects.create_superuser(email="admin@example.com", password="x-test-only")
        staff = Client(HTTP_HOST="localhost")
        staff.force_login(admin_user)
        for url in ["/admin/customers/customer/", f"/admin/customers/customer/{self.customer.pk}/change/",
                    "/admin/customers/smslog/", "/admin/customers/otpcode/", "/admin/web/sitesettings/1/change/",
                    "/admin/web/sitesettings/1/sms-test/"]:
            self.assertEqual(staff.get(url).status_code, 200, url)
        r = staff.post("/admin/web/sitesettings/1/sms-test/", {"phone": "01712345678"})
        self.assertContains(r, "Result: Sent")
        self.assertEqual(self.sent[-1]["msg"], "WaRa BD test message. Your SMS gateway is working.")
        settings_page = staff.get("/admin/web/sitesettings/1/change/").content.decode()
        self.assertNotIn(">test-key<", settings_page)


class CodePageChangeNumberTests(OtpTestCase):
    """“Change number” on the code page opens its own page with only the mobile number box."""

    def test_checkout_code_moves_to_the_new_number(self):
        Product.objects.create(name="Test Lock", slug="test-lock", price=Decimal("1000"), stock=10)
        data = {"name": "Guest Buyer", "phone": "01912345678", "district": "Dhaka", "thana": "Dhanmondi",
                "address": "House 12, Road 5, Dhanmondi", "payment": "cod", "lines": [{"id": "test-lock", "qty": 1}]}
        self.client.post("/api/checkout/", json.dumps(data), content_type="application/json")
        r = self.client.post("/account/verify/change-number/", {"phone": "01812345678"})
        self.assertRedirects(r, "/account/verify/", fetch_redirect_response=False)
        self.assertTrue(self.sent[-1]["url"])
        self.assertEqual(OtpCode.objects.filter(cancelled=False).get().phone, "01812345678")
        self.client.post("/account/verify/", {"code": self.last_code()})
        self.assertEqual(Order.objects.get().phone, "01812345678")

    def test_login_to_unknown_number_keeps_the_old_code(self):
        Customer.objects.create(phone="01712345678", name="Rahim")
        self.client.post("/account/login/", {"phone": "01712345678"})
        r = self.client.post("/account/verify/change-number/", {"phone": "01812345678"})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "No account uses this number yet")
        self.assertEqual(OtpCode.objects.filter(cancelled=False).get().phone, "01712345678")

    def test_bad_number_stays_on_the_change_page(self):
        Customer.objects.create(phone="01712345678", name="Rahim")
        self.client.post("/account/login/", {"phone": "01712345678"})
        r = self.client.post("/account/verify/change-number/", {"phone": "12345"})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Enter a valid Bangladeshi mobile number")
        self.assertEqual(OtpCode.objects.filter(cancelled=False).get().phone, "01712345678")

    def test_code_page_links_to_the_change_page_and_waits_five_minutes(self):
        Customer.objects.create(phone="01712345678", name="Rahim")
        site = SiteSettings.load()
        site.otp_resend_seconds = 300
        site.save()
        self.client.post("/account/login/", {"phone": "01712345678"})
        page = self.client.get("/account/verify/").content.decode()
        self.assertIn('href="/account/verify/change-number/"', page)
        self.assertNotIn('id="otpChange"', page)
        self.assertRegex(page, r'data-wait="(29\d|300)"')
        self.assertEqual(SiteSettings._meta.get_field("otp_resend_seconds").default, 300)
        change = self.client.get("/account/verify/change-number/")
        self.assertEqual(change.status_code, 200)
        self.assertContains(change, "Change mobile number")
        self.assertContains(change, 'name="phone"')
        self.assertContains(change, 'href="/account/verify/"')

    def test_change_page_without_a_pending_code_goes_to_login(self):
        self.assertRedirects(self.client.get("/account/verify/change-number/"), "/account/login/",
                             fetch_redirect_response=False)
