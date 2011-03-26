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
# middleware (middleware.py)
# --------------------------
#
# Description:
#
#
# Author       : Nick Blundell
# Organisation : www.nickblundell.org.uk
# Version Info : $Id$
#

import re
from django.conf import settings
from urllib import quote
from nbdebug import *
import django.contrib.auth.views
from django.http import HttpResponseRedirect, HttpResponse

LOGIN_URL = "/%s/accounts/login" % settings.URL_PREFIX

class HttpResponseRedirectWithPrefix(HttpResponse):
  def __init__(self, redirect_to):
    HttpResponse.__init__(self)
    self['Location'] = quote("/%s%s" % (settings.URL_PREFIX, redirect_to), safe=django.http.RESERVED_CHARS)
    self.status_code = 302

class URLPrefix(object):
  
  def process_request(self, request):
    if not settings.URL_PREFIX :
      return
    if not settings.URL_PREFIX in request.path :
      raise Exception("Expected URL %s to have prefix %s" % (request.path, settings.URL_PREFIX))
    request.path = request.path.replace("%s/" % settings.URL_PREFIX,"")

  def process_response(self, request, response) :
    if not settings.URL_PREFIX :
      return response
    debugOutput(request.path)
    debugOutput(response.content)
    for attribute in ["href","action","src"] : 
      if attribute in response.content :
        response.content = re.sub("""(%s\s*=\s*"/)""" % attribute,r"""\1%s/""" % settings.URL_PREFIX,response.content)
        debugOutput(response.content)
    return response

class URLPrefixLoginFix(object):
  
  def process_request(self, request):

    # We need to do this until LOGIN_URL appears in django settings file - as in django dev.
    if settings.URL_PREFIX :
      django.http.HttpResponseRedirect = HttpResponseRedirectWithPrefix
      django.contrib.auth.LOGIN_URL = "/%s/accounts/login" % settings.URL_PREFIX
      # XXX: Next line doesnt have an effect.
      django.contrib.auth.LOGIN_REDIRECT_URL = "/%s/accounts/profile" % settings.URL_PREFIX
