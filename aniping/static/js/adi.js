// Javascript Document
// Defines custom functions for aniping


// AJAX stuff
$("#login_err").css('display', 'none', 'important');
$("#form-signin").on('submit', function(e){
	$.ajax({
		type: "POST",
		url: "/login",
		data: "signin_username="+$('#signin_username').val()+"&signin_password="+$('#signin_password').val(),
		error: function(response){
			$("#login_err").css('display', 'block');
			$("#login_err").text("Invalid username or password.");
		},
		success: function(response){
			location.reload();
		}
	});
	
	e.preventDefault();
});

$("#logout_link").on('click', function(e){
	$.ajax({
		type: "GET",
		url: "/logout",
		success: function(response){
			location.reload();
		}
	});
	
	e.preventDefault();
});

$("a.star").on('click', function(e){
	$.ajax({
		type: "GET",
		url: $(this).attr('href'),
		success: function(response){
			var thisshow = "#show-"+response['id'];
			if ($(thisshow).hasClass("starred")) {
				$(thisshow).removeClass("starred");
			} else {
				$(thisshow).addClass("starred");
			}
		}
	});
	
	e.preventDefault();
});

$("#form-search").on('submit', function(e){
	term = $('#q').val();
	$.ajax({
		type: "GET",
		url: "/search",
		data: "q="+term,
		success: function(response){
			$(".container-fluid").html(response);
			if (term != ''){
				history.pushState(null, null, '/?q='+term);
			}else{
				history.pushState(null, null, '/');
			}
		}
	});
	
	e.preventDefault();
});