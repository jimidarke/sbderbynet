<?php @session_start();
require_once('inc/data.inc');
require_once('inc/authorize.inc');
session_write_close();
require_once('inc/banner.inc');
require_once('inc/schema_version.inc');
require_permission(SET_UP_PERMISSION);

if (schema_version() < PARTITION_SCHEMA) {
  header('Location: setup.php');
  exit(0);
}
?><!DOCTYPE html>
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>
<title>Elimination Tournament</title>
<?php require('inc/stylesheet.inc'); ?>
<link rel="stylesheet" type="text/css" href="css/mobile.css"/>
<link rel="stylesheet" type="text/css" href="css/racing-groups.css"/>
<script type="text/javascript" src="js/jquery.js"></script>
<script type="text/javascript" src="js/jquery-ui.min.js"></script>
<script type="text/javascript" src="js/ajax-setup.js"></script>
<script type="text/javascript" src="js/mobile.js"></script>
<script type="text/javascript" src="js/modal.js"></script>
<script type="text/javascript" src="js/elimination-tournament.js"></script>
</head>
<body class="tournament-page">
<?php make_banner('Elimination Tournament', 'setup.php'); ?>

<div id="below-banner" class="tournament-shell">

<!-- Elimination Tournament Setup -->
<div id="tournament-setup-section" class="tournament-card">
  <h2 class="tournament-section-heading">Tournament Setup</h2>

  <p class="instructions">
    Pick a tournament format, then assign each racing group to an age group
    in that format and initialize. Once a group is initialized its bracket is
    locked.
  </p>

  <div id="tournament-config-selector">
    <label for="global-tournament-config">Format:</label>
    <select id="global-tournament-config">
      <option value="">-- Select Format --</option>
    </select>
    <input id="config-editor-button" class="modest-button" type="button"
           value="Edit"
           onclick="window.location.href='elimination-config-editor.php'"/>
  </div>

  <div id="tournament-config-details" class="hidden">
    <small><span id="config-age-groups-count">0</span> age groups defined</small>
  </div>

  <div id="tournament-class-assignments" class="hidden">
    <p class="warning-text">
      <strong>Warning:</strong> Once initialized, tournament cannot be changed.
    </p>
    <table id="class-tournament-table">
      <thead>
        <tr>
          <th>Class</th>
          <th>Age Group</th>
          <th>Status</th>
          <th></th>
        </tr>
      </thead>
      <tbody id="class-tournament-tbody"></tbody>
    </table>
  </div>

  <div id="no-config-message">
    <small>Select a format to assign classes.</small>
  </div>
</div>

</div><!-- below-banner -->
</body>
</html>
