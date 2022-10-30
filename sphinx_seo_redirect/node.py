from typing import List
from docutils import nodes
from sphinx.util import logging


class SEORedirectNode(nodes.Element):
    logger: logging.SphinxLoggerAdapter
    _redirect_list: List[str]

    def __init__(self, redirects: List[str]):
        super().__init__()
        self.logger = logging.getLogger("SEORedirectNode")
        self._redirect_list = redirects.copy()

    def astext(self) -> str:
        return ",".join(self.redirect_list)

    @property
    def redirect_list(self) -> List[str]:
        return self._redirect_list
