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
# tracker (tracker.py)
# --------------------
#
# Description:
#
#
# Author       : Nick Blundell
# Organisation : www.nickblundell.org.uk
# Version Info : $Id$
#


import wikidbase.core.session
from nbdebug import *

IGNORE_URLS = ["media",".png",".jpg",".jpeg",".gif",".js",".ico", ".css","18n","/export_command", "delete_"]

class Tracker(object):
  """Monitors the access of pages in the wikidbase."""

  def process_request(self, request):

    fullPath = request.get_full_path()

    # Don't record media requests.
    for ignorePart in IGNORE_URLS :
      if ignorePart in fullPath.lower() :
        return
    
    # Update the users page-request history
    history = wikidbase.core.session.getVariable(request, "history", [])
    
    # Don't add if this is the same as last page.
    if history and history[0] == fullPath :
      return
    
    history[0:0] = [fullPath]
    debugOutput(history)
    if len(history) > 80 :
      history.pop()
    wikidbase.core.session.setVariable(request, "history", history)
