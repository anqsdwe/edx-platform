from __future__ import absolute_import

import logging

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import redirect
from django.utils.translation import ugettext as _
from edxmako.shortcuts import render_to_string, render_to_response
from xblock.core import XBlock
from xmodule.modulestore.django import modulestore
from contentstore.utils import reverse_course_url, reverse_usage_url

__all__ = ['edge', 'event', 'landing']

EDITING_TEMPLATES = [
    "basic-modal", "modal-button", "edit-xblock-modal", "editor-mode-button", "upload-dialog", "image-modal",
    "add-xblock-component", "add-xblock-component-button", "add-xblock-component-menu",
    "add-xblock-component-menu-problem", "xblock-string-field-editor",
]

# points to the temporary course landing page with log in and sign up
def landing(request, org, course, coursename):
    return render_to_response('temp-course-landing.html', {})


# points to the temporary edge page
def edge(request):
    return redirect('/')


def event(request):
    '''
    A noop to swallow the analytics call so that cms methods don't spook and poor developers looking at
    console logs don't get distracted :-)
    '''
    return HttpResponse(status=204)


def render_from_lms(template_name, dictionary, context=None, namespace='main'):
    """
    Render a template using the LMS MAKO_TEMPLATES
    """
    return render_to_string(template_name, dictionary, context, namespace="lms." + namespace)


def _xmodule_recurse(item, action, ignore_exception=()):
    """
    Recursively apply provided action on item and its children

    ignore_exception (Exception Object): A optional argument; when passed ignores the corresponding
        exception raised during xmodule recursion,
    """
    for child in item.get_children():
        _xmodule_recurse(child, action, ignore_exception)

    try:
        return action(item)
    except ignore_exception:
        return


def get_parent_xblock(xblock):
    """
    Returns the xblock that is the parent of the specified xblock, or None if it has no parent.
    """
    locator = xblock.location
    parent_locations = modulestore().get_parent_locations(locator,)

    if len(parent_locations) == 0:
        return None
    elif len(parent_locations) > 1:
        logging.error('Multiple parents have been found for %s', unicode(locator))
    return modulestore().get_item(parent_locations[0])


def is_unit(xblock):
    """
    Returns true if the specified xblock is a vertical that is treated as a unit.
    A unit is a vertical that is a direct child of a sequential (aka a subsection).
    """
    if xblock.category == 'vertical':
        parent_xblock = get_parent_xblock(xblock)
        parent_category = parent_xblock.category if parent_xblock else None
        return parent_category == 'sequential'
    return False


def xblock_has_own_studio_page(xblock):
    """
    Returns true if the specified xblock has an associated Studio page. Most xblocks do
    not have their own page but are instead shown on the page of their parent. There
    are a few exceptions:
      1. Courses
      2. Verticals that are either:
        - themselves treated as units
        - a direct child of a unit
      3. XBlocks with children, except for:
        - sequentials (aka subsections)
        - chapters (aka sections)
    """
    category = xblock.category

    if is_unit(xblock):
        return True
    elif category == 'vertical':
        parent_xblock = get_parent_xblock(xblock)
        return is_unit(parent_xblock) if parent_xblock else False
    elif category == 'sequential':
        return False

    # All other xblocks with children have their own page
    return xblock.has_children


def xblock_studio_url(xblock):
    """
    Returns the Studio editing URL for the specified xblock.
    """
    if not xblock_has_own_studio_page(xblock):
        return None
    category = xblock.category
    if category in ('course', 'chapter'):
        return reverse_course_url('course_handler', xblock.location.course_key)
    else:
        return reverse_usage_url('container_handler', xblock.location)


def xblock_type_display_name(xblock, default_display_name=None):
    """
    Returns the display name for the specified type of xblock. Note that an instance can be passed in
    for context dependent names, e.g. a vertical beneath a sequential is a Unit.

    :param xblock: An xblock instance or the type of xblock.
    :param default_display_name: The default value to return if no display name can be found.
    :return:
    """

    if hasattr(xblock, 'category'):
        if is_unit(xblock):
            return _('Unit')
        category = xblock.category
    else:
        category = xblock
    component_class = XBlock.load_class(category, select=settings.XBLOCK_SELECT_FUNCTION)
    if hasattr(component_class, 'display_name') and component_class.display_name.default:
        return _(component_class.display_name.default)
    else:
        return default_display_name
