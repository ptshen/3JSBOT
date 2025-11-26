var $head = $('.cube'),
    $eye = $('.pupil'),
    $paw = $('.paw'),
    $paw2 = $('.front'),
    $body = $('.inner'),
    $nose = $('.noseinner'),
    $x_axis  = $('#x-axis'),
    $y_axis  = $('#y-axis'),
    $shadow = $('.shadow'),
    $container = $('body'),
    container_w = $container.width(),
    container_h = $container.height();

$(window).on('mousemove.parallax', function(event) {
  var pos_x = event.pageX,
      pos_y = event.pageY,
      left  = 0,
      top   = 0;

  left = container_w / 2 - pos_x;
  top  = container_h / 2 - pos_y;
  
  TweenMax.to(
    $x_axis, 
    1, 
    { 
      css: { 
        transform: 'translateX(' + (left * -1) + 'px)' 
      }, 
      ease:Expo.easeOut, 
      overwrite: 'all' 
    });
  
  TweenMax.to(
    $y_axis, 
    1, 
    { 
      css: { 
        transform: 'translateY(' + (top * -1) + 'px)' 
      }, 
      ease:Expo.easeOut, 
      overwrite: 'all' 
    });
  TweenMax.to(
    $head, 
    1, 
    { 
      css: { 
        transform: 'rotateY(' + left / -22 + 'deg) rotateX(' + top / 26 + 'deg)' 
      }, 
      ease:Expo.easeOut, 
      overwrite: 'all' 
    });
  TweenMax.to(
    $eye, 
    1, 
    { 
      css: { 
        transform: 'translateX(' + left / -122 + 'px) translateY(' + top / -126 + 'px)' 
      }, 
      ease:Expo.easeOut, 
      overwrite: 'all' 
    });
  TweenMax.to(
    $body, 
    1, 
    { 
      css: { 
        boxShadow: '(' + left / 52 + 'px) (' + top / 20 + 'px) #4d341b' ,
        transform: 'rotateX(80deg) translateX(' + left / -52 + 'px) skewX(' + left / 22 + 'deg)'
      }, 
      ease:Expo.easeOut, 
      overwrite: 'all' 
    });
    TweenMax.to(
    $nose, 
    1, 
    { 
      css: { 
        boxShadow: '(' + left / 72 + 'px) (' + top / 90 + 'px) #000, (' + left / 82 + 'px) (' + top / 100 + 'px) #000, (' + left / 92 + 'px) (' + top / 120 + 'px) #000, (' + left / 102 + 'px) (' + top / 100 + 'px) #000' ,
        transform: 'translateX(' + left / -52 + 'px) skewX(' + left / 22 + 'deg)'
      }, 
      ease:Expo.easeOut, 
      overwrite: 'all' 
    });
    TweenMax.to(
    $shadow, 
    1, 
    { 
      css: { 
        transform: 'skew(' + left / 32 + 'deg)'
      }, 
      ease:Expo.easeOut, 
      overwrite: 'all' 
    });
    TweenMax.to(
    $paw, 
    1, 
    { 
      css: { 
        boxShadow: '(' + left / 32 + 'px) (' + top / 50 + 'px) #4d341b, (' + left / 42 + 'px) (' + top / 60 + 'px) #4d341b, (' + left / 62 + 'px) (' + top / 70 + 'px) #4d341b' ,
         transform: 'translateX(' + left / -122 + 'px) translateY(' + top / -126 + 'px)' 
      }, 
      ease:Expo.easeOut, 
      overwrite: 'all' 
    });
    
 });


$('.wrap').mousedown(function(){
	$('.wrap').addClass('happy');
});

$('.wrap').mouseup(function(){
	$('.wrap').removeClass('happy');
});