#!/usr/bin/python
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
# init-script (init-script.py)
# ----------------------------
#
# Description:
#
#
# Author       : Nick Blundell
# Organisation : www.nickblundell.org.uk
# Version Info : $Id$
#

import sys, os, time

def run(command) :
  os.system(command)

try :
  command = sys.argv[1].lower()
except :
  command = None;

if command == "start" :
  run("""START_COMMAND""")
elif command == "stop" :
  run("""STOP_COMMAND""")
elif command == "restart" :
  run("""STOP_COMMAND""")
  time.sleep(3)
  run("""START_COMMAND""")
