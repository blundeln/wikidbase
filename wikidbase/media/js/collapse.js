// Borrowed from drupal: $Id: collapse.js,v 1.6 2006/04/14 13:48:56 killes Exp $

/**
 * Only enable Javascript functionality if all required features are supported.
 */
function isJsEnabled() {
  if (typeof document.jsEnabled == 'undefined') {
    // Note: ! casts to boolean implicitly.
    document.jsEnabled = !(
     !document.getElementsByTagName ||
     !document.createElement        ||
     !document.createTextNode       ||
     !document.documentElement      ||
     !document.getElementById);
  }
  return document.jsEnabled;
}

// Global Killswitch on the <html> element
if (isJsEnabled()) {
  document.documentElement.className = 'js';
}

/**
 * Make IE's XMLHTTP object accessible through XMLHttpRequest()
 */
if (typeof XMLHttpRequest == 'undefined') {
  XMLHttpRequest = function () {
    var msxmls = ['MSXML3', 'MSXML2', 'Microsoft']
    for (var i=0; i < msxmls.length; i++) {
      try {
        return new ActiveXObject(msxmls[i]+'.XMLHTTP')
      }
      catch (e) { }
    }
    throw new Error("No XML component installed!");
  }
}


/**
 * Emulate PHP's ereg_replace function in javascript
 */
function eregReplace(search, replace, subject) {
  return subject.replace(new RegExp(search,'g'), replace);
}

/**
 * Retrieves the absolute position of an element on the screen
 */
function absolutePosition(el) {
  var sLeft = 0, sTop = 0;
  var isDiv = /^div$/i.test(el.tagName);
  if (isDiv && el.scrollLeft) {
    sLeft = el.scrollLeft;
  }
  if (isDiv && el.scrollTop) {
    sTop = el.scrollTop;
  }
  var r = { x: el.offsetLeft - sLeft, y: el.offsetTop - sTop };
  if (el.offsetParent) {
    var tmp = absolutePosition(el.offsetParent);
    r.x += tmp.x;
    r.y += tmp.y;
  }
  return r;
};


/**
 * Adds a function to the window onload event
 */
function addLoadEvent(func) {
  var oldOnload = window.onload;
  if (typeof window.onload != 'function') {
    window.onload = func;
  }
  else {
    window.onload = function() {
      oldOnload();
      func();
    }
  }
}

/**
 * Toggles a class name on or off for an element
 */
function toggleClass(node, className) {
  if (!removeClass(node, className) && !addClass(node, className)) {
    return false;
  }
  return true;
}

/**
 * Returns true if an element has a specified class name
 */
function hasClass(node, className) {
  if (node.className == className) {
    return true;
  }
  var reg = new RegExp('(^| )'+ className +'($| )')
  if (reg.test(node.className)) {
    return true;
  }
  return false;
}

/**
 * Removes an element from the page
 */
function removeNode(node) {
  if (typeof node == 'string') {
    node = $(node);
  }
  if (node && node.parentNode) {
    return node.parentNode.removeChild(node);
  }
  else {
    return false;
  }
}

/**
 * Adds a class name to an element
 */
function addClass(node, className) {
  if (hasClass(node, className)) {
    return false;
  }
  node.className += ' '+ className;
  return true;
}

/**
 * Removes a class name from an element
 */
function removeClass(node, className) {
  if (!hasClass(node, className)) {
    return false;
  }
  // Replaces words surrounded with whitespace or at a string border with a space. Prevents multiple class names from being glued together.
  node.className = eregReplace('(^|\\s+)'+ className +'($|\\s+)', ' ', node.className);
  return true;
}


if (isJsEnabled()) {
  addLoadEvent(collapseAutoAttach);
}

function collapseAutoAttach() {
  var fieldsets = document.getElementsByTagName('fieldset');
  var legend, fieldset;
  for (var i = 0; fieldset = fieldsets[i]; i++) {
    if (!hasClass(fieldset, 'collapsible')) {
      continue;
    }
    legend = fieldset.getElementsByTagName('legend');
    if (legend.length == 0) {
      continue;
    }
    legend = legend[0];
    var a = document.createElement('a');
    a.href = '#';
    a.onclick = function() {
      toggleClass(this.parentNode.parentNode, 'collapsed');
      if (!hasClass(this.parentNode.parentNode, 'collapsed')) {
        collapseScrollIntoView(this.parentNode.parentNode);
        //if (typeof textAreaAutoAttach != 'undefined') {
          // Add the grippie to a textarea in a collapsed fieldset.
        //  textAreaAutoAttach(null, this.parentNode.parentNode);
        //}
      }
      this.blur();
      return false;
    };
    a.innerHTML = legend.innerHTML;
    while (legend.hasChildNodes()) {
      removeNode(legend.childNodes[0]);
    }
    legend.appendChild(a);
    collapseEnsureErrorsVisible(fieldset);
  }
}

function collapseEnsureErrorsVisible(fieldset) {
  if (!hasClass(fieldset, 'collapsed')) {
    return;
  }
  var inputs = [];
  inputs = inputs.concat(fieldset.getElementsByTagName('input'));
  inputs = inputs.concat(fieldset.getElementsByTagName('textarea'));
  inputs = inputs.concat(fieldset.getElementsByTagName('select'));
  for (var j = 0; j<3; j++) {
    for (var i = 0; i < inputs[j].length; i++) {
      if (hasClass(inputs[j][i], 'error')) {
        return removeClass(fieldset, 'collapsed');
      }
    }
  }
}

function collapseScrollIntoView(node) {
  var h = self.innerHeight || document.documentElement.clientHeight || document.body.clientHeight || 0;
  var offset = self.pageYOffset || document.documentElement.scrollTop || document.body.scrollTop || 0;
  var pos = absolutePosition(node);
  if (pos.y + node.scrollHeight > h + offset) {
    if (node.scrollHeight > h) {
      window.scrollTo(0, pos.y);
    } else {
      window.scrollTo(0, pos.y + node.scrollHeight - h);
    }
  }
}
