<?php
// TODO - Write a photo src template as a data attribute instead of as the src,
//        then convert to a square photo size based on nlanes
//
// When presented as a kiosk page, i.e., when this php file is included from
// kiosks/ondeck.kiosk, the session_start() function will already have been
// called.  The @ is necessary to suppress the error notice that may arise in
// this case.
@session_start();
require_once('inc/data.inc');
require_once('inc/authorize.inc');
session_write_close();
require_once('inc/banner.inc');
require_once('inc/photo-config.inc');
require_once('inc/name-mangler.inc');
require_once('inc/schema_version.inc');
?>
<!DOCTYPE html>
<html>

<head>
  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
  <script type="text/javascript" src="js/jquery.js"></script>
  <script type="text/javascript" src="js/pinny.js"></script>
  <script type="text/javascript" src="js/ajax-setup.js"></script>
  <script type="text/javascript" src="js/modal.js"></script>
  <!-- For measure_text -->
  <script type="text/javascript" src="js/mobile.js"></script>
  <script type="text/javascript">
    var g_nlanes = <?php echo get_lane_count_from_results(); ?>;
    var g_show_car_photos = <?php echo read_raceinfo_boolean('show-cars-on-deck') ? "true" : "false"; ?>;
    var g_set_nextheat = true;
    var g_lane_colors = <?php
      $lane_colors_str = read_raceinfo('lane-colors', '');
      echo $lane_colors_str ? json_encode(explode(',', $lane_colors_str)) : '[]';
    ?>;
    // How long to celebrate a just-finished heat (medals) before advancing.
    var g_ondeck_linger_ms = <?php echo read_raceinfo('ondeck-linger-ms', 10000); ?>;
  </script>
  <script type="text/javascript" src="js/ondeck.js"></script>
  <?php if (isset($as_kiosk)) {
    require_once('inc/kiosk-poller.inc');
    echo "<style type='text/css'>\n";
    echo "body { overflow: hidden; }\n";
    echo "</style>\n";
  } ?>
  <title>Racers On Deck</title>
  <?php require('inc/stylesheet.inc'); ?>
  <link rel="stylesheet" type="text/css" href="css/kiosks.css" />
  <link rel="stylesheet" type="text/css" href="css/main-table.css" />
  <link rel="stylesheet" type="text/css" href="css/ondeck.css" />
  <link rel="stylesheet" type="text/css" href="css/lane-colors.css" />
</head>

<body class="<?php echo isset($as_kiosk) ? 'kiosk' : ''; ?>">
  <?php make_banner('Racers On Deck', isset($as_kiosk) ? '' : 'index.php'); ?>

  <div id="ondeck-header">
    <span class="od-flag">🏁</span>
    <span class="od-pill od-pill--round" id="od-round-pill"></span>
    <span class="od-pill od-pill--group" id="od-group-pill" style="display:none"></span>
  </div>

  <div class="schedule-wrapper">
    <table id="schedule" class="main_table curgroup">
    </table>
  </div>

  <?php require_once('inc/ajax-failure.inc'); ?>

  <div id='photo_view_modal' class="modal_dialog hidden block_buttons">
    <img id='photo_view_img' />
    <br />
    <input type="button" value="Close"
      onclick='close_modal("#photo_view_modal");' />
  </div>

</body>
</html>