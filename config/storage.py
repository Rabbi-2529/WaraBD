"""Static file storage for production.

WhiteNoise's CompressedManifestStaticFilesStorage gives every static file a
hashed name (style.3f2a1c.css) so browsers can cache it for a year. It also
stops `collectstatic` when a CSS file points at a picture or font that is not
there — the bought Rizz admin theme does that (e.g. css/app.css → images/extra/
pet-bg.png, which the theme never shipped). This version keeps such a link as
it is instead of failing, and a missing file in a template gives its plain
name instead of a server error.
"""

from whitenoise.storage import CompressedManifestStaticFilesStorage


class ForgivingManifestStaticFilesStorage(CompressedManifestStaticFilesStorage):
    manifest_strict = False

    def hashed_name(self, name, content=None, filename=None):
        try:
            return super().hashed_name(name, content, filename)
        except ValueError:
            return name
