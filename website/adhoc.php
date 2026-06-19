<?php session_start(); ?>
<?php
require_once('inc/data.inc');
require_once('inc/authorize.inc');
require_once('inc/adhoc.inc');
session_write_close();
require_once('inc/banner.inc');

$adhoc_on = adhoc_mode_active();
$built_utc = read_raceinfo('adhoc-built-utc', '');
?><!DOCTYPE html>
<html>
<head>
  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
  <title>Ad-Hoc Racing — Start Line</title>
  <?php require('inc/stylesheet.inc'); ?>
  <link rel="stylesheet" type="text/css" href="css/adhoc.css" />
  <script type="text/javascript" src="js/jquery.js"></script>
  <script type="text/javascript" src="js/ajax-setup.js"></script>
  <script type="text/javascript">
    var g_adhoc_mode = <?php echo $adhoc_on ? 'true' : 'false'; ?>;
    var g_update_period = <?php echo (int)update_period(); ?>;
  </script>
  <script type="text/javascript" src="js/adhoc.js"></script>
</head>
<body>
<?php make_banner('Ad-Hoc Racing'); ?>

<div id="adhoc-page">

  <div id="adhoc-mode-bar" class="<?php echo $adhoc_on ? 'on' : 'off'; ?>">
    <span id="adhoc-mode-label"><?php echo $adhoc_on ? 'AD-HOC MODE: ON' : 'AD-HOC MODE: OFF'; ?></span>
    <span id="adhoc-built" class="muted"><?php
      echo $adhoc_on && $built_utc ? 'roster built ' . htmlspecialchars($built_utc) : '';
    ?></span>
    <span class="mode-buttons">
      <button id="adhoc-build-btn" class="big-button">Build &amp; Switch to Ad-Hoc</button>
      <button id="adhoc-end-btn" class="big-button danger">End &amp; Back to Official</button>
    </span>
  </div>

  <div id="adhoc-warn-official" class="warn">
    You are on the <b>OFFICIAL</b> database. Turn ad-hoc mode on before entering racers.
  </div>

  <div id="adhoc-arm" class="panel">
    <h2>Next group at the line</h2>
    <div class="pinny-row">
      <label>Lane&nbsp;1<input type="text" class="pinny-input" id="pinny1" inputmode="numeric"
             autocomplete="off" placeholder="pinny" /></label>
      <label>Lane&nbsp;2<input type="text" class="pinny-input" id="pinny2" inputmode="numeric"
             autocomplete="off" placeholder="pinny" /></label>
      <label>Lane&nbsp;3<input type="text" class="pinny-input" id="pinny3" inputmode="numeric"
             autocomplete="off" placeholder="pinny" /></label>
    </div>
    <div class="arm-buttons">
      <button id="adhoc-arm-btn" class="big-button go">Arm Heat</button>
      <button id="adhoc-clear-btn" class="big-button">Clear</button>
    </div>
    <div id="adhoc-message" class="message"></div>
  </div>

  <div id="adhoc-status" class="panel">
    <h2>Current heat <span id="adhoc-heat-num"></span> <span id="adhoc-racing-badge"></span></h2>
    <table id="adhoc-lanes"><tbody></tbody></table>
    <div id="adhoc-timer" class="muted"></div>
  </div>

</div>
</body>
</html>
