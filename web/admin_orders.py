"""Admin → Orders → Create order.

Staff take phone / WhatsApp orders here. The page (templates/admin/web/order/add_form.html
+ static/admin/js/wara-order.js) asks for the customer's mobile number first and fills in a
returning customer's details, picks district → thana (the delivery charge follows them, as on
the shop's checkout), and adds products from a search box. The order gets the next
WBYYYYMMDD### number when it is saved.
"""

from decimal import Decimal, InvalidOperation

from django import forms
from django.db.models import Count, Q, Sum
from django.http import JsonResponse
from django.utils import timezone

from .bd import PHONE_ERROR, normalize_bd_phone
from .delivery import DeliveryError, delivery_quote
from .models import District, Order, Product
from .widgets import ADMIN_SELECT2_CSS, ADMIN_SELECT2_JS

ORDER_CREATE_FIELDS = (
    "phone", "full_name", "email", "city", "thana", "address_line1", "notes",
    "status", "payment_status", "payment_method", "payment_sender", "transaction_id", "shipping",
)
MAX_QTY = 999


def _image_url(product):
    for field in (product.image, getattr(product.gallery.first(), "image", None)):
        try:
            if field:
                return field.url
        except ValueError:
            continue
    return ""


def product_row(product):
    """What the product search box and the order lines need about a product."""
    return {
        "id": product.pk,
        "text": product.name,
        "name": product.name,
        "sku": product.sku or product.model_number or "",
        "price": str(product.current_price.quantize(Decimal("0.01"))),
        "stock": product.stock,
        "active": product.is_active,
        "image": _image_url(product),
    }


class AdminOrderCreateForm(forms.ModelForm):
    """Create-order form. Products arrive as parallel lists: item_product / item_qty / item_price."""

    discount_type = forms.ChoiceField(choices=[("fixed", "৳"), ("percent", "%")], required=False)
    discount_value = forms.DecimalField(min_value=0, max_digits=10, decimal_places=2, required=False)

    class Meta:
        model = Order
        fields = ORDER_CREATE_FIELDS

    class Media:
        js = ADMIN_SELECT2_JS + ("admin/js/wara-order.js",)
        css = {"screen": ADMIN_SELECT2_CSS + ("admin/css/wara-order.css",)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.items = []
        self.quote = None
        self.discount = Decimal("0")
        self.fields["full_name"].label = "Customer name"
        self.fields["city"].label = "District"
        self.fields["thana"].required = True
        self.fields["address_line1"].label = "Address"
        self.fields["shipping"].required = False
        self.fields["payment_status"].required = False
        self.fields["status"].required = False
        self.fields["payment_method"].required = False

    def clean_phone(self):
        try:
            return normalize_bd_phone(self.cleaned_data.get("phone"))
        except ValueError:
            raise forms.ValidationError(str(PHONE_ERROR))

    def clean_full_name(self):
        name = " ".join((self.cleaned_data.get("full_name") or "").split())
        if len(name) < 2:
            raise forms.ValidationError("Enter the customer's name.")
        return name

    def clean_city(self):
        value = (self.cleaned_data.get("city") or "").strip()
        district = District.objects.filter(name_en__iexact=value, is_active=True).first()
        if district is None:
            raise forms.ValidationError("Pick the district from the list.")
        return district.name_en

    def clean_address_line1(self):
        address = " ".join((self.cleaned_data.get("address_line1") or "").split())
        if len(address) < 5:
            raise forms.ValidationError("Enter the house, road and area.")
        return address

    def clean_shipping(self):
        value = self.cleaned_data.get("shipping")
        if value is not None and value < 0:
            raise forms.ValidationError("The delivery charge cannot be negative.")
        return value

    def _read_items(self):
        ids = self.data.getlist("item_product") if hasattr(self.data, "getlist") else []
        qtys = self.data.getlist("item_qty") if hasattr(self.data, "getlist") else []
        prices = self.data.getlist("item_price") if hasattr(self.data, "getlist") else []
        rows = []
        for index, raw_id in enumerate(ids):
            try:
                pk = int(raw_id)
                qty = int(qtys[index])
                price = Decimal(str(prices[index]).replace(",", "").strip())
            except (ValueError, IndexError, InvalidOperation):
                raise forms.ValidationError("A product line is incomplete. Check the quantity and price.")
            if not 1 <= qty <= MAX_QTY:
                raise forms.ValidationError(f"Quantity must be between 1 and {MAX_QTY}.")
            if price < 0:
                raise forms.ValidationError("A price cannot be negative.")
            rows.append((pk, qty, price.quantize(Decimal("0.01"))))
        products = Product.objects.in_bulk([r[0] for r in rows])
        items = []
        for pk, qty, price in rows:
            product = products.get(pk)
            if product is None:
                raise forms.ValidationError("A product in the list no longer exists. Remove it and search again.")
            items.append((product, qty, price))
        return items

    def clean(self):
        cleaned = super().clean()
        try:
            self.items = self._read_items()
        except forms.ValidationError as exc:
            self.add_error(None, exc)
            self.items = []
        else:
            if not self.items:
                self.add_error(None, "Add at least one product to the order.")
        district, thana = cleaned.get("city"), cleaned.get("thana")
        if district:
            try:
                self.quote = delivery_quote(district, thana or "")
            except DeliveryError as exc:
                self.add_error("city", str(exc))
            else:
                if thana and self.quote["thana"] is None:
                    self.add_error("thana", "Pick the thana from the list.")
                elif self.quote["thana"] is not None:
                    cleaned["thana"] = self.quote["thana"].name_en
                if cleaned.get("shipping") is None:
                    cleaned["shipping"] = self.quote["fee"]
        value = cleaned.get("discount_value") or Decimal("0")
        if value:
            if cleaned.get("discount_type") == "percent":
                if value > 100:
                    self.add_error("discount_value", "A percentage discount must be 100 or less.")
                self.discount = (self.subtotal * min(value, Decimal("100")) / Decimal("100")).quantize(Decimal("0.01"))
            else:
                if self.items and value > self.subtotal:
                    self.add_error("discount_value", "The discount is more than the products' total.")
                self.discount = min(value, self.subtotal).quantize(Decimal("0.01"))
        method = cleaned.get("payment_method") or "cod"
        cleaned["payment_method"] = method
        cleaned["status"] = cleaned.get("status") or Order.STATUS_PENDING
        cleaned["payment_status"] = cleaned.get("payment_status") or Order.PAYMENT_UNPAID
        if method in Order.MOBILE_PAYMENT_METHODS and cleaned.get("payment_sender"):
            try:
                cleaned["payment_sender"] = normalize_bd_phone(cleaned["payment_sender"])
            except ValueError:
                self.add_error("payment_sender", str(PHONE_ERROR))
        if method not in Order.MOBILE_PAYMENT_METHODS:
            cleaned["payment_sender"] = ""
            cleaned["transaction_id"] = ""
        else:
            cleaned["transaction_id"] = (cleaned.get("transaction_id") or "").replace(" ", "").upper()
        return cleaned

    @property
    def subtotal(self):
        return sum((price * qty for _p, qty, price in self.items), Decimal("0"))


class AdminOrderChangeForm(forms.ModelForm):
    """Order page (templates/admin/web/order/change_form.html): district → thana dropdowns,
    Bangladeshi mobile number check."""

    class Meta:
        model = Order
        fields = "__all__"

    class Media:
        js = ADMIN_SELECT2_JS + ("admin/js/wara-order-address.js",)
        css = {"screen": ADMIN_SELECT2_CSS + ("admin/css/wara-order.css",)}

    def clean_phone(self):
        try:
            return normalize_bd_phone(self.cleaned_data.get("phone"))
        except ValueError:
            raise forms.ValidationError(str(PHONE_ERROR))


def posted_items(request):
    """Order lines typed before a form error, so the page can show them again."""
    ids = request.POST.getlist("item_product")
    qtys = request.POST.getlist("item_qty")
    prices = request.POST.getlist("item_price")
    products = Product.objects.in_bulk([int(i) for i in ids if str(i).isdigit()])
    rows = []
    for index, raw in enumerate(ids):
        product = products.get(int(raw)) if str(raw).isdigit() else None
        if product is None:
            continue
        row = product_row(product)
        row["qty"] = qtys[index] if index < len(qtys) else 1
        row["price"] = prices[index] if index < len(prices) else row["price"]
        rows.append(row)
    return rows


def product_search(request):
    """GET ?q= → products by name (English / Bangla), SKU, model number or web address."""
    q = " ".join((request.GET.get("q") or "").split())[:80]
    qs = Product.objects.order_by("-is_active", "name_en")
    if q:
        qs = qs.filter(Q(name_en__icontains=q) | Q(name_bn__icontains=q) | Q(sku__icontains=q)
                       | Q(model_number__icontains=q) | Q(slug__icontains=q))
    return JsonResponse({"results": [product_row(p) for p in qs.prefetch_related("gallery")[:20]]})


def customer_lookup(request):
    """GET ?phone=01XXXXXXXXX → the customer's details, saved addresses and order history."""
    try:
        phone = normalize_bd_phone(request.GET.get("phone"))
    except ValueError:
        return JsonResponse({"ok": False, "error": str(PHONE_ERROR)}, status=400)

    from customers.models import Customer

    customer = Customer.objects.filter(phone=phone).prefetch_related("addresses").first()
    orders = Order.objects.filter(phone=phone).order_by("-created_at")
    stats = orders.aggregate(count=Count("id"), spent=Sum("total"))
    last = orders.first()
    data = {"ok": True, "phone": phone, "found": bool(customer or last), "customer": None, "addresses": [],
            "orders": {"count": stats["count"] or 0, "spent": str(stats["spent"] or 0), "last": None}, "fill": {}}

    if last:
        data["orders"]["last"] = {
            "number": last.order_number, "status": last.get_status_display(), "total": str(last.total),
            "date": timezone.localtime(last.created_at).strftime("%d %b %Y"),
        }
        data["fill"] = {"name": last.full_name, "email": last.email, "district": last.city,
                        "thana": last.thana, "address": last.address_line1}
    if customer:
        data["customer"] = {"name": customer.name, "email": customer.email, "active": customer.is_active,
                            "since": timezone.localtime(customer.created_at).strftime("%d %b %Y")}
        addresses = list(customer.addresses.all())
        data["addresses"] = [
            {"label": a.label, "name": a.name, "phone": a.phone, "district": a.district, "thana": a.thana,
             "address": a.address, "default": a.is_default}
            for a in sorted(addresses, key=lambda a: not a.is_default)
        ]
        fill = data["fill"] or {}
        fill.update({"name": customer.name or fill.get("name", ""), "email": customer.email or fill.get("email", "")})
        if data["addresses"] and not fill.get("district"):
            first = data["addresses"][0]
            fill.update({"district": first["district"], "thana": first["thana"], "address": first["address"]})
        data["fill"] = fill
    return JsonResponse(data)
