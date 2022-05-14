from typing import Dict, List, Any
from docutils import nodes
from sphinx.util import logging
from node import SEORedirectNode


class DoctreeWalker(nodes.SparseNodeVisitor):
    logger = logging.getLogger("DoctreeWalker")

    def __init__(self, document: nodes.document):
        super().__init__(document)
        self._section_redirects: Dict[str, List[str]] = dict()
        self._root_section: str = ""
        self.find_root_section(document)

    def find_root_section(self, document: nodes.document):
        for child in document.children:
            if isinstance(child, nodes.section):
                for attr in child.attlist():
                    if attr[0] == "ids":
                        self._root_section = attr[1][0]
                        self.logger.debug(
                            "find_root_section: found root section: %s"
                            % self._root_section
                        )
                        break

    def visit_section(self, node: nodes.section):
        # get section id
        section_id: str = ""
        for att in node.attlist():
            if att[0] == "ids":
                # FIXME: search the att array for "ids" instead of assuming it's at att[0]
                section_id = att[1][0]
                if section_id != "":
                    self.logger.debug(
                        "visit_section: visiting section %s" % section_id
                    )
                break
        # look for redirective nodes; remove them when we're done
        redirects: List[str] = list()
        for child in node.children:
            if isinstance(child, SEORedirectNode):
                redir_node: SEORedirectNode = child
                redirects.extend(redir_node.redirect_list)
                self.logger.debug(
                    "visit_section: child node redirects: %s"
                    % ",".join(redir_node.redirect_list)
                )
                child.replace_self([])
                break
        if len(redirects) > 0 and section_id != "":
            self.logger.debug(
                "visit_section: adding %d redirects to section %s"
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
