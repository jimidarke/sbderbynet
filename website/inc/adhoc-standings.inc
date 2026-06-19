<?php
// Ad-hoc leaderboard: best single time per pinny, grouped by the age group the
// coordinator picked for that pinny (RaceChart.agegroup_classid), top-N per group.
// Public-safe — emits the pinny + age-group label only, NEVER a racer name
// (project PII rule; in the roster-less model there are no names anyway).
//
// Racing all happens in one synthetic Ad-Hoc Open round; ranking is per age group
// straight off each result's stored age group — no roster / RegistrationInfo join.
// Grouping/limiting is done in PHP (not SQL window functions) for SQLite-version
// portability.

require_once('inc/data.inc');

// Returns an ordered list of groups:
//   array( array('classid'=>, 'class'=>, 'entries'=> array( array('carnumber','best_time','runs') ... )) )
// ordered by Classes.sortorder, each group holding its $limit fastest pinnies.
// 'carnumber' carries the display pinny (key kept for the renderer/kiosk).
function adhoc_leaderboard_groups($limit = 3) {
  global $db;
  $roundid = read_raceinfo('adhoc-roundid', false);

  $sql = 'SELECT rc.agegroup_classid AS classid, c.class, c.sortorder AS sortorder,'
       . '       rc.display_pinny AS pinny,'
       . '       MIN(rc.finishtime) AS best_time, COUNT(*) AS runs'
       . ' FROM RaceChart rc'
       . ' JOIN Classes c ON c.classid = rc.agegroup_classid'
       . ' WHERE rc.agegroup_classid IS NOT NULL'
       . '   AND rc.display_pinny IS NOT NULL'
       . '   AND rc.finishtime IS NOT NULL AND rc.finishtime < ' . DNF_TIME
       . '   AND COALESCE(rc.ignoretime, 0) = 0'
       . ($roundid !== false ? ' AND rc.roundid = :rid' : '')
       . ' GROUP BY rc.agegroup_classid, c.class, c.sortorder, rc.display_pinny'
       . ' ORDER BY c.sortorder, c.class, best_time ASC, CAST(rc.display_pinny AS INTEGER) ASC';

  $stmt = $db->prepare($sql);
  $stmt->execute($roundid !== false ? array(':rid' => $roundid) : array());

  $groups = array();
  $order = array();
  while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
    $cid = $row['classid'];
    if (!isset($groups[$cid])) {
      $groups[$cid] = array('classid' => $cid, 'class' => $row['class'], 'entries' => array());
      $order[] = $cid;
    }
    if (count($groups[$cid]['entries']) < $limit) {
      $groups[$cid]['entries'][] = array(
        'carnumber' => $row['pinny'],
        'best_time' => $row['best_time'],
        'runs' => $row['runs'],
      );
    }
  }
  $stmt->closeCursor();

  $out = array();
  foreach ($order as $cid) { $out[] = $groups[$cid]; }
  return $out;
}

// Render the leaderboard as one card/table per age group. Pinny + time only.
function adhoc_write_leaderboard($limit = 3) {
  $fmt = get_finishtime_formatting_string();
  $groups = adhoc_leaderboard_groups($limit);

  if (count($groups) == 0) {
    echo '<div class="adhoc-empty">No times yet — let\'s race!</div>';
    return;
  }

  foreach ($groups as $g) {
    echo '<div class="adhoc-group">';
    echo '<h2 class="adhoc-group-name">' . htmlspecialchars($g['class']) . '</h2>';
    echo '<table class="adhoc-board"><tbody>';
    $place = 0;
    foreach ($g['entries'] as $e) {
      $place++;
      echo '<tr class="adhoc-place adhoc-place-' . $place . '">';
      echo '<td class="adhoc-rank">' . $place . '</td>';
      echo '<td class="adhoc-pinny">' . htmlspecialchars(pinny_display($e['carnumber'])) . '</td>';
      echo '<td class="adhoc-time">' . htmlspecialchars(sprintf($fmt, $e['best_time'])) . '</td>';
      echo '</tr>';
    }
    echo '</tbody></table>';
    echo '</div>';
  }
}
?>
