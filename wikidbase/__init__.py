#
# Copyright (C) 2009 Nick Blundell.
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
# __init__ (__init__.py)
# ----------------------
#
# Description:
#
#
# Author       : Nick Blundell
# Organisation : www.nickblundell.org.uk
# Version Info : $Id: __init__.py 1162 2009-08-05 11:56:06Z blundeln $
#

import os
VERSION_PARTS = ("1","0","b3")


def getMeta() :

  meta = {}
  
  import re
  import pkg_resources

  try :
    pkgInfo = pkg_resources.resource_string(__name__, "/../EGG-INFO/PKG-INFO")
  except :
    pkgInfo = None

  if pkgInfo :
    version = re.search("^Version:\s*(?P<version>\S+)", pkgInfo, flags=re.MULTILINE)
    version = version and version.groupdict()["version"] or None
    if version : meta["version"] = version
    
  return meta

def getCredits() :
  return "wikidbase %s Copyright (C) Nick Blundell (www.nickblundell.org.uk) 2006-2009" % (VERSION)

def getCodeRoot() :
  return os.path.dirname(__file__)

META = getMeta()
BASE_VERSION = "%s%s" % (".".join(VERSION_PARTS[0:-1]), VERSION_PARTS[-1] and ".%s" % VERSION_PARTS[-1])
VERSION = "version" in META and META["version"] or BASE_VERSION
