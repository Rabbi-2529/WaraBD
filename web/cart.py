
"""
WaRa BD — Session-Based Shopping Cart

Stores cart data in:
request.session["cart"]

Structure:
{
    "1": {
        "quantity": 2,
        "price": "500.00"
    }
}

Important:
- Product prices are always read from the database.
- Client-submitted prices are never trusted.
- Cart quantities are validated.
- Deleted products are safely ignored and removed.
- Cart data is stored in the Django session.
"""

from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError


class Cart:
    SESSION_KEY = "cart"
    MAX_QUANTITY = 99

    def __init__(self, request):
        self.session = request.session

        cart = self.session.get(self.SESSION_KEY)

        if not isinstance(cart, dict):
            cart = {}
            self.session[self.SESSION_KEY] = cart
            self.session.modified = True

        self.cart = cart

    # ==========================================================
    # VALIDATION
    # ==========================================================

    @classmethod
    def _validate_quantity(cls, quantity):
        """
        Validate cart quantity.

        Accepts positive integers only.
        Boolean values are rejected because bool is a subclass of int.
        """

        if isinstance(quantity, bool):
            raise ValidationError("Invalid product quantity.")

        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            raise ValidationError("Invalid product quantity.")

        if quantity < 1:
            raise ValidationError("Quantity must be at least 1.")

        if quantity > cls.MAX_QUANTITY:
            raise ValidationError(
                f"Maximum quantity allowed is {cls.MAX_QUANTITY}."
            )

        return quantity

    # ==========================================================
    # CART MUTATION
    # ==========================================================

    def add(self, product, quantity=1, override=False):
        """
        Add a product to the cart.

        Args:
            product: Product model instance.
            quantity: Quantity to add.
            override: Replace existing quantity instead of adding.
        """

        from .models import Product

        if not isinstance(product, Product):
            raise TypeError("Expected a Product instance.")

        quantity = self._validate_quantity(quantity)

        product_id = str(product.pk)

        if product_id not in self.cart:
            self.cart[product_id] = {
                "quantity": 0,
                "price": str(product.current_price),
            }

        if override:
            self.cart[product_id]["quantity"] = quantity
        else:
            new_quantity = (
                self.cart[product_id].get("quantity", 0) + quantity
            )

            self.cart[product_id]["quantity"] = self._validate_quantity(
                new_quantity
            )

        self.cart[product_id]["price"] = str(product.current_price)

        self.save()

    def update(self, product, quantity):
        """
        Update an existing product quantity.
        """

        quantity = self._validate_quantity(quantity)

        self.add(
            product=product,
            quantity=quantity,
            override=True,
        )

    def remove(self, product):
        """
        Remove a product from the cart.
        """

        product_id = str(product.pk)

        if product_id in self.cart:
            del self.cart[product_id]
            self.save()

    def clear(self):
        """
        Empty the cart.
        """

        self.cart = {}
        self.session[self.SESSION_KEY] = {}
        self.save()

    def save(self):
        """
        Mark the session as modified.
        """

        self.session[self.SESSION_KEY] = self.cart
        self.session.modified = True

    # ==========================================================
    # CART ITERATION
    # ==========================================================

    def __iter__(self):
        """
        Iterate through cart items.

        Product information and prices are always retrieved
        from the database.
        """

        from .models import Product

        product_ids = list(self.cart.keys())

        products = Product.objects.filter(
            pk__in=product_ids
        ).select_related("category")

        valid_product_ids = set()

        for product in products:
            product_id = str(product.pk)
            valid_product_ids.add(product_id)

            item = self.cart.get(product_id, {})

            try:
                quantity = self._validate_quantity(
                    item.get("quantity", 1)
                )
            except ValidationError:
                continue

            price = product.current_price

            yield {
                "product": product,
                "quantity": quantity,
                "price": price,
                "total_price": price * quantity,
            }

        # Remove products that no longer exist.
        missing_ids = set(product_ids) - valid_product_ids

        if missing_ids:
            for product_id in missing_ids:
                self.cart.pop(product_id, None)

            self.save()

    # ==========================================================
    # CART TOTALS
    # ==========================================================

    def __len__(self):
        """
        Return total quantity of all cart items.
        """

        total_quantity = 0

        for item in self.cart.values():
            try:
                quantity = self._validate_quantity(
                    item.get("quantity", 0)
                )
                total_quantity += quantity
            except ValidationError:
                continue

        return total_quantity

    def get_total(self):
        """
        Calculate the total cart price using current database prices.
        """

        from .models import Product

        product_ids = list(self.cart.keys())

        products = Product.objects.filter(
            pk__in=product_ids
        )

        total = Decimal("0.00")

        for product in products:
            item = self.cart.get(str(product.pk), {})

            try:
                quantity = self._validate_quantity(
                    item.get("quantity", 0)
                )
            except ValidationError:
                continue

            total += product.current_price * quantity

        return total

    # ==========================================================
    # ADDITIONAL HELPERS
    # ==========================================================

    def get_item(self, product):
        """
        Get a cart item by Product instance.
        """

        product_id = str(product.pk)
        item = self.cart.get(product_id)

        if not item:
            return None

        try:
            quantity = self._validate_quantity(
                item.get("quantity", 0)
            )
        except ValidationError:
            return None

        return {
            "product": product,
            "quantity": quantity,
            "price": product.current_price,
            "total_price": product.current_price * quantity,
        }

    def get_quantity(self, product):
        """
        Get the quantity of a specific product.
        """

        item = self.get_item(product)

        return item["quantity"] if item else 0

    def is_empty(self):
        """
        Check whether the cart contains any valid items.
        """

        return not any(iter(self))

    def count_items(self):
        """
        Return the number of distinct products in the cart.
        """

        return sum(1 for _ in self)
