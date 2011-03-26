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
# renderer (renderer.py)
# ----------------------
#
# Description:
#
#
# Author       : Nick Blundell
# Organisation : www.nickblundell.org.uk
# Version Info : $Id: renderer.py 969 2008-05-23 10:29:17Z blundeln $
#

import re
import urllib

import docutils.core

import django.forms
import django.template
import django.conf

import wikidbase.core.pagecontent
import wikidbase.core.pagestore
import wikidbase.core.queryresultsrenderer
import wikidbase.core.context
import wikidbase.core.widgets
import wikidbase.core.security

from nbdebug import *

EXPLICIT_WIKI_L = "[["
EXPLICIT_WIKI_R = "]]"

# Wiki link regexes
wikiwordsCamelCase = re.compile(r"[^/](\b[A-Z][a-z]\w+[A-Z][a-z]\w+\b)", re.MULTILINE)
wikiwordsExplicit = re.compile(r"\[\[(\w[\w ]+\w)\]\]")

# Ajax urls.
PAGE_LOOKUP_URL = "/%sajax/page_lookup/" % (django.conf.settings.URL_PREFIX and "%s/" % django.conf.settings.URL_PREFIX or "")
LINK_LOOKUP_URL = "/%sajax/foreignlink_lookup/" % (django.conf.settings.URL_PREFIX and "%s/" % django.conf.settings.URL_PREFIX or "")



def renderWikidpage(request, wikidpage, form) :
  """
  This important function takes a wikidpage and its generated for object and renders it into html
  by passing through a series of filters.
  """
  
  debugOutput("Rendering wikidage.")

  renderedPage = wikidpage.getContent().template
  renderedPage = _renderFormatting(renderedPage, wikidpage.format)
  renderedPage = _renderWikiwords(renderedPage)
  renderedPage = _renderFields(request, renderedPage, form, wikidpage)
  renderedPage = _renderRelationalFields(request, renderedPage, form, wikidpage)
  renderedPage = _renderCommands(request, renderedPage, form, wikidpage)

  return renderedPage


def _renderFormatting(renderedPage, format) :
  """Renders the page using some formatting system: eg. restructured text."""
  if format == "rest" :
    renderedPage = docutils.core.publish_parts(renderedPage, writer_name="html")["html_body"]
  return renderedPage


def _renderWikiwords(renderedPage) :
  """Looks for WikiWords or explicit wiki links (e.g. [[Some page]]) and substitutes the link."""

  debugOutput("Redering wikiwords in: %s" % renderedPage)

  def subWikiword(match) :

    debugOutput(dir(match))
    wholeMatch = match.group()
    pageName = match.groups()[0]
    debugOutput("wholeMatch %s, pageName %s" % (wholeMatch, pageName))
    wikidpage = wikidbase.core.pagestore.getWikidpage(pageName)
    if wikidpage :
      link = """<a href="%s">%s</a>""" % (wikidpage.get_absolute_url(), pageName)
    else :
      link = """%s<a title="Click here to create this new page." href="/%s/EDIT/CREATE"><span class="wikiwordquestion">?</span></a>""" % (pageName, pageName)
 
    preSymbols = wholeMatch.replace(pageName, "")

    if wholeMatch.startswith(EXPLICIT_WIKI_L) :
      return link
    else :
      return wholeMatch.replace(pageName, link)

  # Substitute camels and explicit.
  renderedPage = wikiwordsCamelCase.sub(subWikiword, renderedPage)
  renderedPage = wikiwordsExplicit.sub(subWikiword, renderedPage)
  
  return renderedPage


def _renderFields(request, renderedPage, form, wikidpage) :
  """
  Given a wikidpage and its genreated form, this renders the fields of a form, replacing
  tokens in the rendered wikidpage with form elements.
  """
  nContext = wikidbase.core.context.normaliseTerm(wikidpage.context)
  
  # Process each field in the form.
  for field in form.fields :
    debugOutput("field %s" % field.field_name)
    
    # For each of the possible data fields...
    for fieldType in wikidbase.core.pagecontent.WP_DATA_FIELDS :
      
      # Look for a tag/token for this field in the so-far-rendered page.
      nFieldname = wikidbase.core.context.normaliseTerm(field.field_name)
      fieldTag = "[%s-%s]" % (fieldType, nFieldname) 
      if fieldTag not in renderedPage :
        continue
      
      debugOutput("field %s tag %s " % (field.field_name, fieldTag))
     
      # Load and render the field template and substitute this into the rendered page.
      t = django.template.loader.get_template("field.html")
      renderedField = t.render(django.template.Context({"field":field, "nContext":nContext, "nFieldname":nFieldname, "permissions":wikidbase.core.security.getTemplatePerms(request)}))
      renderedPage = renderedPage.replace(fieldTag,unicode(renderedField,"utf-8"))
  
  return renderedPage


def _renderRelationalFields(request, renderedPage, form, wikidpage) :
  """
  Renders the relational fields of a wikidpage.
  """
  
  debugOutput("Rendering")

  # TODO: Just need to get link field names at this point.
  # Make sure pending links are shown on rendered page.
  links = wikidbase.core.pagestore.getLinks(wikidpage.id)
  futureLinks = {}
  if "linkBack" in request.GET :
    remoteID, remoteRelField, localRelField = request.GET["linkBack"].split("-")
    futureLinks[wikidbase.core.normaliseTerm(localRelField)] = [remoteID]

  debugOutput("Links = %s" % links)

  linkFields = {}


  # Add links from relationship definitions.
  nContext = wikidbase.core.context.normaliseTerm(wikidpage.context)
  relationships = wikidbase.core.context.getContextRelationships(nContext)
  if relationships :
    for linkName in relationships :
      nLinkName = wikidbase.core.context.normaliseTerm(linkName)
      if nLinkName not in linkFields :
        linkFields[nLinkName] = linkName

  # Add link fields from actual links.
  if links :
    for linkName in links.keys() :
      nLinkName = wikidbase.core.context.normaliseTerm(linkName)
      if nLinkName not in linkFields :
        linkFields[nLinkName] = linkName

  # TODO: add future linkfield display name
  for futureLink in futureLinks :
    nFutureLink = wikidbase.core.normaliseTerm(futureLink)
    if nFutureLink not in linkFields :
      linkFields[nFutureLink] = futureLink

  renderedLinks = ""

  # Process each link field.
  for nLinkField in linkFields :
    
    # Load the relational field template.
    t = django.template.loader.get_template("relationalfield.html")

    # Try to get a display name for this link
    #try :
    #  displayName = wikidbase.core.context.getContexts()[wikidbase.core.context.normaliseTerm(wikidpage.context)].linkContexts[nLinkField].nameVariations.getMostCommon()
    #except :
    displayName = linkFields[nLinkField]

    # Only add the adding widget if relationships have been defined.
    ajaxLinkAddWidget = None
    for relationship in relationships :
      if wikidbase.core.context.normaliseTerm(relationship) == nLinkField and relationships[relationship] :
        # Render the widget for adding links.
        ajaxLinkAddWidget = wikidbase.core.widgets.AjaxLinkAddWidget(lookupURL=PAGE_LOOKUP_URL, linkLookupURL=LINK_LOOKUP_URL, localLinkName=nLinkField, wikidpage=wikidpage)
        break

    # Render the queryset for this link.
    renderedQuerySet = wikidbase.core.queryresultsrenderer.renderLinkField(request, wikidpage.id, nLinkField, futureLinks = nLinkField in futureLinks and futureLinks[nLinkField] or None)

    tContext = {
      "displayName":displayName,
      "renderedQuerySet":renderedQuerySet,
      "containerID":"link-%s" % nLinkField,
      "ajaxLinkAddWidget": ajaxLinkAddWidget and ajaxLinkAddWidget.render("%s-link-add" % nLinkField,None) or None,
      # ---- For the link add widget
      "wikidpage":wikidpage,
      "pageLookupURL":PAGE_LOOKUP_URL,
      "linkLookupURL":LINK_LOOKUP_URL,
      "permissions":wikidbase.core.security.getTemplatePerms(request),
    }

    # Render the field.
    renderedField = t.render(django.template.Context(tContext))

    # Add the rendered field to the rendered page.
    renderedLinks = renderedLinks + renderedField

  # Add add-new-relational form to the bottom of the relationships section.
  if wikidpage and wikidpage.context :
    
    # Build up a list of existing local link names for this context.
    localRelFields = []
    wikidpageContext = wikidbase.core.context.getContexts()[wikidbase.core.normaliseTerm(wikidpage.context)]
    linkContexts = wikidpageContext.linkContexts
    for nField in linkContexts :
      localRelFields.append(linkContexts[nField].nameVariations.getMostCommon().capitalize())
   
    # Create a link-adding widget.
    localLinkNameChoices = [(localRelField, localRelField) for localRelField in localRelFields]
    ajaxLinkAddWidget = wikidbase.core.widgets.AjaxLinkAddWidget(lookupURL=PAGE_LOOKUP_URL, linkLookupURL=LINK_LOOKUP_URL, localLinkName=localLinkNameChoices, wikidpage=wikidpage)
    
    # TODO: This should go into a loadable template.
    # XXX: Lets try doing it without this.
    #renderedLinks += """<fieldset class="collapsible collapsed addnewrel"><legend>Add new relationship</legend>%s</fieldset>""" % ajaxLinkAddWidget.render("link-add",None)
    #renderedPage = """%s<br/><fieldset class="collapsible collapsed"><legend id="relationships">Relationships</legend>%s</fieldset>""" % (renderedPage, unicode(renderedLinks,"utf-8"))
    renderedPage = """%s<br/>%s""" % (renderedPage, unicode(renderedLinks,"utf-8"))

  return renderedPage


def _renderCommands(request, renderedPage, form, wikidpage) :
  """
  This renders commands on a wikidpage. For now, commands are queries, but they could
  make anything appear in the page (e.g. a graph, a flash app).
  I'd like to develop this into a plug-in system.
  """
  
  pageContent = wikidpage.getContent()
  
  # Process each command specified in the page.
  for attributeName in pageContent.attributes :
    attribute = pageContent.attributes[attributeName]
    if attribute.type != wikidbase.core.pagecontent.WP_COMMAND :
      continue
    
    # Substitute the tag with the rendered command.
    attributeTag = "[%s-%s]" % (wikidbase.core.pagecontent.WP_COMMAND, attribute.nName) 
    command = attribute.data
    debugOutput(command)
    renderedPage = renderedPage.replace(attributeTag, unicode(wikidbase.core.queryresultsrenderer.renderCommand(request, source = wikidpage.id or wikidpage.name, command = command), "utf-8"))
  
  return renderedPage
