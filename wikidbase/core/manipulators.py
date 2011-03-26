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
# manipulators (manipulators.py)
# ------------------------------
#
# Description:
#
#
# Author       : Nick Blundell
# Organisation : www.nickblundell.org.uk
# Version Info : $Id: manipulators.py 1152 2009-04-17 10:14:10Z blundeln $
#

import datetime

from django import oldforms as forms # this is oldforms

import pagecontent, datatype, query
import widgets
import wikidbase.core
import wikidbase.core.context
import pagestore

from nbdebug import *

DEFAULT_PAGE_NAME = "wikidpage"
VIEW_MODE = "VIEW_MODE"
EDIT_MODE = "EDIT_MODE"

class WikidpageContentManipulator(forms.Manipulator) :
  
  def __init__(self, wikidpage, create=False) :
    """Builds a manipulator from a wikidpage's semi-structured content."""
   
    assert(wikidpage)
    self.wikidpage = wikidpage
    
    debugOutput("context = %s" % self.wikidpage.context)
    
    # Get the fields of the wikidpage
    self.fields = []
    wikidpageFields = wikidpage.getFields().getDict()
    
    # For each data field, add a widget to this form.
    for nFieldName in wikidpageFields :
      field = wikidpageFields[nFieldName]
      if wikidbase.core.pagecontent.isDataField(field) :
        self.fields.append(self._selectWidget(field, wikidpage))

  # TODO: Seperate widget selection logic from this function
  def _selectWidget(self, field, wikidpage) :
    """Select the appropriate widget for a wikidpage field.""" 
    
    data = field.data
    
   
    # Try to get the context for this page
    wikidpageContext = None
    if wikidpage.context :
      wikidpageContexts = wikidbase.core.context.getContexts()
      nContext = wikidbase.core.normaliseTerm(wikidpage.context)
      if nContext in wikidpageContexts :
        wikidpageContext = wikidpageContexts[nContext]

    # If there is no data to guess the widget from, look in the context of this page.
    if not data and wikidpageContext :
      if field.nName in wikidpageContext.dataFieldContexts :
        try :
          data = wikidpageContext.dataFieldContexts[field.nName].representativeData.stack[0]
        except :
          pass

    dataObject = datatype.convert(data, mode=datatype.TO_PYTHON)
   
    debugOutput("field %s, data: %s, dataObject: %s, type: %s" % (field.nName, data, dataObject, type(dataObject)))
    
    
    formField = None

    # TODO:
    #
    # if date - > date
    # if bdolean -> checkbox
    # if multiline data
    #   if not list -> text area
    #   else -> multiselect
    # if date - > date
    # if boolean -> checkbox
    # else (if just single line text)
    #   if mlist -> multiselect
    #   if slist -> select
    #   else :
    #     single text field.
    
    # Load the context state.
    widgetType = wikidbase.core.context.AUTO_WIDGET
    listSort = wikidbase.core.context.SORT_MOST_COMMON
    listChoices = []
    if wikidpage.context :
      nContext = wikidbase.core.context.normaliseTerm(wikidpage.context)
      nFieldName = field.nName
      contextFieldState = wikidbase.core.state.getContextFieldState(nContext, nFieldName)
      try :
        widgetType = contextFieldState[wikidbase.core.context.LIST_STYLE]
        listSort = contextFieldState[wikidbase.core.context.LIST_SORT]
        listChoices = contextFieldState[wikidbase.core.context.LIST_CHOICES].splitlines()
      except :
        pass

    debugOutput("widgetType %s, listSort %s, listChoices %s" % (widgetType, listSort, listChoices))
    
    
    # Compute selection choices.
    if wikidpageContext and field.nName in wikidpageContext.dataFieldContexts :
      choices = [choice for choice in wikidpageContext.dataFieldContexts[field.nName].selectionSet]
    else :
      choices = []
  
    # Append field state choices
    choices[0:0] = listChoices

    if data :
      # Note, we interpret lines as multiple selections.
      dataLines = data.splitlines()
      for dataItem in dataLines :
        if dataItem not in choices :
          choices[0:0] = [dataItem]

    # Remove duplicates - could be more efficient.
    uniqueChoices = []
    for choice in choices :
      if choice not in uniqueChoices :
        uniqueChoices.append(choice)
    choices = uniqueChoices

    # Sort choices
    if listSort == wikidbase.core.context.SORT_ASCEND :
      choices.sort()
    elif listSort == wikidbase.core.context.SORT_DESCEND :
      choices.sort(reverse=True)
   
    choices = [[choice, choice] for choice in choices]
   
    # TODO: We should be able to add hooks here so people can add widgets .
    # In wikidbase, there are two ways to choose a widget for a field:
    #  * Explicit: the user sets the widget to single-select/multi-select list, textarea, etc.
    #  * Implicit: the widget is chosen based on data or on context data for that field if empty (e.g. date string -> cal widget).
    if widgetType == wikidbase.core.context.TEXTAREA :
      formField = widgets.LargeTextFieldExtra(field_name=field.name, is_required=False, rows=6,cols=40)
    # TODO: Should we use WP_MULTILINE_FIELD to choose widget now?
    elif data and (field.type == wikidbase.core.pagecontent.WP_MULTILINE_FIELD or "\n" in data) :
      if widgetType == wikidbase.core.context.AUTO_WIDGET :
        formField = widgets.LargeTextFieldExtra(field_name=field.name, is_required=False, rows=6,cols=40)
      else :
        formField = forms.SelectMultipleField(field_name=field.name, is_required=False, choices=choices)
    elif type(dataObject) == datetime.date :
      formField = widgets.NickDatetimeField(field_name=field.name, is_required=False, showsTime=False)
    elif type(dataObject) == datetime.datetime :
      formField = widgets.NickDatetimeField(field_name=field.name, is_required=False, showsTime=True)
    elif type(dataObject) == datetime.time :
      formField = widgets.NickDatetimeField(field_name=field.name, is_required=False, showsTime=True, inputDate=False)
    elif type(dataObject) == bool :
      formField = forms.CheckboxField(field_name=field.name)
    else :
      if widgetType == wikidbase.core.context.MS_LIST :
        formField = forms.SelectMultipleField(field_name=field.name, is_required=False, choices=choices)
      elif widgetType == wikidbase.core.context.SS_LIST :
        formField = widgets.EditableSelectField(field_name=field.name, is_required=False, choices=choices)
      elif field.nName in ["password"] :
        formField = forms.PasswordField(field_name=field.name, is_required=False)
      else :
        formField = widgets.TextFieldExtra(field_name=field.name, is_required=False)

    return formField


  def flatten_data(self) :
    
    debugOutput("Flattening data.")
    data = {}
    
    wikidpageFields = self.wikidpage.getFields().getDict()
    for nFieldName in wikidpageFields :
      field = wikidpageFields[nFieldName]
      if not wikidbase.core.pagecontent.isDataField(field):
        continue

      debugOutput("field.data %s" % field.data)
      dataObject = datatype.convert(field.data, mode=datatype.TO_PYTHON)

      # Expand list data to a list.
      if dataObject and type(dataObject) == str and self.wikidpage.context :
        nContext = wikidbase.core.context.normaliseTerm(self.wikidpage.context)
        nFieldName = field.nName
        contextFieldState = wikidbase.core.state.getContextFieldState(nContext, nFieldName)
        try :
          widgetType = contextFieldState[wikidbase.core.context.LIST_STYLE]
        except :
          widgetType = wikidbase.core.context.AUTO_WIDGET

        if widgetType == wikidbase.core.context.MS_LIST :
          data[field.name] = dataObject.splitlines()
        else :
          data[field.name] = dataObject
      else :
        data[field.name] = dataObject 

    debugOutput("data %s" % data)
    return data


  def save(self, newData) :
    
    debugOutput("Saving data: '%s'" % newData)

#    raise Exception("newData %s" % newData.getlist("Home address"))

    # Try to get the context.
    wikidpageContext = None
    if self.wikidpage.context :
      wikidpageContexts = wikidbase.core.context.getContexts()
      nContext = wikidbase.core.normaliseTerm(self.wikidpage.context)
      if nContext in wikidpageContexts :
        wikidpageContext = wikidpageContexts[nContext]

    
    wikidpageFields = self.wikidpage.getFields().getDict()
    for nFieldName in wikidpageFields :
      field = wikidpageFields[nFieldName]
      if not wikidbase.core.pagecontent.isDataField(field):
        continue
     
      # Get the data object from either the data or the context.
      if field.data :
        dataObject = datatype.convert(field.data, mode=datatype.TO_PYTHON)
      else :
        try :
          dataObject = datatype.convert(wikidpageContext.dataFieldContexts[field.nName].representativeData.stack[0], mode=datatype.TO_PYTHON)
        except :
          dataObject = None

      debugOutput("data object for '%s' is type '%s'" % (field.name, type(dataObject)))

      # TODO: Is this field an ms list.
      nContext = wikidbase.core.context.normaliseTerm(self.wikidpage.context)
      nFieldName = field.nName
      contextFieldState = wikidbase.core.state.getContextFieldState(nContext, nFieldName)
      try :
        widgetType = contextFieldState[wikidbase.core.context.LIST_STYLE]
      except :
        widgetType = wikidbase.core.context.AUTO_WIDGET

      if field.name in newData :
        data = newData.getlist(field.name)
        debugOutput("fname %s type %s data %s" % (field.name, type(data), data))
        if type(data) == list :
          data = "\n".join(data)
          debugOutput("joined data %s" % data)
        # Double convert the data.
        field.data = datatype.convert(datatype.convert(data, mode=datatype.TO_PYTHON), mode=datatype.TO_STRING)
      # Interperet non-posted boolean data.
      elif type(dataObject) == bool :
        field.data = datatype.convert(False, mode=datatype.TO_STRING)
      elif widgetType == wikidbase.core.context.MS_LIST :
        field.data = ""
      # Interpret non-posted multi-select as an empty set.
      # TODO: What happens when no list is posted for ms select.

    self.wikidpage.save()

    # Ensure the wikidpage is given a name.
    if not self.wikidpage.name :
      self.wikidpage.name = "%s-%s" % (wikidbase.core.normaliseTerm(self.wikidpage.context) or DEFAULT_PAGE_NAME,self.wikidpage.id)
      self.wikidpage.save()
    
    return self.wikidpage


def getWikidpageManipulator(editMode, wikidpage) :
  
  create = wikidpage.id == None
  
  if editMode == EDIT_MODE :
    manipulator = create and wikidbase.core.models.WikidPage.AddManipulator() or wikidbase.core.models.WikidPage.ChangeManipulator(wikidpage.id)
  else :
    manipulator = WikidpageContentManipulator(wikidpage=wikidpage, create=create)

  return manipulator
