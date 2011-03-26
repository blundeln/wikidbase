#
# Copyright (C) 2006-TODAY Nick Blundell.
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
# query (query.py)
# ----------------
#
# Description:
#   This module handles anything related to searching or querying a wikidbase.
#   A query is a string command that returns a list of tuples.
#
# Author       : Nick Blundell
# Organisation : www.nickblundell.org.uk
# Version Info : $Id: query.py 957 2008-04-30 18:56:15Z blundeln $
#

import re, time, datetime
import pyparsing

import wikidbase.core.pagestore
import wikidbase.core.pagecontent
import wikidbase.core.datatype
import wikidbase.core.context
import wikidbase.core.cache
import wikidbase.thirdparty.odict
import wikidbase.core.module

from nbdebug import *


PRIMARY_WIKIDPAGE = ""

MAX_LOOKUP_LEN = 40
ANY_FIELD = "ANYFIELD"
ANYTHING = "ANYTHING"
PAGES = "PAGES"

#
# Query operators and their parsible symbols.
#

OPERATOR_EQUAL = "OPERATOR_EQUAL"
OPERATOR_STARTSWITH = "OPERATOR_STARTSWITH"
OPERATOR_CONTAINS = "OPERATOR_CONTAINS"
OPERATOR_GE = "OPERATOR_GE"
OPERATOR_GT = "OPERATOR_GT"
OPERATOR_LE = "OPERATOR_LE"
OPERATOR_LT = "OPERATOR_LT"
OPERATOR_OR = "OPERATOR_OR"
OPERATOR_AND = "OPERATOR_AND"
OPERATOR_NOT = ["!","not"]

COND_OPERATOR_SYMBOLS = {
  OPERATOR_EQUAL : ["=","=="],
  OPERATOR_GE : [">="],
  OPERATOR_GT : [">"],
  OPERATOR_LE : ["<="],
  OPERATOR_LT : ["<"],
  OPERATOR_STARTSWITH : ["startswith"],
  OPERATOR_CONTAINS : ["contains","like"],
}

JOIN_OPERATOR_SYMBOLS = {
  OPERATOR_AND : ["and"],
  OPERATOR_OR : ["or"],
}

# Create a dict of all symbols
OPERATOR_SYMBOLS = {}
for sym in COND_OPERATOR_SYMBOLS :
  OPERATOR_SYMBOLS[sym] = COND_OPERATOR_SYMBOLS[sym]
for sym in JOIN_OPERATOR_SYMBOLS :
  OPERATOR_SYMBOLS[sym] = JOIN_OPERATOR_SYMBOLS[sym]

SORT_ASCEND = "SORT_ASCEND"
SORT_DESCEND = "SORT_DESCEND"

CONDITION_TOKEN = "__cond__"
QUOTED_STRING_TOKEN = "__quoted_string__"
LEFT_BRACKET = "("
RIGHT_BRACKET = ")"


EXAMPLE_QUERIES = """
show me people where name == fred  ==> simple query of one type with one condition.
show me animals people where name = frank and date of birth > 1/2/2001 ==> simple query with two types and anded conditions
people fred - shorthand for 'show me people where body contains fred'
SPECIFY FIELDS
RELATION QUERIES
show me person where friend.name == john
show me person with fields name, friend.name <== Infer relational query on rel field friend.
SORTING
show me blah blah sort up date, sort down name
OR in queries
Note, python will group ands
show me people where name contains jane or name contains john and dob > 31/5/1980
show me people where (name contains jane or name contains john) and dob > 31/5/1980
"""


class QueryExecutor :
  """Executes a query to produce results from the wikidbase."""
  
  def __init__(self) :
    debugOutput("Creating")
  
  def executeQuery(self, query) :
    debugOutput("Executing query %s" % query)

    # TODO: Check if results have ben cached for this query.
    # TODO: idea.  Can we cache clauses of queries - that would be powerful.

    # Get the context pages
    wikidpages = []
    if query.contexts :
      # Get pages for each specified context.
      if wikidbase.core.context.normaliseTerm(ANYTHING) in query.contexts :
        wikidpages = wikidbase.core.pagestore.getAllPages()
      else :
        for context in query.contexts :
          wikidpages += wikidbase.core.pagestore.getPagesInContext(context != wikidbase.core.context.normaliseTerm(PAGES) and context or None)
    else :
      wikidpages = []

    debugOutput("No context pages %s" % len(wikidpages))
    
    # Get results for each condition
    if query.conditionalClause :
      conditions = query.conditionalClause.getConditions()
    else :
      conditions = []

    debugOutput("conditions: %s" % str(conditions))
    
    # Evaluate each condition of the nested query clauses.
    for condition in conditions :
      
      debugOutput("Evaluating condition: %s" % condition)
      fieldName = condition.field.getBasePart()
      relationalPath = condition.field.getPrefixPart()
      debugOutput("relationalPath %s fieldName %s" % (relationalPath, fieldName))

      debugOutput("Evaluating condition '%s'" % condition)
      conditionResults = self._evaluateCondition(wikidpages, relationalPath, fieldName, condition.operator, condition.value, negate = condition.negate)
      querySet = self._generateQueryResultsFromConditionalResults(conditionResults, relationalPath=relationalPath)
      debugOutput("Number of matching pages for condition '%s': %s" % (condition, len(querySet)))

      # Store the conditional results in the condition that caused them.
      condition.querySet = querySet
    
    # Recursively join results from each condition
    if query.conditionalClause :
      results = query.conditionalClause.getResults(self._joinQuerySets)
    else :
      results = QueryResults([wikidpage.id for wikidpage in wikidpages])

    # update results fields
    results.updateHeadings(clear=True)

    debugOutput("Length of query results %s" % len(results))
   
    # Store the query object in the results for conveniece.
    results.setQuery(query)
    
    # Return results
    return results

  
  def _evaluateCondition(self, wikidpages, relationalPath, fieldName, operator, value, negate) :
    """
    Evaluates a condition of a query, recursing through wikidpage links as neccessary.
    Here we may either be searching for a condition on local fields (e.g. name, date of birth).
    or we may be doing so on a related pages fields (e.g. pet.vet.address).
    """
    debugOutput("wikidpages %s relationalPath %s fieldName %s operator %s value %s" % (wikidpages, relationalPath, fieldName, operator, value))

    results = {}

    if relationalPath :
     
      # Since there is a relational path, we must explore a wikidpages relation.

      # Pop off the first link in the path and normalise it's name; this is where we must start our journey.
      linkField = relationalPath[0]
      nLinkField = wikidbase.core.normaliseTerm(linkField)
      
      # For each of the wikidpages, get their outbound links for this field.
      for wikidpage in wikidpages :
        linkedWikidpages = []
        links = wikidbase.core.pagestore.getLinks(wikidpage.id)
        try :
          outboundLinks = links[nLinkField]
        except :
          continue

        # Build up a list of candidate wikidpages that are linked at this level of the relational path.
        for outboundLink in outboundLinks :
          # Load the wikidpage with the linked id from the wikidbase.
          linkedWikidpage = wikidbase.core.pagestore.getWikidpage(outboundLink[0])
          if linkedWikidpage :
            linkedWikidpages.append(linkedWikidpage)
      
        debugOutput("Candidate wikidpages of %s linked by %s are %s" % (repr(wikidpage), nLinkField, linkedWikidpages))
        # Recurse to the next level of the relational path.
        result = self._evaluateCondition(linkedWikidpages, relationalPath[1:], fieldName, operator, value, negate)
        
        # Store results for this wikidpage.
        if result :
          results[wikidpage] = result

    else :
     
      # For each candidate wikidpage, check the condition on one or more fields.
      for wikidpage in wikidpages :

        if fieldName == ANY_FIELD.lower() :
          # For the special field 'anyfield' consider all fields
          fields = wikidpage.getFields().getList()
        else :
          try :
            fields = [wikidpage.getFields().getField(fieldName)]
          except :
            fields = []
        
        # Check each field and break if we get a positive condition.
        for field in fields :
          fieldValue = field and field.data or None
          
          # Pass the actual value, the field value and the operator to the condition function.
          conditionStatus = self.testCondition(fieldValue, operator, value)
          
          # Negate the condition if specifed in the query.
          if negate : conditionStatus = not conditionStatus

          if conditionStatus :
            # Add the wikidpage to the results.
            results[wikidpage] = None
            debugOutput("field %s of %s MATCHES" % (field, wikidpage.name))
            break;
          else :  
            debugOutput("field %s of %s DOES NOT match %s '%s'" % (field, wikidpage.name, operator, value))
          

    debugOutput("Results = %s" % results)
    return results


  def testCondition(self, value1, operator, value2, ignoreCase=True) :
    """
    Tests the condition of a query using data type recognition.
    """
    # TODO: How to handle a list value.
    # XXX: if values of x are [a, b, c], x = a -> x contains a
    if ignoreCase : 
      value1 = type(value1) == str and value1.lower() or value1
      value2 = type(value2) == str and value2.lower() or value2

    if True:
      value1 = wikidbase.core.datatype.convert(value1,wikidbase.core.datatype.TO_PYTHON) 
      value2 = wikidbase.core.datatype.convert(value2,wikidbase.core.datatype.TO_PYTHON) 
    
      # Handle date and datetime comparisons.
      value1 = type(value1) == datetime.datetime and type(value2) == datetime.date and value1.date() or value1
      value2 = type(value2) == datetime.datetime and type(value1) == datetime.date and value1.date() or value2

      debugOutput("%s<%s> %s %s<%s>" % (value1, type(value1), operator, value2, type(value2)))
    try :

      if operator == OPERATOR_STARTSWITH :
        return value1.startswith(value2)
      elif operator == OPERATOR_CONTAINS :
        return value2 in value1
      elif operator == OPERATOR_EQUAL :
        return value2 == value1
      elif operator == OPERATOR_GT :
        return value1 > value2
      elif operator == OPERATOR_GE :
        return value1 >= value2
      elif operator == OPERATOR_LT :
        return value1 < value2
      elif operator == OPERATOR_LE :
        return value1 <= value2
    except Exception:
      pass

    return False


  def _generateQueryResultsFromConditionalResults(self, wikidpageDict, path=None, queryResults=None, relationalPath=None) :
    """Gosh, what a long name for a function! This flattens the dict from condtion results into a query results object."""
    
    debugOutput("Generating query set from %s." % wikidpageDict)
    path = path or []
    if queryResults == None :
      queryResults = QueryResults()

    # Recursively flatten the results.
    for wikidpage in wikidpageDict :
      nextWikidpageDict = wikidpageDict[wikidpage]
      if nextWikidpageDict :
        self._generateQueryResultsFromConditionalResults(nextWikidpageDict, path = path + [wikidpage], queryResults=queryResults, relationalPath=relationalPath)
      else :
        debugOutput("Path = %s" % (path + [wikidpage]))
        queryResults.addItem(QueryResultsItem(path + [wikidpage], linkFields = relationalPath))

    return queryResults


  def _joinQuerySets(self, qs1, operator, qs2) :
    """Joins the results of two conditions together with AND or OR."""
    debugOutput("Joining qs1 %s and qs2 %s with operator %s" % (len(qs1.queryResults), len(qs2.queryResults), operator))
    #XXX: queryResults = QueryResults(displayFields = self.displayFields)

    if operator == OPERATOR_AND :

      queryResults = QueryResults()
      for queryItem1 in qs1.queryResults :
        for queryItem2 in qs2.queryResults :
          debugOutput("Comparing %s with %s" % (queryItem1.getPrimaryWikidpage().id, queryItem2.getPrimaryWikidpage().id))
          if queryItem1.equivalientTo(queryItem2) :
            debugOutput("Merging %s" % queryItem1.getPrimaryWikidpage().name)
            
            # Must copy, since change during iteration can affect join results.
            queryItem1Copy = QueryResultsItem(sourceItem=queryItem1)
            queryItem1Copy.merge(queryItem2)
            queryResults.addItem(queryItem1Copy)

    elif operator == OPERATOR_OR :

      queryResults = qs1
      # If item is in both, we want to merge the data
      # else, we just want to add it.
      removeList = []
      for queryItem1 in queryResults.queryResults :
        for queryItem2 in qs2.queryResults :
          #if queryItem1.getPrimaryWikidpage() == queryItem2.getPrimaryWikidpage() :
          if queryItem1.equivalientTo(queryItem2) :
            queryItem1.merge(queryItem2)
            removeList.append(queryItem2)

      # Now remove merged items
      for queryItem in removeList :
        qs2.queryResults.remove(queryItem)
        
      # Now add the remaining items in qs2 to results
      for queryItem in qs2.queryResults :
        queryResults.addItem(queryItem)

    debugOutput("join results length: %s" % len(queryResults))

    return queryResults


 

#
# QueryResultsItem
#

class QueryResultsItem:
  """This is a row/tuple in a queryset and, through relational queries, can be a combination of server wikidpages.
     There is always at least one primary wikidpage and there may be others and information about their relationship to
     to the primary page (e.g. a query of people's pet's vets, might result in a primary page of John will relational
     pages for the the pet and vet.
  """ 
  
  def __init__(self, wikidpages=None, linkFields=None, sourceItem=None):
    """
    Build a query set item based upon a list of wikidpages and a description of how they linked.
    If sourceItem is give, a copy is created of the item.
    """
    debugOutput("Creating")

    if wikidpages :
      # BUild from pages and links.
      self.buildFields(wikidpages, linkFields)
    elif sourceItem :
      # Build a copy
      self.wikidpages = sourceItem.wikidpages
      self.fields = sourceItem.fields.copy()
    
    # Store the primary wikidpage.
    self.primaryWikidpage = self.wikidpages[0]


   
  def buildFields(self, wikidpages, linkFields) :
    
    # Ensure we have a list.
    linkFields = linkFields or []

    # Store a link to the primary wikidpage.
    self.wikidpages = wikidpages or []

    # Build up a list of fields, index by their relation path e.g. pet.vet.name -> (field, wikidpage, fieldHeading)
    self.fields = wikidbase.thirdparty.odict.OrderedDict()
    for i in range(0,len(wikidpages)) :
      fieldBasePath = linkFields[0:i]
      wikidpage = wikidpages[i]
      debugOutput("fieldBasePath %s" % fieldBasePath)
      fields = wikidpage.getFields().getDict() 
      for nField in fields :
        field = fields[nField]
        fieldHeading = wikidbase.core.context.TermPath(fieldBasePath + [field.name])
        debugOutput("fieldHeading %s" % fieldHeading)
        self.fields[fieldHeading.getNormalisedForm()] = (field, wikidpage, fieldHeading)

  
  def getFields(self) :
    """Returns the fields of this query item."""
    return self.fields

  def getData(self, heading) :
    """Returns data from a specified field in this query set item."""

    debugOutput("get '%s'" % heading)

    # Try to return the field data and the wikidpage it belongs to.
    try :
      return self.fields[heading]
    except :
      return None, None, None

  def equivalientTo(self, queryResultsItem) :
    
    # Do they have the same primary wikidpage?
    if self.primaryWikidpage != queryResultsItem.getPrimaryWikidpage() :
      return False

    # Check all existing field data matches.
    for nField in self.fields :
      if nField in queryResultsItem.fields and self.fields[nField][0].data != queryResultsItem.fields[nField][0].data :
        return False

    return True

  def getPrimaryWikidpage(self):
    """Returns the primary wikidpage of this query set item."""
    return self.primaryWikidpage or None
 

  def isSingleWikidpage(self) :
    """Returns true if this query set item consits only of a primary page."""
    return len(self.wikidpages) == 1


  def merge(self, queryResultsItem) :
    """Merges another query set item into this one.  This is useful to preserve data when query sets are joined together."""
    debugOutput("merging %s and %s" % (self, queryResultsItem))
    
    for field in queryResultsItem.fields :
      if field not in self.fields :
        debugOutput("Merging field into self.fields: %s" % field)
        self.fields[field] = queryResultsItem.fields[field]

    #debugOutput(self.fields.keys())

  def copy(self) :
    aCopy = self.__class__()
    return aCopy
    

  def __str__(self) :
    output = ""
    for nField in self.fields :
      output += nField + "-"
    return output
  
  def getSummary(self) :
    """Returns a html summary of this query set item, eg. for when a user hovers this item in a calendar view."""
    # TODO: Needs fixing.
    summary = ""
    for linkField in self.items :
      for field in self.items[linkField].getFields().getList() :
        if field.type in wikidbase.core.pagecontent.WP_DATA_FIELDS :
          summary += "<b>%s</b>: %s<br/>" % (field.name, field.data)
    debugOutput(summary)
    return summary
   

  def getSignificantFields(self) :
    """
    Tries to get significant fields from the query set item to display in condensed form.
    TODO: This is very application specific, so a user should be able to pick fields that appear in a summary of the item.
    """
    #TODO: Needs fixing.
    # TODO: 'name' should be configurable.
    sigFields = ""
    for linkField in self.items :
      for field in self.items[linkField].getFields().getList() :
        if field.type in wikidbase.core.pagecontent.WP_DATA_FIELDS and "name" in field.name.lower() :
          sigFields += "%s, " % (field.data)
    sigFields = sigFields.strip(", ")
   
    if sigFields :
      return sigFields

    # TODO: Pick of the first few single line fields
    sigFields = self.items[PRIMARY_WIKIDPAGE].name
    
    debugOutput(sigFields)
    return sigFields
    

#
# QueryResults
#

class QueryResults:
  """This represents what you get when you run a query.  To outsiders, this resembles a table with headings and data items."""
  
  def __init__(self, wikidpageIDs=None):
    """Create new QueryResults.""" 
    debugOutput("Creating")
    
    self.queryResults = [] # This holds query result items.
    
    # We may want to associate query results with the query that generated them.
    self.query = None

    # If some wikidpage IDs have been given, add them to the query set for convenience.
    if wikidpageIDs :
      self._buildResultsFromIDs(wikidpageIDs)
      self.updateHeadings(clear=True)


  def setQuery(self, query) :
    """Allow the original query to be stored for convenience."""
    self.query = query 

  def getQuery(self) :
    return self.query

  def getCommonData(self) :
    """Returns any common field or relationa data of this query set."""
    pass

  def updateHeadings(self, clear=False) :
    """Updates the results headings from its results items' headings"""

    if clear :
      self.primaryContexts = {} # This holds the primary context(s) of this query results (e.g. are they all people, animals?).
      # This records all of the fields in the query results (e.g. fieldsInfo['pets.vets']['name'] as QueryResultsFieldInfo).
      self.fieldsInfo = wikidbase.thirdparty.odict.OrderedDict()
    
    for resultsItem in self.queryResults :
      # Process each field of the item, storing information about it's headings, etc.
      queryItemFields = resultsItem.getFields()
      for nFieldHeading in queryItemFields :
        
        # Get information about the field: field, wikidbase owning the field, and the field heading.
        field, wikidpage, fieldHeading = queryItemFields[nFieldHeading]
        
        # Get or create the field info object for this field.
        if nFieldHeading not in self.fieldsInfo :
          self.fieldsInfo[nFieldHeading] = QueryResultsFieldInfo(fieldHeading, [], 0)
        fieldInfo = self.fieldsInfo[nFieldHeading]
        
        # Record some information about the field here: name, a count of how many exist in the results items, and the datatype(s) of that field.
        fieldInfo.count += 1
        dataType = type(wikidbase.core.datatype.convert(field.data, wikidbase.core.datatype.TO_PYTHON))
        if dataType not in fieldInfo.dataTypes :
          fieldInfo.dataTypes.append(dataType)
          debugOutput("Adding wikidbase.core.datatype %s" % dataType)

      # Update the primary contexts of these query results, so we can identify if these are all people, or projects, etc.
      primaryWikidpage = resultsItem.getPrimaryWikidpage()
      primaryContext = primaryWikidpage and primaryWikidpage.context or None
      if primaryContext :
        nPrimaryContext = wikidbase.core.normaliseTerm(primaryContext)
        if nPrimaryContext not in self.primaryContexts :
          self.primaryContexts[nPrimaryContext] = primaryContext
     

  def addItem(self, queryResultsItem) :
    """Adds a new item to the query results, upating field info."""
    
    # Add the item.
    self.queryResults.append(queryResultsItem)
   
   
  
  def getPrimaryContexts(self) :
    """Return the primary contexts of these query results."""
    return self.primaryContexts


  def getFieldTypes(self, heading) :
    """Return the data types of the specified field.  Note, since this is semi-structured, there may be more than one type for a field."""
    fieldTypes = self.fieldsInfo[heading].dataTypes
    debugOutput("field types %s %s" % (heading, fieldTypes))
    return fieldTypes

  def getFieldsInfo(self) :
    """
    Returns a list of headings of fields in these results, sorted by most-occurant first,
    and catogorised in a dict by thier relationship to the primary page.
    Again, wikidpages need not have the same fields within a particular context.
    """
    
    #TODO : This most-common header sorting should be moved to the table view.
    return self.fieldsInfo
   

    # TODO: Common data heading sorting can be useful, so perhaps revisit this.
    headings = wikidbase.thirdparty.odict.OrderedDict()

    debugOutput("fields: %s" % self.fieldsInfo)

    for linkField in self.fieldsInfo :
      sortedHeadings = [(self.fieldsInfo[linkField][attributeName].name, self.fieldsInfo[linkField][attributeName].count) for attributeName in self.fieldsInfo[linkField]]
      sortedHeadings.sort(key=lambda x:x[1], reverse=True)
      sortedHeadings = map(lambda x:x[0], sortedHeadings)
      debugOutput("sortedHeadings: %s" % sortedHeadings)
      headings[linkField] = sortedHeadings

    debugOutput("headings: %s" % headings)
   
    return headings


  def getPrimaryWikidpages(self) :
    """Gets a list of all of the prmary wikidpages in the restults (i.e. the prmary page of each query results item."""
    wikidpages = []
    for item in self.queryResults :
      wikidpage = item.getPrimaryWikidpage()
      if wikidpage not in wikidpages :
        wikidpages.append(wikidpage)
    return wikidpages
  

  def _buildResultsFromIDs(self, wikidpageIDs) :
    """Adds query results items to the results from pages with the specifed ids, for convenience."""
    for id in wikidpageIDs :
      wikidpage = wikidbase.core.pagestore.getWikidpage(id)
      if not wikidpage :
        continue
      self.addItem(QueryResultsItem([wikidpage]))
  
  
  def __len__(self) :
    """The length of these results."""
    return len(self.queryResults)


  def sort(self, nFieldHeading, sortDirection) :
    """This sorts the items based on a field in a specified direction."""
    debugOutput("Sorting on field '%s' %s" % (nFieldHeading, sortDirection))
 
    # TODO: Think about the best way to do sorting.
    # TODO: Update this

    results = self.queryResults[:]

    def sortKeyFunction(item) :
      """Given a nFieldHeading item, this returns the thing we want to sort it on: the data."""
      try :
        value = wikidbase.core.datatype.convert(item.getData(nFieldHeading)[0].data, wikidbase.core.datatype.TO_PYTHON)
      except :
        value = None
      return value

    # Run the sort.
    results.sort(key=sortKeyFunction, cmp=wikidbase.core.datatype.cleverCmp, reverse = sortDirection == SORT_DESCEND)
    
    # XXX: This is some nasty stuff.
    # TODO: Find a neater way to do this.
    # The following code makes sure blanks are always at the bottom of list, otherwise they go anywhere.
    blanks = []
    for i in range(0, len(results)) :
      item = results[i]
      try :
        value = wikidbase.core.datatype.convert(item.getData(nFieldHeading)[0].data, wikidbase.core.datatype.TO_PYTHON)
      except :
        value = None
      if value in ["",None]:
        blanks.append(i)

    tempSet = results
    results = []
    
    for i in range(0, len(tempSet)) :
      if i not in blanks :
        results.append(tempSet[i])
    
    for i in range(0, len(tempSet)) :
      if i in blanks :
        results.append(tempSet[i])

    
    return results



class IQueryBuilder :
  """(Interface) Builds query objects from some representation of a query."""
  def buildQuery(self, queryString) :
    """Takes a query string (i.e. a command) and returns a query object."""
    raise Exception("Not implemented")


class SimpleQueryBuilder(IQueryBuilder) :
  """
  This is a fluffy query string parser, that allows the user to write things fairly naturally like this:
    show me all of my people who have first name = nick and pet.type = dog showing fields title, first name, and pet.name
  and it returns the following important information:

    Context: Person (derived from the word 'people')
    Conditions:
      Person."First Name" == nick
      Person.Pets.Type == dog
    Display Fields:
      Person.Title, Person."First Name", Person.Pets.Name

    TODO: also should allow sorting to be declared.
  """

  def __init__(self) :
    debugOutput("Creating")

  def buildQuery(self, queryString) :
    """parses the given query string into a context, conditions and display fields."""
  
    # XXX

    debugOutput("Parsing query '%s'" % queryString)

    # Reject empty query.
    if not queryString :
      return None

   
    # Normalise quoted spaces and terms in the query string.
    queryString, self.quotedStrings = self._subQuotedStrings(queryString)
    queryString = self._normaliseQueryString(queryString)
    
    # =======================================================================
    # Parse the display fields
    # =======================================================================
    queryFields, queryResidue = self._parseQueryFields(queryString)

    # =======================================================================
    # Parse the conditional clause(s)
    # =======================================================================

    # Identify all conditions and substitute them.
    # TODO: pass fields to this.
    queryResidue, conditionalClause = self.parseConditionalClauses(queryResidue)

    # TODO: Need a good think about this.
    # If there is a field with no condition, add something like this pet.id > 0
    # for each query field with prefxi
      # get prefix
      # for each condition field with prefix
        # if prefixs match 
          # addPrefix condition
          # break 
          #
    
    # =======================================================================
    # Parse the contexts from the query
    # =======================================================================
    queryResidue, contexts = self.parseContexts(queryResidue)
  

    debugOutput("contexts = %s, queryFields = %s" % (str(contexts), str(queryFields)))

    query = Query(contexts, conditionalClause, queryFields)
    return query


  def _parseQueryFields(self, queryString) :
    
    queryFields = []
    #queryFields.append(QueryField(wikidbase.core.context.TermPath("name")))

    # Look for explicit display fields.
    queryStringParts = queryString.split("fields")
    queryString = queryStringParts[0]
    try :
      displayFieldsString = queryStringParts[1]
    except :
      displayFieldsString = None
    
    # Do some more cleverness to get the field names.
    queryFields = self.parseQueryFields(displayFieldsString)
      
      
    debugOutput("queryFields: %s" % queryFields)
    
    # We will wittle down the query, leaving only the redunant residue that is not important for the query.
    queryResidue = queryString

    return queryFields, queryResidue


  def parseConditionalClauses(self, queryResidue) :

    #
    # Build up some regular expressions for parsing the query string.
    #
    
    operatorRE = []
    for operator in COND_OPERATOR_SYMBOLS :
      operatorRE += COND_OPERATOR_SYMBOLS[operator]
    operatorRE = "(?P<operator>%s)" % "|".join(operatorRE)
    debugOutput("operatorRE %s" % operatorRE)

    notRE = []
    for symbol in OPERATOR_NOT :
      notRE.append(symbol)
    notRE = "(?P<not>%s)*" % "|".join(notRE)
    debugOutput("notRE %s" % notRE)

    variableRE = r"""(?P<variable>[\w\.-]+)""" 
    valueRE = r"""(?P<value>[\w\.\d/-]+)""" 

    #
    # Parse the conditions and replace them with tokens in the query string (e.g. something.something [not]< value)
    #

    conditionalRE =  r"""(?P<all>%s\s*%s\s*%s\s*%s)""" % (variableRE, notRE, operatorRE, valueRE)
    debugOutput("conditionalRE %s" % conditionalRE)
    conditions = {}

    def replaceCondition(match) :
      # Replaces a parsed condition with a token.
      debugOutput("match: %s" % match.groupdict())
      
      operator = None

      # Determine the operator of this condition (e.g. <, ==, contains, etc.)
      for cOperator in COND_OPERATOR_SYMBOLS :
        if match.groupdict()["operator"] in COND_OPERATOR_SYMBOLS[cOperator] :
          operator = cOperator
          break
     
      #XXX: variable = self._replaceWithQuotedString(match.groupdict()["variable"])
      # Parse the name of the variable and its relational parts.
      variable = match.groupdict()["variable"]
      
      # Create a token and store this condition in a dict.
      token = "%s%s" % (CONDITION_TOKEN, len(conditions)) 
      conditions[token] = Condition(wikidbase.core.context.TermPath(variable), operator, self._replaceWithQuotedString(match.groupdict()["value"]), negate=match.groupdict()["not"] and True or False)
      return token
    
    # Parse and replace all conditions in the query string.
    queryResidue = re.sub(conditionalRE, replaceCondition, queryResidue)

    debugOutput("queryResidue %s" % queryResidue)

    # Return if no conditions were parsed.
    if not conditions :
      return queryResidue, None

    

    #
    # Now parse parenthesis into a conditional hierarchy
    #

    # Isolate the part of the query string that contains all of the conditions.
    conditionString, queryResidue = self._findConditionString(queryResidue, conditions)

    # Parse the nested conditions. 
    nestedConditions = self._parseNestedConditions(conditionString)

    conditionalClause = self._buildConditionalClause(nestedConditions, conditions)
    debugOutput("conditionalClause: %s" % conditionalClause)

    return queryResidue, conditionalClause


  def _buildConditionalClause(self, nestedConditions, conditions) :
    debugOutput("Building clause")
    clauseItems = []
    for item in nestedConditions :
      debugOutput("item = %s type %s" % (item, type(item)))
      if type(item) in [list, pyparsing.ParseResults] :
        clauseItems.append(self._buildConditionalClause(item, conditions))
      elif item in conditions :
        clauseItems.append(conditions[item])
      elif getOperatorSymbol(item) in [OPERATOR_OR, OPERATOR_AND] :
        clauseItems.append(getOperatorSymbol(item))

    debugOutput("clauseItems %s" % clauseItems)
    return ConditionalClause(clauseItems)

  def _findConditionString(self, queryString, conditions) :
    conditionTokens = conditions.keys()
    conditionTokens.sort()
    firstToken = conditionTokens[0]
    lastToken = conditionTokens[-1]
    firstBracket = queryString.find(LEFT_BRACKET)
    lastBracket = queryString.rfind(RIGHT_BRACKET)
    startIndex = queryString.find(firstToken)
    endIndex = queryString.find(lastToken)+len(lastToken)
    if firstBracket >= 0 and firstBracket < startIndex :
      startIndex = firstBracket
    if lastBracket >= 0 and lastBracket > endIndex :
      endIndex = lastBracket
    conditionString = queryString[startIndex: endIndex+1]
    #raise Exception("%s %s %s" % (queryString, startIndex, endIndex))
    
    # Remove the conditions from the query residue
    queryResidue = queryString.replace(conditionString, "")
    return conditionString, queryResidue



  def _parseNestedConditions(self, conditionString) :
    """Tries to parse nested conditions and falls back on flat parsing."""
    debugOutput(conditionString)
    conditionString = conditionString.strip()
    if not conditionString.startswith(LEFT_BRACKET) or not conditionString.endswith(RIGHT_BRACKET) :
      conditionString = "%s%s%s" % (LEFT_BRACKET, conditionString, RIGHT_BRACKET)

    try :
      import pyparsing
      parsedExpression = pyparsing.nestedExpr().parseString(conditionString)[0]
    except :
      parsedExpression = conditionString.replace(LEFT_BRACKET,"").replace(RIGHT_BRACKET, "").split()
    
    return parsedExpression

  def parseContexts(self, queryResidue) :

    #
    # Do some cleverness to identify contexts of the query (e.g. people, 'special projects', animals, etc.)
    #
   
    contexts = []

    # Get the contexts
    allContexts = wikidbase.core.context.getContexts()
    
    debugOutput("queryResidue '%s'" % queryResidue)
    
    # Search the residue for normalised contexts and remove identifed ones from the residue.
    for residueTerm in queryResidue.split() :
      nResidueTerm = wikidbase.core.normaliseTerm(residueTerm)
      if nResidueTerm in allContexts.keys() + [wikidbase.core.context.normaliseTerm(ANYTHING), wikidbase.core.context.normaliseTerm(PAGES)] :
        # TODO: Add this to contexts.
        contexts.append(nResidueTerm)
        queryResidue = queryResidue.replace(residueTerm,"")

    debugOutput("queryResidue '%s'" % queryResidue)

    return queryResidue, contexts
  
  def oldStuff() :

    # Do some more cleverness to get the field names.
    if displayFieldsString :
      
      # Folk might use commas to delimit fields, but parsing is cleverer than that; anyhow, they must go.
      displayFieldsString = displayFieldsString.replace(","," ")
      
      # Add normalised terms to our list of display fields.
      for rawDisplayFieldTerm in displayFieldsString.split() :
        # TODO: add this as a term path to the fields part of query
        displayFieldTerm = self._replaceWithQuotedString(rawDisplayFieldTerm)
        nDisplayFieldTerm = wikidbase.core.context.normaliseTerm(displayFieldTerm)
        displayFields.append(nDisplayFieldTerm)

    # TODO: Put query together

    debugOutput("contexts %s, conditions %s, displayFields %s" % (contexts, conditions, displayFields))
  
    # Return the query elements.
    return contexts, conditions, displayFields
 

  def parseQueryFields(self, fieldsString) :
    
    queryFields = []
   
    if not fieldsString :
      return queryFields

    # Folk might use commas to delimit fields, but parsing is cleverer than that; anyhow, they must go.
    fieldsString = fieldsString.replace(","," ")
    
    # Add normalised terms to our list of display fields.
    for rawDisplayFieldTerm in fieldsString.split() :
      displayFieldTerm = self._replaceWithQuotedString(rawDisplayFieldTerm)
      debugOutput("Adding field '%s'" % displayFieldTerm)
      queryFields.append(QueryField(wikidbase.core.context.TermPath(displayFieldTerm)))

    return queryFields

  
  def _subQuotedStrings(self, s) :
    """Replaces quotes and their contained spaces with a space-less string, handy for processing."""
    #TODO: Replace quoted strings with tokens.
    quotedStrings = {}
    for quoteChar in ["\"","'"] :
      def sub(match) :
        token = QUOTED_STRING_TOKEN + str(len(quotedStrings))
        quotedStrings[token] = match.groups()[0].strip(quoteChar)
        return token
      s = re.sub("(%s[^%s]+?%s)" % (quoteChar, quoteChar, quoteChar), sub, s)
    
    return s, quotedStrings


  def _replaceWithQuotedString(self, s) :
    """Replaces substituded space-less strings with spaces."""
    if s in self.quotedStrings :
      return self.quotedStrings[s]
    else :
      return s


  def _normaliseQueryString(self, queryString) :
    """Normalises context and field term variations to enable fuzzyness in parsing."""
    
    # Lets start by lowering the case.
    nQueryString = queryString.lower()

    # Build up a list of term variations for contexts and field names.
    termVariations = wikidbase.core.context.getAllTermVariations()
    
    # For each term variation we find in the string, replace it with its normalised form.
    for termVariation in termVariations :
      nQueryString = nQueryString.replace(termVariation.lower(), wikidbase.core.context.normaliseTerm(termVariation))
    
    debugOutput("Normalised '%s' to '%s'" % (queryString, nQueryString))

    return nQueryString




# TODO: move cache to actual query object hash.
@wikidbase.core.cache.memoize
def runQuery(queryString) :
  """
  Entry to the query API, which runs the specified query and returns a query set.
  """

  debugOutput("query = '%s'" % queryString)
  
  # Execture the query
  queryExecutor = QueryExecutor()
  wikidbase.core.performance.startTimer("runQuery")
  results = queryExecutor.executeQuery(SimpleQueryBuilder().buildQuery(queryString))
  wikidbase.core.performance.stopTimer("runQuery")
  return results



def pageLookup(searchString) :
  """
  Page lookup functions used for AJAX, etc. This takes a search string and searches for keywords and contexts,
  returning wikidpages of matches and wikidpages representative of contexts that match.
  """
  contextPages = []
  wikidpages = []
  
  searchString = searchString.lower()
  debugOutput("searchString = '%s'." % searchString)
  
  # Check from contexts to create.
  wikidbaseContexts = wikidbase.core.context.getContexts()
  for nContext in wikidbaseContexts :
    for contextVariation in wikidbaseContexts[nContext].contextNameVariations.getVariations() :
      if contextVariation.lower().startswith(searchString) :
        contextPages.append(contextVariation)

  
  # Look for wikidpages with matching keywords.
  queryResults = runQuery("""%s where %s contains "%s" """ % (ANYTHING, ANY_FIELD, searchString))
 
  
  if queryResults :
    wikidpages = queryResults.getPrimaryWikidpages()
  else :
    wikidpages = []

  return contextPages, wikidpages
 


#
# Utility classes and functions
#


def getOperatorSymbol(text) :
  """Reverse mapping of symbol string to the symbol."""
  for sym in OPERATOR_SYMBOLS :
    if text in OPERATOR_SYMBOLS[sym] :
      return sym
  return None


class Query:
  """Represents a query: page contexts, conditionalClause, and fields (display and sort priorities)."""
  
  def __init__(self, contexts, conditionalClause, queryFields=None) :
    self.contexts, self.conditionalClause, self.queryFields = contexts, conditionalClause, queryFields
    debugOutput("Creating query")
  
  def __str__(self) :
    fieldsString = ""
    for field in self.queryFields :
      fieldsString += " " + str(field)
    return "contexts '%s' conditions '%s'%s" % (str(self.contexts), self.conditionalClause, fieldsString)


class QueryField:
  """Describes a field of a query."""
  def __init__(self, name, sortOrder=None, sortDescend=False) :
    self.name, self.sortOrder, self.sortDescend = name, sortOrder, sortDescend
  def __str__(self) :
    return "QueryField: %s sort %s (order %s)" % (self.name, self.sortDescend and "descending" or "ascending", self.sortOrder)

class Condition :
  """Represents a single condition of a query (e.g. pet.name == "fido")."""
  def __init__(self, field, operator, value, negate=False) :
    self.field, self.operator, self.value, self.negate = field, operator, value, negate
    self.querySet = None
  def getFieldParts(self) :
    return self.field.split(".")
  def getResults(self, join=None) :
    return self.querySet
  def __str__(self) :
    return "%s %s %s" % (self.field, self.operator, self.value)


class ConditionalClause:
  """Represents a join of conditions and condition clauses (i.e. hierarchy of conditions) in a query)."""
  
  def __init__(self, items) :
    """Takes an array of conditions and operators (e.g. [a, and, b, or, c, add f])"""

    debugOutput("Creating wih items %s" % str(items))
    
    self.operands = []
    self.operators = []
    
    lastItem = None
    for item in items :
      if item in [OPERATOR_AND, OPERATOR_OR] :
        self.operators.append(item)
      else :
        # If no join is specified, default to AND
        if lastItem and lastItem not in [OPERATOR_OR, OPERATOR_AND] :
          self.operators.append(OPERATOR_AND)
        self.operands.append(item)
      lastItem = item
  
  
  def getConditions(self) :
    """Returns a flat list of all the conditions in this conditional clause through recursion."""
    conditions = []
    for operand in self.operands :
      if not operand :
        continue
      if operand.__class__ == self.__class__ :
        conditions += operand.getConditions()
      else :
        conditions += [operand]
    return conditions

  def getResults(self, join) :
    """Using the specified join function, returns joined results of this conditional clause; works recursively."""
   
    # Join all of the clause results using their operators.
    results = self.operands[0].getResults(join)
    for operand in self.operands[1:] :
      opIndex = self.operands.index(operand)
      operator = self.operators[opIndex-1]
      results = join(results, operator, operand.getResults(join))

    return results

  def __str__(self) :
    output = ""
    for i in range(0, len(self.operands)) :
      output += "%s " % self.operands[i]
      try :
        output += "%s " % self.operators[i]
      except :
        pass
      
    return "(%s)" % (output)


class QueryResultsFieldInfo:
  def __init__(self, fieldHeading, dataTypes, count) :
    self.fieldHeading, self.dataTypes, self.count = fieldHeading, dataTypes, count


























class TestQueryBuilder(IQueryBuilder) :
  def buildQuery(self, queryString) :
    
    # Create the query.
    condition1 = Condition("name", OPERATOR_EQUAL, "nick")
    condition2 = Condition("dob", OPERATOR_GT, "31/5/80")
    condition3 = Condition("pet.name", OPERATOR_EQUAL, "fido")
    #conditionalClause1 = ConditionalClause(condition1, OPERATOR_OR, condition2)
    #conditionalClause2 = ConditionalClause(conditionalClause1, OPERATOR_AND, condition3)
    
    #conditionalClause2 = ConditionalClause(Condition("name" , OPERATOR_EQUAL, "nick"), OPERATOR_OR, Condition("name", OPERATOR_EQUAL, "fred"))
    #conditionalClause2 = ConditionalClause(Condition("name" , OPERATOR_EQUAL, "fred"))
    #conditionalClause2 = ConditionalClause(Condition("pet.name" , OPERATOR_EQUAL, "Ginger"))
    conditionalClause2 = ConditionalClause(Condition(wikidbase.core.context.TermPath("pet.name") , OPERATOR_EQUAL, "Ginger"), OPERATOR_OR, Condition(wikidbase.core.context.TermPath("name"), OPERATOR_EQUAL, "nick"))
   
    queryFields = []
    #queryFields.append(QueryField(wikidbase.core.context.TermPath("name")))
    #queryFields.append(QueryField(wikidbase.core.context.TermPath("pet.name")))

    query = Query(["people"], conditionalClause2, queryFields)

    return query
  


def testNewQuerySys(queryString) :
  """Test the query engine."""
  debugOutput("Testing %s" % queryString)

   #debugOutput("query = %s" % query)

  # Execture the query
  queryExecutor = QueryExecutor()
  results = queryExecutor.executeQuery(query)
  return results

