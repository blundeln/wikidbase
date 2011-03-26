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
# session (session.py)
# --------------------
#
# Description:
#  Handles browser session things
#
# Author       : Nick Blundell
# Organisation : www.nickblundell.org.uk
# Version Info : $Id$
#

from nbdebug import *

#
# These methods abstract over the django user message API to allow messages for anonymouse users.
# 
def setMessage(request, message) :
  if not hasattr(request.user, "message_set") :
    if "anon_msg" not in request.session :
      request.session["anon_msg"] = []
    request.session["anon_msg"].append(message)
  else :
    request.user.message_set.create(message=message)

def getAndDeleteMessages(request) :
  if not hasattr(request.user, "message_set") :
    if "anon_msg" in request.session :
      messages = request.session["anon_msg"]
      request.session["anon_msg"] = []
    else :
      messages = []
  else :
    #XXX: django will beat us to this, so how can we replace django messages.
    messages = request.user.get_and_delete_messages()

  return messages

def getVariable(request, variable, default=None) :
  if variable in request.session :
    return request.session[variable]
  else :
    return default

def setVariable(request, variable, value) :
  request.session[variable] = value
