
"""
Editable storefront text: {% load cms_tags %}.

    {% cms "home.hero.lead" %}{% translate "Built-in text" %}{% endcms %}
    {% cms "home.hero.title" html %}...may contain <span>/<strong>...{% endcms %}

Shows the admin value (Website Content → Page text) for the page's language,
falling back to English, then to the built-in text between the tags. Rows
are created from these tags by manage.py sync_content.

    {% cms_items "home.steps" as steps %}  → active Page list items, in order
    {{ page.body|page_body }}              → paragraphs / ## headings / - bullets
    {{ page.body|faq_pairs }}              → [{"q":..., "a":...}] from Q:/A: lines
    {{ product.description|rich }}         → CKEditor HTML (cleaned) or plain text as paragraphs
    {{ item.text|rich_inline }}             → same, for text already inside a <p>
    {{ item.text|plain }}                   → no tags (previews, line lists)
"""

import re

from django import template
from django.utils.html import conditional_escape, escape
from django.utils.safestring import mark_safe
from django.utils.translation import get_language

from web import richtext

register = template.Library()


def _request_cache(context, name):
    request = context.get("request")
    cache = getattr(request, name, None) if request is not None else None

    if cache is None:
        cache = {}
        if request is not None:
            setattr(request, name, cache)

    return cache


def _blocks(context):
    from web.models import ContentBlock

    cache = _request_cache(context, "_cms_blocks")
    lang = get_language() or "en"

    if lang not in cache:
        cache[lang] = {
            b.key: (b.value, b.allow_html)
            for b in ContentBlock.objects.all()
        }

    return cache[lang]


class CmsNode(template.Node):

    def __init__(self, key, allow_html, nodelist):
        self.key = key
        self.allow_html = allow_html
        self.nodelist = nodelist

    def render(self, context):
        value, allow_html = _blocks(context).get(
            self.key, ("", False)
        )

        if value and value.strip():
            return mark_safe(value) if allow_html else conditional_escape(value)

        return self.nodelist.render(context)


@register.tag("cms")
def do_cms(parser, token):
    bits = token.split_contents()

    if (
        len(bits) not in (2, 3)
        or bits[1][0] not in "\"'"
        or (len(bits) == 3 and bits[2] != "html")
    ):
        raise template.TemplateSyntaxError(
            'Usage: {% cms "page.key" [html] %}default{% endcms %}'
        )

    nodelist = parser.parse(("endcms",))
    parser.delete_first_token()

    return CmsNode(
        bits[1][1:-1],
        len(bits) == 3,
        nodelist
    )


@register.simple_tag(takes_context=True)
def cms_items(context, group):
    from web.models import ContentItem

    cache = _request_cache(context, "_cms_items")
    lang = get_language() or "en"

    if lang not in cache:
        grouped = {}

        for item in ContentItem.objects.filter(is_active=True):
            grouped.setdefault(item.group, []).append(item)

        cache[lang] = grouped

    return cache[lang].get(group, [])


_HEADING = re.compile(r"^#{2,3}\s+")


@register.filter
def page_body(text):
    """
    Plain text → safe HTML:
    blank line = new paragraph
    ## / ### = heading
    - / • = bullet list

    CKEditor HTML is cleaned and displayed with its formatting.
    """

    if richtext.is_html(text):
        return richtext.rich(text)

    html = []

    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")

    for block in re.split(r"\n\s*\n+", text.strip()):

        lines = [
            line.rstrip()
            for line in block.split("\n")
            if line.strip()
        ]

        if not lines:
            continue

        # Heading
        if len(lines) == 1 and _HEADING.match(lines[0]):
            heading = _HEADING.sub("", lines[0])
            html.append(f"<h2>{escape(heading)}</h2>")

        # Bullet list
        elif all(
            line.lstrip().startswith(("- ", "• "))
            for line in lines
        ):
            items = "".join(
                f"<li>{escape(line.lstrip()[2:].strip())}</li>"
                for line in lines
            )

            html.append(
                f'<ul class="check-list policy-list">{items}</ul>'
            )

        # Normal paragraph
        else:

            if _HEADING.match(lines[0]):
                heading = _HEADING.sub("", lines[0])
                html.append(f"<h2>{escape(heading)}</h2>")
                lines = lines[1:]

            if lines:
                paragraph = "<br>".join(
                    escape(line) for line in lines
                )

                html.append(f"<p>{paragraph}</p>")

    return mark_safe("\n".join(html))


@register.filter
def faq_pairs(text):
    """
    'Q: ...' / 'A: ...' lines → [{"q": ..., "a": ...}].
    Supports CKEditor HTML and plain text.
    """

    pairs = []
    current = None

    if richtext.is_html(text):
        text = richtext.plain(text)
        text = re.sub(r"\s*\n\s*", "\n", text)

    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")

    for line in text.split("\n") + [""]:

        stripped = line.strip()
        head = stripped[:2].upper()

        if head == "Q:":

            if current and current["a"]:
                pairs.append(current)

            current = {
                "q": stripped[2:].strip(),
                "a": ""
            }

        elif head == "A:" and current is not None:

            current["a"] = (
                current["a"] + "\n" + stripped[2:].strip()
            ).strip()

        elif not stripped:

            if current and current["a"]:
                pairs.append(current)

            current = None

        elif current is not None:

            current["a"] = (
                current["a"] + "\n" + stripped
            ).strip()

    return pairs


@register.filter
def rich(text):
    return richtext.rich(text)


@register.filter
def rich_inline(text):
    return richtext.rich_inline(text)


@register.filter
def plain(text):
    return richtext.plain(text)


@register.filter
def lines(text):
    """
    Non-empty lines of a text box.
    CKEditor paragraphs / list items count as lines.
    Bullets are removed.
    """

    out = []

    for line in richtext.plain(text).splitlines():

        line = line.strip()

        if line.startswith(("- ", "• ")):
            line = line[2:].strip()

        if line:
            out.append(line)

    return out


@register.simple_tag(takes_context=True)
def page_faq(context):
    """FAQ rows of the fixed page being shown (Home, Products, Portfolio, About, Contact).
    Edited in admin → Website → Page SEO & FAQ."""
    from web.models import PageSeo
    from web.product_page import clean_faq

    request = context.get("request")
    match = getattr(request, "resolver_match", None)
    name = match.url_name if match else ""
    if name not in dict(PageSeo.PAGES):
        return []
    row = PageSeo.objects.filter(page=name).first()
    return clean_faq(row.faq) if row else []


@register.filter
def faq_list(value):
    """Stored FAQ JSON → [{"q", "a"}] with empty rows dropped."""
    from web.product_page import clean_faq

    return clean_faq(value)
