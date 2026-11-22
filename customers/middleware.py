from django.utils.functional import SimpleLazyObject

from .auth import get_customer


class CustomerMiddleware:
    """Sets request.customer (the logged-in shop customer, or None)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.customer = SimpleLazyObject(lambda: get_customer(request))
        return self.get_response(request)
