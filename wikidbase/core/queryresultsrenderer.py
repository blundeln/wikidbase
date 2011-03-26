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
# queryresultsrenderer (queryresultsrenderer.py)
# ----------------------------------
#
# Description:
#
#
# Author       : Nick Blundell
# Organisation : www.nickblundell.org.uk
# Version Info : $Id$
#

import math
import datetime, calendar, random
from django import template
import pagestore, datatype, query, state
import wikidbase.core
import wikidbase.core.module
from nbdebug import *

MAX_COLUMNS = 2

QS_COMMAND = "QS_COMMAND"
QS_LINKS = "QS_LINKS"

VIEW_TABLE = "VIEW_TABLE"
VIEW_MONTH = "VIEW_MONTH"
VIEW_WEEK = "VIEW_WEEK"
VIEW_DAY = "VIEW_DAY"

MAX_PAGE_ROWS = 12

RENDER_HTML = "RENDER_HTML"
RENDER_CSV = "RENDER_CSV"
UNDISPLAYED_FIELDS = ["id", "body", "xxmodified", "created by", "modified by"]

# TODO: I wonder if we can make this more pluggable so people can write new views.
class QuerySetView :

  def __init__(self) :
    debugOutput("Creating")
    self.sortField = None
    self.viewType = VIEW_TABLE
    self.page = None
    self.maxPageRows = None
    self.hiddenHeaders = []
    self.dateViewField = None
    self.dateOffset = None


  def render(self, queryResults, wikidpage=None, stateSource=None, nLinkField=None, command=None) :
   
    debugOutput("Rendering %s %s %s %s %s" % (queryResults, wikidpage, stateSource, nLinkField, command))

    #if self.sortField and queryResults:
    #  queryResults.sort(self.sortField[0], sortDirection=self.sortField[1])
    
    page = self.page or 0
    
    if stateSource :
      source = nLinkField and "/EXPORT_LINKS/%s/%s/" % (wikidpage and wikidpage.id or stateSource, nLinkField) or "/EXPORT_COMMAND/%s/%s/" % (wikidpage and wikidpage.id or stateSource, command)
    else :
      source = None

    if self.dateViewField :
      currentDate = datetime.date.today() + datetime.timedelta(self.dateOffset or 0)
      renderedData = renderQuerySetAsCalendar(queryResults, self.dateViewField, currentDate, viewType=self.viewType, wikidpage=wikidpage, nLinkField=nLinkField, source=source)
    else :
      renderedData = renderQuerySetAsTable(queryResults, wikidpage=wikidpage, nLinkField=nLinkField, source=source, page=page, maxPageRows = self.maxPageRows or MAX_PAGE_ROWS, hiddenHeaders = self.hiddenHeaders, sortField=self.sortField)

    return renderedData


  def update(self, request) :
    
    debugOutput("Updating with %s" % request.GET)
    
    if "sortField" in request.GET :
      self.sortField = (request.GET["sortField"], request.GET["sortValue"])
      self.page = 0

    if "page" in request.GET :
      self.page = int(request.GET["page"])
    
    if "maxPageRows" in request.GET :
      maxPageRows = int(request.GET["maxPageRows"])
      if maxPageRows > 0 :
        self.maxPageRows = maxPageRows
      self.page = 0
    
    if "hideHeader" in request.GET :
      hiddenHeader = request.GET["hideHeader"]
      if hiddenHeader not in self.hiddenHeaders :
        debugOutput("Hidding header '%s'" % hiddenHeader)
        self.hiddenHeaders.append(hiddenHeader)
        debugOutput("Hidden headers %s" % self.hiddenHeaders)
    
    if "showAllHeaders" in request.GET :
      debugOutput("Clearing hidden headers.")
      self.hiddenHeaders = []

    if "dateViewField" in request.GET :
      self.dateViewField = request.GET["dateViewField"] or None
      debugOutput("Updated dateViewField to %s" % self.dateViewField)

    if "viewType" in request.GET :
      self.viewType = request.GET["viewType"] or None
    
    if "dateOffset" in request.GET :
      try :
        if self.dateOffset :
          self.dateOffset += int(request.GET["dateOffset"])
        else :
          self.dateOffset = int(request.GET["dateOffset"])
      except :
        self.dateOffset = None


def _organiseHeadings(queryResults, hiddenHeaders=None) :
  """Takes some query results, and a list of user-hidden fields, to give a list of headings for display."""

  fieldsInfo = queryResults.getFieldsInfo()
  hiddenHeaders = hiddenHeaders or []

  displayHeaders = wikidbase.thirdparty.odict.OrderedDict()
  
  query = queryResults.getQuery()
  if query and query.queryFields :
    for queryField in query.queryFields :
      nFieldName = queryField.name.getNormalisedForm()
      if nFieldName not in hiddenHeaders and nFieldName in fieldsInfo :
        displayHeaders[nFieldName] = fieldsInfo[nFieldName]
  else :
    for nFieldName in fieldsInfo :
      # TODO: Stop commands being printed out.
      if nFieldName not in hiddenHeaders and fieldsInfo[nFieldName].fieldHeading.getBasePart().lower() not in UNDISPLAYED_FIELDS :
        displayHeaders[nFieldName] = fieldsInfo[nFieldName]

  return displayHeaders


@wikidbase.core.performance.Timer
def renderQuerySetAsTable(queryResults, wikidpage=None, nLinkField=None, source=None, page=0, maxPageRows=MAX_PAGE_ROWS, hiddenHeaders=None, sortField=None) :

  if not queryResults or len(queryResults) == 0 :
    return "<div class='system-message'>There are no results for this query</div>"

  debugOutput("wikidpage.id %s" % (wikidpage and wikidpage.id or None))
  
  queryResultsTemplate = template.loader.get_template("queryresults-table.html") 
  
  # Get display heading list (e.g. - hidden, fields specificed in query).
  displayHeadings = _organiseHeadings(queryResults, hiddenHeaders)

  # Get page worth of query items.
  noPages = int(math.ceil(len(queryResults.queryResults) / float(maxPageRows)))
  startIndex = page * maxPageRows
  endIndex = min(len(queryResults.queryResults), startIndex + maxPageRows)
  nextPage = page < (noPages - 1) and page + 1 or None
  if page > 0 : 
    prevPage = page - 1
  else :
    prevPage = None
  debugOutput("prevpage: %s" % prevPage)
  pageRange = range(0, noPages)

  
  # Get context page for convenient 'add button'.
  addContextPage = None
  if not nLinkField :
    primaryContexts = queryResults.getPrimaryContexts()
    if primaryContexts and len(primaryContexts) == 1 :
      nContext = primaryContexts.keys()[0]
      context = primaryContexts[nContext].capitalize()
      addContextPage = pagestore.getPageFromContext(nContext) 

  # Sort the date if necessary.
  if sortField :
    queryItems = queryResults.sort(sortField[0], sortField[1])
  else :
    queryItems = queryResults.queryResults
  
  # Crop the results for this table page.
  queryItems = queryItems[startIndex:endIndex]

  context = {
    "wikidpage":wikidpage,
    "nLinkField":nLinkField,
    "addContextPage":addContextPage,
    "source":source,
    "page":page, "noPages":noPages, "nextPage":nextPage, "prevPage":prevPage, "pageRange":pageRange, "lastPage":max(noPages-1,0),
    "maxPageRows":maxPageRows,
    "displayHeadings":displayHeadings,
    "queryItems": queryItems,
    "queryResults": queryResults,
    "datatype":datatype,
  }
  
  return queryResultsTemplate.render(template.Context(context))



def renderQuerySetAsCalendar(queryResults, dateViewField, currentDate, viewType=None, wikidpage=None, nLinkField=None, source=None) : 

  # TODO: Obtain content fields from table view settings.
  # TODO: Add add-page on this day option.

  if not queryResults or len(queryResults) == 0 :
    return "There are no results for this query"

  # Get context page for convenient 'add button'.
  addContextPage = None
  if not nLinkField :
    primaryContexts = queryResults.getPrimaryContexts()
    if primaryContexts and len(primaryContexts) == 1 :
      nContext = primaryContexts.keys()[0]
      context = primaryContexts[nContext].capitalize()
      addContextPage = pagestore.getPageFromContext(nContext) 

  queryResultsTemplate = template.loader.get_template("queryresults-calendar.html") 

  # Get display heading list (e.g. - hidden, fields specificed in query).
  displayHeadings = _organiseHeadings(queryResults)
  
  # Get the first visible date.
  if viewType == VIEW_DAY :
    # Same as current date.
    startDate = currentDate
  elif viewType == VIEW_WEEK :
    # Start of week.
    startDate = currentDate - datetime.timedelta(currentDate.weekday())
  else :
    # Start of month, start of week
    startDate = currentDate - datetime.timedelta(currentDate.day-1)
    startDate -= datetime.timedelta(startDate.weekday())
 
  # Work out the number of days to display
  if viewType == VIEW_DAY : noDays = 1
  elif viewType == VIEW_WEEK : noDays = 7
  else : noDays = 7*5

  # Make a list of visible dates.
  visibleDates = [startDate + datetime.timedelta(i) for i in range(0,noDays)]
  dayNames = [visibleDates[i].strftime("%a") for i in range(0,min(7, noDays))]

  debugOutput("visibleDates %s" % visibleDates)

  # Populate a calendar matrix with appropriate queryResultsItems
  dateDict = {}
  
  # Sort the queryset ascending by the date field.
  queryItems = queryResults.sort(dateViewField, wikidbase.core.query.SORT_ASCEND)

  # Use this to store cell details.
  class CalendarItem : pass

  displayDateViewField = None

  # Store wikidpages with dates in a date-index dictionary.
  for queryResultsItem in queryItems :
    field, dataPage, fieldHeading = queryResultsItem.getData(dateViewField)
    
    # Store a date field heading suitable for display.
    if not displayDateViewField :
      displayDateViewField = fieldHeading
    
    pyData = wikidbase.core.datatype.convert(field.data, mode=wikidbase.core.datatype.TO_PYTHON)
    dataDate = wikidbase.core.datatype.getDatePart(pyData)
    dataTime = wikidbase.core.datatype.getTimePart(pyData)
    if not dataDate :
      continue
    if dataDate not in dateDict :
      dateDict[dataDate] = []
    
    # Add helpful info to a cal item object for the template to render.
    calItem = CalendarItem()
    calItem.queryResultsItem = queryResultsItem

    # Choose the display field for the cal item.
    if displayHeadings :
      displayField = queryResultsItem.getData(displayHeadings.keys()[0])
    else : 
      displayField = None

    if not (displayField and displayField[0] and displayField[0].data) :
      displayField = queryResultsItem.getData("page")
    calItem.wikidpage = displayField[1]
    calItem.content = displayField[0].data
    
    # Add time
    calItem.time = dataTime

    dateDict[dataDate].append(calItem)

  dateMatrix = []
  for i in range(0, (len(visibleDates) / 7) or 1) :
    dateRow = []
    for j in range(0,min(7, len(visibleDates))) :
      dateRow.append(visibleDates[i*7 + j])
    dateMatrix.append(dateRow)
    dateRow = []

  debugOutput("dateMatrix %s" % dateMatrix)
 
  # Calculate page navigation stuff.
  # TODO: Update for days and weeks
  if viewType == VIEW_DAY :
    daysToNextPage, daysToPrevPage = 1, -1
  elif viewType == VIEW_WEEK :
    daysToNextPage, daysToPrevPage = 7, -7
  else :
    daysToNextPage = 1 + calendar.monthrange(currentDate.year, currentDate.month)[1] - currentDate.day 
    lastMonth = currentDate - datetime.timedelta(currentDate.day)
    daysToPrevPage = 1 - currentDate.day - calendar.monthrange(lastMonth.year, lastMonth.month)[1]

  context = {
    "source":source,
    "dayNames":dayNames,
    "visibleDates":visibleDates,
    "dateMatrix":dateMatrix,
    "dateDict":dateDict,
    "currentDate":currentDate,
    "today":datetime.date.today(),
    "daysToNextPage":daysToNextPage,
    "daysToPrevPage":daysToPrevPage,
    "datatype":wikidbase.core.datatype,
    "dateViewField":dateViewField,
    "displayDateViewField":displayDateViewField,
    "viewType":viewType,
    "random":random,
    "addContextPage":addContextPage,
  }
  
  return queryResultsTemplate.render(template.Context(context))


@wikidbase.core.performance.Timer
def renderCommand(request, source, command, renderFormat = RENDER_HTML) :
  """Renders a wikidpage command: a query or a module function call."""
  debugOutput("Running command %s" % command)

  # See if the source will yield a wikidpage
  wikidpage = pagestore.getWikidpage(source)
  stateSource = wikidpage and (wikidpage.context or wikidpage.id) or source

  if ">>" in command and command.lower().strip().startswith("command") :
    result = wikidbase.core.module.runModuleCallString(request, command.split(">>")[1])
    return str(result)

  # Then try to run this as a query

  # Get a query set.
  wikidbase.core.performance.startTimer("runQuery")
  queryResults = query.runQuery(command)
  wikidbase.core.performance.stopTimer("runQuery")

  if renderFormat == RENDER_HTML :

    # Get a view from the user's state.
    wikidbase.core.performance.startTimer("get view from user state")
    queryResultsView = state.getItem(request, state.STATE_VIEW, stateSource, command)
    if not queryResultsView or dir(QuerySetView()) != dir(queryResultsView):
      queryResultsView = QuerySetView()
    queryResultsView.update(request)
    state.setItem(request, state.STATE_VIEW, stateSource, command, queryResultsView)
    wikidbase.core.performance.stopTimer("get view from user state")

    # Render the view.
    wikidbase.core.performance.startTimer("queryResultsView.render")
    renderedData = queryResultsView.render(queryResults, wikidpage=wikidpage, stateSource=stateSource, command=command)
    wikidbase.core.performance.stopTimer("queryResultsView.render")

  elif renderFormat == RENDER_CSV :
    renderedData = renderCSV(queryResults)

  return renderedData




def renderLinkField(request, wikidpageID, linkName, renderFormat=RENDER_HTML, futureLinks=[]) :
  
  debugOutput("linkName %s, futureLinks %s" % (linkName, futureLinks))
  
  nLinkField = wikidbase.core.normaliseTerm(linkName)
  
  wikidpage = pagestore.getWikidpage(wikidpageID)
  stateSource = wikidpage and (wikidpage.context or wikidpage.id) or None

  if wikidpage or futureLinks :
    try :
      links = pagestore.getLinks(wikidpage.id)[nLinkField]
    except :
      links = []
    # XXX: This next line is a bit wasteful.
    linkIDs = [link[0] for link in links]
    queryResults = query.QueryResults(futureLinks or [] + linkIDs)
  else :
    queryResults = None

  if renderFormat == RENDER_HTML :
    # Get a view from the user's state.
    queryResultsView = state.getItem(request, state.STATE_VIEW, stateSource, nLinkField)
    if not queryResultsView or dir(QuerySetView()) != dir(queryResultsView):
      queryResultsView = QuerySetView()
    queryResultsView.update(request)
    if stateSource :
      state.setItem(request, state.STATE_VIEW, stateSource, nLinkField, queryResultsView)
    
    renderedData = queryResultsView.render(queryResults, wikidpage, stateSource=stateSource, nLinkField=nLinkField)

  elif renderFormat == RENDER_CSV :
    renderedData = renderCSV(queryResults)

  return renderedData

def renderCSV(queryResults) :

  import csv
  import StringIO
  
  csvOutput = StringIO.StringIO()
  writer = csv.writer(csvOutput)

  # Get heading list.
  fieldsInfo = queryResults.getFieldsInfo()
  displayHeadings = []
  for nField in fieldsInfo :
    displayHeadings.append(str(fieldsInfo[nField].fieldHeading))
  
  writer.writerow(displayHeadings)
  writer.writerow(["" for i in range(0, len(displayHeadings))])

  # Get data matrix
  for queryItem in queryResults.queryResults :
    dataRow = []
    for nField in fieldsInfo :
      field, dataPage, fieldHeading = queryItem.getData(nField)
      displayData = datatype.convert(datatype.convert(field.data, mode=datatype.TO_PYTHON), mode=datatype.TO_STRING, form=datatype.STRING_FORM_SHORT)
      dataRow.append(displayData)

    writer.writerow(dataRow)
  
  return csvOutput.getvalue()
