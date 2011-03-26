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
# pagestore (pagestore.py)
# ------------------------
#
# Description:
#
# This module handles loading and storing wikidpages and their relational links.
#
# Author       : Nick Blundell
# Organisation : www.nickblundell.org.uk
# Version Info : $Id: pagestore.py 957 2008-04-30 18:56:15Z blundeln $
#

import pickle, os, shutil, tarfile, datetime
import pkg_resources

import django.conf

import wikidbase
import wikidbase.core.models
import wikidbase.core.pagecontent

import wikidbase.core.context
import wikidbase.core.query
import wikidbase.core.cache

from nbdebug import *


INDEX_PAGE = "index"
MODE_UPDATE = "MODE_UPDATE"
MODE_CLEAR = "MODE_CLEAR"


#
# Page functions
#

def getNewPage(cloneSource=None, name=None) :
  """Returns a new wikidpage, ready to be save to the database."""
  
  # Create the page from the model and set its name if pre-specified.
  newWikidpage = wikidbase.core.models.WikidPage()
  if name : newWikidpage.name = name
  
  # If clone source has been specified, create the new page as its clone.
  if cloneSource :
    newWikidpage.context = cloneSource.context
    newWikidpage.content = cloneSource.getContent().getClone(wikidbase.core.pagecontent.CLONE_ONLY_FIELDS,cloneData=False).getText()
  
  return newWikidpage



def getAllPages() :
  """Returns all pages in the wikidbase."""
  return wikidbase.core.models.WikidPage.objects.all()


def getWikidpage(nameOrID, indexCheck=True, id=None) :
  """Returns the specified wikidpage from the wikidbase."""

  debugOutput("Getting page '%s' id %s." % (nameOrID, id))
 
  # If there is an id, look for the page.
  if id :
    return wikidbase.core.models.WikidPage.objects.get(id=id)
  
  # Default to the index page if no page was specified.
  if not nameOrID :
    nameOrID = INDEX_PAGE
  
  wikidpage = None

  try :
    wikidpage = wikidbase.core.models.WikidPage.objects.get(id=int(nameOrID))
  except :
    try : 
      wikidpage = wikidbase.core.models.WikidPage.objects.get(name=nameOrID)
    except :
      # If there is no index page, initialise the wikidbase.
      if nameOrID == INDEX_PAGE and indexCheck :
        initialiseWikidbase()
        wikidpage = wikidbase.core.models.WikidPage.objects.get(name=nameOrID)

  return wikidpage


def deletePage(id) :
  """Delete the wikidpage with the specified id.""" 
  debugOutput("Deleting page with id %s" % id)
  
  # Get the page and delete it and its links to other pages.
  wikidpage = getWikidpage(id)
  if wikidpage :
    deleteAllLinks(id)
    wikidpage.delete()
  else :
    raise Exception("Unable to delete page %s" % id)



def getPagesInContext(context) :
  """
  Returns a list of pages with the specified context.  If no context is specified, returns pages with no context.
  """

  if context :
    return list(getAllPages().filter(nContext__exact=wikidbase.core.context.normaliseTerm(context)))
  else :  
    return list(getAllPages().filter(context__exact=""))



def getPageFromContext(context) :
  """
  Returns a page representing the specified context.  Usually this will be, say, the most recently edited page in the context.
  """
  if not context :
    raise Exception("No context specified")
 
  # Try to get the context page from the wikidbase context.
  wikidpageContext = None
  wikidpageContexts = wikidbase.core.context.getContexts()
  nContext = wikidbase.core.normaliseTerm(context)
  if nContext in wikidpageContexts :
    wikidpageContext = wikidpageContexts[nContext]

  try :
    contextPage = wikidpageContext.representativeWikidpages.stack[0]
  except :
    contextPage = None

  debugOutput("contextPage is %s for %s" % (contextPage.name, context))
  
  return contextPage


#
# Link functions
#


def addLink(page1, page2, linkName1, linkName2) :
  """Adds a bi-directional link from page1 to page2 with the specified relationship names.""" 
  nLinkName1 = wikidbase.core.context.normaliseTerm(linkName1)
  nLinkName2 = wikidbase.core.context.normaliseTerm(linkName2)

  # Get all of the links for page 1.
  try :
    links = getLinks(page1)[nLinkName1]
  except :
    links = None
  
  # Check if the link exists already.
  if links :
    for link in links :
      if link[0] == page2 and wikidbase.core.context.normaliseTerm(link[1]) == nLinkName2 :
        raise Exception("Link already exists")
  
  # Sort the link arguments so we can determine how they go into the database.
  debugOutput("Adding link %s(%s) <-> %s(%s)" % (page1, linkName1, page2, linkName2))
  page1, page2, linkName1, linkName2 = _sortLinkArgs(page1, page2, linkName1, linkName2)
 
  # Create the link from the model and save it.
  link = wikidbase.core.models.WikidPageLink(page1=page1,page2=page2,linkName1=linkName1,linkName2=linkName2)
  link.save()
  debugOutput("Added link %s(%s) <-> %s(%s)" % (page1, linkName1, page2, linkName2))
  
  return link


def deleteAllLinks(id) :
  """
  Deletes all of a wikidpage's links.
  """
  wikidbase.core.models.WikidPageLink.objects.filter(page1=id).delete()
  wikidbase.core.models.WikidPageLink.objects.filter(page2=id).delete()


def deleteLink(id, linkID, linkName) :
  """
  Deletes a specific link of a wikidpage.
  """

  # TODO: Can sort ids for this.
  debugOutput("Deleting link %s %s %s" % (id, linkID, linkName))

  # Normalise the link name.
  nLinkName = wikidbase.core.context.normaliseTerm(linkName)
  deleted = False

  #
  # Note, we must look for links going both directions in the database.
  #

  links = wikidbase.core.models.WikidPageLink.objects.filter(page1=id, page2=linkID)
  for link in links :
    if wikidbase.core.context.normaliseTerm(link.linkName1) == nLinkName :
      link.delete()
      deleted = True
  
  links = wikidbase.core.models.WikidPageLink.objects.filter(page2=id, page1=linkID)
  for link in links :
    if wikidbase.core.context.normaliseTerm(link.linkName2) == nLinkName :
      link.delete()
      deleted = True

  if not deleted :
    raise Exception("Unable to delete the link.")


def getLinks(pageID, rawLinks=None):
  """Gets a page's links with normalised names."""
  rawLinks = rawLinks or getRawLinks(pageID)
  links = {}
  for linkName in rawLinks :
    nLinkName = wikidbase.core.context.normaliseTerm(linkName)
    if nLinkName not in links :
      links[nLinkName] = []
    for link in rawLinks[linkName] :
      links[nLinkName].append(link)

  return links


# TODO: Can we make this more efficient - takes up a big proprtion of time?
def getRawLinks(pageID) : 
  """
  Gets a page's links with their original (non-normalised) link names.
  """
  links = {}
  if pageID == None :
    return links

  debugOutput("pageID %s" % pageID)

  selfLinkAdded = False
  for i in range(0,2) :
    # Get all links from page with id pageID
    if i==0 :
      linkItems = wikidbase.core.models.WikidPageLink.objects.filter(page1=pageID)
    else :
      linkItems = wikidbase.core.models.WikidPageLink.objects.filter(page2=pageID)
      
    # Add the links into a dictionary.
    debugOutput("linkItems %s" %  linkItems)
    for linkItem in linkItems :
      
      # Don't repeat a self-link.
      if linkItem.page1 == linkItem.page2 :
        if selfLinkAdded :
          debugOutput("Not adding link %s-%s selfLinkAdded %s" % (linkItem.page1, linkItem.page2, selfLinkAdded))
          continue
        else :
          selfLinkAdded = True
     
      linkName = i==0 and linkItem.linkName1 or linkItem.linkName2
      if not linkName in links : links[linkName] = []
      # XXX: Consider what might happen for a page with id 0
      links[linkName].append([i==0 and linkItem.page2 or linkItem.page1, i==0 and linkItem.linkName2 or linkItem.linkName1])
 
  return links


def dump(hostname, uploadFolder) :
  """Dumps the entire wikidbase data: pages, links, files to a compressed file."""
  debugOutput("Dumping")
 
  # Set up the file structure.
  timeStamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
  dumpFolder = "/tmp/wikidbase_tmp/wikidbase-data-%s-%s-%s" % (hostname, timeStamp, wikidbase.VERSION)
  filesPath = os.path.join(dumpFolder,"files")
  dataFile = os.path.join(dumpFolder, "data")
  
  # This also makes parent folders.
  os.makedirs(filesPath)
  
  # This will hold all of the data.
  container = {}

  # Simply add all of the model instances in the database to a giant container.
  for currentModel in [wikidbase.core.models.WikidPage, wikidbase.core.models.WikidPageLink, wikidbase.core.models.GlobalState] :
    objs = []
    debugOutput("Dumping: %s" % currentModel._meta.module_name)
    for obj in currentModel.objects.all() :
      objs.append(obj.getState())

    container[currentModel._meta.module_name] = objs

  # Pickle the container to a file.
  debugOutput("Dumping objects to %s" % dataFile)
  pickle.dump(container, open(dataFile, "w"))
  
  # Copy attached files.
  for filename in os.listdir(uploadFolder) :
    debugOutput("copying file %s to %s" % (filename, filesPath))
    try :
      shutil.copy(os.path.join(uploadFolder, filename), filesPath)
    except :
      debugOutput("Could not copy %s" % filename)

  # Tar it up
  tarFilePath = "%s.tar.gz" % dumpFolder
  tar = tarfile.open(tarFilePath, "w:gz")
  for path in [dataFile, filesPath] :
    debugOutput("Adding %s to %s" % (path, tarFilePath))
    tar.add(path, os.path.basename(path))
  tar.close()

  # Remove the temporary folder.
  shutil.rmtree(dumpFolder)

  return tarFilePath


def load(dumpFile, mode, uploadFolder) :
  """Loads dumped data into a wikidbase."""

  # XXX:
  assert(mode == MODE_CLEAR)
  
  debugOutput("Loading data from %s with mode %s" % (dumpFile, mode))
  extractPath = "/tmp/%s-dir" % os.path.basename(dumpFile)
  os.mkdir(extractPath)
  newIDMap = {}

  # Extract the dump file.
  tar = tarfile.open(dumpFile)
  dataFile = tar.extractfile("data")
  if not dataFile :
    raise Exception("Cannot extract data file")
  
  # Unpickle the data into a container.
  container = pickle.loads(dataFile.read())
  
  #
  # Load wikidpages
  #
  
  if mode == MODE_CLEAR :
    getAllPages().delete()

  for wikidpageData in container["wikidpage"] :
    # Create the wikidpage object.
    newWikidpage = wikidbase.core.models.WikidPage()
    newWikidpage.setState(wikidpageData)

    # Check for an existing page with this id
    existingPage = getWikidpage(newWikidpage.id)
    if existingPage and newWikidpage.modifiedDate > existingPage.modifiedDate :
      # TODO
      pass
    
    newWikidpage.save(autoFields = False)
    
  #
  # Load links
  #

  if mode == MODE_CLEAR :
    wikidbase.core.models.WikidPageLink.objects.all().delete()

  for linkData in container["wikidpagelink"] :
    newLink = wikidbase.core.models.WikidPageLink()
    newLink.setState(linkData)
    newLink.save()

  # TODO: Load global data.

  #
  # Copy attached files
  #
  
  if "files/" in tar.getnames() :
    filesExtractPath = os.path.join(extractPath,"files")
    debugOutput(tar.getnames())
    for member in tar.getnames() :
      tar.extract(member, extractPath)
    
    for filename in os.listdir(filesExtractPath) :
      debugOutput("copying file %s to %s" % (filename, uploadFolder))
      try :
        shutil.copy(os.path.join(filesExtractPath, filename), uploadFolder)
      except :
        debugOutput("Could not copy %s" % filename)


  # Remove the extraction folder.
  shutil.rmtree(extractPath)

  # Clear all caches.
  wikidbase.core.cache.clearAllCaches()


def initialiseWikidbase() :
  """Loads pre-defined pages into the wikidbase (e.g. help pages, index page)."""
  
  debugOutput("Initialising wikidbase.")
  pagesDir = "resources/pages" 

  # Look in the package resources for wikidpages to preload (e.g an index page, etc).
  for dirItem in pkg_resources.resource_listdir(wikidbase.__name__, pagesDir) :
    if not dirItem.endswith(".rst") : continue
    
    pageFile = os.path.join(pagesDir, dirItem)
    pageName = os.path.basename(pageFile).replace(".rst","")
    
    # Create the page
    wikidpage = getWikidpage(pageName, indexCheck=False)
    if not wikidpage :
      wikidpage = getNewPage(name=pageName)
    
    if pageName == INDEX_PAGE and wikidpage.content :
      # Do note overwite the index page if it exists.
      pass
    else :
      wikidpage.content = pkg_resources.resource_string(wikidbase.__name__, pageFile)
      wikidpage.format = wikidbase.core.models.CONTENT_FORMATS[0][0]
      wikidpage.save()


#
# Mass wikidpage manipulation functions
#



def addField(nContext, fieldName, defaultData, position=None, nField=None) :
  debugOutput("nContext %s fieldName %s defaultData %s position %s nField %s" % (nContext, fieldName, defaultData, position, nField))

  # Get a list of all the pages in the context.
  wikidpages = getPagesInContext(nContext)
  
  for wikidpage in wikidpages :
    wikidpageContent = wikidpage.getContent()
    wikidpageContent.addField(fieldName, defaultData, (position, nField))
    wikidpage.save()


def deleteField(nContext, nFieldName) :
  debugOutput("nContext %s nFieldName %s" % (nContext, nFieldName))
  
  # Get a list of all the pages in the context.
  wikidpages = getPagesInContext(nContext)
  
  for wikidpage in wikidpages :
    wikidpageContent = wikidpage.getContent()
    wikidpageContent.deleteField(nFieldName)
    wikidpage.save()


#
# Useful functions.
#

def _sortLinkArgs(page1, page2, linkName1, linkName2) :
  """
  Sorts link attributes for efficient storage and retrieval.
  """
  if page1 > page2 :
    temp = page1, linkName1
    page1, linkName1 = page2, linkName2
    page2, linkName2 = temp
  return page1, page2, linkName1, linkName2

