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
# models (models.py)
# ------------------
#
# Description:
#
#
# Author       : Nick Blundell
# Organisation : www.nickblundell.org.uk
# Version Info : $Id: models.py 955 2008-04-25 15:00:45Z blundeln $
#

import pickle, datetime, urllib

import django
from django.db import models

import wikidbase.core
import wikidbase.thirdparty
import wikidbase.core.performance
import wikidbase.core.pagecontent
import wikidbase.core.cache

from nbdebug import *

# Alternate formats for rendering wikidpages
CONTENT_FORMATS = (
  ("rest","Restructured text"),
  ("plain","Plain text"),
  ("html","HTML"),
)

MODEL = "MODEL"
WIKIDPAGE = "WIKIDPAGE"
PROPERTY = "PROPERTY"

SELECT_SET = "SELECT_SET"
MULTILINE = "MULTILINE"

ID = "ID"
PAGE = "Page"
BODY = "Body"
TYPE = "Page Type"
MODIFIED = "Modified"

PROP_MOD_BY = "PROP_MOD_BY"
PROP_CREATED_BY = "PROP_CREATED_BY"
PROP_ATTACHMENTS = "PROP_ATTACHMENTS"


class WikidPage(models.Model) :
  """
  Stores a wikidpage with as few native database fields as possible, such that arbitrary properties
  may be added in the future in the properties field.
  """
  name = models.CharField(maxlength=256,unique=True, blank=False)
  content = models.TextField(blank=False)
  format = models.CharField(maxlength=40, choices=CONTENT_FORMATS, blank=False, default=CONTENT_FORMATS[0][0])
  context = models.CharField(maxlength=256,blank=True)
  modifiedDate = models.DateTimeField(editable=False, auto_now=False)
 
  # This field helps to speed up queries, and will eventually be replaced with dynamic db optimisation.
  # TODO: Add some lightly-bound native db fields for efficiency.
  nContext = models.CharField(maxlength=256,blank=True, editable=False)
  
  #
  # Arbitrary wikidpage properties.
  #

  propertiesObject = models.TextField(editable=False)

  def getProperties(self) :
    try :
      return self._props
    except :
      self._props = {}#wikidbase.core.Properties()
      if self.propertiesObject :
        try :
          self._props = pickle.loads(self.propertiesObject)
        except :
          self._props = {}
    return self._props
  properties = property(getProperties)

  
  def getContent(self, refresh=False) :
    """Returns an object representation of the wikidpage's content (i.e. with parsed fields)."""
    if refresh or not hasattr(self, "contentCache") :
      self.contentCache = wikidbase.core.pagecontent.WikidpageContent(self.content, pageName=self.name or None)
    return self.contentCache

  
  def getFields(self, refresh=False) :
    """Returns all meta and db fields of he wikidpage"""

    debugOutput("Getting fields")

    if refresh or not hasattr(self, "fieldsCache") :
      fields = Fields()

      # Create fields from the model
      #debugOutput("Create model fields.")
      fields.addField(WikidPageField(name=ID, type=MODEL, data=self.id))
      fields.addField(WikidPageField(name=PAGE, type=MODEL, data=self.name))
      fields.addField(WikidPageField(name=BODY, type=MODEL, data=self.content))
      fields.addField(WikidPageField(name=TYPE, type=MODEL, data=self.context))
      fields.addField(WikidPageField(name=MODIFIED, type=MODEL, data=self.modifiedDate))

      # Create fields from the page's content.
      debugOutput("Create wikidbase fields.")
      
      wikidpageContent = self.getContent() 
      
      for field in wikidpageContent.getOrderedAttributes() :
        fields.addField(field)

      #TODO: Create fields based on properties.
      debugOutput("props %s" % self.properties)
      try :
        fields.addField(WikidPageField(name="Modified by", type=PROPERTY, data=self.properties[PROP_MOD_BY]))
      except :
        pass
      try :
        fields.addField(WikidPageField(name="Created by", type=PROPERTY, data=self.properties[PROP_CREATED_BY]))
      except :
        pass

      self.fieldsCache = fields
    
    debugOutput("Fields: %s" % self.fieldsCache)

    return self.fieldsCache


  def save(self, autoFields=True):
   
    debugOutput("Saving wikidpage")
    
    # Save the properties
    try : self.propertiesObject = pickle.dumps(self._props)
    except : pass
   

    # Update auto fields
    if autoFields :
      self.modifiedDate = datetime.datetime.now()

    # Sync content with the potentially-changed wikidpage fields.
    self.content = self.getContent().getText()

    # Set nContext for faster queries.
    if self.context :
      self.nContext = wikidbase.core.context.normaliseTerm(self.context)

    super(WikidPage, self).save()

    # Clear the caches
    wikidbase.core.cache.clearAllCaches()

  
  def delete(self) :
    # Clear the caches
    wikidbase.core.cache.clearAllCaches()
    super(WikidPage, self).delete()

  
  def getAttachedFiles(self) :
    if PROP_ATTACHMENTS in self.properties :
      return self.properties[PROP_ATTACHMENTS]
    else :
      return {}

  
  def isWikiEditable(self) :
    if self.id :
      return True
    else :
      return False

  
  def getState(self) :

    state = {}
    state["ID"] = self.id
    state["NAME"] = self.name
    state["CONTENT"] = self.content
    state["FORMAT"] = self.format
    state["CONTEXT"] = self.context
    state["MODIFIED_DATE"] = self.modifiedDate
    state["PROPERTIES"] = self.propertiesObject
    return state

  
  def setState(self, state) :
    self.id = state["ID"]
    self.name = state["NAME"]
    self.content = state["CONTENT"]
    self.format = state["FORMAT"]
    self.context = state["CONTEXT"]
    self.modifiedDate = state["MODIFIED_DATE"]
    self.propertiesObject = state["PROPERTIES"]

  
  class Admin:
    list_display = ('name','modifiedDate')
 
  
  class Meta:
    ordering = ["name"]

  
  def get_absolute_url(self):
    return "/%s/" % urllib.quote(self.name)

  
  def __repr__(self) :
    return "%s(%s-%s)" % (self.__class__.__name__, self.name, self.id)

  # Utility fields reserved for later native db optimsation.
  int1 = models.IntegerField(editable=False,db_index=True, null=True)
  int2 = models.IntegerField(editable=False,db_index=True, null=True)
  dt1 = models.DateTimeField(editable=False,db_index=True, null=True)
  dt2 = models.DateTimeField(editable=False,db_index=True, null=True)
  t1 = models.TextField(editable=False, db_index=True)
  t2 = models.TextField(editable=False, db_index=True)
  c1 = models.CharField(maxlength=256, editable=False, db_index=True)
  c2 = models.CharField(maxlength=256, editable=False, db_index=True)

    
class WikidPageLink(models.Model) :
  """ Links two wikidpages together. """
  # TODO: Model should also store normalised link names.
  page1 = models.IntegerField(blank=False,db_index=True)
  page2 = models.IntegerField(blank=False,db_index=True)
  linkName1 = models.CharField(maxlength=256)
  linkName2 = models.CharField(maxlength=256)
 
  def save(self):
    super(WikidPageLink, self).save()
    # Clear the caches
    wikidbase.core.cache.clearAllCaches()

  def delete(self) :
    # Clear the caches
    # TODO: Delete attached files here.
    super(WikidPageLink, self).delete()
    wikidbase.core.cache.clearAllCaches()

  def getState(self) :
    state = [self.page1, self.page2, self.linkName1, self.linkName2]
    return state

  def setState(self, state) :
    self.page1, self.page2, self.linkName1, self.linkName2 = state

  class Admin:
    list_display = ("page1","linkName1","page2","linkName2")


class GlobalState(models.Model) :
  """Stores arbitrary global state in the database."""
  stateName = models.CharField(editable=False, maxlength=256)
  globalState = models.TextField(editable=False)

  def getState(self) :
    # This may fail if wikidbase has been updated significantly (e.g. refs to old modules).
    try :
      return pickle.loads(self.globalState)
    except :
      return {}
  
  def setState(self, state) :
    self.globalState = pickle.dumps(state)



#
# Useful classes
#

class WikidPageField :
  """This defines a wikidpage field wrapper, allowing db fields and meta fields to be accessed with a common interface."""
  def __init__(self, name, type, data, flags=[]) :
    self.name, self.type, self.data, self.flags = name, type, data, flags
    self.nName = wikidbase.core.context.normaliseTerm(self.name)
    debugOutput("Creating %s %s %s %s" % (name, type, data, flags))

  def __str__(self) :
    return "%s: %s %s (%s) [%s]" % (self.__class__.__name__, self.name, self.type, self.flags or "", type(self.data) == str and self.data[0:min(len(self.data),20)] or self.data)


class Fields :
  def __init__(self) :
    debugOutput("Creating")
    self.fields = wikidbase.thirdparty.odict.OrderedDict()

  def addField(self, field) :
    debugOutput("Adding field %s" % field)
    self.fields[field.nName] = field

  def getField(self, fieldName) :
    nFieldName = wikidbase.core.context.normaliseTerm(fieldName)
    return self.fields[nFieldName]

  def getList(self) :
    fieldList = []
    for nFieldName in self.fields :
      fieldList.append(self.fields[nFieldName])
    return fieldList

  def getDict(self) :
    return self.fields

  def __str__(self) :
    result = ""
    for nFieldName in self.fields :
      result = "%s\n%s" % (result, self.fields[nFieldName])
    return result

