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
# pagecontent (pagecontent.py)
# ----------------------------
#
# Description:
#
#
# Author       : Nick Blundell
# Organisation : www.nickblundell.org.uk
# Version Info : $Id: pagecontent.py 972 2008-05-25 21:44:48Z blundeln $
#

import re
import datatype

import wikidbase.core.models
import wikidbase.core.context
import wikidbase.thirdparty

from nbdebug import *

TOP = "TOP"
BELOW = "BELOW"

#TODO: If multiline, add delemeters; if not, remove them.

# Wikidpage cloning methods.
CLONE_WHOLE = "CLONE_WHOLE"
CLONE_ONLY_FIELDS = "CLONE_ONLY_FIELDS"

# Wikidpage element types.
WP_FIELD = "WP_FIELD"
WP_SELECT_FIELD = "WP_SELECT_FIELD" # Deprecated
WP_MULTILINE_FIELD = "WP_MULTILINE_FIELD"
WP_COMMAND = "WP_COMMAND"

# A grouping of wikidpage data elements.
WP_DATA_FIELDS = [
  WP_FIELD,
  WP_MULTILINE_FIELD,
]


class WikidpageContent :
  """This is the essence of wikidbase, parsing wikidpage source into a data object with fields, etc."""


  def __init__(self,text=None, pageName=None):
    debugOutput("Creating.")
    if not text : text = ""
    self.pageName = pageName
    self.setText(text)


  def _parseAttributeData(self, text) :
    """Parses wikidpage attributes from the source."""
    
    debugOutput("Synchronising attributes.")
    self.attributes = wikidbase.thirdparty.odict.OrderedDict()
    self.template = text
    self.noCommands = 0

    def subField(match) :
      """Parses elements from the page and substitutes them in the text to create a rendering template."""
      debugOutput("matches: %s" % match.groupdict())
      
      # Determine type of element (e.g. command, field)
      if match.groupdict()["command"] != None :
        # This is a command, so remember its regex and generate an internal name for the command.
        expression = commandExpression
        name = "%s" % (self.noCommands)
        data = match.groupdict()["command"]
        self.noCommands += 1
      else :
        # This is some sort of field, so remember its regex and store its name and data.
        for i in range(0, len(allExpressions)) :
          if match.groupdict()["fieldName%s" % i] :
            break
        expression = allExpressions[i]
        name = match.groupdict()["fieldName%s" % i]
        data = match.groupdict()["data%s" % i]

      # Select the field type based on the regex matched by this element.
      if expression == commandExpression :
        type = WP_COMMAND
      elif expression == multilineFieldExpression :
        type = WP_MULTILINE_FIELD
      else :
        type = WP_FIELD
     
      debugOutput("name=%s type=%s data='%s'" % (name, type, data))

      # Create the field object and store it.
      field = wikidbase.core.models.WikidPageField(type=type, name=name, data=data.strip())
      self.attributes[field.nName] = field

      # Return a substitution token for this element, so that, during renedering, a form field/rendered command can be subsituted.
      return "[%s-%s]" % (type, field.nName)

    # Create a template from the source by substituting elements with tokens.
    self.template = anyFieldExpression.sub(subField, self.template)

  def addField(self, fieldName, value, position) :
    debugOutput("Adding field %s %s %s" % (fieldName, value, position))
    
    # Create the field
    field = wikidbase.core.models.WikidPageField(type=WP_FIELD, name=fieldName, data=value)
   
    if field.nName in self.attributes :
      debugOutput("Field already exists.")
      return

    # Determine the above or below field
    if position[0] == "above" and position[1] in self.attributes :
      # Position okay.
      pass
    else :
      # TODO: What if not fields already?
        # Add to top of page???
      position = ("below", self.attributes.keys()[-1])
    
    debugOutput(position)

    # Add the field.
    self.attributes[field.nName] = field

    # Regenerate text with the field in.
    self._regenerateText(field, position)
    

  def deleteField(self, nFieldName) :
    if nFieldName in self.attributes :
      del self.attributes[nFieldName]

  def _encodeFieldAsText(self, field) :
    if field.type == WP_MULTILINE_FIELD or (type(field.data) == str and len(field.data.splitlines()) > 1):
      # If it is a muliline field, format it nicely in the source (ie. with new lines).
      fieldText = "%s%s%s\n%s\n%s" % (field.name, DELIMITER, LEFT_DELIMITER, field.data, RIGHT_DELIMITER)
    else :
      fieldText = "%s%s%s %s" % (field.name, field.type == WP_SELECT_FIELD and SELECT_SYMBOL or "", DELIMITER, field.data)
    return fieldText


  def _regenerateText(self, newField=None, position=None) :
    """This reciprocates source parsing by re-generating source based on current field data."""
    
    debugOutput("Syncing page text.")
   
    #
    # Sync the text to the attributes.
    #
    def subSyncText(match) :

      # Add field
      # If this is first, and new field above it
      # else if field below this, return with new text below.

      # Get the name, normalised name, and original data from the source.
      name = match.group("fieldName").strip()
      nName = wikidbase.core.context.normaliseTerm(name)
      originalData = match.groupdict()["data"].strip()
      
      if nName not in self.attributes :
        # If there was no field, assume it has been deleted, so sub with ''.
        return ""
      else :
        # Get the parsed field object for this element.
        field = self.attributes[nName]

      if originalData == field.data :
        # If the data is unchanged, replace with original pattern matched. 
        replacement = match.groups()[0]
      else :
        # Regenerate the source from the field object.
        replacement = self._encodeFieldAsText(field)
      
      # Check if a new field is to be added.
      if newField :
        debugOutput("newField %s position %s nName %s" % (newField, position, nName))
      if newField and position[1] == nName :
        if position[0] == "above" :
          replacement = "%s\n%s" % (self._encodeFieldAsText(newField), replacement)
        else :
          replacement = "%s\n%s" % (replacement, self._encodeFieldAsText(newField))
   
      return replacement
    
    # Run the various regexs on the text to generate new text based on current element data.
    self.text = fieldExpression.sub(subSyncText, self.text)
    self.text = multilineFieldExpression.sub(subSyncText, self.text)
    self.text = selectFieldExpression.sub(subSyncText, self.text)

    if newField :
      debugOutput(self.text)


  def getOrderedAttributes(self) :
    """Returns a source-ordered list of the attributes."""
    return [self.attributes[nFieldName] for nFieldName in self.attributes]


  def setText(self,text) :
    """Update the source of the wikidpage, causing it to be parsed."""
    self.text = text
    self._parseAttributeData(self.text)


  def getText(self) :
    """Gets the regenerated source of this wikidpage."""
    self._regenerateText()
    return self.text


  def getClone(self, mode=CLONE_WHOLE, cloneData=False) :
    """Returns a clone of this wikidpage (i.e. a page with identical semi-structure).""" 
    debugOutput("Cloning content")
  
    debugOutput("Source Text: %s" % self.getText())

    if mode == CLONE_WHOLE :
      
      # If we make a whole clone, we want all the page text (e.g. fields and unstructured stuff like text).
      contentClone = WikidpageContent(text=self.getText())
    
    elif mode == CLONE_ONLY_FIELDS :
      
      # If we make a field-only clone, we want only the fields and not general text from the page.
      newText = ""
      # For each element, generate some source for the field.
      for attribute in self.getOrderedAttributes() :
        debugOutput(attribute.name)
        
        # Write the appropriate field markup.
        if attribute.type == WP_FIELD :
          newText += "%s%s\n" % (attribute.name, DELIMITER)
        elif attribute.type == WP_MULTILINE_FIELD :
          newText += "%s%s%s\n\n%s\n" % (attribute.name, DELIMITER, LEFT_DELIMITER, RIGHT_DELIMITER)

      # Create a clone based on the newly generated field-only source.
      contentClone = WikidpageContent(text=newText)
   
    # Clone or erase the field data as specified.
    for attribute in contentClone.getOrderedAttributes() :
      if attribute.type in WP_DATA_FIELDS :
        attribute.data = cloneData and self.attributes[attribute.nName].data or ""
   
    return contentClone


  def __str__(self): 
    """A string representation of this object, for debugging."""
    displayString = ""
    firstDisplayed = False
    for attribute in self.getOrderedAttributes() :
      if attribute.type != WP_FIELD :
        continue
      if attribute.data and type(datatype.convert(attribute.data, mode=datatype.TO_PYTHON)) == str and "\n" not in attribute.data:
        displayString += "%s: %s, " % (attribute.name, attribute.data)
        firstDisplayed = True
    return displayString.rstrip(", ")



#
# Regular expressions for parsing wikidpage element markup.
#

# Wikidpage markup symbols.
DELIMITER = "::"
COMMAND_DELIMITER = ":::"
LEFT_DELIMITER = "{{"
RIGHT_DELIMITER = "}}"
SELECT_SYMBOL = "[]"

# TODO: Need to alter this so can support non-english field names. re.UNICODE???
FIELD_NAME_RE = "\w[\w ]+\w"


fieldExpression = re.compile(
  "(^"
    "(?P<fieldName>%s)(%s)"
    "(?P<data>[^\n^(%s)]*)"
  "$)" % (FIELD_NAME_RE, DELIMITER,LEFT_DELIMITER),
re.MULTILINE)

selectFieldExpression = re.compile(
  "(^"
    "(?P<fieldName>\w[\w ]+\w)\[\](%s)"
    "(?P<data>[^\n^(%s)]*)"
  "$)" % (DELIMITER, LEFT_DELIMITER),
re.MULTILINE)

multilineFieldExpression = re.compile(
  "(^"
    "(?P<fieldName>\w[\w ]+\w)(%s)"
    "[\s]*(%s)(?P<data>.*?)(%s)"
  ")" % (DELIMITER, LEFT_DELIMITER, RIGHT_DELIMITER),
re.MULTILINE | re.DOTALL)

# XXX: Deprecated.
relationalFieldExpression = re.compile(
  "(^"
    "(%s)(?P<fieldName>\w[\w ]+\w)(%s)"
  ")" % (DELIMITER,DELIMITER),
re.MULTILINE)


commandExpression = re.compile(
  "("
    "(%s)(?P<command>[^%s^\n]*)(%s)"
  ")" % (COMMAND_DELIMITER,COMMAND_DELIMITER,COMMAND_DELIMITER),
re.MULTILINE)


allExpressions = [fieldExpression, selectFieldExpression, multilineFieldExpression, commandExpression]
anyFieldPattern = ""
for expression in allExpressions :
  i = allExpressions.index(expression)
  anyFieldPattern += "%s|" % expression.pattern.replace("fieldName","fieldName%s" % i).replace("data","data%s" % i)
anyFieldPattern = anyFieldPattern.strip("|")

anyFieldExpression = re.compile(anyFieldPattern, re.MULTILINE | re.DOTALL)



#
# Useful functions.
#

def isDataField(field) :
  if field.type in WP_DATA_FIELDS :
    return True
  else :
    return False
