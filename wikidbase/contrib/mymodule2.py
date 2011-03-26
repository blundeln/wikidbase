#
# Copyright (C) 2008 Nick Blundell.
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
# mymodule (mymodule.py)
# ----------------------
#
# Description:
#
#
# Author       : Nick Blundell
# Organisation : www.nickblundell.org.uk
# Version Info : $Id$
#

import datetime

from django.http import HttpResponse
import django.shortcuts

from wikidbase.core.module import ModuleInfo
import wikidbase.core.query

#
# Module hook implementations
#

def hookInfo() :
  """Tell wikidbase about this module."""
  return ModuleInfo(
    name="My Module 2",
    version="1.2",
    author="Some Author",
    description="A module that does something else."
  )

def hookURLs() :
  """Tell wikidbase about pages my module generates."""
  urls = (
    (r'^HelloWorld/$', myView),
    (r'^a-simple-view/$', simpleView),
  )
  return urls

#
# Custom wikidbase commands
#

@wikidbase.core.module.command
def date() :
  return "<b>%s</b>" % datetime.datetime.now(); 

@wikidbase.core.module.command
def count(query) :
  # Run a query and get the length of the results.
  queryResults = wikidbase.core.query.runQuery(query)
  total = len(queryResults)
  return total

@wikidbase.core.module.command
def listnames(query) :
  names = ""
  queryResults = wikidbase.core.query.runQuery(query)
  for item in queryResults.queryResults :
    name = item.getData("name")[0].data
    if name :
      names += "%s, " % name.capitalize()
  return names



#
# Custom django views

def simpleView(request) :
  return HttpResponse("This is a simple view.")


def myView(request, arg1=None) :
  """This view renders a page using the wikidbase template."""

  context = {
    "content" : "Hello World",
  }
  
  return django.shortcuts.render_to_response("wikidbase.html", django.template.RequestContext(request, context))
