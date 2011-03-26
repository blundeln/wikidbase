function getSelectionId(text, li) {
  options = $("linkfield").options;

  // Now get the available fields for this id.
  updateLinks(li.id);
}

function updateLinks(id) {
  //alert("Updating links for " + id);
  new Ajax.Request('linkfields.html', { method:'get',
      onSuccess: function(transport){
      json = eval("("+transport.responseText+")");
      //alert(json); 
      options = $("linkfield").options;
      options.length = 0;
      for (var i = 0; i < json.length; i++) {
        options[i] = new Option(json[i],json[i]);
      }
      $("pageID").value = id;
      }
  });
}
