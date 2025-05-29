<?php
/*
 * Copyright (C) 2025 Jimi Ford <jimiford@gmail.com>
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy of this software and 
 * associated documentation files (the "Software"), to deal in the Software without restriction, 
 * including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, 
 * and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, 
 * subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all copies or substantial 
 * portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT 
 * LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. 
 * IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, 
 * WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE 
 * SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

// Shared slideshow template that can be configured for different kiosk types
require_once('inc/banner.inc');
require_once('inc/photo-config.inc');
require_once('inc/slideshow-config.inc');

// Determine kiosk type from caller or default to slideshow
$kiosk_type = isset($slideshow_kiosk_type) ? $slideshow_kiosk_type : 'slideshow';
$slideshow_config = get_slideshow_config($kiosk_type);

// Include kiosks.inc if we're operating as a kiosk to get kiosk_parameters() function
if (isset($as_kiosk) || isset($slideshow_kiosk_type)) {
    require_once('inc/kiosks.inc');
}
?><!DOCTYPE html>
<html>
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>
    <title><?php echo htmlspecialchars($slideshow_config['title']); ?></title>
    <script type="text/javascript" src="js/jquery.js"></script>
<?php 
// Check if this is being used as a kiosk (either $as_kiosk is set or we're in a kiosk context)
if (isset($as_kiosk) || isset($slideshow_kiosk_type)) {
    require_once('inc/kiosk-poller.inc'); 
}
?>
<?php require('inc/stylesheet.inc'); ?>
    <link rel="stylesheet" type="text/css" href="css/kiosks.css"/>
    <link rel="stylesheet" type="text/css" href="css/slideshow.css"/>
    <script type="text/javascript">
       var g_kiosk_parameters = <?php
            if ((isset($as_kiosk) || isset($slideshow_kiosk_type)) && function_exists('kiosk_parameters')) {
                echo json_encode(kiosk_parameters());
            } else {
                echo "{}";
            }
       ?>;
       var g_slideshow_config = <?php echo get_slideshow_js_config($kiosk_type); ?>;
    </script>
    <script type="text/javascript" src="js/shared-slideshow.js"></script>
  </head>

  <body>
  <?php if (!isset($as_kiosk)) make_banner($slideshow_config['title']); ?>
  <div id="photo-background" class="photo-background">
    <div class="next">
      <img class='mainphoto' onload='mainphoto_onload(this)'
           src='slide.php/title<?php echo $slideshow_config['folder'] ? '/' . htmlspecialchars($slideshow_config['folder']) : ''; ?>'/>
    </div>
  </div>

  <?php if (isset($as_kiosk) || isset($slideshow_kiosk_type)) require('inc/ajax-failure.inc'); ?>
  </body>
</html>