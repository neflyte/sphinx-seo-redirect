from typing import List
from docutils import nodes
from sphinx.util import logging
from sphinx.util.docutils import SphinxDirective

from .node import SEORedirectNode

"""
Directive usage example:

.. seo-redirect:: old/page1,old/page2#section,...

  old2/page3#section4
  old2/page4
  ...
"""


class SEORedirectDirective(SphinxDirective):
    has_content = True
    optional_arguments = 1
    logger = logging.getLogger("SEORedirectDirective")

    def run(self) -> List[nodes.Node]:
        redirects: List[str] = list()
        # If there was an argument, split it on commas and add to the redirects list
        if len(self.arguments) == 1:
            redirects.extend(self.arguments[0].split(","))
        # If there is content, each line is a redirect
        for line in self.content:
            if line != "":
                redirects.append(line)
        self.logger.verbose("run(): collected %d redirects" % len(redirects))
        return [SEORedirectNode(redirects)]
