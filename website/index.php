<?php @session_start();
////////////////////////////////////////////////////////////////////////////////////////////////////////
// 
// If you're seeing this page, your web server isn't configured correctly.  (PHP is not enabled.)
//
////////////////////////////////////////////////////////////////////////////////////////////////////////

// Redirects to setup page if the database hasn't yet been set up
require_once('inc/data.inc');
require_once('inc/schema_version.inc');
require_once('inc/banner.inc');
require_once('inc/authorize.inc');
require_once('inc/adhoc.inc');

// This first database access is surrounded by a try/catch in order to catch
// broken/corrupt databases (e.g., sqlite pointing to a file that's not actually
// a database).  The pdo may get created OK, but then fail on the first attempt
// to access.
try {
  $schema_version = schema_version();
} catch (PDOException $p) {
  $_SESSION['setting_up'] = 1;
  header('Location: setup.php');
  exit();
}
session_write_close();

$show_voting_button =
  $schema_version >= BALLOTING_SCHEMA &&
  read_single_value('SELECT COUNT(*) FROM BallotAwards') > 0;

// Pending heading is printed lazily just before the first visible button
// in its section, so empty sections (all permissions gated off) collapse.
$pending_section_heading = null;

function set_section_heading($title) {
  global $pending_section_heading;
  $pending_section_heading = $title;
}

function flush_section_heading() {
  global $pending_section_heading;
  if ($pending_section_heading !== null) {
    echo "<h2 class='menu_section_heading'>".htmlspecialchars($pending_section_heading)."</h2>\n";
    $pending_section_heading = null;
  }
}

// Returns true if we actually showed a button
function make_link_button($label, $link, $permission, $button_class) {
  if (have_permission($permission)) {
    flush_section_heading();
    echo "<a class='button_link ".$button_class."' href='".$link."'>".$label."</a>\n";
    return true;
  } else {
    return false;
  }
}

function make_spacer_if($cond) {
  if ($cond) {
    echo "<div class='index_spacer'>&nbsp;</div>\n";
  }
}

?><!DOCTYPE html>
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>
<title>Pinewood Derby Race Information</title>
<?php require('inc/stylesheet.inc'); ?>
<script type="text/javascript" src="js/jquery.js"></script>
<script type="text/javascript" src="js/modal.js"></script>
<script type="text/javascript">
// Ad-Hoc Racing toggle. POSTs action=adhoc.mode and, on success, lands on the
// coordinator page (when enabling) or back home (when disabling). Official event
// data is never touched — ad-hoc lives in a separate, isolated database.
function derbynet_adhoc_toggle(mode) {
  var on = (mode === 'on');
  var msg = on
    ? 'Switch to Ad-Hoc racing?\n\nThis builds a separate, isolated database for casual come-as-you-are fun runs. Your official event results are NOT touched, and you can switch back any time.'
    : 'Exit Ad-Hoc racing and return to the official event database?';
  if (!confirm(msg)) return false;
  $.ajax({type: 'POST', url: 'action.php', dataType: 'json',
          data: {action: 'adhoc.mode', mode: mode}})
   .done(function(data) {
     if (data && data.outcome && data.outcome.summary === 'success') {
       window.location = on ? 'coordinator.php' : 'index.php';
     } else {
       alert('Could not switch ad-hoc mode: ' +
             ((data && data.outcome && data.outcome.description) || 'unknown error'));
     }
   })
   .fail(function() { alert('Could not reach the server to switch ad-hoc mode.'); });
  return false;
}
</script>
<style type="text/css">
div.index_spacer {
  height: 24px;
}

div.index_background {
  width: 100%;
}

div.index_background.cols-2 div.index_column {
  width: 50%;
  display: inline-block;
  float: left;
}

div.index_background.cols-3 div.index_column {
  width: 33.333%;
  display: inline-block;
  float: left;
}

div.index_background.cols-4 div.index_column {
  width: 25%;
  display: inline-block;
  float: left;
}

@media (max-width: 1280px) {
  div.index_background.cols-4 div.index_column {
    width: 50%;
  }
}

@media (max-width: 1080px) {
  div.index_background.cols-3 div.index_column {
    width: 50%;
  }
  div.index_background.cols-3 div.index_column:nth-child(3) {
    width: 100%;
  }
}

/* Highlight the Ad-Hoc button while ad-hoc mode is active, so it is obvious the
   whole rig is on the isolated fun-run database and not the official event. */
a.button_link.adhoc_menu_button--on {
  background-color: #b35900;
  border-color: #8a4500;
  color: #fff;
}
</style>
</head>
<body>
<?php
  make_banner('', /* back_button */ false);

 $need_spacer = false;

 // Multi-column layout: Race Coordinator (SET_UP_PERMISSION) gets a 4-column
 // layout (Before / During / After / Other). Anyone else stays single-column.
 $num_columns = have_permission(SET_UP_PERMISSION) ? 4 : 1;
 $multi_column = $num_columns > 1;

echo "<div class='index_background cols-".$num_columns."'>\n";

if ($multi_column) {
  echo "<div class='index_column'>\n";
}

echo "<div class='block_buttons'>\n";

// *********** Before ***************
set_section_heading('Before the Race');
$need_spacer = make_link_button('Set-Up', 'setup.php', SET_UP_PERMISSION, 'before_button');
$need_spacer = make_link_button('Racing Groups', 'racing-groups.php', SET_UP_PERMISSION, 'before_button') || $need_spacer;
$need_spacer = make_link_button('Tournament', 'elimination-tournament.php', SET_UP_PERMISSION, 'before_button') || $need_spacer;
$need_spacer = make_link_button('Race Check-In', 'checkin.php', CHECK_IN_RACERS_PERMISSION, 'before_button') || $need_spacer;
if ($schema_version > 1) {
  $need_spacer = make_link_button('Racer Photos', 'photo-thumbs.php?repo=head', ASSIGN_RACER_IMAGE_PERMISSION, 'before_button') || $need_spacer;
  $need_spacer = make_link_button('Car Photos', 'photo-thumbs.php?repo=car', ASSIGN_RACER_IMAGE_PERMISSION, 'before_button') || $need_spacer;
} else {
  $need_spacer = make_link_button('Edit Racer Photos', 'photo-thumbs.php?repo=head', ASSIGN_RACER_IMAGE_PERMISSION, 'before_button') || $need_spacer;
}

make_spacer_if($need_spacer && $num_columns < 3);

// Column break before "During"
if ($multi_column) {
  echo "</div>\n";  // block_buttons
  echo "</div>\n";  // index_column
  echo "<div class='index_column'>\n";
  echo "<div class='block_buttons'>\n";
}

// *********** During ***************
set_section_heading('During the Race');
$need_spacer = make_link_button('Race Dashboard', 'coordinator.php', SET_UP_PERMISSION, 'during_button');
// Ad-Hoc Racing — build/enter (or exit) the isolated come-as-you-are database on
// the live rig. Coordinator-gated; the actual switch is a POST to action=adhoc.mode
// (see derbynet_adhoc_toggle), then we land on the coordinator page (enabling) or
// back home (disabling). The label + highlight reflect the persisted state.
if (have_permission(CONTROL_RACE_PERMISSION)) {
  flush_section_heading();
  $adhoc_on = adhoc_mode_active();
  echo "<a class='button_link during_button adhoc_menu_button"
       . ($adhoc_on ? " adhoc_menu_button--on" : "") . "'"
       . " href='coordinator.php'"
       . " onclick=\"return derbynet_adhoc_toggle('" . ($adhoc_on ? 'off' : 'on') . "');\">"
       . ($adhoc_on ? 'Exit Ad-Hoc Racing' : 'Ad-Hoc Racing')
       . "</a>\n";
  $need_spacer = true;
}
$need_spacer = make_link_button('Kiosk Dashboard', 'kiosk-dashboard.php', SET_UP_PERMISSION, 'during_button') || $need_spacer;
$need_spacer = make_link_button('LED Signs', 'ledsign-dashboard.php', SET_UP_PERMISSION, 'during_button') || $need_spacer;
// Virtual Hardware control panel — cloud twin only. Coordinator-gated.
// Opens in a popup window (not a new tab) so the test instruments stay
// visually separate from the main dashboard. The Pi build never sets
// DERBYNET_CLOUD_MODE so this link is hidden there.
if (function_exists('is_cloud_mode') && is_cloud_mode() && have_permission(CONTROL_RACE_PERMISSION)) {
  flush_section_heading();
  echo "<a class='button_link during_button' href='virtual/index.php'"
       . " onclick=\"window.open(this.href, 'derbynet_virtual_hw',"
       . " 'width=1400,height=900,toolbar=no,menubar=no,location=no,resizable=yes,scrollbars=yes');"
       . " return false;\">Virtual Hardware</a>\n";
  $need_spacer = true;
}
// TEMPORARILY HIDDEN: $need_spacer = make_link_button('Judging', 'judging.php', JUDGING_PERMISSION, 'during_button') || $need_spacer;
if (!have_permission(SET_UP_PERMISSION)) {
  $need_spacer = make_link_button('Slideshow', 'slideshow.php', VIEW_RACE_RESULTS_PERMISSION, 'during_button') || $need_spacer;
  if ($show_voting_button) {
    $need_spacer = make_link_button('Vote!', 'vote.php', VIEW_RACE_RESULTS_PERMISSION, 'during_button') || $need_spacer;
  }
}

// *********** During, part 2 ***************
$need_spacer = make_link_button('Racers On Deck', 'ondeck.php', -1, 'during_button') || $need_spacer;
$need_spacer = make_link_button('Results By Racer', 'racer-results.php', VIEW_RACE_RESULTS_PERMISSION, 'during_button')
    || $need_spacer;

// Column break before "After"
if ($multi_column) {
  echo "</div>\n";  // block_buttons
  echo "</div>\n";  // index_column

  echo "<div class='index_column'>\n";
  echo "<div class='block_buttons'>\n";
}

// *********** After ***************
set_section_heading('After the Race');
$need_spacer = make_link_button('Device status', 'device-status.php', VIEW_DEVICE_STATUS, 'after_button');

// TEMPORARILY HIDDEN: $need_spacer = make_link_button('Present Awards', 'awards-presentation.php', PRESENT_AWARDS_PERMISSION, 'after_button');
$need_spacer = make_link_button('Standings', 'standings.php', VIEW_AWARDS_PERMISSION, 'after_button') || $need_spacer;
$need_spacer = make_link_button('Export Results', 'export.php', VIEW_RACE_RESULTS_PERMISSION, 'after_button') || $need_spacer;

// TEMPORARILY HIDDEN: $need_spacer = make_link_button('Retrospective', 'history.php', SET_UP_PERMISSION, 'after_button') || $need_spacer;

make_spacer_if($need_spacer && $num_columns < 4);

// Column break before "Other" when using 4-column layout
if ($num_columns >= 4) {
  echo "</div>\n";  // block_buttons
  echo "</div>\n";  // index_column
  echo "<div class='index_column'>\n";
  echo "<div class='block_buttons'>\n";
}

// *********** Other ***************
set_section_heading('Other');
make_link_button('Documentation', 'docs/site/index.html', -1, 'other_button');
make_link_button('Schedule', 'render-document.php/summary/ScheduleDocument?options=%7B%7D&ids=0', VIEW_RACE_RESULTS_PERMISSION, 'other_button');
make_link_button('Printables', 'print.php', ASSIGN_RACER_IMAGE_PERMISSION, 'other_button');
// TEMPORARILY HIDDEN: make_link_button('About', 'about.php', -1, 'other_button');

if (@$_SESSION['role']) {
  make_link_button('Log out', 'login.php?logout', -1, 'other_button');
} else {
  make_link_button('Log in', 'login.php', -1, 'other_button');
}
if (is_cloud_mode() && !empty($_SESSION['tenant_slug'])) {
  make_link_button('Quit (switch sandbox)', 'tenant-picker.php?switch=1', -1, 'other_button');
}

echo "</div>\n";  // block_buttons
if ($multi_column) {
  echo "</div>\n";  // index_column
}

echo "</div>\n";  // index_background
echo "</body>\n";
echo "</html>\n";
?>

