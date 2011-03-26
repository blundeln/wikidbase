#
# Copyright (C) 2006-2009 Nick Blundell.
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
# widgets (widgets.py)
# --------------------
#
# Description:
#
#
# Author       : Nick Blundell
# Organisation : www.nickblundell.org.uk
# Version Info : $Id: widgets.py 1152 2009-04-17 10:14:10Z blundeln $
#

import datetime

from django import oldforms, newforms, template
from django.core import validators
from django.utils.html import escape
import wikidbase
import wikidbase.core.pagestore
import django.conf

import datatype

from nbdebug import *

def isValidDatetime(field_data, all_data):
  debugOutput("isValidTime %s" % field_data)
  if not type(datatype.convert(field_data,mode=datatype.TO_PYTHON)) == datetime.datetime:
    raise validators.ValidationError, 'Enter a valid date <b>and</b> time.'

def isValidDate(field_data, all_data):
  if not type(datatype.convert(field_data,mode=datatype.TO_PYTHON)) == datetime.date:
    raise validators.ValidationError, 'Enter a valid date.'

def isValidTime(field_data, all_data):
  if not type(datatype.convert(field_data,mode=datatype.TO_PYTHON)) == datetime.time:
    raise validators.ValidationError, 'Enter a valid time.'


def getFieldExtras(data) :
  extras = ""
  if data and type(data) == str:
    postcode = datatype.getPostcode(data)
    if postcode : extras += """ <a title="View location" href="http://maps.google.co.uk/maps?q=%s"><img src="/media/images/map.png"></a>""" % (postcode)
    emailAddress = datatype.getEmailAddress(data)
    if emailAddress : extras += """ <a title="Write email" href="mailto:%s"><img src="/media/images/email.png"></a>""" % (emailAddress)
    url = datatype.getURL(data)
    if url : extras += """<a title="Open link" href="%s"><img src="/media/images/urllink.png"></a>""" % (url)


  return extras



class EditableChoiceField(newforms.ChoiceField) :
  def widget_attrs(self, widget):
    return {"class":"editable"}


class AjaxLookupWidget(newforms.TextInput) :
  def __init__(self, lookupURL=None, *args, **kwargs):
    super(AjaxLookupWidget, self).__init__(*args, **kwargs)
    self.lookupURL = lookupURL
  
  def render(self, name, value, attrs=None):
    if value is None: value = ''
    final_attrs = self.build_attrs(attrs, type=self.input_type, name=name)
    
    t = template.loader.get_template("ajaxlookup.html")
    tContext = {
      "lookupURL":self.lookupURL,
      "name":name,
    }
    return t.render(template.Context(tContext))

class AjaxLookupField(newforms.Field) :
  def __init__(self, lookupURL, required=True, widget=AjaxLookupWidget, label=None, initial=None, help_text=None):
    super(AjaxLookupField, self).__init__(required, widget, label, initial, help_text)
    self.widget.lookupURL = lookupURL
    self.lookupURL = lookupURL


class AjaxLinkAddWidget(newforms.TextInput) :
  def __init__(self, lookupURL=None, linkLookupURL=None, localLinkName=(), wikidpage=None, *args, **kwargs):
    super(AjaxLinkAddWidget, self).__init__(*args, **kwargs)
    self.lookupURL = lookupURL
    self.linkLookupURL = linkLookupURL
    self.localLinkName = localLinkName
    self.wikidpage = wikidpage
  
  def render(self, name, value, attrs=None):
    if value is None: value = ''
    final_attrs = self.build_attrs(attrs, type=self.input_type, name=name)
   
    localLinkID = "%s-local-link-name" % name
    foreignLinkID = "%s-foreign-link-name" % name
    inline = False


    if type(self.localLinkName) == list :
      localLinkNameWidget = newforms.Select(attrs={"class":"editable"}, choices = self.localLinkName)
      localLinkNameWidget = localLinkNameWidget.render(name = localLinkID, value=None, attrs={"id":localLinkID})
    else :
      localLinkNameWidget = None
      inline = True
   

    if type(self.localLinkName) in [str, unicode] :
      localLinkName = self.localLinkName
    else :
      localLinkName = None
    
    # XXX: Don't allow this to be editable.
    #foreignLinkNameWidget = newforms.Select(attrs={"class":"editable"}, choices = ()) 
    foreignLinkNameWidget = newforms.Select(choices = ()) 

    t = template.loader.get_template("ajaxlinkadd.html")
    tContext = {
      "lookupURL":self.lookupURL,
      "linkLookupURL":self.linkLookupURL,
      "name":name,
      "localLinkNameWidget":localLinkNameWidget,
      "foreignLinkNameWidget":foreignLinkNameWidget.render(name = foreignLinkID, value=None, attrs={"id":foreignLinkID}),
      "localLinkID":localLinkID,
      "foreignLinkID":foreignLinkID,
      "wikidpage":self.wikidpage,
      "localLinkName":localLinkName,
      "inline":inline,
    }
    return t.render(template.Context(tContext))

    #if value != '': final_attrs['value'] = smart_unicode(value) # Only add the 'value' attribute if a value is non-empty.
    #return u'<input%s />' % flatatt(final_attrs)



class FileUploadForm(newforms.Form): 
  attach_file = newforms.Field(widget=newforms.FileInput())

  def save(self, wikidpage, uploadPath) :
    filename = self.clean_data['attach_file']['filename']
    data = self.clean_data['attach_file']['content']
    debugOutput("Saving %s" % filename)
   
    # Try to make a safe name for duplicate names.
    for i in range(0,100) :
      if i > 0 :
        safeFilename = "%s-%s" % (i, filename)
      else :
        safeFilename = filename
      filePath = os.path.join(uploadPath, safeFilename)
      if not os.path.exists(filePath) :
        break
    
    open(filePath, "w").write(data)

    if wikidbase.core.models.PROP_ATTACHMENTS not in wikidpage.properties :
      wikidpage.properties[wikidbase.core.models.PROP_ATTACHMENTS] = {}
    fileAttachments = wikidpage.properties[wikidbase.core.models.PROP_ATTACHMENTS]
    fileAttachments[safeFilename] = safeFilename
    debugOutput("fileAttachments: %s" % fileAttachments)


class FieldConfigForm(newforms.Form) :

  def __init__(self, listChoices, sortChoices, *args, **kwargs):
    debugOutput("Creating")
    super(FieldConfigForm, self).__init__(*args, **kwargs)
    self.fields["field_type"] = newforms.ChoiceField(required=True, choices=listChoices)#, widget=newforms.RadioSelect)
    self.fields["list_sort"] = newforms.ChoiceField(required=True, choices=sortChoices)#, widget=newforms.RadioSelect)
    self.fields["list_values"] = newforms.CharField(required=False, widget=newforms.Textarea(attrs={"cols":35,"rows":15}))



#
# oldforms
#

class EditableSelectField(oldforms.SelectField) :
  def render(self, data):
    output = ['<select id="%s" class="v%s%s editable" name="%s" size="%s">' % \
        (self.get_id(), self.__class__.__name__,
         self.is_required and ' required' or '', self.field_name, self.size)]
    str_data = str(data) # normalize to string
    for value, display_name in self.choices:
        selected_html = ''
        if str(value) == str_data:
            selected_html = ' selected="selected"'
        output.append('    <option value="%s"%s>%s</option>' % (escape(value), selected_html, escape(display_name)))
    output.append('  </select>')
    return '\n'.join(output)

  def isValidChoice(self, data, form):
    pass

class TextFieldExtra(oldforms.TextField) :
  def render(self, data):
    html = oldforms.TextField.render(self, data)
    return "%s %s" % (html, getFieldExtras(data))

class LargeTextFieldExtra(oldforms.LargeTextField) :
  def render(self, data):
    html = oldforms.LargeTextField.render(self, data)
    return "%s %s" % (html, getFieldExtras(data))

class NickDatetimeField(oldforms.TextField):
  def __init__(self, field_name, length=30, maxlength=None, is_required=False, validator_list=None, showsTime=True, inputDate=True):
    if validator_list is None: validator_list = []
    self.field_name = field_name
    self.length, self.maxlength = length, maxlength
    self.is_required = is_required
    
    if inputDate :
      if showsTime :
        self.validator_list = [isValidDatetime] + validator_list
      else :
        self.validator_list = [isValidDate] + validator_list
    else :
      self.validator_list = [isValidTime] + validator_list
        
    self.showsTime = showsTime
    self.inputDate = inputDate

  # XXX: Hmmm, do I need this???
  def html2python(data):
    "Converts the field into a datetime.datetime object"
    import datetime
    try:
      date, time = data.split()
      y, m, d = date.split('-')
      timebits = time.split(':')
      h, mn = timebits[:2]
      if len(timebits) > 2:
        s = int(timebits[2])
      else:
        s = 0
      return datetime.datetime(int(y), int(m), int(d), int(h), int(mn), s)
    except ValueError:
      return None
  html2python = staticmethod(html2python)

  
  def _calendarSetupString(self, inputFieldID, triggerButtonID) :

    if self.inputDate :
      inputFormat = self.showsTime and datatype.DEFAULT_DATETIME_FORMAT or datatype.DEFAULT_DATE_FORMAT
    else :
      inputFormat = datatype.DEFAULT_TIME_FORMAT
 
    # TODO: Really this should use a template.
    html = """<script type="text/javascript">
Calendar.setup({
  inputField     :    "%s",
  ifFormat       :    "%s",
  showsTime      :    %s,
  button         :    "%s",
  singleClick    :    true,
  step           :    1,
});
</script>
""" % (inputFieldID, inputFormat, self.showsTime and "true" or "false", triggerButtonID)
    
    return html

  def render(self, data):
    if data is None:
      data = ''
    maxlength = ''
    if self.maxlength:
      maxlength = 'maxlength="%s" ' % self.maxlength
    if isinstance(data, unicode):
      data = data.encode(django.conf.settings.DEFAULT_CHARSET)
   
    triggerID = self.get_id()+"_trigger"
   
    return """<input type="%s" id="%s" class="v%s%s" name="%s" size="%s" value="%s" %s/> <button type="reset" id="%s">...</button>%s""" % \
      (self.input_type, self.get_id(), self.__class__.__name__, self.is_required and ' required' or '',
      self.field_name, self.length, escape(datatype.convert(data, mode=datatype.TO_STRING, form=datatype.STRING_FORM_SHORT)), maxlength, triggerID, self._calendarSetupString(self.get_id(), triggerID))


