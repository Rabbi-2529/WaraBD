"""Turn a Product's JSON fields into clean lists for the product page.

Products keep highlights, specs, features, steps, FAQ and applications in
JSON fields that staff edit by hand in the admin, so every helper here
accepts slightly wrong shapes (dicts vs lists, other key names, blanks)
and silently drops anything unusable instead of breaking the page.
"""

import re


def _text(value):
    return str(value).strip() if value is not None else ""


def _as_list(value):
    return value if isinstance(value, list) else []


def _pick(item, *keys):
    for key in keys:
        value = _text(item.get(key))
        if value:
            return value
    return ""


def clean_highlights(value):
    return [t for t in (_text(v) for v in _as_list(value)) if t]


def clean_tags(value):
    return clean_highlights(value)


def clean_specs(value):
    """[["Model", "FT-SCL029"], ...] or [{"label": ..., "value": ...}] -> [(label, value)]"""
    rows = []
    for item in _as_list(value):
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            label, val = _text(item[0]), _text(item[1])
        elif isinstance(item, dict):
            label = _pick(item, "label", "key", "name", "title")
            val = _pick(item, "value", "val", "text")
        else:
            continue
        if label and val:
            rows.append((label, val))
    return rows


def clean_features(value):
    rows = []
    for item in _as_list(value):
        if not isinstance(item, dict):
            continue
        title = _pick(item, "title", "name")
        text = _pick(item, "text", "description", "desc")
        if title or text:
            rows.append({"icon": _pick(item, "icon") or "check", "title": title, "text": text})
    return rows


def clean_steps(value):
    rows = []
    for item in _as_list(value):
        if isinstance(item, dict):
            title, text = _pick(item, "title", "name"), _pick(item, "text", "description")
        elif isinstance(item, str):
            title, text = "", _text(item)
        else:
            continue
        if title or text:
            rows.append({"title": title, "text": text})
    return rows


_TAGS_RE = re.compile(r"<[^>]+>")


def clean_faq(value):
    rows = []
    for item in _as_list(value):
        if isinstance(item, dict):
            q = _pick(item, "q", "question")
            a = _pick(item, "a", "answer")
        elif isinstance(item, (list, tuple)) and len(item) >= 2:
            q, a = _text(item[0]), _text(item[1])
        else:
            continue
        # Older data had <strong> tags; answers are shown as plain text.
        a = _TAGS_RE.sub("", a)
        if q and a:
            rows.append({"q": q, "a": a})
    return rows


def clean_applications(value):
    value = value if isinstance(value, dict) else {}
    return {
        "compatible": clean_highlights(value.get("compatible")),
        "places": clean_highlights(value.get("places")),
    }


def description_paragraphs(text):
    """Split the description on blank lines into paragraphs."""
    parts = re.split(r"\n\s*\n", _text(text).replace("\r\n", "\n"))
    return [p.strip() for p in parts if p.strip()]


def product_images(product):
    """Main image first, then gallery images: [{"src", "caption"}]."""
    images = []
    for field, caption in [(product.image, product.name)] + [
        (g.image, g.caption or product.name) for g in product.gallery.all()
    ]:
        try:
            url = field.url if field else ""
        except (ValueError, AttributeError):
            url = ""
        if url:
            images.append({"src": url, "caption": caption})
    return images


def card_image(product):
    images = product_images(product)
    return images[0]["src"] if images else ""


def build_context(product):
    current = product.current_price
    save = product.price - current if current < product.price else 0
    applications = clean_applications(product.applications)
    return {
        "images": product_images(product),
        "price_now": current,
        "price_old": product.price if save else None,
        "save": save,
        "save_pct": round(save / product.price * 100) if save and product.price else 0,
        "can_buy": product.stock_status == product.STOCK_IN,
        "highlights": clean_highlights(product.highlights),
        "tags": clean_tags(product.tags),
        "paragraphs": description_paragraphs(product.description),
        "specs": clean_specs(product.specs),
        "features": clean_features(product.features),
        "steps": clean_steps(product.steps),
        "faq": clean_faq(product.faq),
        "applications": applications,
        "has_applications": bool(applications["compatible"] or applications["places"]),
    }
