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
# __init__ (__init__.py)
# ----------------------
#
# Description:
#
#
# Author       : Nick Blundell
# Organisation : www.nickblundell.org.uk
# Version Info : $Id$
#

import django.shortcuts
import django.template
import django.http
import django.views.static
from wikidbase.core.module import ModuleInfo
import wikidbase.core.security
import wikidbase.core.session
import wikidbase.core.context
import wikidbase.core.pagecontent
import wikidbase.thirdparty.odict
import forms

from nbdebug import *

#
# Module Views
#

def controlPanel(request) :
  wikidbase.core.security.barrier(request.user.username, "access administration pages")
 
  context = {
    "pageTabs":getPageTabs(),
  }

  return django.shortcuts.render_to_response("controlpanel.html", django.template.RequestContext(request, django.template.Context(context)))  


def users(request, username=None) :
  wikidbase.core.security.barrier(request.user.username, "access administration pages")

  users = wikidbase.core.security.getUsers()

  if username :
    user = wikidbase.core.security.getUser(username)
  else :
    user = None

  if request.method == 'POST':
    userForm = forms.UserForm(request.POST)
    if userForm.is_valid():
      userForm.save()
      if user :
        wikidbase.core.session.setMessage(request, message="The user has been updated.")
        return django.http.HttpResponseRedirect("/controlpanel/users/%s" % username)
      else :
        wikidbase.core.session.setMessage(request, message="The new user has been added.")
        return django.http.HttpResponseRedirect("/controlpanel/users")
  else:
    userForm = forms.UserForm(user=user)

  context = {
    "users":users,
    "pageTabs":getPageTabs("Users"),
    "userForm":userForm,
  }
  return django.shortcuts.render_to_response("users.html", django.template.RequestContext(request, context))  
 

def userDelete(request, username=None) :
  wikidbase.core.security.barrier(request.user.username, "access administration pages")
  
  if request.POST :
    if "Delete" in request.POST :
      wikidbase.core.security.deleteUser(username)
      wikidbase.core.session.setMessage(request, message="User '%s' has been deleted." % (username))
    
    return django.http.HttpResponseRedirect("/controlpanel/users")
  else :
    # Render a question to the user.
    message = "Are you sure you wish to delete the user '%s'?" % username
    options = ["Delete","Cancel"]
    return django.shortcuts.render_to_response("message.html", django.template.RequestContext(request, {"message":message, "options":options}))

def roles(request) :

  wikidbase.core.security.barrier(request.user.username, "access administration pages")
  
  roles = wikidbase.core.security.getRoles()

  if request.POST :
    addRoleForm = forms.AddRoleForm(request.POST)
    if addRoleForm.is_valid():
      addRoleForm.save()
      wikidbase.core.session.setMessage(request, message="The new role has been added.")
      return django.http.HttpResponseRedirect("/controlpanel/roles")

  else :
    addRoleForm = forms.AddRoleForm()
  
  context = {
    "pageTabs":getPageTabs("Roles"),
    "roles":roles,
    "addRoleForm":addRoleForm,
  }
  return django.shortcuts.render_to_response("roles.html", django.template.RequestContext(request, context))  

def roleDelete(request, role) :
  wikidbase.core.security.barrier(request.user.username, "access administration pages")
  
  if request.POST :
    if "Delete" in request.POST :
      roles = wikidbase.core.security.getRoles()
      if role in roles :
        del roles[role]
        wikidbase.core.security.setRoles(roles)
        wikidbase.core.session.setMessage(request, message="Role '%s' has been deleted." % (role))
    
    return django.http.HttpResponseRedirect("/controlpanel/roles")
  else :
    # Render a question to the user.
    message = "Are you sure you wish to delete the role '%s'?" % role
    options = ["Delete","Cancel"]
    return django.shortcuts.render_to_response("message.html", django.template.RequestContext(request, {"message":message, "options":options}))


def permissions(request) :
  wikidbase.core.security.barrier(request.user.username, "access administration pages")
  
  if request.POST :
    permissionsForm = forms.PermissionsForm(request.POST)
    if permissionsForm.is_valid(): 
      permissionsForm.save()
      wikidbase.core.session.setMessage(request, message="Permissions have been updated.")
    
    return django.http.HttpResponseRedirect("/controlpanel/permissions")

  else :
    permissionsForm = forms.PermissionsForm()
    
  context = {
    "pageTabs":getPageTabs("Permissions"),
    "permissionsForm":permissionsForm,
  }

  return django.shortcuts.render_to_response("permissions.html", django.template.RequestContext(request, django.template.Context(context)))  


def data(request, filename=None) :
  """Data management view."""
  wikidbase.core.security.barrier(request.user.username, "access administration pages")

  # Download the data file.
  if filename and filename.startswith("wikidbase-data") and "tar" in filename :
    debugOutput(filename)
    renderedPage = django.views.static.serve(request, filename, "/tmp/wikidbase_tmp")
    os.remove(os.path.join("/tmp", "wikidbase_tmp", filename))
    return renderedPage

  # Handle file uploads
  post_data = request.POST.copy()
  post_data.update(request.FILES)
  
  # Handle file uploads
  if post_data :
    dataLoadForm = forms.DataLoadForm(post_data)
    debugOutput("valid: %s" % dataLoadForm.is_valid())
    if dataLoadForm.is_valid() :
      dataLoadForm.save()

    wikidbase.core.session.setMessage(request, message="Data has been loaded.")

  else :
    dataLoadForm = forms.DataLoadForm()

  if request.POST :
    if "dump-button" in request.POST and request.POST["dump-button"] == "dump" :
      debugOutput("Dumping data")
      dumpFile = wikidbase.core.pagestore.dump(request.META["HTTP_HOST"], django.conf.settings.UPLOAD_FOLDER)
      return django.http.HttpResponseRedirect("/controlpanel/data/%s" % os.path.basename(dumpFile))
  
  context = {
    "pageTabs":getPageTabs("Data"),
    "dataLoadForm":dataLoadForm.as_p(),
  }
  
  return django.shortcuts.render_to_response("datamanage.html", django.template.RequestContext(request, context))


def datatypes(request) :
 
  wikidbase.core.security.barrier(request.user.username, "access administration pages")

  # Get a list of all contexts.
  contexts = wikidbase.core.context.getContexts(); 

  # Get the name variations.
  contextNames = {}
  for nContext in contexts :
    contextNames[nContext] = contexts[nContext].contextNameVariations.getVariations()[0]
 
  if request.POST :
    relationshipsForm = forms.RelationshipsForm(request.POST)
    if relationshipsForm.is_valid() :
      relationshipsForm.save()

    wikidbase.core.session.setMessage(request, message="Relationship definitions have been saved.")

  # We always want an empty 
  relationshipsForm = forms.RelationshipsForm()


  context = {
    "pageTabs":getPageTabs("Data Types"),
    "contexts": contextNames,
    "relationshipsForm":relationshipsForm,
  }

  return django.shortcuts.render_to_response("datatypes.html", django.template.RequestContext(request, django.template.Context(context)))  

def deleteRelationship(request, relationshipNo) :
  debugOutput("Deleting relationship %s" % relationshipNo)

  if request.POST :
    if "Delete" in request.POST :
      wikidbase.core.context.deleteRelationship(int(relationshipNo))
      wikidbase.core.session.setMessage(request, message="The relationship has been deleted.")

    return django.http.HttpResponseRedirect("/controlpanel/datatypes")
  else :
    # Render a question to the user.
    message = "Are you sure you wish to delete the relationship?"
    options = ["Delete","Cancel"]
    return django.shortcuts.render_to_response("message.html", django.template.RequestContext(request, {"message":message, "options":options}))


def datatype(request, context) :

  wikidbase.core.security.barrier(request.user.username, "access administration pages")
  # Get the fields of this context.
  wikidbaseContexts = wikidbase.core.context.getContexts()
  nContext = wikidbase.core.context.normaliseTerm(context)
  wikidbaseContext = wikidbaseContexts[nContext]

  fieldContexts = wikidbaseContext.getFieldContexts()

  configurableFields = wikidbase.thirdparty.odict.OrderedDict()
  for nFieldName in fieldContexts :
    if fieldContexts[nFieldName].fieldType in wikidbase.core.pagecontent.WP_DATA_FIELDS :
      configurableFields[nFieldName] = fieldContexts[nFieldName].fieldNameVariations.getVariations()[0]

  # Handle file uploads
  if request.POST :
    addFieldForm = forms.AddFieldForm(request.POST, fields=configurableFields)
    if addFieldForm.is_valid() :
      addFieldForm.save(nContext)
      wikidbase.core.session.setMessage(request, message="The field has been added to all '%s' wikidpages." % (nContext))
  else :
    addFieldForm = forms.AddFieldForm(fields=configurableFields)

  context = {
    "pageTabs":getPageTabs("Data Types"),
    "fields":configurableFields,
    "context":wikidbaseContext.contextNameVariations.getVariations()[0],
    "nContext":nContext,
    "addFieldForm":addFieldForm,
  }

  return django.shortcuts.render_to_response("datatype.html", django.template.RequestContext(request, context))  

def deleteField(request, nContext, nField) :
  
  wikidbase.core.security.barrier(request.user.username, "access administration pages")
  if request.POST :
    if "Delete" in request.POST :
      wikidbase.core.pagestore.deleteField(nContext, nField)
      wikidbase.core.session.setMessage(request, message="Field '%s' has been deleted." % (nField))
    
    return django.http.HttpResponseRedirect("/controlpanel/datatype/%s" % nContext)
  else :
    # Render a question to the user.
    message = "Are you sure you wish to delete the field '%s' and its data from all %s pages? This cannot be undone." % (nField, nContext)
    options = ["Delete","Cancel"]
    return django.shortcuts.render_to_response("message.html", django.template.RequestContext(request, {"message":message, "options":options}))

  
  return django.http.HttpResponseRedirect("/controlpanel/datatype/%s" % nContext)


#
# Module hook implementations
#

def hookURLs() :
  urls = (
    (r'^controlpanel/$', controlPanel),
    (r'^controlpanel/users/$', users),
    (r'^controlpanel/users/(?P<username>.*?)/delete/$', userDelete),
    (r'^controlpanel/users/(?P<username>.*?)/$', users),
    (r'^controlpanel/roles/$', roles),
    (r'^controlpanel/roles/(?P<role>.*?)/delete/$', roleDelete),
    (r'^controlpanel/permissions/$', permissions),
    (r'^controlpanel/data/(?P<filename>.*?)$', data),
    
    (r'^controlpanel/datatypes/$', datatypes),
    (r'^controlpanel/datatypes/deleterelation/(?P<relationshipNo>.*)/$', deleteRelationship),
    (r'^controlpanel/datatype/(?P<nContext>.*?)/delete/(?P<nField>.*?)/$', deleteField),
    (r'^controlpanel/datatype/(?P<context>.*?)/$', datatype),

    # Add a url to serve our module's media.
    (r'^controlpanel/media/(?P<path>.*)$', 'django.views.static.serve', {"document_root":wikidbase.core.module.getModuleDir("controlpanel","media")}),
  )
  return urls

def hookDefinePermissions(permissions) :

  if "Administrator" not in permissions :
    permissions["Administrator"] = []
  
  permissions["Administrator"] = [
    "access administration pages",
  ]

  return permissions

def hookMainMenu(context, menuLinks) :
  username = context["user"].username
  
  if wikidbase.core.security.hasPermission(username, "access administration pages") :
    menuLinks[0:0] = [
      ("/controlpanel","Control panel","Go to the control panel","/controlpanel/media/images/controlpanel.png"),
      None,
    ]
  else :
    pass

  return menuLinks

def hookInfo() :
  info = ModuleInfo(name="Control Panel", version="1.0", author="Nick Blundell", description="Wikidbase Control Panel")
  return info

#
# Helper functions.
#

def getPageTabs(active=None) :
  pageTabs = []
  pageTabs.append(("Users", "/controlpanel/users", active=="Users", "", "Manage users" ))
  pageTabs.append(("Roles", "/controlpanel/roles", active=="Roles", "", "Manage user roles" ))
  pageTabs.append(("Permissions", "/controlpanel/permissions", active=="Permissions", "", "Manage permissions" ))
  pageTabs.append(("Data Types", "/controlpanel/datatypes", active=="Data Types", "", "Data Type Settings" ))
  pageTabs.append(("Data", "/controlpanel/data", active=="Data", "", "Manage data" ))
  return pageTabs
