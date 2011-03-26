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
# tests (tests.py)
# ----------------
#
# Description:
#
#
# Author       : Nick Blundell
# Organisation : www.nickblundell.org.uk
# Version Info : $Id$
#

from wikidbase.core import pagestore
from wikidbase.core.context import normaliseTerm
import wikidbase.core.performance
import wikidbase
import unittest
import random
import time

random.seed("test")

from nbdebug import *

NO_PAGES = 2500
LINKAGE_DENSITY = 0.4

# TODO:
# Load some test pages
# * Random pages
# * Test contexts
# Test field-ed page
# * Flex field types.

class BasicWikidpageTests(unittest.TestCase) :
  def setUp(self) :
    pass

  def testCreateWikidpage(self):
    # Create a new page.
    newWikidpage = pagestore.getNewPage(name="New page")
    newWikidpage.save()
    self.assert_(newWikidpage.name == "New page")
    
    # Try to create a page with the same name.
    newWikidpage = pagestore.getNewPage(name="New page")
    self.assertRaises(Exception, newWikidpage.save)
  
  def tearDown(self) :
    pass


class BenchmarkingTests(unittest.TestCase) :

  def test1ContextEfficiency(self) :

    noPages = NO_PAGES
    noLinks = int(LINKAGE_DENSITY * noPages)
    ids = []

    for i in range(0, noPages) :
      # Create a page with random data.
      wikidpage = createWikidpage(name=randomString(), content=PERSON_TEMPLATE, type="person")
      
      # Randomise some of the fields
      fields = wikidpage.getFields()
      fields.getField("Name").data = randomString()
      fields.getField("Title").data = randomString()
      fields.getField("DOB").data = randomDate()
      wikidpage.save()
      ids.append(wikidpage.id)

    print "ids length = %s" % len(ids)

    # Now add some random links.
    for i in range(0,noLinks) :
      try :
        wikidbase.core.pagestore.addLink(random.choice(ids), random.choice(ids), "linkA","linkB")
      except :
        pass

    # Reset the timer after adding stuff.
    wikidbase.core.performance.globalTimer.reset()

    # How long to build context
    timer = startTimer("Building pages=%s links=%s context" % (noPages, noLinks))
    wikidbase.core.context.getContexts()
    stopTimer(timer)
    
    query = """show me all people """
    timer = startTimer("Running query '%s' pages=%s links=%s context" % (query, noPages, noLinks))
    wikidbase.core.query.runQuery(query)
    stopTimer(timer)

    query = """show me all people """
    timer = startTimer("Running query '%s' pages=%s links=%s context" % (query, noPages, noLinks))
    wikidbase.core.query.runQuery(query)
    stopTimer(timer)

    query = """show me all people linkA.name = "fred" """
    timer = startTimer("Running query '%s' pages=%s links=%s context" % (query, noPages, noLinks))
    wikidbase.core.query.runQuery(query)
    stopTimer(timer)
    
    query = """show me all people linkA.name = "fred" and linkB.name = "hello" """
    timer = startTimer("Running query '%s' pages=%s links=%s context" % (query, noPages, noLinks))
    wikidbase.core.query.runQuery(query)
    stopTimer(timer)

    query = """show me all people linkA.name = "fred" and linkB.name = "hello" """
    timer = startTimer("Running query '%s' pages=%s links=%s context" % (query, noPages, noLinks))
    wikidbase.core.query.runQuery(query)
    stopTimer(timer)




class MoreTests(unittest.TestCase) :
  def setUp(self) :
    pass

  def testCreateWikidpage(self):
    # Create a new page.
    pass
  
  def tearDown(self) :
    pass



# Helper functions.

def createWikidpage(name, content, type=None) :
  newWikidpage = pagestore.getNewPage(name=name)
  newWikidpage.content = content
  if type :
    newWikidpage.context = type
  newWikidpage.save()
  return newWikidpage


def startTimer(message) :
  return [message, time.time()]

def stopTimer(timer) :
  print("%s took %s seconds." % (timer[0], time.time() - timer[1]))

def randomString() :
  length = random.randint(10, 20)
  randomString = ""
  for i in range(0, length) :
    randomString += random.choice("abcdefghajklmnop")
  return randomString

def randomDate() :
  return "%s/%s/%s" % (random.randint(1,28), random.randint(1,12), random.randint(1910, 2007))

#
# Strings and constants.
#

PERSON_TEMPLATE = """
Title[]:: Mr
Name::Fred
Surname:: Jones
Address::{
123 The House,
The Street,
The Town
}
DOB:: 31/5/1980
Postcode::CV1 1EA
Telephone::1234 56678
Email::fred.jones@somewhere.co.uk
""" 
