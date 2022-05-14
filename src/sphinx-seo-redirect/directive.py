from typing import List
from docutils import nodes
from sphinx.util import logging
from sphinx.util.docutils import SphinxDirective
from node import SEORedirectNode


class SEORedirectDirective(SphinxDirective):
    has_content = False
    required_arguments = 1
    final_argument_whitespace = True
    logger = logging.getLogger("SEORedirectDirective")

    def run(self) -> List[nodes.Node]:
        redirect_args = " ".join(self.arguments)
        redirects = redirect_args.split(" ")
        self.logger.verbose("Directive: parsed redirects: %s" % ",".join(redirects))
        return [SEORedirectNode(redirects)]
