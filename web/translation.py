"""English / Bangla fields (django-modeltranslation).

Each field listed here gets `<field>_en` and `<field>_bn` database columns.
Reading `obj.<field>` returns the value for the active language (set from
the URL: "/" = English, "/bn/" = Bangla) and falls back to English when the
Bangla value is empty, so a page is never blank while translations are
still being written.
"""

from modeltranslation.translator import TranslationOptions, register

from .models import (
    Category,
    ContentBlock,
    ContentItem,
    District,
    Page,
    PageSeo,
    PortfolioProject,
    Product,
    ProductImage,
    SiteFeature,
    SiteHighlight,
    SiteSettings,
    Thana,
    TimelineStep,
    UseCase,
)

# JSON list/dict fields store [] / {} when empty; treat those as "not
# translated" too so the Bangla page shows the English list instead.
_EMPTY_LIST = []
_EMPTY_DICT = {}


@register(Category)
class CategoryTranslation(TranslationOptions):
    fields = ("name", "description")


@register(Product)
class ProductTranslation(TranslationOptions):
    fields = (
        "name",
        "subtitle",
        "short_description",
        "description_title",
        "description",
        "color",
        "warranty",
        "highlights",
        "specs",
        "features",
        "applications",
        "steps",
        "faq",
        "seo_title",
        "seo_description",
    )
    fallback_undefined = {
        "highlights": _EMPTY_LIST,
        "specs": _EMPTY_LIST,
        "features": _EMPTY_LIST,
        "steps": _EMPTY_LIST,
        "faq": _EMPTY_LIST,
        "applications": _EMPTY_DICT,
    }


@register(ProductImage)
class ProductImageTranslation(TranslationOptions):
    fields = ("caption",)


@register(PortfolioProject)
class PortfolioProjectTranslation(TranslationOptions):
    fields = ("title", "short_description", "description")


@register(SiteSettings)
class SiteSettingsTranslation(TranslationOptions):
    fields = (
        "name",
        "address",
        "hours",
        "announcement",
        "delivery_inside_eta",
        "delivery_outside_eta",
        "meta_title",
        "meta_description",
    )


@register(SiteHighlight)
class SiteHighlightTranslation(TranslationOptions):
    fields = ("title", "subtitle")


@register(SiteFeature)
class SiteFeatureTranslation(TranslationOptions):
    fields = ("title", "text", "badge", "best_for")


@register(UseCase)
class UseCaseTranslation(TranslationOptions):
    fields = ("title", "place", "text")


@register(TimelineStep)
class TimelineStepTranslation(TranslationOptions):
    fields = ("title", "text")


@register(ContentBlock)
class ContentBlockTranslation(TranslationOptions):
    fields = ("value",)


@register(ContentItem)
class ContentItemTranslation(TranslationOptions):
    fields = ("value", "title", "text")


@register(Page)
class PageTranslation(TranslationOptions):
    fields = ("title", "intro", "body", "meta_description", "seo_title")


@register(PageSeo)
class PageSeoTranslation(TranslationOptions):
    fields = ("title", "description")


@register(District)
class DistrictTranslation(TranslationOptions):
    fields = ("name", "delivery_eta")


@register(Thana)
class ThanaTranslation(TranslationOptions):
    fields = ("name",)
