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
# files (files.py)
# ----------------
#
# Description:
#  File system api for wikidbase.  This modules has methods for all of the file system things.
#
#
# Author       : Nick Blundell
# Organisation : www.nickblundell.org.uk
# Version Info : $Id$
#

import os

import django.conf

from nbdebug import *


def getUploadFolder() :
  """Returns the upload folder if one had been specified and is writable by wikidbase."""
  try :
    uploadPath = django.conf.settings.UPLOAD_FOLDER
  except :
    uploadPath = None

  # If the upload path does not exist, try to create it.
  if not os.path.exists(uploadPath) :
    try :
      os.makedirs(uploadPath)
    except :
      pass

  if uploadPath and os.access(uploadPath, os.W_OK) :
    return uploadPath

  return None
