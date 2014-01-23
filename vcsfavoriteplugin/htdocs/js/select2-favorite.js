// Once the page is fully loaded
$(document).ready(function() {
  // Toggle the favorite, this will need to do an Ajax call, and then should redraw the icon
  function toggle_favorite(data,target) {
    var newState = target.hasClass('icon-star-empty'),
        path = data.id,
        defaultClasses = 'toggleable';
    console.log(path);
    target.attr('class', defaultClasses + ' icon-spinner icon-spin');
    $.post(window.tracBaseUrl + 'vcsfavorites/' + (newState ? 'add' : 'remove'), {
      path:path,
      '__FORM_TOKEN': window.formToken
    }, function(data,textStatus,jqXHR){
      if(jqXHR.status == 200){
        target.attr('class', defaultClasses + ' icon-star' + (newState ? '' : '-empty' ));
      }
      else {
        target.attr('class', defaultClasses + ' icon-star' + (newState ? '-empty' : '' ));
      }
    });
  }
  var select2Options = {
    width: "off",
    placeholder :'Search directories or select from favorites',
    dropdownCssClass: "ui-dialog favorites-dropdown",
    ajax: {
      url: window.tracBaseUrl + 'vcsfavorites',
      dataType: 'json',
      data : function(term,page) {
        return {
          format:'json',
          q: term
          }
      },
      results : function(data,page){
        return {
          results: data
        }
      }
    },
    formatResult: function(object, container, query) {
      var text = object.text,
          icon = "";
      if (object.id && object.hasOwnProperty('is_favorite')){
        icon = "<i class='toggleable " + (object.is_favorite ?  "icon-star" : "icon-star-empty") + "'></i>";
      }
      return icon + text;
    }
  }

  // Generate our select2 object
  var $select = $(".favorites-select2").select2(select2Options);
  console.log($select);
  // Get the underlying instance methods    
  var select2_data = $select.data("select2");
  console.log(select2_data);
  // Overwrite the onselect method, to check for a click on our icon
  select2_data.onSelect = (function(fn) {
    return function(data, options) {
      console.log(data,options);
      var target;            
      if (options != null) target = $(options.target);
      if (target && target.hasClass('toggleable')) {
        toggle_favorite(data, target);
      }
      else {
        return fn.apply(this, arguments);
      }
    }
  })(select2_data.onSelect);
});