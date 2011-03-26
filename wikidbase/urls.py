#
# Copyright (C) 2007 Nick Blundell.
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
# urls (urls.py)
# --------------
#
# Description:
#
#
# Author       : Nick Blundell
# Organisation : www.nickblundell.org.uk
# Version Info : $Id: urls.py 951 2008-04-22 15:32:07Z blundeln $
#

from django.conf.urls.defaults import patterns, include
import django.conf

import wikidbase.core.module


# Map URLs to django view functions.
urlpatterns = patterns('',
    
    # Django pages.
    (r'^admin/', include('django.contrib.admin.urls')),
    (r'^jsi18n/$', 'django.views.i18n.javascript_catalog', {'packages': 'django.conf'}),
    (r'^accounts/login/$', 'django.contrib.auth.views.login', {"template_name":"login.html"}),
    (r'^accounts/logout/$', 'django.contrib.auth.views.logout', {"template_name":"logout.html"}),
)

# Add urls from plugin modules.
moduleUrls = wikidbase.core.module.hookURLs()
if moduleUrls :
  urlpatterns += patterns('', *moduleUrls)

urlpatterns += patterns('',
    
    # XXX: Redirect this until django lets us set in settings. 
    (r'^accounts/profile.*$', 'wikidbase.core.views.redirect', {"dest":"/"}),
    
    # Media files.
    (r'^media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': django.conf.settings.MEDIA_ROOT}),
    
    # Uploaded files.
    (r'^FILES/(?P<path>.*)$', 'django.views.static.serve', {'document_root': django.conf.settings.UPLOAD_FOLDER}),
    (r'^DELETE_FILE/(?P<pageID>.*?)/(?P<filename>.*?)$', 'wikidbase.core.views.deleteFile'),

    # Initialise.
    (r'^INIT/$', 'wikidbase.core.views.initialise'),
   
    # Configure a field
    (r'^CONFIG_FIELD/(?P<context>.+?)/(?P<fieldName>.+?)$', 'wikidbase.core.views.configField'),
    
    # AJAX Stuff.
    (r'^ajax/page_lookup/$', 'wikidbase.core.views.pageLookup'),
    (r'^ajax/foreignlink_lookup/$', 'wikidbase.core.views.foreignlinkLookup'),

    # Load a system page.
    (r'^SYSTEM/(?P<systemPage>.*)/$', 'wikidbase.core.views.page'),
    
    # Data export
    (r'^EXPORT_COMMAND/(?P<source>.+?)/(?P<command>.*)/(?P<filename>.*?)$', 'wikidbase.core.views.exportCommand'),
    (r'^EXPORT_LINKS/(?P<pageID>.*?)/(?P<linkName>.*?)/(?P<filename>.*?)$', 'wikidbase.core.views.exportLinks'),
    
    # Wikidpage manipulation
    (r'^(?P<page>.*)EDIT/CREATE/(?P<clonePage>.*)$', 'wikidbase.core.views.page',{"editSource":True,"create":True}),
    (r'^(?P<page>.*)CREATE/(?P<clonePage>.*)$', 'wikidbase.core.views.page',{"editSource":False,"create":True}),
    (r'^(?P<page>.*)EDIT/$', 'wikidbase.core.views.page',{"editSource":True}),
    (r'^(?P<id>.*)/DELETE_PAGE/$', 'wikidbase.core.views.deletePage'),
    (r'^(?P<id>.*)/DELETE_LINK/(?P<linkID>.*)/(?P<linkField>.*)/$', 'wikidbase.core.views.deleteLink'),
    (r'^(?P<page>.*)$', 'wikidbase.core.views.page'),
)

