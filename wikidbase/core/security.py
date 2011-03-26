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
# security (security.py)
# ----------------------
#
# Description:
#  Contains wikidbase authorisation API.
#
#
# Author       : Nick Blundell
# Organisation : www.nickblundell.org.uk
# Version Info : $Id$
#


from django.contrib.auth.models import User, check_password

import query, pagecontent, pagestore
import wikidbase.core.context
import wikidbase.core.state

from nbdebug import *

ANONYMOUS = "anonymous"
AUTHENTICATED = "authenticated"

# This gets thrown from the barrier function.
class NotAuthorised(Exception) : pass

def hasPermission(username, permission):
  """
  This is the main method for checking user's permissions within the wikidbase.
  Permissions may look like this -> create.people, edit.page 1, graphmodule.view, graphmodule.edit
  """  
  assert(type(permission) == str and type(username) == str)

  debugOutput("Checking if %s has permission %s" % (username, permission))

  # Note, user might be non if anonymous.
  user = getUser(username)
  if user and user["is_superuser"] :
    return True

  # Get a list of permission variables to check for this user.
  permissionVars = [encodePermission(permission, username=username)]
  groups = getUserRoles(username)
  debugOutput("%s belongs to groups %s" % (username, groups))
  for group in groups :
    permissionVars.append(encodePermission(permission, group=group))
  
  # Check each permission to see if at least one is set.
  for permissionVar in permissionVars :
    if wikidbase.core.state.getVariable(permissionVar) :
      debugOutput("%s has permission %s" % (username, permissionVar))
      return True

  return False

def roleHasPermission(role, permission):
  """
  This checks whether a roles has the specified permission.
  """  
  assert(type(permission) == str)
  permissionVar = encodePermission(permission, group=role)
  # TODO: must also check against a user's groups.
  if wikidbase.core.state.getVariable(permissionVar) :
    return True
 
  return False

def setPermission(permission, value, username=None, group=None) :
  """Set a permissions for a user or group."""
  assert(username or group)
  permissionVar = encodePermission(permission, username, group)
  if value :
    wikidbase.core.state.setVariable(permissionVar, True)
  else :
    wikidbase.core.state.setVariable(permissionVar, None)

def barrier(username, *args) :
  """
  Throws NotAuthorised if the user does not have specified permission.
  args are permission strings for ORing.  This is useful for view functions.
  """
  authorised = False
  for permission in args :
    if hasPermission(username, permission) :
      authorised = True
      break
    
  if not authorised :
    raise NotAuthorised(username, permission)

def getPermissionsList() :
  """
  Returns a list of all possible permissions in wikidbase, including those provided by plugins.
  as a dict of category -> permissions
  """
  permissions = {}
  corePermissions = {}
  permissions = {
    "Wikidpages" : [
      "create",
      "view",
      "edit",
      "wiki-edit",
      "delete",
    ],
  }

  # Allow modules to define permissions.
  permissions = wikidbase.core.module.hookDefinePermissions(permissions)

  return permissions


def getUsers() :
  """Gets a dictionary of wikidbase users."""
  djangoUsers = User.objects.all()
  users = {}

  for djangoUser in djangoUsers :
    users[djangoUser.username] = getUser(djangoUser.username)

  return users
  
  

def getUser(username) :
  """Gets a user - and augmented django user."""
  try :
    djangoUser = User.objects.get(username__exact = username)
  except :
    return None

  # Convert user to a dict, so we can add more info from wikidbase
  user = {}
  user["username"] = djangoUser.username
  user["first_name"] = djangoUser.first_name
  user["last_name"] = djangoUser.last_name
  user["is_superuser"] = djangoUser.is_superuser
  user["email"] = djangoUser.email

  # TODO: Could possibly add a hook here, so mods can add stuff to users.

  return user
  
def saveUser(user) :
  """Saves a user."""
  # Check if the user exists.
  try :
    djangoUser = User.objects.get(username = user["username"])
  except :
    djangoUser = User()

  # Update the django user.
  if not djangoUser.username :
    # Enforce that uernames cannot be changed once created.
    djangoUser.username = user["username"]
  djangoUser.first_name = user["first_name"]
  djangoUser.last_name = user["last_name"]
  djangoUser.is_superuser = user["is_superuser"]
  djangoUser.email = user["email"]

  # Update the new password.
  if "password" in user and user["password"] :
    djangoUser.set_password(user["password"])

  # TODO: Could possibly add a hook here, so mods can add stuff to users.
  
  djangoUser.save()


def deleteUser(username) :
  if username not in getUsers() :
    raise Exception("User %s does not exist." % username)

  # Remove the user from groups.
  setUserRoles(username, [])

  # Delete the django user.
  djangoUser = User.objects.get(username = username)
  djangoUser.delete()



def getRoles() :
  return wikidbase.core.state.getVariable("user roles", {})

def setRoles(groups) :
  wikidbase.core.state.setVariable("user roles", groups)

def getRoleNames() :
  """Returns the names of all groups, including authenticated and anonymous."""
  return [ANONYMOUS, AUTHENTICATED] + getRoles().keys()

def getUserRoles(username) :
  """Gets a list of roles of the user."""
  if not username :
    return [ANONYMOUS]

  groups = [AUTHENTICATED]
  allGroups = getRoles()
  # For each group, check if the user is in it.
  for group in allGroups :
    if username in allGroups[group] :
      groups.append(group)
  debugOutput("username %s roles %s" % (username, groups))
  return groups


def setUserRoles(username, roles) :
  """Sets a user's roles."""
  allGroups = getRoles()
  debugOutput("username %s roles %s allGroups %s" % (username, roles, allGroups))
  for group in allGroups :
    if group in roles :
      if username not in allGroups[group] :
        debugOutput("Added %s to %s" % (username, group))
        allGroups[group].append(username)
    else :
      try :
        allGroups[group].remove(username)
        debugOutput("Removed %s from %s" % (username, group))
      except ValueError :
        pass

  setRoles(allGroups)



def getTemplatePerms(request) :
  """
  Returns a dict-like object that looks up perms for a user.  This is just for convience in templates
  so you can write {% if permissions.can_do_this %} -> hasPermission(..., "can do this").
  """
  class TemplatePerms: 
    def __init__(self, username) :
      self.username = username
    def __getitem__(self, key) :
      # Django templates don't like spaces here, so allow user to sub '_'.
      if hasPermission(self.username, key) :
        return True
      else :
        return hasPermission(self.username, key.replace("_"," "))
  return TemplatePerms(request.user.username)


#
# Override django's permission checking function.
#

def permissionIntercept(self, permission):
  # Note that self will be a user object when this method is grafted onto the django class.
  if hasPermission(self.username, permission) :
    return True
  
  # Then fall back on the Django permission stuff - needed for and django pages, such as admin pages.
  return self.orig_has_perm(permission)


class AddWikidbasePermissions(object):
    def process_request(self, request):
      debugOutput("Adding wikidbase permissions")
      
      # Slyly add our permission method wrapper to the user class.
      if not hasattr(request.user.__class__, "orig_has_perm") :
        request.user.__class__.orig_has_perm = request.user.__class__.has_perm
        request.user.__class__.has_perm = permissionIntercept


#
# Utility functions.
#

def encodePermission(permission, username=None, group=None) :
  """Encodes a permission for storing in the wikidbase state."""
  type = group and "group" or "user"
  return "permission.%s.%s.%s" % (type, username or group, permission)

