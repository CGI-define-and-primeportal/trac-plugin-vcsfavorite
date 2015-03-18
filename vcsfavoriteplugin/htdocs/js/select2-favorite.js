// Once the page is fully loaded
$(document).ready(function() {
  $(".favorites-select2").vcsFavorites();
});

(function($) {
  $.fn.vcsFavorites = function(opts) {

    // Allow the user to add custom select2 options
    opts = opts || {};
    opts = $.extend(select2Options, opts);

    return this.each(function() {

      // Generate our select2 object
      var $select = $(this).select2(opts);

      // Get the underlying instance methods
      var select2_data = $select.data("select2");

      // Overwrite the onselect method, to check for a click on our icon
      select2_data.onSelect = (function(fn) {
        return function(data, options) {
          var target;
          if(options != null) target = $(options.target);
          if(target && target.hasClass('toggleable')) {
            toggle_favorite(data, target);
          }
          else {
            return fn.apply(this, arguments);
          }
        }
      })(select2_data.onSelect);
    });
  };

  // Toggle the favorite, this will need to do an Ajax call,
  // and then should redraw the icon
  function toggle_favorite(data,target) {
    var newState = target.hasClass('fa-star-o'),
        path = data.id,
        defaultClasses = 'toggleable';

    target.attr('class', defaultClasses + ' fa fa-spinner fa-spin');
    $.post(window.tracBaseUrl + 'vcsfavorites/' + (newState ? 'add' : 'remove'), {
      path:path,
      '__FORM_TOKEN': window.formToken
    }, function(data,textStatus,jqXHR){
      if(jqXHR.status == 200){
        target.attr('class', defaultClasses + ' fa fa-star' + (newState ? '' : '-empty' ));
      }
      else {
        target.attr('class', defaultClasses + ' fa fa-star' + (newState ? '-empty' : '' ));
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
        icon = "<i class='toggleable " + (object.is_favorite ?  "fa fa-star" : "fa fa-star-o") + "'></i>";
      }
      return icon + text;
    }
  };

}(jQuery));