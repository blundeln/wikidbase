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
# performance (performance.py)
# ----------------------------
#
# Description:
#
#
# Author       : Nick Blundell
# Organisation : www.nickblundell.org.uk
# Version Info : $Id$
#

import time

from nbdebug import *

timerReported = False

timings = {}

class GlobalTimer: 

  def __init__(self) :
    self.reset()

  def addDuration(self, message, duration, key) :
    if key not in self.timerData :
      self.timerData[key] = 0
    self.timerData[key] += duration
    debugOutput("%s took %.4f seconds." % (message, duration))

  def reset(self) :
    self.timerData = {}

  def report(self) :
    debugOutput("Creating report.")
    for item in self.timerData :
      debugOutput("%s: %.4f" % (item, self.timerData[item]))

  def __del__(self) :
    #self.report()
    pass


class Timer(object):
  
  def __init__(self, func):
    self.func = func
  
  def __call__(self, *args, **kwds):
    message = "%s" % (self.func.__name__)
    key = self.func.__name__
    startTimer(message, key)
    value = self.func(*args, **kwds)
    stopTimer(key)
    return value



#def startTimer(message, key=None) :
#  key = key or message
#  return [time.time(), message, key]

#def stopTimer(t) :
#  message, duration, key = t[1], time.time() - t[0], t[2]
#  debugOutput("%s %s %s" % (message, duration, key))
#  globalTimer.addDuration(message, duration, key)

def startTimer(message, key=None) :
  global timings
  key = key or message
  if key not in timings :
    timings[key] = [message, time.time(), 0]
  else :
    timings[key][1] = time.time()
  

def stopTimer(key) :
  global timings
  duration = time.time() - timings[key][1]
  timings[key][2] += duration
  debugOutput("%s took %.4f seconds (total %.4f)." % (timings[key][0], duration, timings[key][2]))

def timerReset() :
  global timings
  timings = {}

def timerReport() :
  global timings
  debugOutput("Timing report\n\n")
  for key in timings :
    debugOutput("%s took %.4f seconds." % (timings[key][0], timings[key][2]))
    


globalTimer = GlobalTimer()
