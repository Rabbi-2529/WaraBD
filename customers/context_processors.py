def customer(request):
    """`customer` in every template: the logged-in shop customer or None."""
    value = getattr(request, "customer", None)
    # SimpleLazyObject wrapping None is truthy, so unwrap it.
    return {"customer": value if value else None}
