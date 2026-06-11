<?php session_start(); ?>
<?php
require_once('inc/data.inc');
require_once('inc/authorize.inc');
session_write_close();
require_once('inc/banner.inc');
require_once('inc/permissions.inc');

require_permission(CONTROL_RACE_PERMISSION);

$running = get_running_round();
$roundid = isset($running['roundid']) ? intval($running['roundid']) : -1;
$has_active_round = ($roundid > 0 && $roundid != TIMER_TEST_ROUNDID);

$roster = array();
if ($has_active_round) {
  global $db;
  $stmt = $db->prepare(
    'SELECT r.racerid, r.firstname, r.lastname, r.carnumber, r.carname,'
    . ' COUNT(*) AS unraced_heats'
    . ' FROM RegistrationInfo r'
    . ' INNER JOIN RaceChart c ON c.racerid = r.racerid'
    . ' WHERE c.roundid = :roundid'
    . '   AND c.finishtime IS NULL AND c.finishplace IS NULL'
    . ' GROUP BY r.racerid'
    . ' ORDER BY CAST(r.carnumber AS INTEGER), r.carnumber'
  );
  $stmt->execute(array(':roundid' => $roundid));
  while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
    $roster[] = array(
      'racerid'       => intval($row['racerid']),
      'firstname'     => $row['firstname'],
      'lastname'      => $row['lastname'],
      'carnumber'     => $row['carnumber'],
      'carname'       => $row['carname'],
      'unraced_heats' => intval($row['unraced_heats']),
    );
  }
}

$round_label = '';
if ($has_active_round) {
  $round_label = trim(($running['class'] ?? '') . ' — ' . ($running['roundname'] ?? ('Round ' . $running['round'])), ' —');
}
?><!DOCTYPE html>
<html>
<head>
  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Pull Forward</title>
  <?php require('inc/stylesheet.inc'); ?>
  <link rel="stylesheet" type="text/css" href="css/mobile.css" />
  <link rel="stylesheet" type="text/css" href="css/pull-forward.css" />
  <script type="text/javascript" src="js/jquery.js"></script>
  <script type="text/javascript" src="js/pinny.js"></script>
  <script type="text/javascript" src="js/ajax-setup.js"></script>
  <script type="text/javascript">
    var g_pf_roundid = <?php echo json_encode($roundid); ?>;
    var g_pf_has_active_round = <?php echo $has_active_round ? 'true' : 'false'; ?>;
    var g_pf_roster = <?php echo json_encode($roster, JSON_HEX_TAG | JSON_HEX_AMP); ?>;
    var g_pf_round_label = <?php echo json_encode($round_label, JSON_HEX_TAG | JSON_HEX_AMP); ?>;
  </script>
  <script type="text/javascript" src="js/pull-forward.js"></script>
</head>
<body>
<?php make_banner('Pull Forward', 'coordinator.php'); ?>

<div id="pf-page">
  <?php if (!$has_active_round): ?>
    <div class="pf-empty-state">
      <h2>No active round</h2>
      <p>Pull-forward only operates on the round that is currently racing.
         Start a round on the coordinator page, then come back here.</p>
    </div>
  <?php elseif (empty($roster)): ?>
    <div class="pf-empty-state">
      <h2>No racers with remaining heats</h2>
      <p><?php echo htmlspecialchars($round_label, ENT_QUOTES, 'UTF-8'); ?> has
         no racers with unraced heats. Nothing to pull forward.</p>
    </div>
  <?php else: ?>
    <div id="pf-round-banner">
      <span class="pf-round-label"><?php echo htmlspecialchars($round_label, ENT_QUOTES, 'UTF-8'); ?></span>
      <span class="pf-round-hint">Tap a racer to simulate dropping them out.</span>
    </div>

    <div id="pf-roster"></div>

    <div id="pf-preview" class="pf-section hidden" aria-live="polite">
      <!-- Filled in by renderProposal() -->
    </div>

    <div id="pf-error" class="pf-error hidden"></div>

    <div id="pf-actions" class="pf-actions hidden">
      <input type="button" class="pf-btn pf-btn-apply"   value="Apply"            onclick="pfApply(false);" />
      <input type="button" class="pf-btn pf-btn-announce" value="Apply + Announce" onclick="pfApply(true);"  />
      <input type="button" class="pf-btn pf-btn-discard" value="Discard"          onclick="pfDiscard();"   />
    </div>
  <?php endif; ?>
</div>

</body>
</html>
