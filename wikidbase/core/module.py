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
# module (module.py)
# ------------------
#
# Description:
#
#
# Author       : Nick Blundell
# Organisation : www.nickblundell.org.uk
# Version Info : $Id$
#

# TODO: Tracebacks on command errors.
#       Modules should be able to define template folders and media directories
# Modules should decare: resources (e.g. files) templates, and logic.

import sys
import os
import wikidbase

import django.conf
from django.template import TemplateDoesNotExist

from nbdebug import *

CONTRIB_PATH = os.path.join(wikidbase.getCodeRoot(), "contrib")

# Global list of module info.
modulesInfo = []

class ModuleInfo() :
  def __init__(self, name, version, description, dependencies=None, author=None) :
    """Holds information about a wikidbase module."""
    self.name, self.version, self.description, self.dependencies, self.author = name, version, description, dependencies, author
    self.exposedFunctions = []
    self.path = None
    self.moduleName = None

  def addExposedFunction(self, function) :
    if function not in self.exposedFunctions :
      self.exposedFunctions.append(function)

  def __str__(self) :
    return """Module %s: '%s' (v%s) (by %s): %s\nFunctions: %s""" % (self.moduleName, self.name, self.version, self.author, self.description, str(self.exposedFunctions))


class CallParser:
  def __init__(self, callString) :
    debugOutput("Creating with '%s'" % callString)
    self.moduleName, self.functionName, self.functionCall = self._parseCall(callString)

  def _parseCall(self, callString) :
    debugOutput("Parsing '%s'" % callString)
    callString = callString.strip()
    functionCall = callString
    moduleName = callString.split(".")[0]
    functionName = callString.replace("%s." % moduleName,"")
    functionName = functionName[0:functionName.find("(")]
    return moduleName, functionName, functionCall

  def __str__(self) :
    return "%s %s %s" % (self.moduleName, self.functionName, self.functionCall)


def command(func) :
  """This is a decorator that a user may use to declare wikidbase command functions in their modules."""
  def newfunc(*arg, **argv) :
    return func(*arg, **argv)
  newfunc._exposed = True
  return newfunc


def getModulesInfo() :
  global modulesInfo

  if not modulesInfo :
    modulesInfo = buildModulesInfo()

  return modulesInfo

def buildModulesInfo() :

  modulesInfo = {}
  importPaths = [CONTRIB_PATH]
  # Get paths from the user's settings file.
  for path in django.conf.settings.MODULE_PATHS :
    importPaths.append(path)

  debugOutput("Loading module info from paths: %s" % str(importPaths))

  for importPath in importPaths :
    debugOutput("Looking in importPath %s" % str(importPath))
    moduleList = searchForModules(importPath)
    debugOutput("moduleList %s" % str(moduleList))
    if importPath not in sys.path :
      sys.path.append(importPath)

    for module in moduleList :
      mod = __import__(module)
      try :
        info = mod.hookInfo()
      except Exception, e:
        debugOutput("The module '%s' had no info modulesInfo function: %s" % (module, e))
        continue
      info.path = importPath
      info.file = mod.__file__
      if "__init__" in info.file :
        info.dir = os.path.dirname(info.file)
      else :
        info.dir = None
      info.moduleName = module
      info.mod = mod
      debugOutput("ModuleInfo %s" % info)
      modulesInfo[module] = info
    
  return modulesInfo

def runModuleCallString(request, commandString) :
  # Get the 
  modulesInfo = getModulesInfo()
  call = CallParser(commandString)
  debugOutput(str(call))

  # Check the module exists
  if call.moduleName not in modulesInfo :
    return "<div class='system-message'>There is no plugin module called '%s'</div>" % call.moduleName
  #Check the function is an exposed one
  moduleInfo = modulesInfo[call.moduleName]
  
  try :
    func = getModuleFunction(call.moduleName, call.functionName)
  except :
    return "<div class='system-message'>There is no command function called '%s' in the plug-in module '%s'</div>" % (call.functionName, call.moduleName)
    

  if not (hasattr(func, "_exposed") and func._exposed) :
    return "<div class='system-message'>The function '%s' has not been exposed by the plug-in module '%s'</div>" % (call.functionName, call.moduleName)

  # TODO: This allows arbitrary python code to be run so must be restricted.
  globs = globals()
  globs[call.moduleName] = __import__(call.moduleName)
  return eval(call.functionCall, globs)


def getModuleFunction(moduleName, functionName) :
  modulesInfo = getModulesInfo()
  if moduleName not in modulesInfo :
    raise Exception("Can't find plugin module %s" % moduleName)

  mod = __import__(moduleName)
  return mod.__dict__[functionName]


def runModuleFunction(moduleName, functionName, *args, **kargs) :
  """Run a module function with the specified args."""

  debugOutput("Running module function %s %s %s %s" % (moduleName, functionName, args, kargs))
  func = getModuleFunction(moduleName, functionName)

  if not (hasattr(func, "_exposed") and func._exposed) :
    raise Exception("The function has not been exposed by the module: %s" % call.functionName)

  result = func(*args, **kargs)
  debugOutput("result: %s" % result)
  return result


def searchForModules(searchPath) :
  """Returns a list of modules in the specified path."""
  modules = []
  if not os.path.exists(searchPath) :
    return modules
  for item in os.listdir(searchPath) :
    debugOutput("item '%s'" % item)
    itemPath = os.path.join(searchPath, item)
    if item.endswith(".py") :
      modules.append(item.replace(".py",""))
    elif os.path.isdir(itemPath) and "__init__.py" in os.listdir(itemPath) :
      modules.append(item)
  return modules

def getModuleDir(moduleName, *args) :
  """Gets the path to media files of a module. args are subdirectories."""
  modulesInfo = getModulesInfo()
  if moduleName not in modulesInfo :
    return None
  
  moduleInfo = modulesInfo[moduleName]
  if not moduleInfo.dir :
    return None
  
  mediaPath = os.path.join(moduleInfo.dir, *args)
  if os.path.exists(mediaPath) :
    return mediaPath
  
  return None

  

def loadModuleTemplate(template_name, template_dirs=None):
  """Allows django to load templates from wikidbase plugins"""
  
  # For each module, see if it has a templates dir and see if template is in there.
  modulesInfo = getModulesInfo()
  for moduleName in modulesInfo :
    moduleInfo = modulesInfo[moduleName]
    if not moduleInfo.dir :
      continue
    templatePath = os.path.join(moduleInfo.dir, "templates", template_name)
    debugOutput(templatePath)
    if not os.path.exists(templatePath) :
      continue

    return (open(templatePath,"r").read(), templatePath)

  raise TemplateDoesNotExist, template_name
loadModuleTemplate.is_usable = True


#
# Module hooks
#

def getHook(mod, hookName) :
  if hookName in dir(mod) :
    return mod.__dict__[hookName]
  else :
    return None
 
def getHookList(hookName) :
  """Gets a list of module hook functions with the specified name."""
  # TODO: Perhaps modules can define a hook priority/weight, which these will be sorted by.
  hooks = []
  modulesInfo = getModulesInfo()
  for moduleName in modulesInfo :
    mod = modulesInfo[moduleName].mod
    hook = getHook(mod, hookName)
    if hook :
      hooks.append(hook)
  return hooks

def callAllHooks(hookName, *args, **kargs) :
  results = ()
  modulesInfo = getModulesInfo()
  for hook in getHookList(hookName) :
    results += hook(*args, **kargs)
  return results

def hookMainMenu(context, menuLinks) :
  hooks = getHookList("hookMainMenu")
  for hook in hooks :
    menuLinks = hook(context, menuLinks)

  return menuLinks
  

def hookDefinePermissions(permissions) :
  # Pass the permissions data structure through all hooks
  hooks = getHookList("hookDefinePermissions")
  for hook in hooks :
    permissions = hook(permissions)

  return permissions
  

def hookURLs() :
  # Build a list of urls for each module.
  urls = callAllHooks("hookURLs")
  return urls

#def register media
#  # For each module,
