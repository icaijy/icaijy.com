from django.contrib.staticfiles.storage import ManifestStaticFilesStorage


class HashedManifestStaticFilesStorage(ManifestStaticFilesStorage):
    """Static storage with content hashes, including ES module imports."""

    support_js_module_import_aggregation = True
