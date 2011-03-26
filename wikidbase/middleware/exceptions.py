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
# exceptions (exceptions.py)
# --------------------------
#
# Description:
#
#
# Author       : Nick Blundell
# Organisation : www.nickblundell.org.uk
# Version Info : $Id$
#

import django.contrib.auth
from django.conf import settings
from django.http import HttpResponseRedirect
import django.template
import django.shortcuts
import wikidbase.core.security

class ExceptionHandler :
  def process_exception(self, request, exception) :
    self.require_login_path = getattr(settings, 'REQUIRE_LOGIN_PATH', django.contrib.auth.LOGIN_URL)
    # Handle NotAuthorised exception.
    if exception.__class__ == wikidbase.core.security.NotAuthorised :
      message = "Sorry, but you are not authorised to do this."
      if request.user.is_anonymous() :
        message += "<br/><a href='/accounts/login'>[login]</a>"
      return django.shortcuts.render_to_response("message.html", django.template.RequestContext(request, {"message":message}))
