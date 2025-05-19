<?php

// $_POST['rule']: 'one-group' or 'by-partition' (or 'custom')

require_once('inc/events.inc');
require_once('inc/form_groups_by_rule.inc');
require_once('inc/newracer.inc');
require_once('inc/partitions.inc');


if (!have_permission(CONTROL_RACE_PERMISSION)) {
  json_not_authorized();
} else if (!is_allowed_group_formation_rule($_POST['rule'])) {
  json_failure('bad-rule', 'Rule value '.$_POST['rule'].' not recognized.');
} else if (read_single_value('SELECT COUNT(*) FROM RaceChart'
                             .' WHERE finishtime IS NOT NULL OR finishplace IS NOT NULL')
           > 0) {
  json_failure('results-exist', 'Racing results already exist.');
} else {
  $current_rule = group_formation_rule();
  $new_rule = $_POST['rule'];
  
  // Only apply if rule actually changes
  if ($current_rule !== $new_rule) {
      record_event(EVENT_GROUP_FORMATION_RULE_APPLIED,
                  array('other' => $current_rule.' -> '.$new_rule));

      write_group_formation_rule($new_rule);
      write_raceinfo('use-subgroups', ($new_rule == 'by-partition') ? '0' : '1');

      form_groups_by_rule($new_rule);
      clean_up_empty_classes_and_ranks();
      record_action_partition_structure();
  }

  json_success();
}

?>
