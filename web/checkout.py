"""Turn validated checkout data into an Order.

Used by the checkout API (orders that need no SMS code) and by the OTP
page once the customer has entered the right code.
"""

import logging

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

from .cart import Cart
from .delivery import DeliveryError, delivery_quote
from .emails import send_admin_new_order, send_order_confirmation
from .models import Product
from .services import place_order

logger = logging.getLogger(__name__)


def place_checkout_order(request, cleaned, customer=None):
    """Returns (order, error_message, http_status). `cleaned` comes from views._validate_checkout."""
    cart = Cart(request)
    cart.clear()

    for item in cleaned.get("lines") or []:
        if not isinstance(item, dict):
            return None, _("Invalid cart item."), 400
        try:
            qty = int(item.get("qty", 0))
        except (TypeError, ValueError):
            return None, _("Invalid product quantity."), 400
        product = Product.objects.filter(slug=str(item.get("id") or "")).first()
        if product is None:
            return None, _("A product in your cart is no longer available. Please refresh your cart."), 400
        cart.add(product, qty)

    # Delivery charge is worked out again here from the district / thana tables
    # (the order may be placed minutes later, after the SMS code).
    try:
        quote = delivery_quote(cleaned["district"], cleaned.get("thana", ""))
    except DeliveryError as exc:
        cart.clear()
        return None, str(exc), 400

    try:
        order = place_order(
            cart=cart,
            customer_data={
                "full_name": cleaned["name"],
                "phone": cleaned["phone"],
                "email": cleaned["email"],
                "address_line1": cleaned["address"],
                "city": cleaned["district"],
                "thana": cleaned.get("thana", ""),
                "country": "Bangladesh",
                "notes": cleaned["note"],
            },
            user=request.user if request.user.is_authenticated else None,
            delivery_zone=quote["zone"],
            delivery_fee=quote["fee"],
            payment_method=cleaned["payment"],
            payment_sender=cleaned["sender"],
            transaction_id=cleaned["trx"],
        )
    except ValidationError as exc:  # includes StockError
        cart.clear()
        return None, " ".join(exc.messages), 400
    except Exception:
        cart.clear()
        logger.exception("Checkout failed")
        return None, _("Something went wrong. Please try again or call us."), 500

    cart.clear()

    if customer:
        order.customer = customer
        order.save(update_fields=["customer", "updated_at"])
        _remember_address(customer, cleaned)

    try:
        if order.email:
            send_order_confirmation(order)
        send_admin_new_order(order)
    except Exception:
        logger.exception("Failed to send email for order %s", order.order_number)

    return order, "", 200


def _remember_address(customer, cleaned):
    """Save the first delivery address to the customer's address book."""
    from customers.models import CustomerAddress

    if customer.addresses.exists():
        return
    CustomerAddress.objects.create(
        customer=customer, label="", name=cleaned["name"], phone=cleaned["phone"],
        district=cleaned["district"], thana=cleaned.get("thana", ""), address=cleaned["address"], is_default=True,
    )
