from typing import Dict, Any, List, Tuple

from docutils import nodes
from sphinx.application import Sphinx
from sphinx.environment import BuildEnvironment
from sphinx.util import logging

from node import SEORedirectNode
from directive import SEORedirectDirective
from walker import DoctreeWalker

# Sphinx logger
logger = logging.getLogger(__name__)


def setup(app: Sphinx) -> Dict[str, Any]:
    """
    Sphinx extension setup function.

    :param app: The Sphinx Application instance
    :return: A dict of Sphinx extension options
    """
    # FIXME: add config setting for template HTML file
    # FIXME: add config setting for redirect title
    app.add_directive("seo-redirect", SEORedirectDirective)
    app.add_node(SEORedirectNode)
    app.connect("env-purge-doc", env_purge_doc)
    app.connect("env-merge-info", env_merge_info)
    app.connect("html-collect-pages", html_collect_pages)
    app.connect("doctree-resolved", doctree_resolved)
    return {
        "version": "0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }


def env_purge_doc(app: Sphinx, env: BuildEnvironment, docname: str) -> None:
    """
    Purge an existing document from the pickled document list.
    This function is called when the Sphinx `env-purge-doc` event is fired.

    :param app: The Sphinx instance; unused
    :param env: The Sphinx BuildEnvironment
    :param docname: The name of the document to purge
    """
    if hasattr(env, "seo_redirect_redirects"):
        if docname in env.seo_redirect_redirects:
            logger.verbose(
                "env_purge_doc: redirects contains %s; removing it" % docname
            )
            env.seo_redirect_redirects.pop(docname)


def env_merge_info(
    app: Sphinx, env: BuildEnvironment, docnames: List[str], other: BuildEnvironment
) -> None:
    """
    Merge collected document names from parallel readers (workers) into the master Sphinx environment.
    This function is called when the Sphinx `env-merge-info` event is fired.

    :param app: The Sphinx Application instance; unused
    :param env: The master Sphinx BuildEnvironment
    :param docnames: A list of the document names to merge; unused
    :param other: The Sphinx BuildEnvironment from the reader worker
    """
    if not hasattr(env, "seo_redirect_redirects"):
        env.seo_redirect_redirects = dict()
    # Add any links that were present in the reader worker's environment
    if hasattr(other, "seo_redirect_redirects"):
        for linkKey in other.seo_redirect_redirects:
            if linkKey in env.seo_redirect_redirects:
                env.seo_redirect_redirects[linkKey].extend(
                    other.seo_redirect_redirects[linkKey]
                )
            else:
                env.seo_redirect_redirects[linkKey] = other.seo_redirect_redirects[
                    linkKey
                ]


def html_collect_pages(app: Sphinx) -> List[Tuple[str, Dict[str, Any], str]]:
    """
    Collect the redirect page files.

    :param app: The Sphinx Application instance
    :return: A list of redirect pages to create
    """
    redirect_pages: List[Tuple[str, Dict[str, Any], str]] = list()
    if hasattr(app.env, "seo_redirect_redirects"):
        # get html_baseurl
        html_baseurl = ""
        if app.config.html_baseurl != "":
            html_baseurl = app.config.html_baseurl
        # return an entry for each redirect page to write
        for redir_from in app.env.seo_redirect_redirects:
            for redir_to in app.env.seo_redirect_redirects[redir_from]:
                to_uri = html_baseurl
                if not html_baseurl.endswith("/"):
                    to_uri += "/"
                if "#" in str(redir_to):
                    toks: List[str] = str(redir_to).split("#")
                    if len(toks) == 1:
                        to_uri += "%s.html" % toks[0]
                    elif len(toks) >= 2:
                        to_uri += "%s.html#%s" % (toks[0], toks[1])
                    else:
                        to_uri += "%s.html" % redir_to
                else:
                    to_uri += "%s.html" % redir_to
                logger.verbose(
                    "html_collect_pages: Redirecting %s to %s" % (redir_from, to_uri)
                )
                redirect_pages.append(
                    (
                        redir_from,
                        {
                            "title": "redirecting...",
                            "to_uri": to_uri,
                        },
                        "redirective.html",
                    )
                )
    return redirect_pages


def doctree_resolved(app: Sphinx, doctree: nodes.document, docname: str) -> None:
    """
    Wallk the doctree and assemble the list of redirects
    :param app: The Sphinx application instance
    :param doctree: The resolved doctree
    :param docname: The name of the document
    :return:
    """
    doctree_walker: DoctreeWalker = DoctreeWalker(doctree)
    doctree.walk(doctree_walker)
    if len(doctree_walker.section_redirects) == 0:
        return
    if not hasattr(app.env, "seo_redirect_redirects"):
        app.env.seo_redirect_redirects = dict()
    for section_id in doctree_walker.section_redirects:
        # from: section_redirects[section_id]...
        for redirect_from in doctree_walker.section_redirects[section_id]:
            # to: docname + '#' + section_id
            if section_id == doctree_walker.root_section:
                redirect_to = docname
            else:
                redirect_to = "%s#%s" % (docname, section_id)
            logger.verbose(' >> %s' % redirect_to)
            if redirect_from in app.env.seo_redirect_redirects:
                app.env.seo_redirect_redirects[redirect_from].append(redirect_to)
            else:
                app.env.seo_redirect_redirects[redirect_from] = [redirect_to]
