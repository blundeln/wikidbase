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
# __init__ (__init__.py)
# ----------------------
#
# Description:
#
#
# Author       : Nick Blundell
# Organisation : www.nickblundell.org.uk
# Version Info : $Id: __init__.py 681 2007-05-30 14:28:19Z blundeln $
#


def normaliseTerm(term) :
  import wikidbase.core.context
  return wikidbase.core.context.normaliseTerm(term)

def singulariseTerm(term) :
  import wikidbase.core.context
  return wikidbase.core.context.singulariseTerm(term)

# Need to loose this.
class xProperties :
  def __init__(self) : self.__dict__["properties"] = {}
  def __setattr__(self, name, value) : self.__dict__["properties"][name] = value
  def __getattr__(self, name, default=None) : return name in self.properties and self.properties[name] or default
  def __str__(self) : return str(self.__dict__)
