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
# run-tests (run-tests.py)
# ------------------------
#
# Description:
#
#
# Author       : Nick Blundell
# Organisation : www.nickblundell.org.uk
# Version Info : $Id$
#

import os, unittest, time, sys, optparse
import nbutil.unittesttools
import seleniumtest
from nbdebug import *

# Setup command line options.
argParser = optparse.OptionParser()
argParser.add_option("--selenium", action="store_true", help="", dest="runSeleniumTests", default=False)
argParser.add_option("--twill", action="store_true", help="", dest="runTwillTests", default=False)
argParser.add_option("--internal", action="store_true", help="", dest="runInternalTests", default=False)
argParser.add_option("--manual", action="store_true", help="", dest="runManualTests", default=False)
argParser.add_option("--list", action="store_true", help="", dest="listTests", default=False)
argParser.add_option("--clear-data", action="store_true", help="", dest="clearData", default=False)

# Parse the command-line args.
(options, args) = argParser.parse_args()


SOURCE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__),".."))
#SELENIUM_PATH = "/home/blundeln/work/selenium/selenium-remote-control-0.9.1-SNAPSHOT/server/selenium-server.jar"
#SELENIUM_PATH = "/home/blundeln/work/selenium/selenium-remote-control-0.9.2-SNAPSHOT/selenium-server-0.9.2-SNAPSHOT/selenium-server.jar"
#SELENIUM_PATH = "/home/blundeln/Desktop/Resources/apps/selenium/selenium-remote-control-1.0-beta-1/selenium-server-1.0-beta-1/selenium-server.jar -multiWindow"
SELENIUM_PATH = "/home/blundeln/Desktop/Resources/apps/selenium/selenium-remote-control-1.0-beta-2/selenium-server-1.0-beta-2/selenium-server.jar -multiWindow"
SELENIUM_SETUP_DELAY = 1

SUPERUSER_CODE = """
from django.contrib.auth.create_superuser import createsuperuser
createsuperuser('admin','admin@admin.com','admin')
exit
"""

def runCommand(command) :
  debugOutput(command)
  os.system(command)



def runDjangoTests() :
  debugOutput("Running Django tests")
  DB_FILE = "/tmp/wbdjangotestdb"
  PIPE_OUT = " > /dev/null 2>&1 "
  MANAGE_FILE = os.path.join(SOURCE_PATH, "wikidbase","manage.py")
  runCommand("rm -rf '%s'" % DB_FILE)
  runCommand("""TESTDB="%s" python %s createcachetable wbcache --noinput %s""" % (DB_FILE,MANAGE_FILE,PIPE_OUT))
  runCommand("""TESTDB="%s" python %s test""" % (DB_FILE, MANAGE_FILE))


def launchTestServer(port, clearData=False) :
  "Run the app in a testing server"
  d("Launching test server on port %s" % port)
  
  DB_FILE = "/home/blundeln/wbdjangotestdb"
  PIPE_OUT = " > /dev/null 2>&1 "
  #PIPE_OUT = " "

  # TODO: This also needs to happen the first time test is run
  # Clear the data.
  if clearData or not os.path.exists(DB_FILE) :
    runCommand("rm -rf '%s'" % DB_FILE)
    runCommand("""TESTDB="%s" python wikidbase/manage.py createcachetable wbcache --noinput %s""" % (DB_FILE,PIPE_OUT))
    runCommand("""TESTDB="%s" python wikidbase/manage.py syncdb --noinput %s""" % (DB_FILE,PIPE_OUT))
    runCommand("""echo "%s" | TESTDB="%s" python wikidbase/manage.py shell %s""" % (SUPERUSER_CODE,DB_FILE, PIPE_OUT))# > /dev/null 2>&1 &""")
  
  # Launch django server
  runCommand("""TESTDB="%s" python wikidbase/manage.py runserver 0.0.0.0:%s %s &""" % (DB_FILE, port, PIPE_OUT))

  # Give it chance to boot.
  time.sleep(2)


def killTestServer(port) :
  # Kill django server
  d("Killing test server on port %s" % port)
  runCommand("""pkill -f "wikidbase/manage.py runserver 0.0.0.0:%s" """ % port)


def runManualTests() :
  """This just runs the test server so we can inspect the app in a browser"""
  
  PORT = 8085

  # Launch the test server
  launchTestServer(PORT, options.clearData)

  raw_input("Press any key to terminate the test server") 

  # Kill the test server
  killTestServer(PORT)



def runTwillTests() :
  debugOutput("Running tests")
  import twill_tests
  
  try :
    testSequence = nbutil.unittesttools.parseTestSequence(args[0])
  except :
    testSequence = None
 
  # Set test parameters
  twill_tests.HOST = "localhost"
  twill_tests.PORT = 8081

  # Launch the test server
  launchTestServer(twill_tests.PORT, options.clearData)

  testSuite = nbutil.unittesttools.loadFileOrderedTests(twill_tests, testSequence=testSequence, listTests=options.listTests)
  debugOutput(testSuite)
  unittest.TextTestRunner(verbosity=3).run(testSuite)

  # Kill the test server
  killTestServer(twill_tests.PORT)

def runSeleniumTests() :
  debugOutput("Running tests")
  
  try :
    testSequence = nbutil.unittesttools.parseTestSequence(args[0])
  except :
    testSequence = None
  testSuite = nbutil.unittesttools.loadFileOrderedTests(seleniumtest, testSequence=testSequence, listTests=options.listTests)
  nbutil.unittesttools.filterTests(testSuite, args)
  debugOutput(testSuite)

  
  # Launch selenium
  runCommand("""PATH=$PATH:/usr/lib/firefox java -jar %s > /dev/null 2>&1 &""" % SELENIUM_PATH)
  time.sleep(SELENIUM_SETUP_DELAY)
 
  # Launch the test server
  launchTestServer(seleniumtest.TEST_PORT, options.clearData)

  # Run the tests
  unittest.TextTestRunner(verbosity=3).run(testSuite)
  
  #time.sleep(10)
  # Kill django server
  killTestServer(seleniumtest.TEST_PORT)

  # Kill selenium
  runCommand("""pkill -f "selenium-server.jar" """)
  

def runTests() :
  from django.conf import settings
  debugOutput("Running tests.")
 
  # If we're logging the results, it's useful to record the date and time
  os.system("date")

  runAllTests = not (options.runSeleniumTests or options.runInternalTests or options.runTwillTests or options.runManualTests)
  
  if runAllTests or options.runManualTests :
    runManualTests()
  
  if runAllTests or options.runTwillTests :
    runTwillTests()
  
  if runAllTests or options.runSeleniumTests :
    print "Running selenium tests"
    runSeleniumTests()
  
  if runAllTests or options.runInternalTests :
    print "Running internal tests"
    runDjangoTests()

if __name__=="__main__" :
  runTests()
