from sphinx_seo_redirect.sphinx import (
    builder_inited as ext_builder_inited,
    env_updated as ext_env_updated,
    html_page_context as ext_html_page_context,
    html_collect_pages as ext_html_collect_pages,
    compute_redirects as ext_compute_redirects,
    build_js_object as ext_build_js_object,
    CONFIG_OPTION_REDIRECTS,
    CTX_HAS_FRAGMENT_REDIRECTS,
    CTX_FRAGMENT_REDIRECTS,
    DEFAULT_PAGE,
    ENV_COMPUTED_REDIRECTS,
    ENV_INTRA_PAGE_FRAGMENT_PAGES,
    ENV_DOCTREE_REDIRECTS,
)
from sphinx_seo_redirect import setup as ext_setup
from typing import Dict, List


class TestBuilderInited:
    def test_nominal(self, app):
        ext_setup(app)
        ext_builder_inited(app)
        assert hasattr(app.env, ENV_COMPUTED_REDIRECTS)
        assert hasattr(app.env, ENV_DOCTREE_REDIRECTS)


# TODO: env_purge_doc, env_merge_info


class TestEnvUpdated:
    def test_nominal(self, app):
        ext_setup(app)
        app.env.all_docs["foo"] = 0
        app.config[CONFIG_OPTION_REDIRECTS] = dict({"foo": "bar"})
        ext_builder_inited(app)
        ext_env_updated(app, app.env)
        assert hasattr(app.env, ENV_INTRA_PAGE_FRAGMENT_PAGES)
        intra_page_fragments: List[str] = getattr(
            app.env, ENV_INTRA_PAGE_FRAGMENT_PAGES
        )
        assert len(intra_page_fragments) == 1
        assert intra_page_fragments[0] == "foo"

    def test_fragment_not_in_alldocs(self, app):
        ext_setup(app)
        app.env.all_docs["foo"] = 0
        app.config[CONFIG_OPTION_REDIRECTS] = dict({"narf": "fnord"})
        ext_builder_inited(app)
        ext_env_updated(app, app.env)
        assert hasattr(app.env, ENV_INTRA_PAGE_FRAGMENT_PAGES)
        intra_page_fragments: List[str] = getattr(
            app.env, ENV_INTRA_PAGE_FRAGMENT_PAGES
        )
        assert len(intra_page_fragments) == 0

    def test_no_computed_redirects(self, app):
        ext_setup(app)
        app.env.all_docs["foo"] = 0
        app.config[CONFIG_OPTION_REDIRECTS] = dict({"": "fnord"})
        ext_builder_inited(app)
        ext_env_updated(app, app.env)
        assert hasattr(app.env, ENV_INTRA_PAGE_FRAGMENT_PAGES)
        intra_page_fragments: List[str] = getattr(
            app.env, ENV_INTRA_PAGE_FRAGMENT_PAGES
        )
        assert len(intra_page_fragments) == 0


class TestHtmlPageContext:
    def test_nominal(self, app):
        expected_templatename = "template.html"
        expected_fragment_redirects = (
            "const " + CTX_FRAGMENT_REDIRECTS + ' = Object.freeze({"-":"bar"});'
        )
        ext_setup(app)
        app.env.all_docs["foo"] = 0
        app.config[CONFIG_OPTION_REDIRECTS] = dict({"foo": "bar"})
        ext_builder_inited(app)
        ext_env_updated(app, app.env)
        ctx = dict()
        templatename = ext_html_page_context(app, "foo", "template.html", ctx, dict())
        assert templatename == expected_templatename
        assert len(ctx) == 2
        assert ctx[CTX_HAS_FRAGMENT_REDIRECTS]
        assert ctx[CTX_FRAGMENT_REDIRECTS] == expected_fragment_redirects

    def test_page_not_in_fragments(self, app):
        expected_templatename = "template.html"
        ext_setup(app)
        app.env.all_docs["foo"] = 0
        app.config[CONFIG_OPTION_REDIRECTS] = dict({"narf": "fnord"})
        ext_builder_inited(app)
        ext_env_updated(app, app.env)
        ctx = dict()
        templatename = ext_html_page_context(app, "foo", "template.html", ctx, dict())
        assert templatename == expected_templatename
        assert len(ctx) == 1
        assert not ctx[CTX_HAS_FRAGMENT_REDIRECTS]


class TestHtmlCollectPages:
    def test_nominal_simple_redirect(self, app):
        expected_collected_page = ("foo", {"to_uri": "bar"}, "simpleredirect.html")
        ext_setup(app)
        app.env.all_docs["narf"] = 0
        app.config[CONFIG_OPTION_REDIRECTS] = dict({"foo": "bar"})
        ext_builder_inited(app)
        ext_env_updated(app, app.env)
        ctx = dict()
        ext_html_page_context(app, "foo", "template.html", ctx, dict())
        collected_pages = ext_html_collect_pages(app)
        assert len(collected_pages) == 1
        assert collected_pages[0] == expected_collected_page

    def test_nominal_redirect(self, app):
        expected_jsobject = (
            "const "
            + CTX_FRAGMENT_REDIRECTS
            + ' = Object.freeze({"-":"bar","frag1":"bar#frag2"});'
        )
        expected_collected_page = (
            "foo",
            {CTX_FRAGMENT_REDIRECTS: expected_jsobject},
            "redirect.html",
        )
        ext_setup(app)
        app.env.all_docs["bar"] = 0
        app.config[CONFIG_OPTION_REDIRECTS] = dict(
            {"foo": "bar", "foo#frag1": "bar#frag2"}
        )
        ext_builder_inited(app)
        ext_env_updated(app, app.env)
        ctx = dict()
        ext_html_page_context(app, "foo", "template.html", ctx, dict())
        collected_pages = ext_html_collect_pages(app)
        assert len(collected_pages) == 1
        assert collected_pages[0] == expected_collected_page


# TODO: doctree_resolved, build_finished. compute_doctree_redirects


class TestComputeRedirects:
    def test_nominal(self, app):
        ext_setup(app)
        app.env.all_docs = {"foo": 0, "baz": 1, "fnord": 2, "qux": 3}
        redirects: Dict[str, str] = {
            "foo": "bar",
            "baz#frag1": "bar#frag1",
            "fnord#frag2": "fnord#frag3",
            "narf#frag4": "zot",
            "": "emptyredirect",
            "emptyredirect": "",
            "qux": "quux#frag5",
            "invalid#redirect#page": "should#not-work",
        }
        app.config[CONFIG_OPTION_REDIRECTS] = redirects
        expected_computed_redirects: Dict[str, Dict[str, str]] = {
            "foo": {DEFAULT_PAGE: "bar"},
            "baz": {"frag1": "bar#frag1"},
            "fnord": {"frag2": "fnord#frag3"},
            "narf": {"frag4": "zot"},
            "qux": {DEFAULT_PAGE: "quux#frag5"},
        }
        actual_computed_redirects = ext_compute_redirects(app, redirects)
        assert actual_computed_redirects == expected_computed_redirects


class TestBuildJSObject:
    def test_nominal(self, app):
        pagemap: Dict[str, str] = {
            DEFAULT_PAGE: "foo.html",
            "frag1": "foo2.html#frag2",
            "frag3": "#frag4",
        }
        expected_js_object = (
            "const "
            + CTX_FRAGMENT_REDIRECTS
            + ' = Object.freeze({"-":"foo.html","frag1":"foo2.html#frag2","frag3":"#frag4"});'
        )
        actual_js_object = ext_build_js_object(pagemap)
        assert actual_js_object == expected_js_object
