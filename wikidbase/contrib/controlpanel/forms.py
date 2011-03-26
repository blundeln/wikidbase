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
# forms (forms.py)
# ----------------
#
# Description:
#
#
# Author       : Nick Blundell
# Organisation : www.nickblundell.org.uk
# Version Info : $Id$
#

from django import newforms
import django.conf

import wikidbase.core.security
import wikidbase.core.pagestore
import wikidbase.core.context

from nbdebug import *


class PermissionsForm(newforms.Form):
  
  def __init__(self, *args, **kwargs):
    debugOutput("Creating")
    
    super(self.__class__, self).__init__(*args, **kwargs)

    # Add some fields
    roles = wikidbase.core.security.getRoleNames()
    permissions = wikidbase.core.security.getPermissionsList()
    for role in roles :
      for category in permissions :
        for permission in permissions[category] :
          initial = wikidbase.core.security.roleHasPermission(role, permission)
          self.fields[self.getFieldName(role, category, permission)] = newforms.BooleanField(required=False, initial=initial)

  def getFieldName(self, role, category, permission) :
     return "%s--%s--%s" % (wikidbase.core.context.normaliseTerm(role), category, permission)
     #return unicode("%s--%s--%s" % (role, category, permission),errors="replace")

  def save(self) :
    debugOutput("Saving")
    
    roles = wikidbase.core.security.getRoleNames()
    permissions = wikidbase.core.security.getPermissionsList()
    for role in roles :
      for category in permissions :
        for permission in permissions[category] :
          fieldName = self.getFieldName(role, category, permission)
          if fieldName in self.clean_data :
            wikidbase.core.security.setPermission(permission, self.clean_data[fieldName], group=role)


  def __unicode__(self) :
    output = u""
  
    roles = wikidbase.core.security.getRoleNames()
    permissions = wikidbase.core.security.getPermissionsList()
    
    # Roles
    headings = u""
    headings += "<tr><th></th>"
    for role in roles :
      headings += "<th>%s</th>" % role.capitalize()
    headings += "</tr>\n"
    output += headings

    for category in permissions :
      output += "<tr class='category'><td colspan='50'>%s</td></tr>\n" % category.capitalize()

      for permission in permissions[category] :
        cells = u""
        for role in roles :
          fieldName = self.getFieldName(role, category, permission)
          field = self.fields[fieldName]
          cells += "<td>%s</td>" % unicode(newforms.forms.BoundField(self, field, fieldName))
        row = u"<tr><td>%s</td>%s</tr>" % (permission.capitalize(), cells)
        output += row

   
    # If all permissions are unchecked, nothing gets posted, so this field ensures a post.
    forcePostField = """<input type="hidden" name="force-field" value="forcepost"/>"""
    output += forcePostField

    output = "<table class='permissions'>%s</table>" % output

    return output
    

class AddRoleForm(newforms.Form):

  new_role = newforms.CharField(max_length=50)

  def save(self) :
    roles = wikidbase.core.security.getRoles()
    newRole = self.clean_data["new_role"]
    if newRole not in roles :
      roles[newRole] = []
    wikidbase.core.security.setRoles(roles)


class UserForm(newforms.Form):

  username = newforms.CharField(max_length=50)
  first_name = newforms.CharField()
  last_name = newforms.CharField()
  email = newforms.EmailField()
  password = newforms.CharField(widget=newforms.PasswordInput(render_value=False), required=False)
  password_confirm = newforms.CharField(widget=newforms.PasswordInput(render_value=False), required=False)
  is_superuser = newforms.BooleanField(required=False)
  
  def __init__(self, *args, **kwargs) :
    debugOutput("Creating")

    # Pre-load with user details if there is a user.
    if "user" in kwargs and kwargs["user"] :
      user = kwargs["user"]
      initial = user
      self.mode = "edit"
      # TODO: Load the roles of this user.
    else :
      initial = None
      user = None
      self.mode = "create"
    
    if "user" in kwargs :
      del kwargs["user"]
    super(self.__class__, self).__init__(initial=initial, *args, **kwargs)
   
    # Setup the roles field.
    choices = [(role, role) for role in wikidbase.core.security.getRoles()]
    userRoles = user and wikidbase.core.security.getUserRoles(user["username"]) or []
    self.fields["roles"] = newforms.MultipleChoiceField(initial=userRoles, widget=newforms.CheckboxSelectMultiple, choices=choices, required=False)

  def clean(self):
    if 'password' in self.clean_data and 'password_confirm' in self.clean_data:
      if self.clean_data['password'] != self.clean_data['password_confirm']:
        raise newforms.ValidationError(u'The passwords do not match.')
    return self.clean_data

  def save(self) :
    debugOutput("Saving")

    # Try to get an existing user
    user = wikidbase.core.security.getUser(self.clean_data["username"]) or {}
    for field in self.clean_data :
      user[field] = self.clean_data[field]

    # Update roles.
    wikidbase.core.security.setUserRoles(self.clean_data["username"], self.clean_data["roles"])

    # Save the user.
    wikidbase.core.security.saveUser(user)


class DataLoadForm(newforms.Form): 
  upload_data_file = newforms.Field(widget=newforms.FileInput(), required=False)
  server_data_file = newforms.CharField(required=False)

  def save(self) :
   
    if self.clean_data["server_data_file"] :
      wikidbase.core.pagestore.load(self.clean_data["server_data_file"], wikidbase.core.pagestore.MODE_CLEAR, django.conf.settings.UPLOAD_FOLDER)
    elif self.clean_data['upload_data_file'] :
      filename = self.clean_data['upload_data_file']['filename']
      data = self.clean_data['upload_data_file']['content']
      filePath = os.path.join("/tmp", filename)
      open(filePath, "wb").write(data)
      wikidbase.core.pagestore.load(filePath, wikidbase.core.pagestore.MODE_CLEAR, django.conf.settings.UPLOAD_FOLDER)
      os.remove(filePath)
    else :
      return

class RelationshipsForm(newforms.Form) :
 
 def __init__(self, *args, **kwargs) :
    debugOutput("Creating")

    super(self.__class__, self).__init__(*args, **kwargs)
   
    # Get a list of contexts.
    types = []
    wikidbaseContexts = wikidbase.core.context.getContexts()
    for nContext in wikidbaseContexts :
      types.append(wikidbaseContexts[nContext].contextNameVariations.getMostCommon())
    types = [(x,x.capitalize()) for x in types]


    self.fields["relationtypea"] = newforms.ChoiceField(choices=types, required=False)
    self.fields["relationtypeb"] = newforms.ChoiceField(choices=types, required=False)
    self.fields["relationnamea"] = newforms.CharField(required=False)
    self.fields["relationnameb"] = newforms.CharField(required=False)
    
    # TODO: ensure initial values are not displayed.
    # Make sure the fields do not get autocompleted by the browser.
    #for fieldName in ["relationtypea", "relationtypeb", "relationnamea", "relationnameb"] :
    #  field = self.fields[fieldName]
    #  field.widget.attrs.update({"autocomplete":"off"})
    

 def save(self) :
  debugOutput("Saving")
  if self.clean_data["relationtypea"] and self.clean_data["relationtypeb"] and self.clean_data["relationnamea"] and self.clean_data["relationnameb"] :
    wikidbase.core.context.addRelationship(self.clean_data["relationtypea"], self.clean_data["relationtypeb"], self.clean_data["relationnamea"], self.clean_data["relationnameb"])


 def __unicode__(self) :
 
  output = u""

  output += u"<tr><th colspan='2'>Types</th><th colspan='2'>Relationship</th><th></th></tr>"

  # Get relationships
  relationships = wikidbase.core.context.getAllRelationships()
  
  for relationship in relationships :
    row = ""
    for item in relationship:
      row += u"<td>%s</td>" % unicode(item).capitalize()

    row += """<td> <a href="/controlpanel/datatypes/deleterelation/%s" title="Delete this relationship definition"><img src="/media/images/delete.png"/></a> </td>""" % relationships.index(relationship)
    output += "<tr>%s</tr>" % row

  row = ""
  for fieldName in ["relationtypea", "relationtypeb", "relationnamea", "relationnameb"] :
    row += u"<td>%s</td>" % unicode(newforms.forms.BoundField(self, self.fields[fieldName], fieldName))
  output += "<tr>%s</tr>" % row

  output = u"<table>%s</table>" % output

  return output


class AddFieldForm(newforms.Form): 
  #TODO: Delete relationships.
  field_name = newforms.CharField()
  default_value = newforms.CharField(required=False)
  
  def __init__(self, *args, **kwargs) :
    debugOutput("Creating")

    if "fields" in kwargs and kwargs["fields"] :
      fields = kwargs["fields"]
      del kwargs["fields"]
    else :
      fields = []
    
    super(self.__class__, self).__init__(*args, **kwargs)
    
    choices = [("above__" + nField, "Above " + fields[nField]) for nField in fields]
    choices.append(("bottom", "Bellow all fields"))
    self.fields["position"] = newforms.ChoiceField(choices=choices, required=True)

  def save(self, nContext) :
    
    if self.clean_data["position"] == "bottom" :
      position, nField = "bottom", None
    else :
      position, nField = self.clean_data["position"].split("__")

    defaultData = "default_value" in self.clean_data and self.clean_data["default_value"] or ""

    wikidbase.core.pagestore.addField(nContext, fieldName = self.clean_data["field_name"], defaultData = defaultData, position=position, nField=nField)
