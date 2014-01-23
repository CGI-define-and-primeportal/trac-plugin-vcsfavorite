jQuery(document).ready(function($) {
    $('#favorite_path').autocomplete({
      source: function(request, response) {
    	console.error('Funktion running');
    	repo_path_endpoint = tracBaseUrl + "diff";
        $.get(repo_path_endpoint, {q:request.term, format:'json'}, response)
      },
      minLength: 1
    })
  });