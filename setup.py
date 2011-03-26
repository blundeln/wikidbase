#
# Copyright (C) 2006-2009 Nick Blundell.
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
# setup (setup.py)
# ----------------
#
# Description:
#
#
# Author       : Nick Blundell
# Organisation : www.nickblundell.org.uk
# Version Info : $Id: setup.py 1161 2009-08-04 15:58:12Z blundeln $
#

import os, sys

VIRTUAL_ENV = "/usr/lib/wikidbase/wikidbase_env"
DJANGO_URL  = "http://media.djangoproject.com/releases/0.96/Django-0.96.3.tar.gz"
DJANGO_TAR_GZ = DJANGO_URL.split("/")[-1]

ENV_PYTHON = os.path.join(VIRTUAL_ENV, "bin","python")
ENV_EASY_INSTALL = os.path.join(VIRTUAL_ENV, "bin","easy_install")

WIKIDBASE_ADMIN = os.path.join("/usr", "bin", "wikidbase-admin")
ENV_WIKIDBASE_ADMIN = os.path.join(VIRTUAL_ENV, "bin", "wikidbase-admin")

def run(command) :
  print command
  os.system(command)

def install() :

  run("python ez_setup.py")
  run("easy_install virtualenv")
  run("virtualenv --no-site-packages '%s'" % VIRTUAL_ENV)

  if not os.path.exists(DJANGO_TAR_GZ) :
    run("wget %s" % DJANGO_URL)
  run("%s %s" % (ENV_EASY_INSTALL, DJANGO_TAR_GZ))
  run("%s real_setup.py install" % (ENV_PYTHON))
  run("ln -fs %s %s" % (ENV_WIKIDBASE_ADMIN, WIKIDBASE_ADMIN))


if __name__ == "__main__" :
  try :
    command = sys.argv[1].lower()
  except :
    command = None

  if command == "install" :
    install()
