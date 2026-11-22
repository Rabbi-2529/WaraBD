
"""
WaRa BD — Order Business Logic

All order creation and cancellation operations MUST be transactional.

Responsibilities:
- Validate cart items.
- Lock product rows before checking stock.
- Prevent overselling on databases supporting SELECT FOR UPDATE.
- Calculate totals using current database prices.
- Save price snapshots in OrderItem.
- Decrement stock atomically.
- Restore stock only once when cancelling an order.
"""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext as _

from .models import Order, OrderItem, Product, SiteSettings


class StockError(ValidationError):
    """Raised when requested quantity exceeds available stock."""


def delivery_fee_for(zone):
    """Delivery fee in BDT for a zone, read from Site Settings."""
    site = SiteSettings.load()
    if zone == Order.ZONE_OUTSIDE:
        return Decimal(site.delivery_outside_fee)
    if zone == Order.ZONE_INSIDE:
        return Decimal(site.delivery_inside_fee)
    raise ValidationError(_("Please choose a delivery area."))


# ==============================================================================
# PLACE ORDER
# ==============================================================================

@transaction.atomic
def place_order(
    *,
    cart,
    customer_data,
    user=None,
    delivery_zone=Order.ZONE_INSIDE,
    delivery_fee=None,
    payment_method="cod",
    payment_sender="",
    transaction_id="",
):
    """
    Create an Order and its OrderItems atomically.

    Args:
        cart:
            Cart instance from web.cart.Cart.

        customer_data:
            Dictionary containing validated CheckoutForm data.

        user:
            Authenticated user or None.

        delivery_zone:
            "inside" or "outside" Dhaka. The fee comes from Site Settings,
            never from the browser.

        payment_method / payment_sender / transaction_id:
            bKash and Nagad orders keep the sender number and TrxID and
            start as "Awaiting verification" until staff confirm them.

    Returns:
        Order instance.

    Raises:
        StockError:
            If cart is empty, product is unavailable, or stock is insufficient.

        ValidationError:
            If cart data is invalid.
    """

    # --------------------------------------------------------------------------
    # 1. Read cart items
    # --------------------------------------------------------------------------

    items = list(cart)

    if not items:
        raise StockError(_("Your cart is empty."))

    # Validate quantities and collect product IDs.
    product_quantities = {}

    for item in items:
        product = item.get("product")
        quantity = item.get("quantity")

        if product is None:
            raise StockError(_("A product in your cart is unavailable."))

        if isinstance(quantity, bool) or not isinstance(quantity, int):
            raise StockError(_("Invalid product quantity."))

        if quantity < 1 or quantity > 99:
            raise StockError(_("Product quantity must be between 1 and 99."))

        product_id = product.pk

        if product_id in product_quantities:
            product_quantities[product_id] += quantity
        else:
            product_quantities[product_id] = quantity

    product_ids = sorted(product_quantities.keys())

    # --------------------------------------------------------------------------
    # 2. Lock product rows
    # --------------------------------------------------------------------------

    locked_products = list(
        Product.objects.select_for_update()
        .filter(pk__in=product_ids)
        .order_by("pk")
    )

    locked = {
        product.pk: product
        for product in locked_products
    }

    # Detect products deleted or unavailable after cart loading.
    missing_ids = set(product_ids) - set(locked.keys())

    if missing_ids:
        raise StockError(
            _("One or more products in your cart are no longer available. Please refresh your cart.")
        )

    # --------------------------------------------------------------------------
    # 3. Validate product availability and stock
    # --------------------------------------------------------------------------

    for product_id, quantity in product_quantities.items():

        product = locked[product_id]

        if not product.is_active:
            raise StockError(
                _('"%(name)s" is currently unavailable.') % {"name": product.name}
            )

        if product.stock < quantity:
            raise StockError(
                _('"%(name)s" only has %(stock)s in stock. You requested %(quantity)s.')
                % {"name": product.name, "stock": product.stock, "quantity": quantity}
            )

    # --------------------------------------------------------------------------
    # 4. Calculate subtotal using locked database prices
    # --------------------------------------------------------------------------

    subtotal = sum(
        (
            locked[product_id].current_price * quantity
            for product_id, quantity in product_quantities.items()
        ),
        start=locked_products[0].current_price * 0,
    )

    # delivery_fee comes from the district / thana table (web.delivery);
    # without it fall back to the Site Settings inside/outside Dhaka fee.
    shipping = Decimal(delivery_fee) if delivery_fee is not None else delivery_fee_for(delivery_zone)
    total = subtotal + shipping

    if payment_method not in dict(Order.PAYMENT_METHOD_CHOICES):
        raise ValidationError(_("Please choose a payment method."))

    is_mobile_payment = payment_method in Order.MOBILE_PAYMENT_METHODS
    payment_status = (
        Order.PAYMENT_VERIFYING if is_mobile_payment else Order.PAYMENT_UNPAID
    )

    # --------------------------------------------------------------------------
    # 5. Create order
    # --------------------------------------------------------------------------

    order = Order.objects.create(
        user=user if getattr(user, "is_authenticated", False) else None,

        full_name=customer_data["full_name"],
        email=customer_data["email"],
        phone=customer_data["phone"],

        address_line1=customer_data["address_line1"],
        address_line2=customer_data.get("address_line2", ""),

        city=customer_data["city"],
        thana=customer_data.get("thana", ""),
        postal_code=customer_data.get("postal_code", ""),
        country=customer_data.get("country", "Bangladesh"),

        notes=customer_data.get("notes", ""),

        delivery_zone=delivery_zone,
        subtotal=subtotal,
        shipping=shipping,
        total=total,

        status=Order.STATUS_PENDING,
        payment_method=payment_method,
        payment_status=payment_status,
        payment_sender=payment_sender if is_mobile_payment else "",
        transaction_id=transaction_id if is_mobile_payment else "",
    )

    # --------------------------------------------------------------------------
    # 6. Create order items and decrement stock
    # --------------------------------------------------------------------------

    order_items = []

    for product_id, quantity in product_quantities.items():

        product = locked[product_id]

        current_price = product.current_price

        order_items.append(
            OrderItem(
                order=order,
                product=product,
                quantity=quantity,
                price=current_price,
            )
        )

        product.stock -= quantity

    OrderItem.objects.bulk_create(order_items)

    # Save stock changes.
    for product in locked_products:
        if product.pk in product_quantities:
            product.save(update_fields=["stock", "updated_at"])

    return order


# ==============================================================================
# CANCEL ORDER
# ==============================================================================

@transaction.atomic
def cancel_order(order, restore_stock=True):
    """
    Cancel an order safely.

    The order row is locked first to prevent two simultaneous
    cancellation requests from restoring stock twice.

    Args:
        order:
            Order instance.

        restore_stock:
            Restore product stock when True.

    Returns:
        Updated Order instance.
    """

    # --------------------------------------------------------------------------
    # 1. Lock and refresh the order
    # --------------------------------------------------------------------------

    locked_order = (
        Order.objects.select_for_update()
        .get(pk=order.pk)
    )

    # Already cancelled: do not restore stock again.
    if locked_order.status == Order.STATUS_CANCELLED:
        return locked_order

    # --------------------------------------------------------------------------
    # 2. Restore product stock
    # --------------------------------------------------------------------------

    if restore_stock:

        order_items = list(
            locked_order.items.all().order_by("product_id")
        )

        product_ids = sorted(
            {item.product_id for item in order_items}
        )

        locked_products = {
            product.pk: product
            for product in (
                Product.objects.select_for_update()
                .filter(pk__in=product_ids)
                .order_by("pk")
            )
        }

        for item in order_items:

            product = locked_products.get(item.product_id)

            if product is not None:
                product.stock += item.quantity

        for product in locked_products.values():
            product.save(update_fields=["stock", "updated_at"])

    # --------------------------------------------------------------------------
    # 3. Update order status
    # --------------------------------------------------------------------------

    locked_order.status = Order.STATUS_CANCELLED

    locked_order.save(
        update_fields=["status", "updated_at"]
    )

    return locked_order
