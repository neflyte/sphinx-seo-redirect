from typing import Dict, List, Any
from docutils import nodes
from sphinx.util import logging

from .node import SEORedirectNode


class DoctreeWalker(nodes.SparseNodeVisitor):
    logger: logging.SphinxLoggerAdapter
    _section_redirects: Dict[str, List[str]]
    _root_section: str

    def __init__(self, document: nodes.document):
        super().__init__(document)
        self.logger = logging.getLogger("DoctreeWalker")
        self._section_redirects = dict()
        self._root_section = ""
        self.find_root_section(document)

    def find_root_section(self, document: nodes.document):
        for child in document.children:
            if isinstance(child, nodes.section):
                if "ids" in child.attributes:
                    node_ids: List[str] = child.attributes["ids"]
                    if len(node_ids) > 0:
                        self._root_section = node_ids[0]
                        self.logger.debug(
                            "find_root_section: found root section: %s"
                            % self._root_section
                        )
                        break

    def visit_section(self, node: nodes.section):
        # get section id
        section_id = ""
        if "ids" in node.attributes:
            ids_attr: List[str] = node.attributes["ids"]
            if len(ids_attr) > 0:
                section_id = ids_attr[0]
                if section_id != "":
                    self.logger.debug(
                        "visit_section(): visiting section %s" % section_id
                    )
        # look for SEORedirectNode nodes; remove them when we're done
        redirects: List[str] = list()
        for child in node.children:
            if isinstance(child, SEORedirectNode):
                redirects.extend(child.redirect_list)
                self.logger.debug(
                    "visit_section(): child node redirects: %s"
                    % ",".join(child.redirect_list)
                )
                child.replace_self([])
                break
        if len(redirects) > 0 and section_id != "":
            self.logger.debug(
                "visit_section(): adding %d redirects to section %s"
                % (len(redirects), section_id)
            )
            self._section_redirects[section_id] = redirects

    def unknown_visit(self, node: nodes.Node) -> Any:
        raise nodes.SkipNode

    @property
    def section_redirects(self) -> Dict[str, List[str]]:
        return self._section_redirects

    @property
    def root_section(self) -> str:
        return self._root_section
