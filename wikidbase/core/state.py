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
# state (state.py)
# ----------------
#
# Description:
#
#
# Author       : Nick Blundell
# Organisation : www.nickblundell.org.uk
# Version Info : $Id$
#

ITEM_SORT = "ITEM_SORT"
STATE_PAGE = "STATE_PAGE"
STATE_VIEW = "STATE_VIEW"

USER_STATE = "USER_STATE"

CONTEXT_STATE = "CONTEXT_STATE"

from nbdebug import *
import wikidbase

# TODO: Can we make this more flexible and general, like drupal set/get_variable.
#       Should not have specifici functions for users/etc, state should be an API for modules and core object storage.

#
# User state
#

def generateStateKey(stateType, stateSource, item) :
  
  return (stateType, stateSource, item)
  
def getItem(request, stateType, stateSource, item) :

  if not stateSource :
    return None

  stateKey = generateStateKey(stateType, stateSource, item)
  
  # Get the user's state
  userState = getUserState(request.user.username)

  if stateKey not in userState :
    return None
  else :
    return userState[stateKey]

def setItem(request, stateType, stateSource, item, data) :
  
  if not stateSource :
    return

  stateKey = generateStateKey(stateType, stateSource, item)
  
  # Get the user's state
  userState = getUserState(request.user.username)
  userState[stateKey] = data
  setUserState(request.user.username, userState)


# TODO: replace these with simple string keys in global state, is much more flexible.
def getUserState(user) :
  globalState = getGlobalState()
  try :
    return globalState[USER_STATE][user]
  except :
    return {}

def setUserState(user, userState) :
  
  # Get user session dict.
  globalState = getGlobalState()
  if USER_STATE not in globalState :
    globalState[USER_STATE] = {}
  
  globalState[USER_STATE][user] = userState

  setGlobalState(globalState)


def getContextState(nContext) :
  globalState = getGlobalState()
  try :
    return globalState[CONTEXT_STATE][nContext]
  except :
    return {}
  
def setContextState(nContext, contextState) :
  
  # Get contextState dict.
  globalState = getGlobalState()
  if CONTEXT_STATE not in globalState :
    globalState[CONTEXT_STATE] = {}
  
  globalState[CONTEXT_STATE][nContext] = contextState

  setGlobalState(globalState)


def getContextFieldState(nContext, nFieldname) :
  contextState = getContextState(nContext)
  try :
    return contextState[nFieldname]
  except :
    return {}

def setContextFieldState(nContext, nFieldname, fieldState) :
  contextState = getContextState(nContext)
  contextState[nFieldname] = fieldState
  setContextState(nContext, contextState)
 

def getVariable(variableKey, defaultValue=None) :
  globalState = getGlobalState()
  if variableKey not in globalState :
    return defaultValue
  # TODO: would be good only to load global state when we know it has changed.
  return globalState[variableKey]
 

def setVariable(variableKey, newValue) :
  """Set a variable.  A value of None will unset the variable."""
  globalState = getGlobalState()
  if newValue == None and variableKey in globalState :
    del globalState[variableKey]
  else :
    globalState[variableKey] = newValue
  setGlobalState(globalState)

#
# Global state
#

def getGlobalState() :
  
  # Try to get the state.
  try :
    globalState = wikidbase.core.models.GlobalState.objects.get(stateName="GS-1")
  except :
    globalState = wikidbase.core.models.GlobalState(stateName="GS-1")
    globalState.setState({})
    globalState.save()
 
  debugOutput("state: %s" % globalState.getState())

  return globalState.getState()


def setGlobalState(state) :
  globalState = wikidbase.core.models.GlobalState.objects.get(stateName="GS-1")
  globalState.setState(state)
  globalState.save()
