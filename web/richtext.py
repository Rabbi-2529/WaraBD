"""Rich text from CKEditor (admin) → safe HTML on the website.

Text written before CKEditor (plain text with blank lines between
paragraphs) keeps working: anything without HTML tags is treated as plain
text and turned into paragraphs, exactly as before.

    rich(text)         block HTML: <p>, headings, lists, tables, images, links
    rich_inline(text)  for places already inside a <p> or <span>: bold / italic / links / line breaks only
    plain(text)        no tags at all (meta descriptions, JS cards, short previews)
"""

import html
import re

import nh3
from django.utils.html import escape, linebreaks
from django.utils.safestring import mark_safe

BLOCK_TAGS = {
    "p", "br", "strong", "b", "em", "i", "u", "s", "sub", "sup", "a", "span", "code", "pre", "hr",
    "h2", "h3", "h4", "h5", "ul", "ol", "li", "blockquote",
    "table", "thead", "tbody", "tfoot", "tr", "th", "td", "caption",
    "figure", "figcaption", "img",
}
INLINE_TAGS = {"strong", "b", "em", "i", "u", "s", "sub", "sup", "a", "br", "span", "code"}
ATTRIBUTES = {
    "a": {"href", "title", "target"},
    "img": {"src", "alt", "width", "height", "title", "loading"},
    "figure": {"class", "style"},
    "td": {"colspan", "rowspan"},
    "th": {"colspan", "rowspan", "scope"},
    "ol": {"start", "reversed"},
}
# CKEditor's own layout classes for images / tables (nothing else).
ALLOWED_CLASSES = {"image", "image_resized", "image-style-side", "image-style-align-left",
                   "image-style-align-right", "image-style-align-center", "image-style-block-align-left",
                   "image-style-block-align-right", "table"}
_STYLE_WIDTH = re.compile(r"^\s*width\s*:\s*\d{1,3}(\.\d+)?%\s*;?\s*$")
_HAS_TAG = re.compile(r"<\s*/?\s*[a-zA-Z][^>]*>")


def is_html(text):
    return bool(text and _HAS_TAG.search(str(text)))


def _attr_filter(element, attribute, value):
    if attribute == "class":
        kept = [c for c in value.split() if c in ALLOWED_CLASSES]
        return " ".join(kept) or None
    if attribute == "style":           # only CKEditor's resized-image width
        return value if element == "figure" and _STYLE_WIDTH.match(value) else None
    if attribute == "target":
        return "_blank" if value == "_blank" else None
    return value


def sanitize(value, tags=BLOCK_TAGS):
    return nh3.clean(
        str(value or ""),
        tags=tags,
        attributes={k: v for k, v in ATTRIBUTES.items() if k in tags},
        attribute_filter=_attr_filter,
        url_schemes={"http", "https", "mailto", "tel"},
        link_rel="noopener noreferrer",
    )


def rich(value):
    """Block HTML for a description / body."""
    if not value:
        return ""
    if is_html(value):
        cleaned = sanitize(value)
        # Lazy-load pictures inside long descriptions.
        cleaned = re.sub(r"<img(?![^>]*\bloading=)", '<img loading="lazy"', cleaned)
        return mark_safe(cleaned)
    return mark_safe(linebreaks(str(value), autoescape=True))


def rich_inline(value):
    """For text placed inside an existing <p>: paragraphs become line breaks, blocks are dropped."""
    if not value:
        return ""
    if is_html(value):
        text = str(value)
        text = re.sub(r"</(p|h[1-6]|li|blockquote|div)>\s*", "<br>", text, flags=re.I)
        text = re.sub(r"<li[^>]*>", "• ", text, flags=re.I)
        cleaned = sanitize(text, INLINE_TAGS).strip()
        cleaned = re.sub(r"(<br\s*/?>\s*)+$", "", cleaned)
        return mark_safe(cleaned)
    return mark_safe(escape(str(value)).replace("\r\n", "\n").replace("\n", "<br>"))


def plain(value):
    """Text only. Paragraphs / list items / <br> become new lines."""
    if not value:
        return ""
    text = str(value)
    if not is_html(text):
        return text
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"</(p|h[1-6]|li|blockquote|div|tr|figure)>", "\n\n", text, flags=re.I)
    text = re.sub(r"<li[^>]*>", "- ", text, flags=re.I)
    text = nh3.clean(text, tags=set())
    text = html.unescape(text)
    text = re.sub(r"[ \t ]+", " ", text)
    return re.sub(r"\n\s*\n\s*(\n\s*)+", "\n\n", text).strip()
