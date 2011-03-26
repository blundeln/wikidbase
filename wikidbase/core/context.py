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
# context (context.py)
# --------------------
#
# Description:
#  This module is concerned with infering contextual information from the wikidbase data.
#
# Author       : Nick Blundell
# Organisation : www.nickblundell.org.uk
# Version Info : $Id$
#

import re, copy

import wikidbase.thirdparty
import wikidbase.core.pagestore
import wikidbase.core.pagecontent
import wikidbase.core.cache
import wikidbase.core.performance
import wikidbase.core.state

from nbdebug import *


# Maximum number of term variations to store.
MAX_VARIATIONS = 20

MAX_SELECTION_SET = 100

# TODO: Move this to settings file.
SINGULARS = {
  "pages":"page",
  "people":"person",
}

# Context state constants.
LIST_CHOICES = "LIST_CHOICES"
LIST_STYLE = "LIST_STYLE"
SS_LIST = "SS_LIST"
MS_LIST = "MS_LIST"
AUTO_WIDGET = "AUTO_WIDGET"
TEXTAREA = "TEXTAREA"
LIST_SORT = "LIST_SORT"
SORT_ASCEND = "SORT_ASCEND"
SORT_DESCEND = "SORT_DESCEND"
SORT_MOST_COMMON = "SORT_MOST_COMMON"


class FieldContext :
  """Stores contextual information about a particular field of a wikidpage of a particular context."""

  def __init__(self) :
    """Creation."""
    debugOutput("Creating")
    self.fieldNameVariations = TermVariations()
    self.representativeData = LimitedStack(MAX_VARIATIONS)
    self.selectionSet = []

  def __str__(self) :
    return "%s: %s data: %s selections: %s" % (self.__class__.__name__, self.fieldNameVariations, self.representativeData, self.selectionSet)

  def __repr__(self) :
    return self.__str__()



class LinkContext :
  """
  Stores contextual information about a link between wikidpages.
  This little fella' is what learns about a user's relational model.  Suppose I had a person page
  and I had a project page and I create a link like this 'person -> works on -> project' and the reciprocal
  'project -> staff -> person' then this allows this sort of link to be infered for other people and projects and
  offered to the user for convenience, so they don't have to re-describe and existing relationship.
  """
  
  def __init__(self) :
    """Creation."""
    debugOutput("Creating")
    self.nameVariations = TermVariations()
    self.commonTargets = {}

  def addCommonTarget(self, targetLink) :
    """Adds the target link name variation."""
    nTargetLink = normaliseTerm(targetLink)
    if nTargetLink not in self.commonTargets :
      commonTarget = self.commonTargets[nTargetLink] = TermVariations()
      commonTarget.addVariation(targetLink)



class WikidpageContext :
  """
  Stores contextual imformation about a particular wikidpage context. For example:
    * Fields and their name variations.
    * Relationships between wikidpages of this context
  """

  def __init__(self) :
    """Creation."""

    debugOutput("Creating")
    
    # Variations in the context name: e.g. Person, person, Animal, ANIMAL, etc.)
    self.contextNameVariations = TermVariations()
    
    # A selection of wikidpages represtative of this context - remember: wikidbase has no seperate data model: data defines the model.
    self.representativeWikidpages = LimitedStack(MAX_VARIATIONS)
    
    # Stores contextual information about each field.
    self.dataFieldContexts = wikidbase.thirdparty.odict.OrderedDict()
    
    # Stores contextual information about links.
    self.linkContexts = {}
    


  def updateLinkContext(self, wikidpage) :
    """Update link context using this wikidpage."""

    debugOutput("Adding link information.")
    
    # Get the links of this wikidpage.
    rawLinks = wikidbase.core.pagestore.getRawLinks(wikidpage.id)

    # Examine each link.
    for linkName in rawLinks :
      
      # If there is yet no record of this link name, add it to the context.
      nLinkName = normaliseTerm(linkName)
      if nLinkName not in self.linkContexts :
        self.linkContexts[nLinkName] = LinkContext()
      linkContext = self.linkContexts[nLinkName]
      
      # Add the link name variation.
      linkContext.nameVariations.addVariation(linkName)
      
      # Add target link names that reciprocate this link to the context.
      for link in rawLinks[linkName] :
        linkContext.addCommonTarget(link[1])

  
  def addField(self, field) :
    """Add field information to the context."""

    debugOutput("Adding field %s" % field)
   
    if field.nName not in self.dataFieldContexts :
      self.dataFieldContexts[field.nName] = FieldContext()
    dataFieldContext = self.dataFieldContexts[field.nName]
    
    # Add the field name variation. 
    dataFieldContext.fieldNameVariations.addVariation(field.name)
   
    # Store the field type.
    dataFieldContext.fieldType = field.type

    # If there is data in this field, record some information about that data (sample values, type).
    if field.data :
      dataFieldContext.representativeData.addItem(field.data)
      if field.type == wikidbase.core.pagecontent.WP_FIELD and len(dataFieldContext.selectionSet) < MAX_SELECTION_SET :
        if field.data not in dataFieldContext.selectionSet :
          dataFieldContext.selectionSet.append(field.data)
    

  def getFieldContexts(self) :
    return self.dataFieldContexts

  def __str__(self) :
    return "%s:\nContext name: %s\nFields: %s" % (self.__class__.__name__, self.contextNameVariations, self.dataFieldContexts)



@wikidbase.core.cache.memoize
def getContexts() :
  """API function that returns the computed wikidbase context."""
  debugOutput("Getting contexts")
  return buildContexts()
  

def buildContexts() :
  """This is the main process of building a context from a wikidbase."""

  debugOutput("Building contexts")

  contexts = {}

  # Get all of the wikidpages.
  wikidpages = wikidbase.core.pagestore.getAllPages().order_by("modifiedDate")
  
  # Process each wikidpage.
  for wikidpage in wikidpages :
    
    # We only need to process pages with contexts.
    context = wikidpage.context
    if not context :
      continue

    # Normalise the context term.
    nContext = wikidbase.core.normaliseTerm(context)
    
    # Add a new container for the context if it has not yet been processed.
    if nContext not in contexts :
      contexts[nContext] = WikidpageContext()
   
    # Update the wikidpage context.
    wikidpageContext = contexts[nContext]
    wikidpageContext.contextNameVariations.addVariation(context)
    wikidpageContext.representativeWikidpages.addItem(wikidpage)
    
    # Update the context with each wikidpage field.
    fields = wikidpage.getFields().getDict()
    for nFieldName in fields :
      wikidpageContext.addField(fields[nFieldName])
   
    # Update the context with link information from this wikidpage.
    wikidpageContext.updateLinkContext(wikidpage)
  
  return contexts



#
# Useful methods and classes.
#

# Normalisation and singlurisation regexs.
reNormalise = re.compile(r"\W")
reSingular1 = re.compile(r"ies$")
reSingular2 = re.compile(r"([^sS])s$")
reSingular3 = re.compile("sses$")


class LimitedStack :
  """Stores a limited number of stack items: old things drop off the bottom."""
  
  def __init__(self, limit) :
    self.limit = limit
    self.stack = []
  
  def addItem(self, item) :
    """Adds new item to the top of the stack."""
    if item not in self.stack :
      self.stack[0:0] = [item]
      if len(self.stack) > self.limit :
        self.stack.pop()

  def __str__(self) :
    return "LimitedStack: %s" % (self.stack)



class TermVariations :
  """
  Stores variations of terms and a count of their occurance (i.e. terms before they get irreversibly (I probably can't spell) normalised.
  For example, a term to describe a Field: Firstname may have the following variations entered by users:
    * First Name
    * First name
    * firstname
    * first_name (not implemented this one yet)
  and we don't want smartbox to not figure out what the user means when these variations are used.
  """
  
  def __init__(self) :
    debugOutput("Creating")
    self.terms = {}
  
  def addVariation(self, term) :
    """Add a new term variation."""
    if term not in self.terms :
      self.terms[term] = 1
    else :
      self.terms[term] += 1

  def getVariations(self) :
    """Get all of the term variations."""
    return self.terms.keys()

  def getOrderedTerms(self) :
    """Get a list of term variations ordered by a count of their usage."""
    termList = self.terms.items()
    termList.sort(key=lambda x: x[1])
    debugOutput(termList)
    return [term[0] for term in termList] 
  
  def getMostCommon(self) :
    """Gets the most common of these term variations."""
    return self.getOrderedTerms()[0]
  
  def __str__(self) :
    return "TermVariations: %s" % (self.getVariations())



class TermPath:
  """Allows paths of terms to be manipulated and normalised"""
  def __init__(self,termPath) :
    if type(termPath) == str :
      self.termPath = self.parse(termPath)
    else :
      self.termPath = termPath

  def getParts(self) :
    return self.termPath
  def getPrefixPart(self) :
    return self.termPath[0:-1]
  def getBasePart(self) :
    return self.termPath[-1]

  def parse(self, termPath) :
    return termPath.split(".")

  def getNormalisedForm(self) :
    # TODO: each item in path should be normalised (e.g. pet.name, pets.name -> same)
    return normaliseTerm(self.__str__())

  def __str__(self) :
    return ".".join(self.termPath)


#
# Methods for term normalisation
#

def getAllTermVariations() :
  """Returns a list of term variations in the wikidbase; sort of the opposite of normalising terms."""

  termVariations = []
  contexts = getContexts()
    
  # Build up a list of term variations for contexts and field names.
  for nContext in contexts :
    termVariations += contexts[nContext].contextNameVariations.getVariations()
    for fieldName in contexts[nContext].dataFieldContexts :
      termVariations += contexts[nContext].dataFieldContexts[fieldName].fieldNameVariations.getVariations()
    
    for relFieldName in contexts[nContext].linkContexts :
      termVariations += contexts[nContext].linkContexts[relFieldName].nameVariations.getVariations()

  return termVariations


def deleteRelationship(index) :
  relationships = wikidbase.core.state.getVariable("relationships", [])
  del relationships[index]
  wikidbase.core.state.setVariable("relationships", relationships)

def getContextRelationships(nContext) :
  relationships = getAllRelationships()
  contextRelationships = {}

  for relationship in relationships :
    nRelContextA = normaliseTerm(relationship[0])
    nRelContextB = normaliseTerm(relationship[1])
    relA = relationship[2]
    relB = relationship[3]
    if nRelContextA == nContext :
      if relA not in contextRelationships :
        contextRelationships[relA] = []
      if relB not in contextRelationships[relA] :
        contextRelationships[relA].append(relB)
    if nRelContextB == nContext :
      if relB not in contextRelationships :
        contextRelationships[relB] = []
      if relA not in contextRelationships[relB] :
        contextRelationships[relB].append(relA)
    
  return contextRelationships
  

# TODO: Not sure if this should go here.
def getAllRelationships() :
  return wikidbase.core.state.getVariable("relationships", [])

def addRelationship(typeA, typeB, relA, relB) :
  relationships = getAllRelationships()
  
  # TODO: Ensure no duplicates get in.
  
  relationships.append((typeA, typeB, relA, relB))
  wikidbase.core.state.setVariable("relationships", relationships)

# TODO: this MUST be made more efficient
@wikidbase.core.performance.Timer
def normaliseTerm(term) :
  """This is the key to providing fuzzy logic for queries and wikidbase model inference."""
  term = reNormalise.sub("", singularTerm(term.lower()).strip())
  return term

def singularTerm(term) :
  """This helps the user a little when doing queries and things."""

  # Hmmm, something to note: 'if' is quicker than 'try ... except'.
  if term in SINGULARS :
    return SINGULARS[term]
 
  term = reSingular2.sub(r"\1", reSingular3.sub("ss",term))
  return term
