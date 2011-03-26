#
# Copyright (C) 2009 Nick Blundell.
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
# twill_tests (twill_tests.py)
# ----------------------------
#
# Description:
#
#
# Author       : Nick Blundell
# Organisation : www.nickblundell.org.uk
# Version Info : $Id$
#

import unittest, time, re, os
import twill
from twill.commands import fv, redirect_output, follow

from nbdebug import *

# These are set by the test runner
HOST = None
PORT = None

# Globals
browser = None

class TestBase(unittest.TestCase):
  """Class for common test functionality"""
  
  def assertInSource(self, text):
    self.assertTrue(text in html())


class LoginTests(TestBase) :

  def testLogin(self):
    self.assertTrue("you are not authorised" in openPage("/"))

    openPage("/accounts/login")
    field_input("username","admin")
    field_input("password","admin")
    browser.submit("login")
    
    self.assertTrue("you are not authorised" not in openPage("/"))

class BasicPageTests(TestBase) :
  
  def testCreatePage(self) :
    createPage(name="My first wikidpage", content="""
Title
-----
This is my first page.

* Point 1
* Point 2
* Point 3

http://www.somesite.com
""")
    self.assertInSource("The page has been")
    self.assertInSource("created")
    self.assertInSource("saved")
    
    # Check rest formatting.
    self.assertInSource("""<h1 class="title">Title</h1>""")
    self.assertInSource("<li>Point 2</li>")
  
  def testEditPage(self) :
    openPage("/MyFirstWikidpage")
    click("Edit")
    #content = sel.get_value("id_content")
    #content = content.replace("Point 2","Point 8")
    #content = sel.type("id_content",content)
    #sel.submit("wikidpage")
    #wait()
    #self.assertInSource("<li>Point 8</li>")

 
  def xtestCreateExistingPage(self) :
    createPage(name="My first wikidpage", content="Blah")
    self.assertInSource("this name already exists")

  def xtestDeletePage(self) :
    openPage("/My first wikidpage")
    sel.click("delete")
    wait()
    self.assertInSource("Are you sure you wish to delete this")
    sel.click("Delete")
    wait()
    self.assertInSource("has been deleted")
    openPage("/My first wikidpage")
    pause()
    self.assertInSource("Page not found")




#
# Helper functions
#


def openPage(page) :
  global browser
  if not browser :
    browser = twill.get_browser()
    redirect_output("/dev/null")
  
  browser.go("http://localhost:%s%s" % (PORT, page))
  return browser.get_html()

def html() :
  return browser.get_html()

def click(link) :
  follow(link)

def field_input(field, value, form=1):
  fv(form, field, value)

def submit(formName=1) :
  browser.submit(formName)

def createPage(name, content, type=None) :
  openPage("/EDIT/CREATE")
  field_input("name", name, 2)
  field_input("id_content", content, 2)
  if type :
    field_input("id_context", type, 2)
  submit("save")
