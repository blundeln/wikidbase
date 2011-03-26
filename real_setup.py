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
# Version Info : $Id: setup.py 1149 2009-04-15 10:51:09Z blundeln $
#
import ez_setup 
ez_setup.use_setuptools()
from setuptools import setup, find_packages
import os, sys
ROOT = os.path.dirname(__file__)

MAIN_PACKAGE = "wikidbase"
exec("import %s" % MAIN_PACKAGE)
VERSION = eval("%s.BASE_VERSION" % MAIN_PACKAGE)

def get_command_classes():
  """Loads additional distutils commands"""
  classes = {}
  if os.path.exists("disttools") and "bdist_deb" in sys.argv:
    sys.path.append("disttools")
    import bdist_deb
    classes["bdist_deb"] = bdist_deb.bdist_deb
    
  return classes


setup(
  name = MAIN_PACKAGE,
  version = VERSION,
  packages = find_packages(),
  install_requires=["django < 1.0","pyparsing","docutils","nbdebug","parsedatetime"],
  dependency_links=[
    "http://www.nickblundell.org.uk/packages/",
    "http://pypi.python.org/packages/source/p/pyparsing/"
  ],
  author="Nick Blundell",
  scripts=["scripts/wikidbase-admin"],
  description = """A highly flexible, easily-evolvable semi-structured database system, based on a wiki.""",
  long_description = """A highly flexible, easily-evolvable semi-structured database system, based on a wiki.  Wikidbase allows you to create simple or complex relational data models and run powerful queries using simple syntax.  As a modular framework, it is also possible to write entire applications as wikidbase plug-ins.""",
  classifiers=["python"],
  include_package_data = True,
  zip_safe=False,
  cmdclass=get_command_classes(),
)
