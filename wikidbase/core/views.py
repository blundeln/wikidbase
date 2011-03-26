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
# views (views.py)
# ----------------
#
# Description:
#
#
# Author       : Nick Blundell
# Organisation : www.nickblundell.org.uk
# Version Info : $Id: views.py 976 2008-06-11 18:51:28Z blundeln $
#

import django.template
import django.http
import django.shortcuts
import django.forms
import django.contrib.auth.decorators
import django.utils.simplejson
import django.views.static
import django.conf

import wikidbase.core.models
import wikidbase.core.pagestore
import wikidbase.core.renderer
import wikidbase.core.manipulators
import wikidbase.core.query
import wikidbase.core.queryresultsrenderer
import wikidbase.core.systempages
import wikidbase.core.state
import wikidbase.core.context
import wikidbase.core.security
import wikidbase.core.session
import wikidbase.core.files

import wikidbase.core.performance
from nbdebug import *


def page(request, page=None, editSource=False, create=False, clonePage=None, systemPage=None):
  """Renders a wikidpage for editing or creation.""" 


  # Do some security checks.
  wikidbase.core.security.barrier(request.user.username, "view")
  if editSource : wikidbase.core.security.barrier(request.user.username, "wiki-edit")
  if create : wikidbase.core.security.barrier(request.user.username, "create")
    

  wikidbase.core.performance.globalTimer.reset()
  wikidbase.core.performance.startTimer("page")
  
  debugOutput("PAGE page=%s editSource=%s create=%s clonePage=%s" % (page, editSource, create, clonePage))
 
  # Normalise wikidpage paramerters.
  if page : page = page.rstrip("/")
  if clonePage : clonePage = clonePage.rstrip("/")

  #
  # Try to fetch the relevant wikidpage.
  #
  if create :
    
    # If a source clone page has been specified, get it.
    if clonePage :
      cloneSource = wikidbase.core.pagestore.getWikidpage(clonePage)
      if not cloneSource :
        raise django.http.Http404("The page you are trying to clone does not exist.")
    else :
      cloneSource = None
    # If we are adding a new page, create an appropriate new page, purely for collecting data.
    wikidpage = wikidbase.core.pagestore.getNewPage(cloneSource=cloneSource, name=page)
  
  else :
    
    if systemPage :
      wikidpage = wikidbase.core.systempages.getSystemPage(request, systemPage)
    else :
      wikidpage = wikidbase.core.pagestore.getWikidpage(page)

  # If no wikidpage was found and we are not creating a page, then flag a 404.
  if not create and not wikidpage :
    raise django.http.Http404

  # Set the method by which we will edit this wikidpage.
  editMode = editSource and wikidbase.core.manipulators.EDIT_MODE or wikidbase.core.manipulators.VIEW_MODE

  # Depending on the rendering mode (view or edit), create the appropriate wikidpage manipulator.
  manipulator = wikidbase.core.manipulators.getWikidpageManipulator(editMode, wikidpage)

  

  #
  # Handle posted form data.
  #

  if request.POST :
   
    if editMode == wikidbase.core.manipulators.EDIT_MODE :
      wikidbase.core.security.barrier(request.user.username, "wiki-edit")
    else :
      wikidbase.core.security.barrier(request.user.username, "edit")

    # Process the incoming data and prepare it for form rendering.
    try : newData, errors = _handlePostedWikidpageData(request, editMode, manipulator, wikidpage)
    except ResponseException, e: return e.response

  else :
    
    # Retrieve the existing wikidpage data for form rendering.
    errors = {}
    newData = manipulator.flatten_data()
    
    # XXX: This seems a bit crappy but will do for now - this is important for adding structure to source-edited cloned pages.
    # XXX: Ideally this should happen in the django model manipluator (i.e. we should override it).
    if editMode == wikidbase.core.manipulators.EDIT_MODE and wikidpage and wikidpage.id == None:
      newData["name"] = wikidpage.name
      newData["content"] = wikidpage.content
      newData["context"] = wikidpage.context

    # Look for any explicit default values
    for item in request.GET :
      if item in newData :
        newData[item] = request.GET[item]

  debugOutput("New data %s" % newData)
 
  # Create a form object (e.g. fields) from the manipulator, new data, and errors.
  form = django.forms.FormWrapper(manipulator, newData, errors)

  #
  # Set up the template's context.
  #

  context = {
    "wikidpage":wikidpage,
    "form":form,
    "uploadFileForm": wikidbase.core.files.getUploadFolder() and wikidbase.core.widgets.FileUploadForm() or None,
    "editSource" : editSource,
  }
 
  if editMode == wikidbase.core.manipulators.EDIT_MODE :
    # Render the editing template.
    contentTemplate = django.template.loader.get_template("source-edit-wikidpage.html")
    context["content"] = contentTemplate.render(django.template.Context(context))
  else :
    # Render the wikidpage.
    wikidbase.core.performance.startTimer("rendering page")
    # TODO: can we render the edit page in this same way.
    context["content"] = wikidbase.core.renderer.renderWikidpage(request, wikidpage, form)
    wikidbase.core.performance.stopTimer("rendering page")
  
  # Set up page tabs.
  #editSource = editMode == wikidbase.core.manipulators.EDIT_MODE
  pageTabs = []
  
  # View and edit tabs
  if not systemPage :
    if not create :
      pageTabs.append(("View", wikidpage.get_absolute_url(), not editSource, "view-link", "View this wikidpage" ))
      if wikidbase.core.security.hasPermission(request.user.username, "wiki-edit") :
        pageTabs.append(("Edit", wikidpage.get_absolute_url()+"EDIT/", editSource, "edit-link", "Edit the contents of this wikidpage" ))
    
    # Clone tab
    if wikidpage.context :
      if create :
        url = None
      else :
        url = "%s/CREATE/%s" % (editSource and "/EDIT" or "", wikidpage.id)
      
      if wikidbase.core.security.hasPermission(request.user.username, "create") :
        pageTabs.append(("New", url, create, "clone-link", "Create a new entry similar to the current page" ))
    
  context["pageTabs"] = pageTabs

  wikidbase.core.performance.stopTimer("page")
  wikidbase.core.performance.timerReport()

  return django.shortcuts.render_to_response("wikidpage.html", django.template.RequestContext(request, context))  


def _handlePostedWikidpageData(request, editMode, manipulator, wikidpage) :
  """Handles data posted to a wikidpage."""
  
  # Integrate file uploads with posted information.
  newData = request.POST.copy()
  #newData.update(request.GET)
  newData.update(request.FILES)
  
  # Copy values of non-posted data from the existing object, so we can have all the data together.
  if editMode == wikidbase.core.manipulators.EDIT_MODE :
    currentData = manipulator.flatten_data()
    for item in currentData :
      if item not in newData :
        newData[item] = str(currentData[item])
 
  # Get any validation errors that occured.
  errors = manipulator.get_validation_errors(newData)
  debugOutput("errors %s" % errors)
  
  if not errors :
    
    # When source is edited, we can use the standard Django process for string to python (type) conversion.
    if editMode == wikidbase.core.manipulators.EDIT_MODE :
      manipulator.do_html2python(newData)
   
    # Save the new data and get the updated wikidpage.
    creatingNewPage = wikidpage.id == None
    wikidpage = manipulator.save(newData)
    wikidbase.core.session.setMessage(request, creatingNewPage and "The page has been <b>created</b> and <b>saved</b>." or "The page has been <b>saved</b>.")

    # Handle file upload.  Note this has to go here, since Django's model manipulator does not retain our wikidpage instance.
    if wikidbase.core.files.getUploadFolder() :
      uploadFileForm = wikidbase.core.widgets.FileUploadForm(newData)
      if uploadFileForm.is_valid():
        success = uploadFileForm.save(wikidpage, wikidbase.core.files.getUploadFolder())

    # Set some useful property information then re-save the wikidpage.
    wikidpage.properties[wikidbase.core.models.PROP_MOD_BY] = request.user.username or "anonymous"
    if creatingNewPage :
      wikidpage.properties[wikidbase.core.models.PROP_CREATED_BY] = request.user.username or "anonymous"
    wikidpage.save()
    debugOutput("wikidpage properties %s" % wikidpage.properties)

    # Handle posted wikidpage linking data.
    _handlePostedWikidpageLinks(request, wikidpage)

    # Redirect based on the submission method.
    redirectTo = wikidpage.get_absolute_url()

    # Try to set a variable to the last page.
    lastPage = None
    
    # Handle the user clicking 'save and back'.
    if "save_and_back" in request.POST :
      lastPage = getPreviousPage(request)
      if lastPage :
        redirectTo = lastPage

    raise ResponseException(django.http.HttpResponseRedirect(redirectTo))
  
  else :
    
    # If there were errors, then the user must correct them before anything can be saved.
    debugOutput("ERRORS: %s" % (errors))
    return newData, errors


def getPreviousPage(request, offset=0) :
  history = wikidbase.core.session.getVariable(request, "history", [])
  lastPage = None
  for i in range(0,len(history)) :
    if i < offset :
      continue
    url = history[i]
    if url != request.get_full_path() :
      lastPage = url
      break;
  return lastPage
      

def _handlePostedWikidpageLinks(request, wikidpage) :
  """Processes any relational link instructions after a page has been saved"""

  # Find posted link information for specific link adding.
  for attributeName in request.POST :
    
    if attributeName.endswith("-link-add") and request.POST[attributeName]:
      
      # Get details of the link to be added.
      localRelField = attributeName.replace("-link-add","")
      remoteIDorContext = request.POST[attributeName]
      try :
        remoteRelField = request.POST["%s-foreign-link-name" % (attributeName)]
      except :
        remoteRelField = None
      debugOutput("linking localfield %s to %s(%s)" % (localRelField, remoteRelField, remoteIDorContext))
   
      if remoteRelField :
        # Try to add a link to an existing page, else redirect user to create a new page.
        try :
          remoteID = int(remoteIDorContext)
        except :
          remoteID = None
          remoteContext = remoteIDorContext
        
        if remoteID :
          try :
            link = wikidbase.core.pagestore.addLink(wikidpage.id, remoteID, localRelField, remoteRelField)
            wikidbase.core.session.setMessage(request, link and "The new <b>link</b> has been <b>added</b>." or "Unable to add link: that link existed already.")
          except Exception, e :
            wikidbase.core.session.setMessage(request, "Unable to add link: %s" % str(e))
        else :
          # Re-direct the user to create a new page, passing a link back reference to the current page.
          linkBack = "%s-%s-%s" % (wikidpage.id, localRelField, remoteRelField)
          raise ResponseException(django.http.HttpResponseRedirect("/CREATE/%s?linkBack=%s" % (wikidbase.core.pagestore.getPageFromContext(remoteContext).id, linkBack)))


  # Handle general link adding.
  try :
    localRelField = request.REQUEST["link-add-local-link-name"]
    foreignRelField = request.REQUEST["link-add-foreign-link-name"]
    linkTarget = request.REQUEST["link-add"]
  except :
    localRelField, foreignRelField, linkTarget = None, None, None

  debugOutput("localRelField %s foreignRelField %s linkTarget %s" % (localRelField, foreignRelField, linkTarget))

  # If a wikidpage has been specified as the target link.
  if linkTarget :

    # Determine whether the target is an actual page or a context for a new page (e.g. to Sam, or to Person).
    try :
      targetID = int(linkTarget)
    except :
      targetID = None
      targetContext = linkTarget
    
    if targetID :
      # If linkTarget is a specific page...
      try :  
        link = wikidbase.core.pagestore.addLink(wikidpage.id, targetID, localRelField, foreignRelField)
        wikidbase.core.session.setMessage(request, link and "The new <b>link</b> has been <b>added</b>." or "Unable to add link: that link existed already.")
      except Exception, e :
        wikidbase.core.session.setMessage(request, "Unable to add link: %s" % str(e))
    else : 
      # Re-direct the user to create a new page, passing a back link reference to the current page.
      linkBack = "%s-%s-%s" % (wikidpage.id, localRelField, foreignRelField)
      raise ResponseException(django.http.HttpResponseRedirect("/CREATE/%s?linkBack=%s" % (wikidbase.core.pagestore.getPageFromContext(targetContext).id, linkBack)))

  # Handle a link-back, which is where we created a new page that must be linked to an existing page on creation.
  if "linkBack" in request.GET :
    remoteID, remoteRelField, localRelField = request.GET["linkBack"].split("-")
    link = wikidbase.core.pagestore.addLink(wikidpage.id, int(remoteID), localRelField, remoteRelField)
    wikidbase.core.session.setMessage(request, link and "The new <b>link</b> has been <b>added</b>." or "Unable to add link: that link existed already.")


def deletePage(request, id) :
  """Called to delete the specified wikidpage."""

  debugOutput(request.POST)
  wikidbase.core.security.barrier(request.user.username, "delete")
 
  # Get the name of the redirection page for after deletion.
  next = "next" in request.POST and request.POST["next"] or "next" in request.GET and request.GET["next"] or None
    
  if request.POST :
    if "Delete" in request.POST :
      debugOutput("Delete requested")
      
      try :
        wikidbase.core.pagestore.deletePage(int(id))
        wikidbase.core.session.setMessage(request, "The wikidpage has been deleted")
      except Exception, e:
        wikidbase.core.session.setMessage(request, str(e))


    # Re-direct the user.
    if next :
      return django.http.HttpResponseRedirect(next)
    else :
      lastPage = getPreviousPage(request)
      # TODO: Need to fix this, so it cannot go back to a deleted page.
      # XXX:
      lastPage = None
      return django.http.HttpResponseRedirect(lastPage or "/")

  else :
    
    # Render a question to the user.
    message = "Are you sure you wish to delete this wikidpage? - it cannot be recovered once deleted!"
    options = ["Delete","Cancel"]
    return django.shortcuts.render_to_response("message.html", django.template.RequestContext(request, {"message":message, "options":options, "next":next}))
 

def deleteLink(request, id, linkID, linkField) :
  """Called to delete the specified link."""
  
  wikidbase.core.security.barrier(request.user.username, "delete")
  debugOutput("Deleting %s %s" % (linkID, linkField))
 
  try :
    wikidbase.core.pagestore.deleteLink(int(id), int(linkID), linkField)
    wikidbase.core.session.setMessage(request, "The link from this wikidpage has been deleted.")
  except Exception, e:
    wikidbase.core.session.setMessage(request, "The link could not be deleted: " + str(e))
  

  # Re-direct the user.
  if "next" in request.GET :
    return django.http.HttpResponseRedirect(request.GET["next"])
  else :
    return django.http.HttpResponseRedirect("/")


def deleteFile(request, pageID, filename) :
  """Called to delete the specified file attachment from a wikidpage"""
  wikidbase.core.security.barrier(request.user.username, "delete")
  wikidpage = wikidbase.core.pagestore.getWikidpage(pageID)
  try :
    attachedFiles = wikidpage.properties[wikidbase.core.models.PROP_ATTACHMENTS]
  except :
    attachedFiles = None

  if attachedFiles and filename in attachedFiles :
    try :
      os.remove(os.path.join(django.conf.settings.UPLOAD_FOLDER, attachedFiles[filename]))
    except OSError:
      pass
    del attachedFiles[filename]
    wikidpage.save()
    wikidbase.core.session.setMessage(request, "The file attachment has been deleted.")

  return django.http.HttpResponseRedirect(wikidpage.get_absolute_url())


@django.contrib.auth.decorators.user_passes_test(lambda user: user.is_superuser)
def initialise(request) :
  """Called to initialise the wikidbase with some default pages."""
  
  wikidbase.core.pagestore.initialiseWikidbase() 
  wikidbase.core.session.setMessage(request, "Wikidbase is now initilised.")
  return django.http.HttpResponseRedirect("/")



def exportCommand(request, source, command, filename=None) :
  """Exports command data in a format based upon the file extension."""
  
  wikidbase.core.security.barrier(request.user.username, "view")
  debugOutput("Exporting command %s" % command)

  mimetype = "text/html"
  renderFormat = wikidbase.core.queryresultsrenderer.RENDER_HTML
  
  # Determine the mime type and rendering format form the requested file's extension.
  if filename and ".csv" in filename.lower() :
    renderFormat = wikidbase.core.queryresultsrenderer.RENDER_CSV
    mimetype = "text/plain"

  return django.http.HttpResponse("%s" % wikidbase.core.queryresultsrenderer.renderCommand(request, source, command, renderFormat), mimetype=mimetype)
 

def exportLinks(request, pageID, linkName, filename=None) :
  """Exports wikidpage link data."""
  mimetype = "text/html"
  wikidbase.core.security.barrier(request.user.username, "view")
  renderFormat = wikidbase.core.queryresultsrenderer.RENDER_HTML
  # Determine the mime type and rendering format form the requested file's extension.
  if filename and ".csv" in filename.lower() :
    renderFormat = wikidbase.core.queryresultsrenderer.RENDER_CSV
    mimetype = "text/plain"

  return django.http.HttpResponse("%s" % wikidbase.core.queryresultsrenderer.renderLinkField(request, pageID, linkName, renderFormat), mimetype=mimetype)



def pageLookup(request):
  """Handles wikidpage look up for the AJAX widget."""

  debugOutput("Handling page lookup")
  wikidbase.core.security.barrier(request.user.username, "view")

  try :
    searchString = request.REQUEST["searchString"]
  except :
    searchString = None

  # Get matching contexts and wikidpages.
  if searchString :
    contexts, wikidpages = wikidbase.core.query.pageLookup(searchString)
  else :
    contexts, wikidpages = []
  
  response = ""
 
  # Render the context list items.
  for context in contexts :
    response += """<li id="%s">Create <b>new</b> %s</li>\n""" % (wikidbase.core.normaliseTerm(context), context)
  
  # If there are not too many matches, render the wikidpage list items.
  pagesAdded = 0
  for wikidpage in wikidpages :

    if not wikidpage.context :
      continue
    
    description = ""
    wikidpageFields = wikidpage.getFields().getDict()
    for nFieldName in wikidpageFields :
      field = wikidpageFields[nFieldName]
      if not wikidbase.core.pagecontent.isDataField(field):
        continue

      if field.data and len(description) < 80:
        try : 
          if len(field.data) > 50 or field.data.contains("\n") :
            continue
        except :
          pass
        description += "<b>%s</b>:%s " % (field.name, field.data)

    # Don't list non-fielded pages.
    if not description :
      continue
    
    description = "[<b>%s</b>] %s" % (wikidpage.context, description)
    response += """<li id="%s">%s</li>\n""" % (wikidpage.id, description)
    pagesAdded += 1
    if pagesAdded > 6 :
      break

  response = "<ul>%s</ul>" % response
  debugOutput("AJAX response: %s" % response)
  return django.http.HttpResponse(response)


def foreignlinkLookup(request) :
  """Handles foreign link field lookup for a wikidpage or a context (e.g. what relations can an animal have, etc.)
  If I'm adding a link from, say, a staff member (LP) to an animial (TP), for a local link name 'pet', then I want to:
  * Get the context of staff
  * Look up common targets for the pet field (e.g. owner) add to results
  * Look up other possible links for an animal

  So, I need a local page and foregin page and a local link.
  
  """

  relationalFields = []
  wikidbase.core.security.barrier(request.user.username, "view")

  debugOutput("Handling foreign link lookup")

  try : localContextName = request.GET["localPageContext"]
  except : localContextName = None
 
  if not localContextName :
    return JsonResponse([])

  # Try to get the normalised term for the local link field (e.g. the outgoing link field of the page).
  try : nLocalField = wikidbase.core.normaliseTerm(request.REQUEST["localLinkField"])
  except : nLocalField = None
  
  # Try to get a wikidpage and/or a context name.
  if "targetPageID" in request.GET :
    try :
      targetWikidpage = wikidbase.core.pagestore.getWikidpage(int(request.REQUEST["targetPageID"]))
      targetContextName = targetWikidpage.context
    except :
      targetContextName = request.REQUEST["targetPageID"]

  debugOutput("localContextName %s nLocalField %s targetContextName %s" % (localContextName, nLocalField, targetContextName))

  #
  # Now we use the defined relationships
  #

  debugOutput("Looking for common links from %s-%s to %s" % (localContextName, nLocalField, targetContextName))
  relationalFields = []
  nContext = wikidbase.core.context.normaliseTerm(localContextName)
  relationships = wikidbase.core.context.getContextRelationships(nContext)
  debugOutput("relationships: %s" % relationships)

  # Now find the matching foriegn relationships.
  for relationship in relationships :
    nRel = wikidbase.core.context.normaliseTerm(relationship)
    if nRel == nLocalField :
      relationalFields += relationships[relationship]
      

  #
  # Old way
  #

  # XXX
  if False and localContextName :
    debugOutput("Looking for common links from %s-%s to %s" % (localContextName, nLocalField, targetContextName))

    commonTargets = []
    targetContext = wikidbase.core.context.getContexts()[wikidbase.core.normaliseTerm(targetContextName)]
    targetContextRelFields = [targetContext.linkContexts[nLinkName].nameVariations.getMostCommon().capitalize() for nLinkName in targetContext.linkContexts]

    if localContextName and nLocalField :
      
      # Get the local wikidpage's context.
      localContext = wikidbase.core.context.getContexts()[wikidbase.core.context.normaliseTerm(localContextName)]
      
      # Get the context of the local link.
      localLinkContext = nLocalField in localContext.linkContexts and localContext.linkContexts[nLocalField] or None
      if localLinkContext :
        
        # First add common targets.
        for nCommonTarget in localLinkContext.commonTargets :
          commonTargets.append(localLinkContext.commonTargets[nCommonTarget].getMostCommon().capitalize())
  
    # Now merge the items.
    for commonTarget in commonTargets :
      relationalFields.append(commonTarget)

    for relField in targetContextRelFields :
      if wikidbase.core.context.normaliseTerm(relField) not in [wikidbase.core.context.normaliseTerm(fieldName) for fieldName in relationalFields] :
        relationalFields.append(relField)

    debugOutput("targetContextRelFields %s, commonTargets %s, relationalFields %s" % (targetContextRelFields, commonTargets, relationalFields))

  return JsonResponse(relationalFields)




 #
 # Some useful classes and functions for views.
 #
 
class ResponseException(Exception) :
  """Allows us to throw HttpResponses, which is very handy for returning from nested function views."""
  def __init__(self, response) : self.response = response
  def __str__(self) : return "ResponseException %s" % self.response


class JsonResponse(django.http.HttpResponse):
  """Creates a JSON response from a python object."""
  def __init__(self, obj):
    self.original_obj = obj
    django.http.HttpResponse.__init__(self, self.serialize())
    self["Content-Type"] = "text/javascript"

  def serialize(self):
    return(django.utils.simplejson.dumps(self.original_obj))


# TODO: Perhaps move this to control panel.
def configField(request, context, fieldName):
  """Explicitly configure a field's widget."""
  
  wikidbase.core.security.barrier(request.user.username, "wiki-edit")
  # Load the context state.
  nContext = wikidbase.core.context.normaliseTerm(context)
  nFieldName = wikidbase.core.context.normaliseTerm(fieldName)
  contextFieldState = wikidbase.core.state.getContextFieldState(nContext, nFieldName)
  
 
  # Set up the choices.
  widgetChoices = [
    (wikidbase.core.context.AUTO_WIDGET, "Auto field"),
    (wikidbase.core.context.TEXTAREA, "Text area"),
    (wikidbase.core.context.SS_LIST, "Single-select List"),
    (wikidbase.core.context.MS_LIST, "Multiple-select List"),
  ]
  
  # Set up sort choices.
  sortChoices = [
    (wikidbase.core.context.SORT_MOST_COMMON, "Most common options first"),
    (wikidbase.core.context.SORT_ASCEND, "Sort ascending"),
    (wikidbase.core.context.SORT_DESCEND, "Sort Descending"),
  ]

  if request.POST : 
    fieldConfigForm = wikidbase.core.widgets.FieldConfigForm(widgetChoices, sortChoices, request.POST)
    if fieldConfigForm.is_valid() :
      debugOutput("Saving data")
      contextFieldState[wikidbase.core.context.LIST_STYLE] = fieldConfigForm.clean_data["field_type"]
      contextFieldState[wikidbase.core.context.LIST_SORT] = fieldConfigForm.clean_data["list_sort"]
      contextFieldState[wikidbase.core.context.LIST_CHOICES] = fieldConfigForm.clean_data["list_values"]
      wikidbase.core.state.setContextFieldState(nContext, nFieldName, contextFieldState)
      
      # return to wikidpage.
      return django.http.HttpResponseRedirect(getPreviousPage(request))
  

  else :
    initial = {
      "field_type":wikidbase.core.context.LIST_STYLE in contextFieldState and contextFieldState[wikidbase.core.context.LIST_STYLE] or wikidbase.core.context.AUTO_WIDGET,
      "list_values":wikidbase.core.context.LIST_CHOICES in contextFieldState and contextFieldState[wikidbase.core.context.LIST_CHOICES] or "",
      "list_sort":wikidbase.core.context.LIST_SORT in contextFieldState and contextFieldState[wikidbase.core.context.LIST_SORT] or wikidbase.core.context.SORT_MOST_COMMON,
    }
    
    fieldConfigForm = wikidbase.core.widgets.FieldConfigForm(widgetChoices, sortChoices, initial=initial)
  context = {
    "fieldConfigForm" : fieldConfigForm,
  }
  return django.shortcuts.render_to_response("fieldconfig.html", django.template.RequestContext(request, context))


def redirect(request, dest) :
  """View that simply redirects the user - used to work around some django stuff."""
  return django.http.HttpResponseRedirect(dest)
