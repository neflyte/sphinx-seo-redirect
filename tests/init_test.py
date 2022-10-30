from sphinx_seo_redirect import (
    setup as ext_setup,
    CONFIG_OPTION_REDIRECTS,
    CONFIG_OPTION_TEMPLATE_FILE,
    CONFIG_URL_PATH_PREFIX,
    CONFIG_WRITE_EXTENSIONLESS_PAGES,
)


class TestSetup:
    def test_nominal(self, app):
        result = ext_setup(app)
        assert "parallel_read_safe" in result
        assert result["parallel_read_safe"]
        assert "parallel_write_safe" in result
        assert result["parallel_write_safe"]
        assert hasattr(app.config, CONFIG_OPTION_REDIRECTS)
        assert hasattr(app.config, CONFIG_OPTION_TEMPLATE_FILE)
        assert hasattr(app.config, CONFIG_URL_PATH_PREFIX)
        assert hasattr(app.config, CONFIG_WRITE_EXTENSIONLESS_PAGES)
