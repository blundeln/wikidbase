#
# Copyright (C) 2006 Nick Blundell.
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
# 
# The GNU GPL is contained in /usr/doc/copyright/GPL on a Debian
# system and in the file COPYING in the Linux kernel source.
# 
# tags (tags.py)
# --------------
#
# Description:
#
#
# Author       : Nick Blundell
# Organisation : www.nickblundell.org.uk
# Version Info : $Id: tags.py 949 2008-04-16 19:03:44Z blundeln $
#

import urllib
from django import template
from django import newforms as forms
register = template.Library()

import wikidbase.core.context
import wikidbase.core.module
import wikidbase.core.session
import wikidbase.core.security

@register.inclusion_tag('ajaxsearch.html', takes_context=True)
def ajaxsearch(context, nLinkField, field, pageURL, linkURL) :
  nField = field.field_name;
  return {
    "nLinkField":nLinkField,
    "pageURL":template.Template(pageURL).render(context),
    "linkURL":template.Template(linkURL).render(context),
    "pageID":"%s_%s" % (nField, "pageID"),
    "linkField":"%s_%s" % (nField, "linkField"),
    "autocomplete":"%s_%s" % (nField, "autocomplete"),
    "indicator":"%s_%s" % (nField, "indicator"),
    "choices":"%s_%s" % (nField, "choices"),
  }

#@register.simple_tag
def startSkinBox(name) :
  html = ""
  for i in range(0,8) :
    html += "<div class='%s%s clear'>" % (name, i+1)
  return html
register.simple_tag(startSkinBox)

#@register.simple_tag
def stopSkinBox(name) :
  return "</div>"*8
register.simple_tag(stopSkinBox)


@register.filter
def urlquote(input) :
  if not input :
    return None
  return urllib.quote(input)

@register.filter
def normaliseTerm(input) :
  return wikidbase.core.context.normaliseTerm(input)

@register.inclusion_tag('mainmenu.html', takes_context=True)
def mainMenu(context) :

  menuLinks = []
  menuLinks.append(("/","Home page","Go to the main page of your wikidbase","/media/images/homebutton.png"))
  menuLinks.append(None)
  
  if context["permissions"]["create"] :
    menuLinks.append(("/EDIT/CREATE","New page","Create a new blank wikidpage","/media/images/newpage.png"))
    menuLinks.append(None)
  
  if context["permissions"]["view"] :
    menuLinks.append(("/SYSTEM/RECENT_CHANGES","View recent changes", "View a list of recent pages","/media/images/recentchangesbutton.png"))
    menuLinks.append(("/SYSTEM/ALL_PAGES","View list of pages","View list of all pages","/media/images/viewpagesbutton.png"))
    menuLinks.append(None)
  
  menuLinks.append(("/help","Help","View documentation","/media/images/helpbutton.png"))

  menuLinks = wikidbase.core.module.hookMainMenu(context, menuLinks)

  return {"menuLinks":menuLinks}

class SearchForm(forms.Form) :
  query = forms.CharField()

@register.inclusion_tag('search.html', takes_context=True)
def searchForm(context) :
  searchForm = SearchForm()
  return {
    "searchForm":searchForm,
  }

@register.inclusion_tag('field.html', takes_context=True)
def renderField(context,field, displayName=None) :
  return {
    "field":field,
    "displayName":displayName,
  }


@register.inclusion_tag('ajaxaddlink.html', takes_context=True)
def ajaxaddlink(context, nLinkField, field, pageURL, linkURL) :
  nField = field.field_name;
  return {
    "nLinkField":nLinkField,
    "pageURL":template.Template(pageURL).render(context),
    "linkURL":template.Template(linkURL).render(context),
    "pageID":"%s_%s" % (nField, "pageID"),
    "linkField":"%s_%s" % (nField, "linkField"),
    "autocomplete":"%s_%s" % (nField, "autocomplete"),
    "indicator":"%s_%s" % (nField, "indicator"),
    "choices":"%s_%s" % (nField, "choices"),
  }


@register.inclusion_tag('quick-edit-guide.html', takes_context=True)
def quickEditGuide(context) :
  return {}
