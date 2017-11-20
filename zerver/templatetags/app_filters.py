import os
from typing import Any, Dict, List, Optional

import markdown
import markdown.extensions.admonition
import markdown.extensions.codehilite
import markdown.extensions.extra
import markdown.extensions.toc
import markdown_include.include
from django.conf import settings
from django.template import Library, engines, loader
from django.utils.lru_cache import lru_cache
from django.utils.safestring import mark_safe

import zerver.lib.bugdown.fenced_code

register = Library()

def and_n_others(values, limit):
    # type: (List[str], int) -> str
    # A helper for the commonly appended "and N other(s)" string, with
    # the appropriate pluralization.
    return " and %d other%s" % (len(values) - limit,
                                "" if len(values) == limit + 1 else "s")

@register.filter(name='display_list', is_safe=True)
def display_list(values, display_limit):
    # type: (List[str], int) -> str
    """
    Given a list of values, return a string nicely formatting those values,
    summarizing when you have more than `display_limit`. Eg, for a
    `display_limit` of 3 we get the following possible cases:

    Jessica
    Jessica and Waseem
    Jessica, Waseem, and Tim
    Jessica, Waseem, Tim, and 1 other
    Jessica, Waseem, Tim, and 2 others
    """
    if len(values) == 1:
        # One value, show it.
        display_string = "%s" % (values[0],)
    elif len(values) <= display_limit:
        # Fewer than `display_limit` values, show all of them.
        display_string = ", ".join(
            "%s" % (value,) for value in values[:-1])
        display_string += " and %s" % (values[-1],)
    else:
        # More than `display_limit` values, only mention a few.
        display_string = ", ".join(
            "%s" % (value,) for value in values[:display_limit])
        display_string += and_n_others(values, display_limit)

    return display_string

md_extensions = None

@register.filter(name='render_markdown_path', is_safe=True)
def render_markdown_path(markdown_file_path, context=None):
    # type: (str, Optional[Dict[Any, Any]]) -> str
    """Given a path to a markdown file, return the rendered html.

    Note that this assumes that any HTML in the markdown file is
    trusted; it is intended to be used for documentation, not user
    data."""
    global md_extensions
    if md_extensions is None:
        md_extensions = [
            markdown.extensions.extra.makeExtension(),
            markdown.extensions.toc.makeExtension(),
            markdown.extensions.admonition.makeExtension(),
            markdown.extensions.codehilite.makeExtension(
                linenums=False,
                guess_lang=False
            ),
            zerver.lib.bugdown.fenced_code.makeExtension(),
            markdown_include.include.makeExtension(base_path='templates/zerver/help/include/'),
        ]
    md_engine = markdown.Markdown(extensions=md_extensions)
    md_engine.reset()

    if context is None:
        context = {}

    jinja = engines['Jinja2']
    markdown_string = jinja.env.loader.get_source(jinja.env, markdown_file_path)[0]
    html = md_engine.convert(markdown_string)
    html_template = jinja.from_string(html)
    return mark_safe(html_template.render(context))
