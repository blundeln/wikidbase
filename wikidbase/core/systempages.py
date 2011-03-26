#
# Copyright (C) 2007 Nick Blundell.
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
# systempages (systempages.py)
# ----------------------------
#
# Description:
#
#
# Author       : Nick Blundell
# Organisation : www.nickblundell.org.uk
# Version Info : $Id$
#

import pagestore
import wikidbase.core.context
import wikidbase.core.query

from nbdebug import *

ALL_PAGES = "ALL_PAGES"
RECENT_CHANGES = "RECENT_CHANGES"
QUERY = "QUERY"
SYSTEM_PAGES = [
  ALL_PAGES,
  RECENT_CHANGES,
  QUERY,
]

def getSystemPage(request, systemPageDescription) :
  debugOutput(systemPageDescription)
  systemPage = systemPageDescription.split("/")[0]
  if systemPage in SYSTEM_PAGES :
    return eval("%s(request)" % systemPage)
  else :
    return None

def QUERY(request) :
  wikidpage = pagestore.getNewPage(cloneSource=None, name=None)
  wikidpage.content = "Results\n=========\n\n"
  queryString = request.REQUEST["query"]
  
  # Have a look at the query to see if we can help the user find stuff.
  query = wikidbase.core.query.SimpleQueryBuilder().buildQuery(queryString)
  if not query.contexts :
    if not query.conditionalClause :
      queryString = """anything where body contains "%s" """ % queryString
    else :
      queryString = "anything %s" % queryString

  # TODO: parse, say: person nick as person where body contains "nick"
    
  wikidpage.content += """\n:::%s:::\n\n""" % (queryString)
  wikidpage.name = "Query"

  return wikidpage

def RECENT_CHANGES(request) :
  wikidpage = pagestore.getNewPage(cloneSource=None, name=None)
  wikidpage.name = "Recent Modifications"
  
  wikidpage.content = "Recent Changes\n====================\n\n"

  displayFields = " fields ID page type page modified name"

  wikidpage.content += """Today\n-----\n\n:::anything where modified = today%s:::\n\n""" % displayFields
  wikidpage.content += """Yesterday\n---------\n\n:::anything where modified = yesterday%s:::\n\n""" % displayFields
  wikidpage.content += """This week\n---------\n\n:::anything where modified < "yesterday" and modified >= "this monday"%s:::\n\n""" % displayFields
  wikidpage.content += """This month\n------------\n\n:::anything where modified >= "this month" and modified < "this monday"%s:::\n\n""" % displayFields
  
  return wikidpage

def ALL_PAGES(request) :
  wikidpage = pagestore.getNewPage(cloneSource=None, name=None)
  wikidpage.content = "All Pages\n=========\n\n"
  # Get a list of contexts
  wikidbaseContexts = wikidbase.core.context.getContexts()
  for nContext in wikidbaseContexts :
    displayTerm = wikidbaseContexts[nContext].contextNameVariations.getMostCommon()
    wikidpage.content += """%s\n%s\n:::%s:::\n\n""" % (displayTerm.capitalize(), "-"*len(displayTerm), nContext)
  displayTerm = "General Pages"
  wikidpage.content += """%s\n%s\n:::%s:::\n\n""" % (displayTerm.capitalize(), "-"*len(displayTerm), "pages")

  wikidpage.name = "All Pages"
 
  debugOutput("wikidpage.content: %s" % wikidpage.content)

  return wikidpage
