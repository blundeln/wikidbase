#
# Copyright (C) 2006-2008 Nick Blundell.
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
# seleniumtest (seleniumtest.py)
# ------------------------------
#
# Description:
#
#
# Author       : Nick Blundell
# Organisation : www.nickblundell.org.uk
# Version Info : $Id$
#

# TODO: File attachment tests
# TODO: Data dump and load test

import unittest, time, re, os
from selenium import selenium

from nbdebug import *

TEST_PORT = "8081"
URL_PREFIX="/prefix"
URL_PREFIX=None
WEB_ROOT = "http://localhost:%s%s" % (TEST_PORT, URL_PREFIX or "")
TIMEOUT = "15000"
AJAX_SPEED = 0
AJAX_WAIT = 5

sel = None



class TestBase(unittest.TestCase):
  
  def setUp(self):
    global sel
    if not sel :
      sel = selenium("localhost", 4444, "*firefox", WEB_ROOT)
      sel.start()
      sel.window_maximize()
    goFast()

  def assertInSource(self, text) :
    self.assertTrue(text in sel.get_html_source())
  
  def assertNotInSource(self, text) :
    self.assertTrue(text not in sel.get_html_source())
  
  def assertInText(self, text) :
    self.assertTrue(text.lower() in sel.get_body_text().lower())

  def assertNotInText(self, text) :
    self.assertFalse(text.lower() in sel.get_body_text().lower())

  def assertTermsInOrder(self, terms) :
    """Checks if terms are in this order in the page text"""
    pattern = ".*".join(terms).lower()
    self.assertTrue(re.search(pattern, sel.get_body_text().lower()))

  def assertNotDjangoError(self) :
    self.assertNotInText("Request Method")


class LoginTests(TestBase) :

  def testLogin(self):
    login("admin","admin")
    openPage("/")
    sel.wait_for_page_to_load(TIMEOUT)
    self.assertTrue("Logout" in sel.get_body_text())



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
    openPage("/My first wikidpage")
    sel.click("edit-link")
    wait()
    content = sel.get_value("id_content")
    content = content.replace("Point 2","Point 8")
    content = sel.type("id_content",content)
    sel.submit("wikidpage")
    wait()
    self.assertInSource("<li>Point 8</li>")

 
  def testCreateExistingPage(self) :
    createPage(name="My first wikidpage", content="Blah")
    self.assertInSource("this name already exists")

  def testDeletePage(self) :
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


class WikiTests(TestBase) :

  def testWikiWord(self) :
    createPage(name="Wiki test", content="MyWikiPage")
    self.assertInSource("""MyWikiPage<a title="Click here to create this new page." href="/MyWikiPage/EDIT/CREATE">""")
    sel.click("link=?")
    wait()
    self.assertEqual(sel.get_value("name"), "MyWikiPage")

  def testExplicit(self) :

    sel.type("id_content", "[[Another page]]")
    sel.submit("wikidpage")
    wait()
    self.assertInSource("""Another page<a title="Click here to create this new page." href="/Another%20page/EDIT/CREATE">""")
    sel.click("link=?")
    wait()
    self.assertEqual(sel.get_value("name"), "Another page")
    sel.type("id_content", "The end of the chain")
    sel.submit("wikidpage")
    wait()
    
  def testLinks(self):
    openPage("/MyWikiPage")
    sel.click("link=Another page")
    wait()
    self.assertInSource("The end of the chain")

  def testFalseWikiWord(self) :
    createPage(name="Wiki test2", content="http://somethingNotWikiWord.org.uk/NotWikiWord")
    self.assertNotInSource("""<span class="wikiwordquestion">?</span>""")
    

class FileAttachTests(TestBase) :

  def xxxtetAttachFile(self) :
    # js restricts setting the value of an input field.
    # TODO: look at sel.attach_file
    testDir = "/tmp/wbtestfiles"
    runCommand("mkdir -p %s" % testDir)
    testFilePath = os.path.join(testDir, "wbtestfile")
    testFile = open(testFilePath,"w")
    testFile.write("Just a test file")
    testFile.close()
    createPage(name="FileTest",content="Nothing")
    goSlow()
    pause(10)
    sel.type("id_attach_file",testFilePath)
    pause(20)
    sel.submit("wikidpage")
    runCommand("rm '%s'" % testFilePath)
    






class ContextTests(TestBase) :
  
  def testCreatePerson(self) :
    # Create a person
    createPage(name="Fred Jones", content=PERSON_TEMPLATE, type="person")
  
  def testClonePerson(self) :

    # Clone the person
    sel.click("clone-link")
    wait()
    #TODO : pick a date sel.type("name='Title'","")
    sel.type("name=Name","Dave")
    sel.type("name=Surname","Blundell")
    sel.type("name=Address","Here\nThere\nEverywhere")
    # TODO: DOB Pick a date
    sel.type("name=Postcode","LA1 4YR")
    sel.type("name=Telephone","1234 122345")
    sel.type("name=Email","nick@nickb.co.uk")
    sel.submit("wikidpage")
    wait()
    self.assertInSource("The page has been")
    self.assertInSource("created")
    self.assertInSource("saved")

  def testPeopleQuery(self) :

    createPage(name="peopleq", content=":::list all People:::")
    self.assertInSource("Fred Jones")
    self.assertInSource("Dave")
    self.assertInSource("Blundell")

  def testAnimals(self) :
   
    createPage(name="Wiskas",content=ANIMAL_TEMPLATE, type="Animal")
    
  def testAnimalClone(self) :  
    
    # Clone the animal
    sel.click("clone-link")
    wait()
    #TODO : pick a date sel.type("name='Title'","")
    sel.type("name=Name","Fido")
    sel.type("name=DOB","31/5/98")
    sel.type("id_Animal type","Dog")
    sel.submit("wikidpage")
    wait()
    self.assertInSource("The page has been")
    self.assertInSource("created")
    self.assertInSource("saved")


class WikidpageWidgetTests(TestBase) :

  #TODO:  Manipulate values through source AND form.

  def testCheckbox(self) :
    createPage(name="cb2",content="My label:: no\n")
    self.assertTrue(re.search("""<input id="id_My label".+type="checkbox">""", sel.get_html_source()))
    self.assertTrue(sel.is_checked("id_My label") == False)
   
    # Tick, save, check ticked
    sel.check("id_My label")
    sel.submit("wikidpage")
    wait()
    self.assertTrue(sel.is_checked("id_My label") == True)
    
    # untick, save, check unticked
    sel.uncheck("id_My label")
    sel.submit("wikidpage")
    wait()
    self.assertTrue(sel.is_checked("id_My label") == False)

    createPage(name="cb1",content="My label::Yes\n", type="cbtest")
    self.assertTrue(re.search("""<input id="id_My label".+type="checkbox">""", sel.get_html_source()))
    self.assertTrue(sel.is_checked("id_My label"))

    # Check a clone has an unchecked checkbox.
    sel.click("clone-link")
    wait()
    self.assertTrue(re.search("""<input id="id_My label".+type="checkbox">""", sel.get_html_source()))
    self.assertTrue(sel.is_checked("id_My label") == False)


  def testDate(self) :
    
    createPage(name="dt1",content="My label:: 31/5/80\n", type="dt1t")
    sel.click("id_My label_trigger")
    sel.mouse_down("//*[contains(@class, 'day-14')]")
    sel.mouse_up("//*[contains(@class, 'day-14')]")
    self.assertTrue(sel.get_value("id_My label") == "14/05/1980")
    sel.submit("wikidpage")
    wait()
    self.assertNotInSource("Enter a valid date")

    sel.type("id_My label","Not a date")
    sel.submit("wikidpage")
    wait()
    self.assertInSource("Enter a valid date")

    # Test a cloned page has a date widget.
    sel.click("clone-link")
    wait()
    sel.click("id_My label_trigger")
    sel.mouse_down("//*[contains(@class, 'day-12')]")
    sel.mouse_up("//*[contains(@class, 'day-12')]")
    self.assertTrue("12" in sel.get_value("id_My label"))

 
  def testDateTime(self) :
    
    createPage(name="dt2",content="My label:: 31/5/80 3pm\n")
    sel.click("id_My label_trigger")
    sel.mouse_down("//*[contains(@class, 'day-14')]")
    sel.mouse_up("//*[contains(@class, 'day-14')]")
    self.assertTrue(sel.get_value("id_My label") == "14/05/1980 03:00 PM")
    sel.submit("wikidpage")
    wait()
    self.assertNotInSource("Enter a valid date")

    sel.type("id_My label","Not a date")
    sel.submit("wikidpage")
    wait()
    self.assertInText("Enter a valid date")


  def testSingleSelect(self) :
    createPage(name="sel1",content="My label::Hello, world\n", type="something1")
    
    # Set this to a single select widget.
    configField("/sel1", "My label", "field_type", "Single-select List")

    self.assertTrue(sel.get_selected_label("id_My label") == "Hello, world")
    
    # Test we can add a new option to the select widget.
    addSelectOption("id_My label","New option")
    sel.submit("wikidpage")
    wait()
    self.assertTrue(sel.get_selected_label("id_My label") == "New option")

    # Test pre-entered options are in the list.
    sel.submit("wikidpage")
    wait()
    configField("/sel1", "My label", "list_values", "Eggs\nBeans\nSausages\nCheese")
    self.assertTrue(sel.get_selected_label("id_My label") == "New option")
    options = sel.get_select_options(("id_My label"))
    self.assertTrue(options == [u'[Add]', u'Eggs', u'Beans', u'Sausages', u'Cheese', u'New option'])

    # Test we can sort the options
    configField("/sel1", "My label", "list_sort", "Sort ascending")
    options = sel.get_select_options(("id_My label"))
    self.assertTrue(options == [u'[Add]', u'Beans', u'Cheese', u'Eggs', u'New option', u'Sausages'])
    
    # Test a clone has the widget
    sel.click("clone-link")
    wait()
    options = sel.get_select_options(("id_My label"))
    self.assertTrue(options == [u'[Add]', u'Beans', u'Cheese', u'Eggs', u'New option', u'Sausages'])


  def testMultipleSelect(self) :
    
    # Change widget to multiple select.
    openPage("/sel1")
    configField("/sel1", "My label", "field_type", "Multiple-select List")
    self.assertInSource("""<select id="id_My label" class="vSelectMultipleField" name="My label" size="1" multiple="multiple">""")
    self.assertTrue(sel.get_selected_label("id_My label") == "New option")
    
    # Test a single selection.
    sel.select("id_My label","Eggs")
    sel.submit("wikidpage")
    wait()
    self.assertTrue(sel.get_selected_label("id_My label") == "Eggs")
    self.assertTrue("My label:: Eggs" in getPageSource("sel1"))
    
    # Test multiple selection.
    openPage("/sel1")
    sel.add_selection("id_My label","Sausages")
    sel.add_selection("id_My label","Cheese")
    sel.submit("wikidpage")
    wait()
    self.assertTrue("""{{\nCheese\nEggs\nSausages\n}}""" in getPageSource("sel1"))

    # Test empty selection.
    openPage("/sel1")
    sel.remove_all_selections("id_My label")
    sel.submit("wikidpage")
    wait()
    self.assertFalse(sel.is_something_selected("id_My label"))
    source = getPageSource("sel1")
    self.assertTrue(re.search("My label::{{\s*}}", source))

    # Test a clone has a multiselect widget.
    openPage("/sel1")
    sel.click("clone-link")
    wait()
    self.assertInSource("""<select id="id_My label" class="vSelectMultipleField" name="My label" size="1" multiple="multiple">""")

  def testActiveLinks(self) :
    # Test email address
    createPage(name="al1",content="My label:: myemail@test.co.uk\n")
    self.assertInSource("mailto:myemail@test.co.uk")

    # Test url
    sel.type("id_My label","www.website.org.uk/projects/ducks")
    sel.submit("wikidpage")
    wait()
    self.assertInSource("http://www.website.org.uk/projects/ducks")

    # Test google maps
    sel.type("id_My label","blah blah CV1 1EA blah")
    sel.submit("wikidpage")
    wait()
    self.assertInSource("http://maps.google.co.uk/maps?q=CV1%201EA")

    


    
  def testTextField(self) :
    createPage(name="txt1",content="My label::Hello, world\n")
    self.assertTrue(sel.get_value("id_My label") == "Hello, world")
    createPage(name="txt2",content="My label::\n")
    self.assertTrue(sel.get_value("id_My label") == "")
  
  def testTextArea(self) :
    createPage(name="ta1",content="My label::Hello, world\n", type="ta1t")
    configField("/ta1", "My label", "field_type", "Text area")
    self.assertTrue(sel.get_value("id_My label") == "Hello, world")
    self.assertInSource("""textarea id="id_My label" """)
    value = "This is a\nmultiline\nvalue\n\n\nThank you"
    createPage(name="ta2",content="My label:: {{ %s }}\n" % value, type="ta2t")
    self.assertTrue(sel.get_value("id_My label") == value)

    # Test a clone has a textarea widget.
    sel.click("clone-link")
    wait()
    self.assertInSource("""textarea id="id_My label" """)

  def testDeleteWidgetPages(self) :
     pages = ["ta1", "ta2", "txt1", "txt2", "al1", "sel1", "dt1", "dt2", "cb1", "cb2"]
     for page in pages :
       deletePage(page) 



class RelationshipTests(TestBase) :
  
  def testDefineRelationships(self) :
    defineRelationship(self, "Person","Animal","Pets","Owners")
    defineRelationship(self, "Person","Animal","Animal Clients","Vets")
    defineRelationship(self, "Person","Person","Friends","Friends")
    defineRelationship(self, "Person","Person","Employer","Employee")


  # Do pet and owner
  def testOwnerPet(self) :
    goSlow(AJAX_SPEED)
    addNewRelationship(self, sourcePage = "Fred Jones", destKeyword="Wiskas", localField="Pets", remoteField="Owners")
    
    self.assertInText("The new link has been added")

    self.assertInText("Wiskas")
    self.assertInText("31/05/2001")
    self.assertInText("Cat")

  # Now do friend-friend
  def testRelationFriendFriend(self) :
    goSlow(AJAX_SPEED)
    addNewRelationship(self, sourcePage = "Fred Jones", destKeyword="Dave", localField="Friends", remoteField="Friends")
    
  def testRelationEmployeeEmployer(self) :
    goSlow(AJAX_SPEED)
    addNewRelationship(self, sourcePage = "Fred Jones", destKeyword="Dave", localField="Employee", remoteField="Employer")

  def testRelationVetAnimalClients(self) :
    goSlow(AJAX_SPEED)
    addNewRelationship(self, sourcePage = "Wiskas", destKeyword="Dave", localField="Vets", remoteField="Animal Clients")

  
  def testRelationEmployeeNewEmployer(self) :
    addNewRelationship(self, sourcePage = "Fred Jones", destKeyword="Person", localField="Employee", remoteField="Employer", create=True)
    self.assertInText("Fred Jones")

  

class PrepareQueryTestData(TestBase) :
  
  def testCreatePeople(self) :
    createPerson(self, "Jamie Hillman", "Jamie","Hillman","4/7/1980","Hillman House", "LA1 4YR", "11234 12345", "jamie@email.com")
    createPerson(self, "Nick Blundell","Nick","Blundell","31/5/80", "Blundell House", "CV1 1EA", "123455","nick@somewhere.com")
    createPerson(self, "Matthew Shepherd", "Matthew","Shepherd","1/12/1968","Shepherd Manor", "CV1 1EA", "123434", "m.s@email.com")
    createPerson(self, "Fred Flintstone", "Fred","Flintstone","4/1/1950","Cave House", "AD 1 123", "54663442", "f.flintstone@test.com")
    createPerson(self, "Vetty Vet", "Vetty","Vet","4/1/1950","Vet lane", "CV1 waq", "54663442", "v.v@vet.com")
    createPerson(self, "Pete Read", "Pete","Read","1/12/1968","Read House", "CV1 1EA", "123434", "p.r@email.com")

  def testCreateAnimals(self) :
    createAnimal(self, "Bob","Bob","23/4/2001", "Dog", True)
    createAnimal(self, "Dino","Dino","23/4/2003", "Cat", False)
    createAnimal(self, "Bubble","Bubble","23/4/1982", "Cat", True)
    createAnimal(self, "Squeek","Squeek","23/4/1978", "Cat", False)

  def testCreateRelations(self) :
    
    # Friendss.
    addNewRelationship(self, sourcePage = "Jamie Hillman", destKeyword="Nick", localField="Friends", remoteField="Friends", create=False)
    addNewRelationship(self, sourcePage = "Fred Flintstone", destKeyword="Vetty", localField="Friends", remoteField="Friends", create=False)
    
    # Pets-owners
    addNewRelationship(self, sourcePage = "Nick Blundell", destKeyword="Bubble", localField="Pets", remoteField="Owners", create=False)
    addNewRelationship(self, sourcePage = "Nick Blundell", destKeyword="Squeek", localField="Pets", remoteField="Owners", create=False)
    addNewRelationship(self, sourcePage = "Fred Flintstone", destKeyword="Dino", localField="Pets", remoteField="Owners", create=False)
    addNewRelationship(self, sourcePage = "Jamie Hillman", destKeyword="Bob", localField="Pets", remoteField="Owners", create=False)
    addNewRelationship(self, sourcePage = "Jamie Hillman", destKeyword="Bubble", localField="Pets", remoteField="Owners", create=False)
    
    # Pet-vets
    addNewRelationship(self, sourcePage = "Vetty Vet", destKeyword="Bubble", localField="Animal Clients", remoteField="Vets", create=False)

    # Employee-employer
    addNewRelationship(self, sourcePage = "Pete Read", destKeyword="Nick", localField="Employee", remoteField="Employer", create=False)
    addNewRelationship(self, sourcePage = "Pete Read", destKeyword="Matthew", localField="Employee", remoteField="Employer", create=False)
    


class QueryTests(TestBase) :

  def testLocalFieldQueries(self) :
    
    # Simple query
    runQuery("""show me people where name == fred""")
    self.assertInText("Flintstone")
    self.assertNotInText("Matthew")
    self.assertNotInText("Hillman")

    #
    # Multiple contexts and multiple conditions
    #
    runQuery("""show me people and animals where name = dino or address contains "hillman house" """)
    self.assertInText("Dino")
    self.assertInText("Cat")
    self.assertInText("Jamie")
    self.assertInText("Hillman")
    self.assertNotInText("Matthew")
    self.assertNotInText("Dog")
    
    runQuery("""show me people and animals where name = dino and address contains "hillman house" """)
    self.assertInText("There are no results for this query")
    
    runQuery("""show me people and animals where name = Jamie and dob = 4/7/80 """)
    self.assertInText("Jamie")
    self.assertInText("Hillman")
    self.assertNotInText("Matthew")
    self.assertNotInText("Dog")
    
    runQuery("""show me people and animals where name contains matt or dob = 4/7/80 """)
    self.assertInText("Jamie")
    self.assertInText("Hillman")
    self.assertInText("Matthew")
    self.assertInText("Shepherd")
    self.assertNotInText("Dog")
    self.assertNotInText("Cat")
    
    runQuery("""show me people and animals where name contains matt or dob > 4/7/80 """)
    self.assertNotInText("Jamie")
    self.assertNotInText("Hillman")
    self.assertInText("Matthew")
    self.assertInText("Shepherd")
    self.assertInText("Bob")
    self.assertInText("Bubble")
    self.assertInText("Dino")
    self.assertNotInText("Pete")
    self.assertNotInText("Squeek")

  def testRelationalQueries(self) :
    runQuery("""show me anything where friend.name = nick""")
    self.assertInText("Jamie")
    self.assertInText("Hillman")
    self.assertInText("Blundell house")
    self.assertNotInText("Matthew")
    self.assertNotInText("Dog")
    
    runQuery("""show me anything where pet.vet.name = vetty""")
    self.assertInText("Blundell house")
    self.assertInText("Bubble")
    self.assertInText("Vetty vet")
    self.assertInText("Vet Lane")
    self.assertInText("Jamie")
    self.assertNotInText("Matthew")
    self.assertNotInText("Dog")
    
    runQuery("""show me anything where pet.vet.name = vetty and name = nick""")
    self.assertInText("Blundell house")
    self.assertInText("Bubble")
    self.assertInText("Vetty vet")
    self.assertInText("Vet Lane")
    self.assertNotInText("Jamie")
    self.assertNotInText("Matthew")
    self.assertNotInText("Dog")
    
    runQuery("""show me people where employee.friend.pet.vet.name = vetty""")
    self.assertInText("Blundell house")
    self.assertInText("Vetty vet")
    self.assertInText("Pete Read")
    self.assertInText("Hillman house")
    self.assertInText("Bubble")
    self.assertNotInText("Matthew")
    self.assertNotInText("Dog")

    
  def testNestedQueries(self) :
    
    runQuery("""show me anything where (pet.vet.name = vetty and pet.animal type = cat and name = nick) or pet.name = dino""")
    self.assertInText("Blundell house")
    self.assertInText("Vetty vet")
    self.assertInText("Bubble")
    self.assertInText("Dino")
    self.assertInText("Fred Flintstone")
    self.assertNotInText("Jamie")
    self.assertNotInText("Matthew")
    self.assertNotInText("Matthew")
    self.assertNotInText("Dog")

  
  def testFieldLimitedQueries(self) :
    
    runQuery("""show me anything where (pet.vet.name = vetty and pet.animal type = cat and name = nick) or pet.name = dino with fields name pet.name pet.animal type pet.vet.name""")
    self.assertInText("Nick")
    self.assertInText("Vetty")
    self.assertInText("Cat")
    self.assertInText("Fred")
    self.assertNotInText("Blundell house")
    self.assertNotInText("Flintstone")
    self.assertNotInText("Dog")
    self.assertNotInText("Vet Lane")


  def testQueryKeywords(self) :
    
    runQuery("""anything""")
    self.assertInText("Page")
    self.assertInText("Animal")
    self.assertInText("Person")
    
    runQuery("""pages""")
    self.assertInText("help")
    self.assertInText("index")

    runQuery("""pet.anyfield = dog""")
    self.assertInText("Jamie")
    self.assertInText("Hillman")
    self.assertInText("Dog")
    self.assertInText("Bob")
    self.assertNotInText("Cat")

  def testDateKeywords(self) :

    runQuery("""modified > today""")
    self.assertInText("There are no results for this query")
    runQuery("""modified <= today""")
    self.assertNotInText("There are no results for this query")

    runQuery("""modified < "last week" """)
    self.assertInText("There are no results for this query")
    runQuery("""modified >= "last week" """)
    self.assertNotInText("There are no results for this query")
    
    runQuery("""modified < "last year" """)
    self.assertInText("There are no results for this query")
    runQuery("""modified >= "last year" """)
    self.assertNotInText("There are no results for this query")
    
    runQuery("""modified > "tomorrow" """)
    self.assertInText("There are no results for this query")
    runQuery("""modified <= "tomorrow" """)
    self.assertNotInText("There are no results for this query")
    
    runQuery("""modified < yesterday """)
    self.assertInText("There are no results for this query")
    runQuery("""modified >= yesterday """)
    self.assertNotInText("There are no results for this query")

  def testBooleanQueries(self) :
    runQuery("animals had injection = yes")
    self.assertInText("Bubble")
    self.assertInText("Bob")
    self.assertNotInText("Squeek")
    
    runQuery("animals had injection = no")
    self.assertNotInText("Bubble")
    self.assertNotInText("Bob")
    self.assertInText("Squeek")
    self.assertInText("Dino")

  def testNotConditions(self) :
  
    # Simple query
    runQuery("""show me people where name !== fred""")
    self.assertNotInText("Flintstone")
    self.assertInText("Matthew")
    self.assertInText("Hillman")

    #
    # Multiple contexts and multiple conditions
    #
    runQuery("""show me people where address not contains "hillman house" """)
    self.assertNotInText("Jamie")
    self.assertNotInText("Hillman")
    self.assertInText("Matthew")
 

  def xtestRelationInferenceFromFields(self) :
    # TODO: Implement this - need a good think.
    runQuery("""people (name = nick or name = ted) fields name, address, pet.name """) # -> people name = nick pet.id > 0
    self.assertInText("Blundell House")
    self.assertInText("Bubble")
    self.assertInText("Squeek")


class DataExportTest(TestBase) :

  def testCSV(self) :

    runQuery("show me all people name = nick and pet.animal type = cat")
    sel.click("//a[@class='exportcsv']")
    self.assertInText("Blundell house")
    self.assertInText("Bubble")
    self.assertInText("Squeek")
    self.assertInText("pet.name")
    self.assertInText(",,,,,") # CSV has something that looks like this.
  
  # TODO: test url queries, results table manipulation, results calendar manipulation.
  # TODO: test field detected condition e.g.: show me people with fields name tasks.name


class TableViewTests(TestBase) :

  def testTableSorting(self) :
    runQuery("people")

    # Ensure all fields are visible for this test.
    sel.click("css=.show-hidden-fields")
    pause(2)
    
    sel.click("//*[contains(@class, 'page_SORT_ASCEND')]")
    pause(AJAX_WAIT)
    expect = ["Fred Flintstone", "Fred Jones", "Jamie Hillman", "Vetty Vet"]
    self.assertTermsInOrder(expect)
    sel.click("//*[contains(@class, 'page_SORT_DESCEND')]")
    pause(AJAX_WAIT)
    expect.reverse()
    self.assertTermsInOrder(expect)
   
    sel.click("//*[contains(@class, 'dob_SORT_ASCEND')]")
    pause(AJAX_WAIT)
    expect = ["04/01/1950","01/12/1968","31/05/1980","04/07/1980"]
    self.assertTermsInOrder(expect)
    sel.click("//*[contains(@class, 'dob_SORT_DESCEND')]")
    pause(AJAX_WAIT)
    expect.reverse()
    self.assertTermsInOrder(expect)


  def testHeaderHiding(self) :

    runQuery("people")
    
    # Check all headers are displayed.
    self.assertInText("Jamie")
    self.assertInText("Jamie Hillman")
    self.assertInText("Hillman House")
    self.assertInText("04/07/1980")
    self.assertInText("jamie@email.com")

    # Hide some headers and check they disappear
    sel.click("css=.name_HIDE_FIELD")
    sel.click("css=.surname_HIDE_FIELD")
    sel.click("css=.address_HIDE_FIELD")
    sel.click("css=.email_HIDE_FIELD")
    sel.click("css=.page_HIDE_FIELD")
    pause(AJAX_WAIT)
    self.assertNotInText("Jamie")
    self.assertNotInText("Hillman House")
    self.assertNotInText("jamie@email.com")
    self.assertInText("04/07/1980")
    
    # Now show all the fields and check they re-appear
    sel.click("css=.show-hidden-fields")
    pause(AJAX_WAIT)
    self.assertInText("Jamie")
    self.assertInText("Jamie Hillman")
    self.assertInText("Hillman House")
    self.assertInText("04/07/1980")
    self.assertInText("jamie@email.com")

  def testRowCollapse(self) :

    runQuery("people")
    sel.click("css=.name_SORT_ASCEND")
    pause(AJAX_WAIT)

    # Reduce the rows
    while not sel.is_element_present("css=.go-to-last-page") :
      sel.click("css=.show-less-rows")
      pause(AJAX_WAIT)
    

    # Check correct items are on last page
    sel.click("css=.go-to-last-page")
    pause(AJAX_WAIT)
    self.assertNotInText("Dave")
    self.assertInText("Vetty")
    
    # Check correct items are on first page
    sel.click("css=.go-to-first-page")
    pause(AJAX_WAIT)
    self.assertInText("Dave")
    self.assertNotInText("Vetty")
    
    # Go back to first page.
    sel.click("css=.go-to-first-page")
    pause(AJAX_WAIT)
    
    # Increase the rows
    while sel.is_element_present("css=.go-to-last-page") :
      sel.click("css=.show-more-rows")
      pause(AJAX_WAIT)
    
    # Test we can see all things on one page.
    self.assertInText("Dave")
    self.assertInText("Vetty")
    

  
class CalendarViewTests(TestBase) :
  
  def testCalendarView(self) :
    runQuery("people fields name, surname, dob, modified")
    
    if not sel.is_element_present("css=.view-table") :
      sel.click("css=.cal-switch-modified")
      pause(AJAX_WAIT)
    
    sel.click("css=.view-week")
    pause(AJAX_WAIT)
    sel.click("css=.view-day")
    pause(AJAX_WAIT)
    sel.click("css=.view-month")
    pause(AJAX_WAIT)
    sel.click("css=.view-table")
    pause(AJAX_WAIT)

 
  def testNavigation(self) :
    
    # View by calendar on modified field.
    if not sel.is_element_present("css=.view-table") :
      sel.click("css=.cal-switch-modified")
      pause(AJAX_WAIT)
   
    # Click month
    sel.click("css=.view-month")
    pause(AJAX_WAIT)

    # Click today
    sel.click("css=.view-today")
    pause(AJAX_WAIT)

    # Go forward a few months
    sel.click("css=.view-next")
    pause(AJAX_WAIT)
    sel.click("css=.view-next")
    pause(AJAX_WAIT)
    
    # Switch to week
    sel.click("css=.view-week")
    pause(AJAX_WAIT)
    
    # Search back each week until we see some items.
    foundItems = False
    for i in range(0,20) :
      if "fred" in sel.get_body_text().lower() :
        foundItems = True
        break
      sel.click("css=.view-prev")
      pause(AJAX_WAIT)
  
    self.assertTrue(foundItems)

  
  def testAddPageOnDate(self) :
    
    runQuery("people fields name, surname, dob, modified")
    
    if not sel.is_element_present("css=.cal-switch-dob") :
      sel.click("css=.view-table")
      pause(AJAX_WAIT)
    
    # View cal for field DOB
    sel.click("css=.cal-switch-dob")
    pause(AJAX_WAIT)
    
    # Swtch to month view
    sel.click("css=.view-month")
    pause(AJAX_WAIT)

    # Locate day, click add to day
    sel.click("css=.day-4 .cal-add")
    wait()

    # Create a new person on that day.
    sel.type("name=Name","Eddie Vedder")
    sel.click("save_and_back")
    wait()

    # Check our new person is there.
    self.assertTrue("Eddie Vedder" in sel.get_text("css=.day-4 .calendaritem"))

  


class AuthorisationTests(TestBase) :
 
  def testUserRoles(self) :
     
     # Open the control panel.
     openPage("/controlpanel")
     sel.click("link=Roles")
     wait()
     
     sel.type("name=new_role", "Site Admin")
     sel.click("name=add_role")
     wait()
     self.assertInText("The new role has been added")
     
     sel.type("name=new_role", "Editor")
     sel.click("name=add_role")
     wait()
     self.assertInText("The new role has been added")

     sel.type("name=new_role", "To be deleted")
     sel.click("name=add_role")
     wait()
     self.assertInText("The new role has been added")
     
     # Check the roles are listed.
     self.assertInText("Site Admin")
     self.assertInText("Editor")
     self.assertInText("To be deleted")

     # Delete a role.
     openPage("/controlpanel/roles/To be deleted/delete")
     self.assertInSource("Are you sure you wish to delete")
     sel.click("Delete")
     wait()
     self.assertInText("has been deleted")
     openPage("/controlpanel/roles")
     self.assertInText("Site Admin")
     self.assertInText("Editor")
     self.assertNotInText("To be deleted")
  
  def testManageUsers(self) :

    # Add some users.
    self.addUser("jamie", "Jamie", "Hillman", "jamie@email.com", "password", ["Editor"], False)
    self.addUser("matthew", "Matthew", "Shepherd", "matt@email.com", "password", ["Editor", "Site Admin"], False)
    self.addUser("extra", "Mr Extra", "Man", "ex@email.com", "password", ["Editor"], False)

    # Delete user
    openPage("/controlpanel/users/extra/delete")
    self.assertInSource("Are you sure you wish to delete")
    sel.click("Delete")
    wait()
    openPage("/controlpanel/users")
    self.assertNotInText("Mr Extra")

    
  def addUser(self, username, name, surname, email, password, roles=None, superUser=False) :
    openPage("/controlpanel/users")
    
    sel.type("name=username", username)
    sel.type("name=first_name", name)
    sel.type("name=last_name", surname)
    sel.type("name=email", email)
    sel.type("name=password", password)
    sel.type("name=password_confirm", password)
    
    if superUser :
      sel.check("name=is_superuser")
    else :
      sel.uncheck("name=is_superuser")
   
    roles = roles or []
    for role in roles :
      sel.check("xpath=//*[@value='%s']" % role)
    
    sel.click("name=add_user")
    wait()
    self.assertInText(username)
    self.assertInText(surname)

class PermissionTests(TestBase) :
  
  # Set permissions and test for view, edit, wiki-edit, delete.
  def testAnonymousPermissions(self) :

    login("admin","admin")
    # Don't let anonymous view pages
    openPage("/controlpanel/permissions")
    sel.uncheck("anonymou--Wikidpages--view")
    #Site Admin--Wikidpages--wiki-edit")
    sel.click("name=save")
    wait()

    logout()
    openPage("/")
    self.assertInText("you are not authorised to do this")
    login("admin","admin")

    # Let anonymous view pages.
    openPage("/controlpanel/permissions")
    sel.check("anonymou--Wikidpages--view")
    #Site Admin--Wikidpages--wiki-edit")
    sel.click("name=save")
    wait()
    
    logout()
    openPage("/")
    self.assertNotInText("you are not authorised to do this")

  def testAuthenticatedPermissions(self) :
    
    login("admin","admin")
    # Don't let anonymous view pages
    openPage("/controlpanel/permissions")
    sel.uncheck("authenticated--Wikidpages--view")
    #Site Admin--Wikidpages--wiki-edit")
    sel.click("name=save")
    wait()

    login("jamie","password")
    openPage("/")
    self.assertInText("you are not authorised to do this")
  
    login("admin","admin")
    # Don't let anonymous view pages
    openPage("/controlpanel/permissions")
    sel.check("authenticated--Wikidpages--view")
    #Site Admin--Wikidpages--wiki-edit")
    sel.click("name=save")
    wait()

    login("jamie","jamie")
    openPage("/")
    self.assertNotInText("you are not authorised to do this")

  def testRolePermissions(self) :
    
    login("admin","admin")
    # Don't let anonymous view pages
    openPage("/controlpanel/permissions")
    sel.uncheck("siteadmin--Wikidpages--wiki-edit")
    sel.click("name=save")
    wait()

    login("matthew","password")
    openPage("/")
    self.assertFalse(sel.is_element_present("edit-link")) 
    openPage("/EDIT")
    wait()
    self.assertInText("you are not authorised to do this")
  
    login("admin","admin")
    # Don't let anonymous view pages
    openPage("/controlpanel/permissions")
    sel.check("siteadmin--Wikidpages--wiki-edit")
    sel.click("name=save")
    wait()

    login("matthew","password")
    openPage("/")
    self.assertTrue(sel.is_element_present("edit-link")) 
    openPage("/EDIT")
    wait()
    self.assertNotInText("you are not authorised to do this")


class CommandTests(TestBase) :
  def testModuleCommand(self) :
    login("admin","admin")
    createPage("comtest", """There are :::command >> mymodule2.count("people")::: people in the wikidbase""")
    self.assertInText("There are 9 people in the wikidbase")


class DataManagementTests(TestBase) :
  pass
  # Tests, test dump data, test load data from server file - since upload file test is not possible.


class SystemPageTests(TestBase) :
  
  def testViewSystemPages(self) :
    openPage("/SYSTEM/ALL_PAGES/")
    self.assertInSource("All Pages")
    openPage("/SYSTEM/RECENT_CHANGES/")
    self.assertInSource("Recent Changes")

  def testViewPreLoadedPages(self) :
    openPage("/help/")
    self.assertTrue("Wikidbase Documentation" in sel.get_body_text())


class Closure(TestBase) :
  
  def testWait(self) :
    time.sleep(1)

  def testLogout(self) : 
    sel.click("link=[Logout]")
    sel.wait_for_page_to_load(TIMEOUT)
    self.assertInSource("You are now logged out")



#
# Helper methods.
#

def wait() : sel.wait_for_page_to_load(TIMEOUT)
def goSlow(speed=2000) : sel.set_speed(speed)
def goFast() : sel.set_speed(0)
def pause(secs=10) : time.sleep(secs)


def openPage(page) :
  sel.open("%s%s" % (WEB_ROOT, page))
  wait()


def login(username, password) :
  openPage("/accounts/login")
  sel.wait_for_page_to_load(TIMEOUT)
  sel.type("username", username)
  sel.type("password", password)
  sel.submit("login")
  openPage("/")

def logout() :
  openPage("/accounts/logout")

def createPage(name, content, type=None) :
  openPage("/EDIT/CREATE")
  wait()
  sel.type("name", name)
  sel.type("id_content", content)
  if type :
    sel.type("id_context", type)
  sel.submit("wikidpage")
  wait()

def deletePage(pageName) :
  openPage("/%s" % pageName)
  sel.click("delete")
  wait()
  sel.click("Delete")


def getPageSource(pageName) :
  openPage("/%s/EDIT" % pageName)
  return sel.get_value("id_content")
  

def runQuery(queryString) :
  openPage("/")
  sel.type("query",queryString)
  sel.submit("query-form")
  wait()

def addSelectOption(locator, newOption) :
  options = sel.get_select_options(locator)
  if options == ["[Add]"] :
    sel.click(locator)
  else :
    sel.select(locator,"[Add]")
  
  pause(0.5) 
  sel.type(locator,newOption)
  pause(0.5) 
  sel.key_press(locator,13)
  pause(0.5)
  

def slowType(locator, text) :
  for char in text :
    sel.key_press(locator, ord(char))
    pause(0.2)

def configField(page, fieldName, setting, value) :
  openPage(page)
  sel.click("link=%s" % fieldName)
  wait()
  if setting in ["field_type", "list_sort"] :
    sel.select(setting, value)
  else :
    sel.type(setting, value)
  sel.submit("field_config")
  wait()
  openPage(page)

def runCommand(command) :
  debugOutput(command)
  os.system(command)


def createPerson(testObject, pageName, name, surname="", dob="", address="", postcode="", telephone="", email="") :
  # Open The first person page
  createPage(name=pageName, content=PERSON_TEMPLATE, type="person")
  sel.type("name=Name",name)
  sel.type("name=Surname",surname)
  sel.type("name=Address",address)
  sel.type("name=DOB",dob)
  sel.type("name=Postcode",postcode)
  sel.type("name=Telephone",telephone)
  sel.type("name=Email",email)

  # Save the page
  sel.submit("wikidpage")
  wait()
  testObject.assertNotDjangoError()


def createAnimal(testObject, pageName, name, dob, animalType, hadInjection=False) :
 
  createPage(name=pageName, content=ANIMAL_TEMPLATE, type="Animal")
  
  sel.type("name=Name",name)
  sel.type("name=DOB",dob)
  sel.type("id_Animal type",animalType)
  if hadInjection :
    sel.check("id_Had Injection")
  else :
    sel.uncheck("id_Had Injection")
  sel.submit("wikidpage")
  wait()
  testObject.assertNotDjangoError()



def normaliseTerm(term) :
  """Fake term normaliser."""
  terms = {
    "Animal Clients":"animalclient",
  }
  if term in terms :
    return terms[term]
  else :
    return term.lower().rstrip("s")

def defineRelationship(self, typeA, typeB, relA, relB) :
  
  openPage("/controlpanel/datatypes")
  sel.select("id_relationtypea",typeA) 
  sel.select("id_relationtypeb",typeB) 
  sel.type("id_relationnamea",relA)
  sel.type("id_relationnameb",relB)
  sel.submit("add_relationship")
  wait()
  self.assertInText("definitions have been saved")
  self.assertInText(relA)
  self.assertInText(relB)

def addNewRelationship(testObject, sourcePage, destKeyword, localField, remoteField, create=False) :
    
    openPage("/%s" % sourcePage)
    pause(2)
    sel.click("link=%s" % localField)
    slowType("xpath=//*/input[@id='%s-link-add-input']" % normaliseTerm(localField), destKeyword)
    pause(5)
    sel.click("xpath=//*[@id='%s-link-add-choices']/ul/li/text()[contains(.,'%s')]/.." % (normaliseTerm(localField), create and "Create" or destKeyword))
    pause(3)
    testObject.assertEqual(sel.get_selected_label("%s-link-add-foreign-link-name" % normaliseTerm(localField)), remoteField)
    sel.submit("wikidpage")
    wait()
    return


if __name__ == "__main__":
  unittest.main()


#
# Templates and text
#

PERSON_TEMPLATE = """
Title:: Mr
Name::Fred
Surname:: Jones
Address::{{
123 The House,
The Street,
The Town
}}
DOB:: 31/5/1980
Postcode::CV1 1EA
Telephone::1234 56678
Email::fred.jones@somewhere.co.uk
"""

ANIMAL_TEMPLATE = """
Name::Wiskas
DOB::31/5/2001
Animal type::Cat
Had Injection::no
"""
