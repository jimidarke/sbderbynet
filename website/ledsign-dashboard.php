<?php session_start(); ?>
<?php
require_once('inc/data.inc');
require_once('inc/authorize.inc');
session_write_close();
require_once('inc/banner.inc');
require_once('inc/ledsign-zones.inc');

require_permission(SET_UP_PERMISSION);

$zones = ledsign_zones();
?><!DOCTYPE html>
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>
<title>LED Signs</title>
<link rel="stylesheet" type="text/css" href="css/jquery-ui.min.css"/>
<?php require('inc/stylesheet.inc'); ?>
<link rel="stylesheet" type="text/css" href="css/mobile.css"/>
<script type="text/javascript" src="js/jquery.js"></script>
<script type="text/javascript" src="js/ajax-setup.js"></script>
<script type="text/javascript" src="js/jquery-ui.min.js"></script>
<script type="text/javascript" src="js/mobile.js"></script>
<script type="text/javascript" src="js/dashboard-ajax.js"></script>
<script type="text/javascript" src="js/ledsign-dashboard.js"></script>
<script type="text/javascript">
// Zone definitions for JavaScript
var g_ledsign_zones = <?php echo json_encode($zones, JSON_HEX_TAG | JSON_HEX_AMP | JSON_PRETTY_PRINT); ?>;
</script>
<style>
/* LED Sign Dashboard Styles */
.ledsign-dashboard {
  max-width: 1200px;
  margin: 0 auto;
}

.ledsign-stats {
  background: #f5f5f5;
  padding: 10px 15px;
  border-radius: 5px;
  margin-bottom: 20px;
}

.ledsign-stats span {
  margin-right: 20px;
}

.ledsign-list {
  margin-bottom: 30px;
}

.ledsign-card {
  background: white;
  border: 1px solid #ddd;
  border-radius: 5px;
  padding: 15px;
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.ledsign-card.unassigned {
  border-left: 4px solid #f0ad4e;
}

.ledsign-card.assigned {
  border-left: 4px solid #5cb85c;
}

.ledsign-info {
  flex: 1;
}

.ledsign-mac {
  font-family: monospace;
  font-size: 1.1em;
  font-weight: bold;
}

.ledsign-details {
  color: #666;
  font-size: 0.9em;
  margin-top: 5px;
}

.ledsign-status {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin-right: 5px;
}

.ledsign-status.online {
  background: #5cb85c;
}

.ledsign-status.offline {
  background: #d9534f;
}

.ledsign-zone-select {
  min-width: 200px;
}

.ledsign-zone-select select {
  width: 100%;
  padding: 8px;
  font-size: 1em;
}

.zone-summary {
  background: #f9f9f9;
  border: 1px solid #ddd;
  border-radius: 5px;
  padding: 15px;
}

.zone-summary h3 {
  margin-top: 0;
  margin-bottom: 15px;
  border-bottom: 1px solid #ddd;
  padding-bottom: 10px;
}

.zone-row {
  display: flex;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid #eee;
}

.zone-row:last-child {
  border-bottom: none;
}

.zone-name {
  flex: 1;
  font-weight: bold;
}

.zone-assigned {
  flex: 1;
  font-family: monospace;
  color: #666;
}

.zone-assigned.unassigned {
  color: #999;
  font-style: italic;
}

.no-signs {
  text-align: center;
  padding: 40px;
  color: #666;
  background: #f9f9f9;
  border-radius: 5px;
}

.no-signs p {
  margin: 10px 0;
}

.no-signs code {
  background: #eee;
  padding: 2px 6px;
  border-radius: 3px;
}

.refresh-btn {
  float: right;
}
</style>
</head>
<body>
<?php make_banner('LED Signs'); ?>

<div class="ledsign-dashboard">

  <div class="block_buttons refresh-btn">
    <input type="button" id="refresh-btn" value="Refresh" onclick="poll_ledsigns_now()"/>
  </div>

  <div class="ledsign-stats">
    <span>Discovered Signs: <strong id="stats-total">0</strong></span>
    <span>Assigned: <strong id="stats-assigned">0</strong></span>
    <span>Unassigned: <strong id="stats-unassigned">0</strong></span>
    <span style="color: #666; font-size: 0.9em;">Polling every 2 seconds</span>
  </div>

  <h3>Discovered LED Signs</h3>
  <div id="ledsign-list" class="ledsign-list">
    <div class="no-signs">
      <p>No LED signs discovered yet.</p>
      <p>LED signs will appear here when they connect to the network.</p>
      <p>Signs poll: <code>GET /ledsign.php?mac=AA:BB:CC:DD:EE:FF</code></p>
    </div>
  </div>

  <h3>Zone Assignment Summary</h3>
  <div id="zone-summary" class="zone-summary">
    <!-- Populated by JavaScript -->
  </div>

</div>

<?php require_once('inc/ajax-failure.inc'); ?>

</body>
</html>
