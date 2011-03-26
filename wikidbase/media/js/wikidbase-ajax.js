
function updateContent(source, container) {
  d = $(container);
  
  myAjax = new Ajax.Updater(
      container, 
      source
  );

}

function getParentAJAXContainer(currentObject, containerClass) {
  ancestors = currentObject.ancestors();
  for (var i=0; i<ancestors.length;i++) {
     ancestor = ancestors[i];
     if ($(ancestor).hasClassName(containerClass)) {
        return ancestor;
     }
  }
  return none;
}
