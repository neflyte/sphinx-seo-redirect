__version__ = "0.1.0"

from typing import Dict, Any
from sphinx.application import Sphinx

from .directive import SEORedirectDirective
from .node import SEORedirectNode
from .sphinx import (
    CONFIG_OPTION_REDIRECTS,
    OPTION_REDIRECTS_DEFAULT,
    CONFIG_OPTION_TEMPLATE_FILE,
    OPTION_TEMPLATE_FILE_DEFAULT,
    CONFIG_URL_PATH_PREFIX,
    URL_PATH_PREFIX_DEFAULT,
    CONFIG_WRITE_EXTENSIONLESS_PAGES,
    WRITE_EXTENSIONLESS_PAGES_DEFAULT,
    builder_inited,
    env_updated,
    html_page_context,
    html_collect_pages,
    build_finished,
)


def setup(app: Sphinx) -> Dict[str, Any]:
    """
    Sphinx extension setup function.

    :param app: The Sphinx Application instance
    :return: A dict of Sphinx extension options
    """
    # FIXME: add config setting for template HTML file
    # FIXME: add config setting for redirect title
    app.add_config_value(CONFIG_OPTION_REDIRECTS, OPTION_REDIRECTS_DEFAULT, "env")
    app.add_config_value(
        CONFIG_OPTION_TEMPLATE_FILE, OPTION_TEMPLATE_FILE_DEFAULT, "env"
    )
    app.add_config_value(CONFIG_URL_PATH_PREFIX, URL_PATH_PREFIX_DEFAULT, "env")
    app.add_config_value(
        CONFIG_WRITE_EXTENSIONLESS_PAGES, WRITE_EXTENSIONLESS_PAGES_DEFAULT, "env"
    )
    app.add_directive("seo-redirect", SEORedirectDirective)
    app.add_node(SEORedirectNode)
    app.connect("builder-inited", builder_inited)
    app.connect("env-updated", env_updated)
    app.connect("html-page-context", html_page_context)
    app.connect("html-collect-pages", html_collect_pages)
    app.connect("build-finished", build_finished)
    return {
        "version": __version__,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
