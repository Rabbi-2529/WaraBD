from django import template

from web import seo as seo_module

register = template.Library()


@register.simple_tag(takes_context=True)
def seo_data(context):
    """{% seo_data as seo %} — title, description, canonical, share image, JSON-LD for this page."""
    return seo_module.build(context)
