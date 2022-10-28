from docutils import nodes
from pathlib import Path
from shutil import copyfile
from sphinx.application import Sphinx
from sphinx.environment import BuildEnvironment
from sphinx.util import logging
from sphinx.util.console import bold, colorize, term_width_line  # type: ignore
from typing import Dict, Mapping, Tuple, Any, List

from .walker import DoctreeWalker

# Global Sphinx configuration options
CONFIG_HTML_BASEURL = "html_baseurl"
# Configuration options
CONFIG_OPTION_REDIRECTS = "redirects"
CONFIG_OPTION_TEMPLATE_FILE = "redirect_html_template_file"
CONFIG_URL_PATH_PREFIX = "url_path_prefix"
CONFIG_WRITE_EXTENSIONLESS_PAGES = "redirect_write_extensionless_pages"
# Option defaults
OPTION_REDIRECTS_DEFAULT: Dict[str, str] = dict()
OPTION_TEMPLATE_FILE_DEFAULT = None
WRITE_EXTENSIONLESS_PAGES_DEFAULT = False
URL_PATH_PREFIX_DEFAULT = ""
# Environment keys
ENV_REDIRECTS_ENABLED = "redirects-enabled"
ENV_COMPUTED_REDIRECTS = "computed-redirects"  # Dict[str, Dict[str, str]]
ENV_INTRA_PAGE_FRAGMENT_PAGES = "intra-page-fragment-pages"
ENV_EXTENSIONLESS_PAGES = "extensionless-pages"
ENV_DOCTREE_REDIRECTS = "doctree-redirects"  # Dict[str, List[str]]
# HTML context keys
CTX_HAS_FRAGMENT_REDIRECTS = "has_fragment_redirects"
CTX_FRAGMENT_REDIRECTS = "fragment_redirects"
# Other constants...
DEFAULT_PAGE = "-"

# Sphinx logger
logger = logging.getLogger(__name__)


def builder_inited(app: Sphinx):
    setattr(app.env, ENV_REDIRECTS_ENABLED, True)
    if not app.config[CONFIG_OPTION_REDIRECTS]:
        logger.warning(
            "No redirects configured; disabling redirects extension for this build"
        )
        setattr(app.env, ENV_REDIRECTS_ENABLED, False)
        return
    if len(app.config[CONFIG_OPTION_REDIRECTS]) == 0:
        logger.warning(
            "Empty redirect definition; disabling redirects extension for this build"
        )
        setattr(app.env, ENV_REDIRECTS_ENABLED, False)
        return
    setattr(app.env, ENV_DOCTREE_REDIRECTS, dict())


def env_purge_doc(app: Sphinx, env: BuildEnvironment, docname: str) -> None:
    """
    Purge an existing document from the pickled document list.
    This function is called when the Sphinx `env-purge-doc` event is fired.

    :param app: The Sphinx instance; unused
    :param env: The Sphinx BuildEnvironment
    :param docname: The name of the document to purge
    """
    if hasattr(env, ENV_DOCTREE_REDIRECTS):
        doctree_redirects: Dict[str, List[str]] = getattr(env, ENV_DOCTREE_REDIRECTS)
        if docname in doctree_redirects:
            logger.verbose(
                "env_purge_doc: redirects contains %s; removing it" % docname
            )
            doctree_redirects.pop(docname)


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
    # Add any links that were present in the reader worker's environment
    if hasattr(other, ENV_DOCTREE_REDIRECTS):
        doctree_redirects: Dict[str, List[str]] = getattr(env, ENV_DOCTREE_REDIRECTS)
        other_redirects: Dict[str, List[str]] = getattr(other, ENV_DOCTREE_REDIRECTS)
        for linkKey in other_redirects:
            if linkKey in doctree_redirects:
                doctree_redirects[linkKey].extend(other_redirects[linkKey])
            else:
                doctree_redirects[linkKey] = other_redirects[linkKey]


def env_updated(app: Sphinx, env: BuildEnvironment) -> List[str]:
    is_enabled: bool = getattr(app.env, ENV_REDIRECTS_ENABLED)
    if not is_enabled:
        return list()
    """
    to do:
    - overlay redirects from config onto redirects from doctree
    """
    doctree_redirects: Dict[str, List[str]] = getattr(app.env, ENV_DOCTREE_REDIRECTS)
    redirects_option: Dict[str, str] = getattr(app.config, CONFIG_OPTION_REDIRECTS)
    computed_redirects: Dict[str, Dict[str, str]] = compute_redirects(
        app, redirects_option
    )
    setattr(app.env, ENV_COMPUTED_REDIRECTS, computed_redirects)
    intra_page_fragments: List[str] = list()
    for page in computed_redirects.keys():
        if page in env.all_docs:
            intra_page_fragments.append(page)
    logger.verbose(
        "env_updated(): found %d intra-page fragment pages" % len(intra_page_fragments)
    )
    setattr(app.env, ENV_INTRA_PAGE_FRAGMENT_PAGES, intra_page_fragments)
    return list()


def html_page_context(
    app: Sphinx, pagename: str, templatename: str, context: Dict, doctree: Dict
) -> str:
    is_enabled: bool = getattr(app.env, ENV_REDIRECTS_ENABLED)
    if not is_enabled:
        return templatename
    context[CTX_HAS_FRAGMENT_REDIRECTS] = False
    intra_page_fragments: List[str] = getattr(app.env, ENV_INTRA_PAGE_FRAGMENT_PAGES)
    if pagename in intra_page_fragments:
        logger.verbose(
            "html_page_context(): page %s has intra-page redirects; adding redirects to HTML context"
            % pagename
        )
        computed_redirects: Dict[str, Dict[str, str]] = getattr(
            app.env, ENV_COMPUTED_REDIRECTS
        )
        context[CTX_FRAGMENT_REDIRECTS] = build_js_object(computed_redirects[pagename])
        context[CTX_HAS_FRAGMENT_REDIRECTS] = True
    return templatename


def html_collect_pages(app: Sphinx) -> List[Tuple[str, Dict[str, Any], str]]:
    """
    Collect the redirect page information and generate a list of redirect pages to write.

    :param app: The Sphinx Application instance
    :return: The list of redirect pages to create
    """
    is_enabled: bool = getattr(app.env, ENV_REDIRECTS_ENABLED)
    if not is_enabled:
        return list()
    redirect_pages: List[Tuple[str, Dict[str, Any], str]] = list()
    extensionless_pages: List[str] = list()
    write_extensionless_pages: bool = getattr(
        app.config, CONFIG_WRITE_EXTENSIONLESS_PAGES
    )
    computed_redirects: Dict[str, Dict[str, str]] = getattr(
        app.env, ENV_COMPUTED_REDIRECTS
    )
    for page in computed_redirects.keys():
        # if page is a real page in the doctree, we've already handled it elsewhere
        if page in app.env.all_docs:
            logger.verbose(
                "html_collect_pages(): page %s has intra-page redirects; skipping it"
                % page
            )
            continue
        # Handle the case where there is a single redirect defined for a source page
        if len(computed_redirects[page]) == 1:
            # if this page only has a redirect to the DEFAULT_PAGE, then use a simple redirect template
            if DEFAULT_PAGE in computed_redirects[page]:
                logger.verbose(
                    "html_collect_pages(): simple redirect from %s to %s"
                    % (page, computed_redirects[page][DEFAULT_PAGE])
                )
                redirect_pages.append(
                    (
                        page,
                        {"to_uri": computed_redirects[page][DEFAULT_PAGE]},
                        "simpleredirect.html",  # TODO: move this into a config variable
                    )
                )
                if write_extensionless_pages:
                    extensionless_pages.append(page)
                continue
            # there's only one fragment redirect, and it's not DEFAULT_PAGE. if someone browses to the page, they
            # will see a blank screen. we add a DEFAULT_PAGE redirect in that case.
            default_page_url = ""
            for frag in computed_redirects[page].keys():
                default_page_url = computed_redirects[page][frag]
                break
            if default_page_url != "":
                computed_redirects[page][DEFAULT_PAGE] = default_page_url
                logger.debug(
                    "html_collect_pages(): added DEFAULT_PAGE redirect for " + page
                )
        # build a JS object that will hold the fragment redirect map
        jsobject = build_js_object(computed_redirects[page])
        logger.verbose("html_collect_pages(): redirect from %s; %s" % (page, jsobject))
        redirect_pages.append(
            (
                page,
                {CTX_FRAGMENT_REDIRECTS: jsobject},
                "redirect.html",  # TODO: move this into a config variable
            )
        )
        if write_extensionless_pages:
            extensionless_pages.append(page)
    # if we're configured to write extensionless pages, save the list of pages to the environment for later processing
    if write_extensionless_pages:
        setattr(app.env, ENV_EXTENSIONLESS_PAGES, extensionless_pages)
    # return the iterable of pages to write
    return redirect_pages


def doctree_resolved(app: Sphinx, doctree: nodes.document, docname: str) -> None:
    """
    Walk the doctree and assemble the list of redirects
    :param app: The Sphinx application instance
    :param doctree: The resolved doctree
    :param docname: The name of the document
    :return:
    """
    # FIXME: replace seo_redirect_redirects with the appropriate constant
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
            logger.verbose(" >> %s" % redirect_to)
            if redirect_from in app.env.seo_redirect_redirects:
                app.env.seo_redirect_redirects[redirect_from].append(redirect_to)
            else:
                app.env.seo_redirect_redirects[redirect_from] = [redirect_to]


def build_finished(app: Sphinx, exception: Exception):
    if exception is None:
        write_extensionless_pages: bool = getattr(
            app.config, CONFIG_WRITE_EXTENSIONLESS_PAGES
        )
        if write_extensionless_pages:
            extensionless_pages: List[str] = getattr(app.env, ENV_EXTENSIONLESS_PAGES)
            for pagename in list_status_iterator(
                extensionless_pages,
                "writing extensionless redirect pages... ",
                "darkgreen",
                len(extensionless_pages),
            ):
                target_file = Path(app.outdir).joinpath(pagename)
                if target_file.is_dir():
                    logger.warning(
                        "target extensionless redirect '%s' is a directory; cannot write this page"
                        % target_file
                    )
                    continue
                source_file = str(target_file) + ".html"
                logger.verbose(
                    "build_finished(): extensionless redirect; %s -> %s"
                    % (source_file, target_file)
                )
                copyfile(source_file, target_file)


def compute_redirects(
    app: Sphinx, redirects_option: Dict[str, str]
) -> Dict[str, Dict[str, str]]:
    computed_redirects: Dict[str, Dict[str, str]] = dict()
    # read parameters from config
    html_baseurl: str = getattr(app.config, CONFIG_HTML_BASEURL)
    html_baseurl = html_baseurl.removesuffix("/")
    url_path_prefix: str = getattr(app.config, CONFIG_URL_PATH_PREFIX)
    url_path_prefix = url_path_prefix.removesuffix("/")
    # process each record in the redirects dict
    for source in redirects_option.keys():
        # split the URL on # so we get the path and page name + the fragment, if any
        tokens = source.split("#")
        if len(tokens) == 2:
            pagename = tokens[0].removesuffix(
                ".html"
            )  # ensure pagename does not end with ".html"
            fragment = tokens[1].removesuffix(
                ".html"
            )  # if the fragment ends in ".html", remove it
        elif len(tokens) == 1:
            pagename = tokens[0].removesuffix(
                ".html"
            )  # ensure pagename does not end with ".html"
            fragment = ""
        else:
            logger.warning("compute_redirects(): invalid redirect: %s" % source)
            continue
        # if the source page is the empty string then the redirect is invalid. warn the user and continue on.
        if pagename == "":
            logger.warning("compute_redirects(): empty page name: %s" % source)
            continue
        # add a new dict to redirect_map if the page has not been seen before
        if pagename not in computed_redirects:
            computed_redirects[pagename] = dict()
        # if the target page has the same prefix as html_baseurl, remove the prefix so intra-site redirects work
        target = redirects_option[source].removeprefix(html_baseurl)
        # if the target is the empty string then the redirect is invalid. warn the user and continue on
        if target == "":
            logger.warning("compute_redirects(): empty target for source %s" % source)
            continue
        # if mm_url_path_prefix is defined and the target path starts with '/', prepend it to the target path.
        if url_path_prefix != "" and target.startswith("/"):
            target = url_path_prefix + target
        # if there's no fragment then we're redirecting to the "default page", which is
        # the `pagename` without any fragment.
        if fragment == "":
            computed_redirects[pagename][DEFAULT_PAGE] = target
            continue
        # redirect the fragment to the desired page
        computed_redirects[pagename][fragment] = target
    # remove empty keys from the map
    empty_keys: List[str] = list()
    for key in computed_redirects.keys():
        if len(computed_redirects[key]) == 0:
            empty_keys.append(key)
    for key in empty_keys:
        computed_redirects.pop(key)
    return computed_redirects


def build_js_object(pagemap: Dict[str, str]) -> str:
    jsobject = "const " + CTX_FRAGMENT_REDIRECTS + " = Object.freeze({"
    for frag in pagemap.keys():
        jsobject += '"' + frag + '":"' + pagemap[frag] + '",'
    jsobject = jsobject.rstrip(",") + "});"
    return jsobject


def old_status_iterator(
    mapping: Mapping[str, str], summary: str, color: str = "darkgreen"
) -> Tuple[str, str]:
    """
    Displays the status of iterating through a Dict/Mapping of strings. Taken from the Sphinx sources.

    :param mapping: The iterable to iterate through
    :param summary: A description of the action or operation
    :param color: The color of the status text; defaults to `darkgreen`
    :return: A tuple containing the next key-value pair from the iterable
    """
    line_count = 0
    for item in mapping.items():
        if line_count == 0:
            logger.info(bold(summary), nonl=True)
            line_count = 1
        logger.info(item[0], color=color, nonl=True)
        logger.info(" ", nonl=True)
        yield item
    if line_count == 1:
        logger.info("")


def status_iterator(
    mapping: Mapping[str, str],
    summary: str,
    color: str = "darkgreen",
    length: int = 0,
    verbosity: int = 0,
) -> Tuple[str, str]:
    """
    Displays the status of iterating through a Dict/Mapping of strings. Taken from the Sphinx sources.
    Status includes percent of records in the iterable that have been iterated through.

    :param mapping: The iterable to iterate through
    :param summary: A description of the action or operation
    :param color:  The color of the status text; defaults to `darkgreen`
    :param length: The number of records in the iterable
    :param verbosity: Flag which writes a newline after each status message
    :return: A tuple containing the next key-value pair from the iterable
    """
    if length == 0:
        yield from old_status_iterator(mapping, summary, color)
        return
    line_count = 0
    summary = bold(summary)
    for item in mapping.items():
        line_count += 1
        s = "%s[%3d%%] %s" % (
            summary,
            100 * line_count / length,
            colorize(color, item[0]),
        )
        if verbosity:
            s += "\n"
        else:
            s = term_width_line(s)
        logger.info(s, nonl=True)
        yield item
    if line_count > 0:
        logger.info("")


def old_list_status_iterator(
    mapping: List[str], summary: str, color: str = "darkgreen"
) -> str:
    """
    Displays the status of iterating through a List of strings. Adapted from the Sphinx sources.

    :param mapping: The List to iterate through
    :param summary: A description of the action or operation
    :param color: The color of the status text; defaults to `darkgreen`
    :return: A tuple containing the next value from the List
    """
    line_count = 0
    for item in mapping:
        if line_count == 0:
            logger.info(bold(summary), nonl=True)
            line_count = 1
        logger.info(item, color=color, nonl=True)
        logger.info(" ", nonl=True)
        yield item
    if line_count == 1:
        logger.info("")


def list_status_iterator(
    mapping: List[str],
    summary: str,
    color: str = "darkgreen",
    length: int = 0,
    verbosity: int = 0,
) -> str:
    """
    Displays the status of iterating through a List of strings. Adapted from the Sphinx sources.
    Status includes percent of records in the List that have been iterated through.

    :param mapping: The List to iterate through
    :param summary: A description of the action or operation
    :param color:  The color of the status text; defaults to `darkgreen`
    :param length: The number of records in the List
    :param verbosity: Flag which writes a newline after each status message
    :return: A tuple containing the next value from the List
    """
    if length == 0:
        yield from old_list_status_iterator(mapping, summary, color)
        return
    line_count = 0
    summary = bold(summary)
    for item in mapping:
        line_count += 1
        s = "%s[%3d%%] %s" % (
            summary,
            100 * line_count / length,
            colorize(color, item),
        )
        if verbosity:
            s += "\n"
        else:
            s = term_width_line(s)
        logger.info(s, nonl=True)
        yield item
    if line_count > 0:
        logger.info("")
