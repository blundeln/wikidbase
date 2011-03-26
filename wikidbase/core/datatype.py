#
# Copyright (C) 2006 Nick Blundell.
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
# datatype (datatype.py)
# ----------------------
#
# Description:
#  Handles data type stuff.
#
# Author       : Nick Blundell
# Organisation : www.nickblundell.org.uk
# Version Info : $Id: datatype.py 953 2008-04-23 18:58:33Z blundeln $
#

import django.conf

import time, datetime, re
import parsedatetime.parsedatetime as pdatetime
from parsedatetime.parsedatetime_consts import Constants
from nbdebug import *

POSTCODE_RE = re.compile("[a-z]{1,2}\d{1,2}[a-z]?\s*\d[a-z]{2}",re.IGNORECASE)
URL_RE = re.compile("(http://\S+)|(www\.\S+)",re.IGNORECASE)
EMAIL_RE = re.compile("\S{2,}@\S{5,}",re.IGNORECASE)

STRING_FORM_SHORT = "STRING_FORM_SHORT"
STRING_FORM_LONG = "STRING_FORM_LONG"

TO_PYTHON = "TO_PYTHON"
TO_STRING = "TO_STRING"

DATETIME_LANG_CODE = django.conf.settings.LANGUAGE_CODE.lower() in ["en-gb","en-au"] and "en_AU" or "en_US"

TIME_FORMATS = [
  "%I:%M %p",
  "%I.%M %p",
  "%H:%M",
  "%H:%M:%S",
  "%I %p",
  "%H %p",
]

def getDateFormats(languageCode) :
  if languageCode in ["en-gb","en-au"] :
    return [
      "%d/%m/%Y",
      "%d.%m.%Y",
      "%d-%m-%Y",
      "%d/%m/%y",
    ]
  else :
    return [
      "%m/%d/%Y",
      "%m.%d.%Y",
      "%m-%d-%Y",
      "%m/%d/%y",
    ]

DATE_FORMATS = getDateFormats(django.conf.settings.LANGUAGE_CODE.lower())


BOOLEAN_TRUE = [
  "yes",
  "true",
  "enabled",
  "on",
]

BOOLEAN_FALSE = [
  "no",
  "false",
  "disabled",
  "off",
]

DEFAULT_TIME_FORMAT = TIME_FORMATS[0]
DEFAULT_DATE_FORMAT = DATE_FORMATS[0]
DEFAULT_DATETIME_FORMAT = DEFAULT_DATE_FORMAT + " " + DEFAULT_TIME_FORMAT


# Compile some regexes to quickly identify types.
reMightBeDateTime = re.compile(r"\bpm\b|\bam\b|:|day|/|week|month|year|tomorrow", re.IGNORECASE)
reMightBeBool = re.compile("|".join(BOOLEAN_TRUE + BOOLEAN_FALSE), re.IGNORECASE)
#TODO: MightBeInt

class CantConvert(Exception) : pass

#
# The methods should convert strings to python and vice versa.
#


def _datetime(data, mode, form) :

  debugOutput("Checking if '%s' is a date or time or both." % data)

  if mode == TO_STRING :
    if type(data) == datetime.date : dataString = data.strftime(DATE_FORMATS[0])
    elif type(data) == datetime.time : dataString = data.strftime(TIME_FORMATS[0])
    elif type(data) == datetime.datetime : dataString = data.strftime(DATE_FORMATS[0]+" "+TIME_FORMATS[0])
    return dataString.lower()
  else :
    try :
      humanParse = parseHumanDateTime(data)
      debugOutput("humanParse from %s -> %s" % (data, humanParse))
      return humanParse
    except Exception, e:
      debugOutput("Caught exception: %s" % e)
      pass
    
    raise CantConvert()


def _boolean(data, mode, form) :
 
  debugOutput("data = %s, mode = %s, form=%s." % (data, mode, form))
  
  if mode == TO_STRING :
    if data == True :
      return BOOLEAN_TRUE[0]
    else :
      return BOOLEAN_FALSE[0]
  else :
    normalisedData = data.lower().strip()

    if normalisedData in BOOLEAN_TRUE :
      return True
    elif normalisedData in BOOLEAN_FALSE :
      return False
    else :
      raise CantConvert()

# Some shortcut methods.
def toPython(data, form=STRING_FORM_LONG) : return convert(data, TO_PYTHON, form)
def toString(data, form=STRING_FORM_LONG) : return convert(data, TO_STRING, form)

def convert(data, mode, form=STRING_FORM_LONG) :
 
  debugOutput("data = %s, type= %s, mode = %s, form=%s." % (data, type(data), mode, form))
 
  if data == None :
    return None

  if mode == TO_STRING :
    if type(data) == bool :
      return _boolean(data, mode, form)
    elif type(data) in [datetime.date, datetime.time, datetime.datetime] :
      return _datetime(data, mode, form)
  
  elif type(data) == str :
   
    # TODO: Have to have a good think about recognising numbers.
    try : return int(data)
    except : 
      pass
    debugOutput("data not a number")

    if reMightBeBool.search(data) :
      try : return _boolean(data, mode, form)
      except CantConvert:
        pass
    debugOutput("data not a boolean")
    
    if "\n" not in data and len(data.split()) < 4 and reMightBeDateTime.search(data) :
      try : return _datetime(data, mode, form)
      except CantConvert:
        pass
    debugOutput("data not a date/time")
        


  # If all fails, return the data as it was.
  return data


def isDateType(dataType) :
  if dataType in [datetime.date, datetime.time, datetime.datetime] :
    return True
  else :
    return False

def getDatePart(data) :
  dataType = type(data)
  if dataType == datetime.datetime :
    return data.date()
  elif dataType == datetime.date :
    return data
  else :
    return None

def getTimePart(data) :
  dataType = type(data)
  if dataType == datetime.datetime :
    return data.time()
  elif dataType == datetime.time :
    return data
  else :
    return None


def getPostcode(data) :
  match = POSTCODE_RE.search(data)
  return match and str(match.group(0)) or None

def getEmailAddress(data) :
  match = EMAIL_RE.search(data)
  email = match and match.group(0) or None
  return email

def getURL(data) :
  match = URL_RE.search(data)
  url = match and match.group(0) or None
  if url and not url.lower().startswith("http://") :
    url = "http://%s" % url

  return url


def parseHumanDateTime(dtString) :
  debugOutput("parsing '%s'" % (dtString))
  # TODO: Adapt this to locale.
  parsedData = pdatetime.Calendar(Constants(fallbackLocales=[DATETIME_LANG_CODE])).parse(dtString)
  debugOutput("%s -> %s" % (dtString, parsedData))
  if parsedData[1] == 1 :
    return datetime.date(*parsedData[0][:3])
  elif parsedData[1] in [2,3] :
    return datetime.datetime(*parsedData[0][:6])
  else :
    raise CantConvert()


def cleverCmp(value1, value2) :
  """Tries to make a clever comparison between two potentially different data types."""
  debugOutput("compare '%s' with '%s'." % (value1, value2))
 
  if type(value1) == str and type(value2) == str :
    return cmp(value1.lower(), value2.lower())

  try :
    return cmp(value1, value2)
  except :
    return cmp(type(value1), type(value2))
