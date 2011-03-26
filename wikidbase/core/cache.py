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
# cache (cache.py)
# ----------------
#
# Description:
#
#
# Author       : Nick Blundell
# Organisation : www.nickblundell.org.uk
# Version Info : $Id$
#

import cPickle

import django.db
from django.core import cache as djangocache

import wikidbase.core.performance

from nbdebug import *

CACHE_SECONDS = 60 * 20

USE_BENCHMARK_CACHE = False
testCache = {}

@wikidbase.core.performance.Timer
def cacheGet(key) :
  if USE_BENCHMARK_CACHE :
    if key in testCache :
      return testCache[key]
    else :
      return None
  else :
    return djangocache.cache.get(key)

@wikidbase.core.performance.Timer
def cacheSet(key, value, timeout) :
  if USE_BENCHMARK_CACHE :
    testCache[key] = value
  else :
    djangocache.cache.set(key, value, timeout)

def cacheDelete(key) :
  djangocache.cache.delete(key)
  

def djangoCacheFunction(function, argsKey, value=None) :
  
  cacheKeys = (function.__name__, argsKey)
 
  cacheKey = "-".join(cacheKeys)
  if value != None :
    cacheSet(cacheKey, value, CACHE_SECONDS)
  else :
    return cacheGet(cacheKey)

  return

  #XXX: OLD

  # Get the function entry
  functionEntry = cacheGet(cacheKeys[0])

  if value != None :
    debugOutput("Caching: %s %s %s" % (function, argsKey, value))
    if not functionEntry :
      functionEntry = {}
    functionEntry[cacheKeys[1]] = value
    cacheSet(cacheKeys[0], functionEntry, CACHE_SECONDS)
  else :
    debugOutput("Looking for entry: %s %s %s" % (function, argsKey, value))
    try :
      value = functionEntry[cacheKeys[1]]
    except :
      value = None

    if value :
      debugOutput("Found entry")
    else :
      debugOutput("Not found entry")
    
    return value

def getCacheKeys() :
  if hasattr(djangocache.cache, "_table") :
    debugOutput("this is db cache")
    cursor = django.db.connection.cursor()
    cursor.execute("SELECT cache_key FROM %s" % djangocache.cache._table)
    rows = cursor.fetchall()
    return [row[0] for row in rows]
  elif hasattr(djangocache.cache, "_cache") :
    return djangocache.cache._cache.keys()
  else :
    raise Exception("Whooops! Currently can only clear cache with db cache backend!")
  

def djangoClearCache(function) :
  
  if function :
    debugOutput("Clearing cache %s" % function)

    cacheKeys = getCacheKeys()
    debugOutput("cacheKeys %s" % cacheKeys)
    for cacheKey in cacheKeys :
      if cacheKey.startswith(function.__name__) :
        debugOutput("deleting %s" % cacheKey)
        cacheDelete(cacheKey)
  

class memoize(object):
  
  def __init__(self, func):
    self.func = func
    self.clearCache()
  
  def clearCache(self) :
    djangoClearCache(self.func)
  
  def __call__(self, *args, **kwds):
    # Create a key.
    t = (args, kwds.items())
    try:
      hash(t)
      key = t
    except TypeError:
      try :
        key = cPickle.dumps(t)
      except cPickle.PicklingError:
        return func(*args, **kwds)
    
    # Try to get a value from the cache
    cachedValue = djangoCacheFunction(self.func, key)
    
    if not cachedValue :
      debugOutput("Computing function for '%s'" % str(t))
      value = self.func(*args, **kwds)
      djangoCacheFunction(self.func, key, value)
    else :
      debugOutput("Using cached result for '%s'" % str(t))
      value = cachedValue
    return value


def clearAllCaches() :
  """Clears all caches"""
  import wikidbase.core.context
  import wikidbase.core.query
  debugOutput("Clearing caches")
  wikidbase.core.context.getContexts.clearCache()
  wikidbase.core.query.runQuery.clearCache()
