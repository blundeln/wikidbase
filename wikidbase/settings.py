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
# settings (settings.py)
# ----------------------
#
# Description:
#
#
# Author       : Nick Blundell
# Organisation : www.nickblundell.org.uk
# Version Info : $Id: settings.py 976 2008-06-11 18:51:28Z blundeln $
#

import os, sys
import wikidbase
from nbdebug import *


#
# Settings
#

# Database settings
DATABASE_ENGINE = ""
DATABASE_NAME = ""
DATABASE_USER = ""
DATABASE_PASSWORD = "" 
DATABASE_HOST = ""
DATABASE_PORT = ""

# Set the cache system.
CACHE_BACKEND = ""

# Set this to a folder on the server that the wikidbase can write to.
UPLOAD_FOLDER = ""

# Local time zone for this installation. All choices can be found here:
# http://www.postgresql.org/docs/current/static/datetime-keywords.html#DATETIME-TIMEZONE-SET-TABLE
TIME_ZONE = 'Europe/London'

# Language code for this installation. All choices can be found here:
# http://www.w3.org/TR/REC-html40/struct/dirlang.html#langcodes
# http://blogs.law.harvard.edu/tech/stories/storyReader$15
# Note that changing this will affect date formats (e.g. en-us will use US style dates)
LANGUAGE_CODE = 'en-gb'



#
# DEBUG SETTINGS
#

DEBUG = "NB_DEBUG" in os.environ
DEBUG = True
TEMPLATE_DEBUG = DEBUG

# EXPERIMENTAL: Set this if wikidbase lives under a url prefix
URL_PREFIX = None

# Setup testing database
if "TESTDB" in os.environ :
  DATABASE_NAME = os.environ["TESTDB"]
  DATABASE_ENGINE = "sqlite3"
  CACHE_BACKEND = "db://wbcache"
  UPLOAD_FOLDER = "/tmp/wikidbasefiles"

# Setup testing cache
if "CACHE_BACKEND" in os.environ:
  CACHE_BACKEND = os.environ["CACHE_BACKEND"]


#
# SYSTEM SETTINGS
#


CODE_ROOT = os.path.dirname(os.path.abspath(wikidbase.__file__))
SITE_ROOT = os.path.dirname(os.path.abspath(__file__))

# Where to look for wikidbase plugin modules.
MODULE_PATHS = [
  os.path.join(SITE_ROOT, "modules"),
]



#
# DJANGO SETTINGS
#

ADMINS = ()
MANAGERS = ADMINS

SITE_ID = 1

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = os.path.join(CODE_ROOT,"media")

# URL that handles the media served from MEDIA_ROOT.
# Example: "http://media.lawrence.com"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/%sadmin_media/' % (URL_PREFIX and ("%s/" % URL_PREFIX) or "")

LOGIN_REDIRECT_URL = "/"

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'f^=yhhideq%7t02_g9cbj4mr$l17l8-t34w2m$^wry2+d4%fcv'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
  'django.template.loaders.filesystem.load_template_source',
  'django.template.loaders.app_directories.load_template_source',
  'wikidbase.core.module.loadModuleTemplate'
)

MIDDLEWARE_CLASSES = (
  'wikidbase.middleware.urlprefix.URLPrefixLoginFix',
  'django.middleware.common.CommonMiddleware',
  'django.contrib.sessions.middleware.SessionMiddleware',
  'django.contrib.auth.middleware.AuthenticationMiddleware',
  'wikidbase.middleware.requirelogin.RequireLoginMiddleware',
  'wikidbase.middleware.exceptions.ExceptionHandler',
  'django.middleware.doc.XViewMiddleware',
  'wikidbase.core.security.AddWikidbasePermissions',
  #XXX: Though we want this, it seems to mess with tar.gz files.
  #'django.middleware.gzip.GZipMiddleware',
  'wikidbase.middleware.urlprefix.URLPrefix',
  'wikidbase.middleware.tracker.Tracker',
)

ROOT_URLCONF = 'wikidbase.urls'

TEMPLATE_DIRS = (
  # Put strings here, like "/home/html/django_templates".
  # Always use forward slashes, even on Windows.
)

INSTALLED_APPS = (
  'django.contrib.auth',
  'django.contrib.contenttypes',
  'django.contrib.sessions',
  'django.contrib.sites',
  'django.contrib.admin',
  'wikidbase.core'
)

TEMPLATE_CONTEXT_PROCESSORS = [
  'django.core.context_processors.auth',
  'django.core.context_processors.debug',
  'django.core.context_processors.i18n',
  'wikidbase.globalcontext.global_context',
]
