from typing import List
from docutils import nodes
from sphinx.util import logging
from sphinx.util.logging import SphinxLoggerAdapter


class SEORedirectNode(nodes.Element):
    logger: SphinxLoggerAdapter
    _redirect_list: List[str]

    def __init__(self, redirects: List[str]):
        super().__init__()
        self.logger = logging.getLogger("SEORedirectNode")
        self._redirect_list = list()
        for redirect in redirects.copy():
            if redirect != "":
                self.logger.verbose("adding redirect: %s" % redirect)
                self._redirect_list.append(redirect)

    def astext(self) -> str:
        return ",".join(self.redirect_list)

    @property
    def redirect_list(self) -> List[str]:
        return self._redirect_list
