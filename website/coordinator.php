<?php session_start(); ?>
<?php
require_once('inc/data.inc');
require_once('inc/authorize.inc');
session_write_close();
require_once('inc/banner.inc');
require_once('inc/partitions.inc');
require_once('inc/scenes.inc');

//require_permission(SET_UP_PERMISSION);  // TODO: What's the correct permission? 

$warn_no_timer = warn_no_timer();

?><!DOCTYPE html>
<html>
<head>
  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
  <title>Race Coordinator Page</title>
  <link rel="stylesheet" type="text/css" href="css/jquery-ui.min.css" />
  <?php require('inc/stylesheet.inc'); ?>
  <link rel="stylesheet" type="text/css" href="css/mobile.css" />
  <script type="text/javascript" src="js/jquery.js"></script>
  <script type="text/javascript" src="js/ajax-setup.js"></script>
  <script type="text/javascript" src="js/jquery-ui.min.js"></script>
  <link rel="stylesheet" type="text/css" href="css/coordinator.css" />
  <script type="text/javascript" src="js/mobile.js"></script>
  <script type="text/javascript" src="js/dashboard-ajax.js"></script>
  <script type="text/javascript" src="js/modal.js"></script>
  <script type="text/javascript" src="js/coordinator-controls.js"></script>
  <script type="text/javascript" src="js/coordinator-poll.js"></script>

  <!-- As of 28-03-2025 -->
  <!-- <script type="text/javascript" src="js/fake-timer.js"></script> -->  

  <script type="text/javascript" src="js/timer-alive.js"></script>
  <script type="text/javascript">
    var g_use_subgroups = <?php echo use_subgroups() ? "true" : "false"; ?>;
    var g_all_scenes = <?php echo json_encode(all_scenes(),
                                              JSON_HEX_TAG | JSON_HEX_AMP | JSON_PRETTY_PRINT); ?>;
    var g_current_scene = <?php echo json_encode(read_raceinfo('current_scene', ''),
                                                 JSON_HEX_TAG | JSON_HEX_AMP); ?>;

    $(function () {
      $("#replay-skipback option[value='<?php
      echo read_raceinfo('replay-skipback', '3000'); ?>']").attr('selected', 'selected');
      mobile_select_refresh('#replay-skipback');
      $("#replay-num-showings option[value='<?php
      echo read_raceinfo('replay-num-showings', '2'); ?>']").attr('selected', 'selected');
      mobile_select_refresh('#replay-num-showings');
      $("#replay-rate option[value='<?php
      echo read_raceinfo('replay-rate', '50'); ?>']").attr('selected', 'selected');
      mobile_select_refresh('#replay-rate');
    });
  </script>
  <style>
    input[type=number].lane-time {
      -moz-appearance: textfield;
      width: 105px;
    }

    input.lane-time::-webkit-inner-spin-button {
      -webkit-appearance: none;
    }

    input.lane-time::-webkit-outer-spin-button {
      -webkit-appearance: none;
      margin: 0;
    }
  </style>
</head>

<body>
  <?php make_banner('Race Dashboard'); ?>

  <div class="double_control_column">
    <div id="not-racing-warning" class="hidden">
      Turn on racing mode or <a target='_blank' href='timer-test.php'>simulate racing</a>
            if you wish to record results.
    </div>
    <div id="now-racing-group" class="scheduling_control_group">
      <p>Waiting for poll.coordinator query...</p>
    </div>
  </div>

  <div class="control_column_container">

    <div class="control_column">

      <div class="control_group heat_control_group">
        <div id="start_race_button_div" class="block_buttons hidden">
          <input type="button" value="Start Race" onclick="handle_start_race_button()" />
        </div>
        
        <?php if (read_raceinfo('show-simulate-results', 0)) { ?>
          <!-- <div class="block_buttons">
            <input type="button" value="Simulate Results" onclick="simulateRaceResults();" id="simulate-results-btn" />
          </div> -->
        <?php } ?>

        <div class="centered_flipswitch">
          <input type="checkbox" class="flipswitch" name="is-currently-racing" id="is-currently-racing"
            checked="checked" data-on-text="Racing" data-off-text="Not Racing" />
        </div>

        <div class="block_buttons">

          <div id="prev_heat_button" class="button_link" onclick="handle_previous_heat_button()">
            <img src="img/left-white-60.png" />
          </div>

          <input type="button" id="manual_results_button" value="Manual Results"
            onclick="on_manual_results_button_click(<?php echo !$warn_no_timer ? "true" : "false"; ?>)" />

          <div id="skip_heat_button" class="button_link" onclick="handle_skip_heat_button()">
            <img src="img/right-white-60.png" />
          </div>

          <input type="button" id="rerun-button" value="Re-Run" data-rerun="none" onclick="handle_rerun(this);" />
        </div>
      </div>

      <div id="supplemental-control-group" class="control_group block_buttons new_round_control hidden">
        <div id="now-racing-group-buttons"></div>
        <div id="add-new-rounds-button" class="hidden">
          <input type="button" value="Add New Rounds" onclick="show_choose_new_round_modal()" />
        </div>
      </div>

      <div class="control_group timer_control_group">
        <?php if (!$warn_no_timer) { ?>
          <p>Not monitoring timer state</p>
        <?php } else { ?>
          <div class="status_icon">
            <img id="timer_status_icon" src="img/status/unknown.png" />
          </div>

          <div id='timer-test' class="block_buttons">
            <a class="button_link" onclick="open_timer_window();">Timer</a>
            <a class='button_link' href='timer-test.php'>Test</a>
          </div>

          <h3>Timer Status</h3>
          <p><b id="timer_status_text">Timer status not yet updated</b></p>
          <p>The track has <span id="lane_count">an unknown number of</span> lane(s).</p>

          <div id='lane-timers' class="lane-timers">
            <!-- <table border="1" cellpadding="10" style="width:fit-content">
      <tbody>
        <?= print_r(read_raceinfo('tt-lane1')); ?>
        <tr>
          <td class="timer-label">Start Timer</td>
          <td class="timer-online">Online</td>
          <td class="timer-ready">Ready</td>
        </tr>
        <tr>
          <td class="timer-label">Lane 1 Timer</td>
          <td class="timer-online">Online</td>
          <td class="timer-ready">Ready</td>
        </tr>
        <tr>
          <td class="timer-label">Lane 2 Timer</td>
          <td class="timer-online">Online</td>
          <td class="timer-not-ready">NOT READY</td>
        </tr>
        <tr>
          <td class="timer-label">Lane 3 Timer</td>
          <td class="timer-offline">OFFLINE</td>
          <td class="timer-not-ready">NOT READY</td>
        </tr>
      </tbody>
    </table> -->


            <!-- <table border="1" cellpadding="10" style="width: fit-content">
      <thead>
        <tr>
          <td class="timer-label">Start Timer</td>
          <td class="timer-heading-status">Online</td>
          <td class="timer-heading-ready">Ready</td>
        </tr>
      </thead>
      <tbody id="timer-statuses">

      </tbody>
    </table> -->

            <!-- <div id='lane-timers' class="lane-timers"> -->
            <table border="1" cellpadding="10" style="width: auto; justify-self: center;">
              <thead>
                <tr>
                  <th>Lane</th>
                  <th>Is-Online</th>
                  <th>Is-Ready</th>
                  <th>Last Heartbeat</th>
                </tr>
              </thead>
              <tbody id="timer-statuses">
                <!-- Dynamic rows will be added here -->
              </tbody>
            </table>
            <!-- </div> -->


          </div>
        <?php } ?>
      </div>

      <!-- Virtual Timer Display (Testing Mode) -->
      <div id="virtual-timer-panel" class="control_group hidden">
        <div class="testing-mode-banner">
          &#9888; TESTING MODE - Race results are simulated
        </div>
        <h3>Virtual Timer Display</h3>
        <div id="virtual-lanes">
          <!-- Populated dynamically by JavaScript -->
        </div>
        <div class="block_buttons" style="margin-top: 15px;">
          <input type="button" id="simulate-race-btn" value="Simulate Race"
                 onclick="handle_simulate_race()" />
          <span id="simulation-status" style="margin-left: 10px; color: #ff9800;"></span>
        </div>
      </div>

      <div class="control_group replay_control_group">
        <div class="status_icon">
          <img id="replay_status_icon" src="img/status/unknown.png" />
        </div>
        <h3>Replay Status</h3>
        <p><b id="replay_status">Remote replay status not yet updated</b></p>
        <div id="test_replay" class="block_buttons">
          <input type="button" value="Trigger Replay" onclick="handle_test_replay();" />
        </div>
        <div class="block_buttons">
          <input type="button" value="Replay Settings" onclick="show_replay_settings_modal();" />
        </div>
      </div>

    </div>

    <div class="control_column">

      <div class="coordinator-control-group">
        <div id="scenes-control-coordinator">
          <label for="scenes-select-coordinator">Current scene:</label>
          <div id="select-wrap-coordinator">
            <select id="scenes-select-coordinator"></select>
          </div>
          <div id="scenes-status-message-coordinator"></div>
        </div>

        <hr class="coordinator-control-divider" />

        <div id="emergency-control-coordinator">
          <div id="emergency-status-banner" class="emergency-status-inactive">
            <span class="emergency-icon">⚠️</span>
            <span id="emergency-status-text">No Active Emergency</span>
          </div>
          <input type="button" id="emergency-clear-btn" value="✓ Clear Emergency"
                 onclick="handle_emergency_clear()" class="hidden" />
          <details id="emergency-broadcast-details" class="emergency-broadcast-details">
            <summary>🚨 Compose Emergency Broadcast</summary>
            <div class="emergency-broadcast-body">
              <label for="emergency-message-coordinator">
                <span class="emergency-label-icon">🚨</span> Emergency Broadcast:
              </label>
              <div class="emergency-char-counter">
                <span id="emergency-char-count">0</span>/255 characters
              </div>
              <div id="emergency-input-wrap-coordinator">
                <input type="text" id="emergency-message-coordinator"
                       maxlength="255"
                       placeholder="Enter EMERGENCY message for all kiosks and LED signs..."
                       oninput="update_emergency_char_count()" />
              </div>
              <div id="emergency-button-wrap">
                <input type="button" id="emergency-broadcast-btn" value="🚨 BROADCAST EMERGENCY"
                       onclick="handle_emergency_broadcast()" />
              </div>
            </div>
          </details>
        </div>
      </div>

      <div id="playlist-group" class="block_buttons">
        <a class='button_link' href='playlist.php'>Rounds Playlist</a>
        <div id="playlist-start">
          <input type="button" value="Start Playlist" onclick="handle_start_playlist();" />
        </div>
      </div>

      <div id="master-schedule-group" class="master_schedule_group"></div>
      <div id="ready-to-race-group" class="scheduling_control_group"></div>
      <div id="not-yet-scheduled-group" class="scheduling_control_group"></div>
      <div id="done-racing-group" class="scheduling_control_group"></div>

    </div>

  </div>

  <?php require_once('inc/ajax-failure.inc'); ?>

  <div id='schedule_modal' class="modal_dialog hidden block_buttons">
    <form>
      <p>How many times should each racer appear in each lane?</p>
      <select id="schedule_num_rounds">
        <option selected>1</option>
        <option>2</option>
        <option>3</option>
        <option>4</option>
        <option>5</option>
        <option>6</option>
      </select>

      <input id="schedule-and-race" type="submit" value="Schedule + Race" data-race="true"
        onclick='mark_clicked($(this));' />
      <input id="schedule-only" type="submit" value="Schedule Only" data-race="false"
        onclick='mark_clicked($(this));' />
      <input type="button" value="Cancel" onclick='close_modal("#schedule_modal");' />
    </form>
  </div>

  <div id='manual_results_modal' class="modal_dialog hidden block_buttons">
    <form>
      <input type="hidden" name="action" value="result.write" />
      <table></table>
      <input type="button" id="discard-results" onclick='handle_discard_results_button();' value="Discard Results" />
      <input type="submit" value="Change" />
      <input type="button" value="Cancel" onclick='close_modal("#manual_results_modal");' />
    </form>
  </div>

  <div id='replay_settings_modal' class="modal_dialog hidden block_buttons">
    <form>
      <input type="hidden" name="action" value="settings.write" />
      <label for="replay-skipback">Duration of replay, in seconds:</label>
      <!-- Value in milliseconds, must match as a string -->
      <select id="replay-skipback" name="replay-skipback">
        <!-- <option value="2000">2.0</option> -->
        <option value="2500">2.5</option>
        <option value="3000">3.0</option>
        <option value="3500">3.5</option>
        <option value="4000">4.0</option>
        <option value="4500">4.5</option>
        <option value="5000">5.0</option>
        <!-- <option value="5500">5.5</option> -->
        <option value="6000">6.0</option>
        <!-- <option value="6500">6.5</option> -->
      </select>

      <label for="replay-num-showings">Number of times to show replay:</label>
      <!-- Could be any positive integer -->
      <select id="replay-num-showings" name="replay-num-showings">
        <option value="1">1</option>
        <option value="2">2</option>
        <option value="3">3</option>
      </select>

      <label for="replay_rate">Replay playback speed:</label>
      <!-- Expressed as a percentage -->
      <select id="replay-rate" name="replay-rate">
        <option value="10">0.1x</option>
        <option value="25">0.25x</option>
        <option value="50">0.5x</option>
        <option value="75">0.75x</option>
        <option value="100">1x</option>
      </select>
      <input type="submit" value="Submit" />
      <input type="button" value="Cancel" onclick='close_modal("#replay_settings_modal");' />
    </form>
  </div>

  <div id='choose_new_round_modal' class="modal_dialog block_buttons hidden">
    <!-- Populated by script: see offer_new_rounds() -->
  </div>

  <div id='new-round-modal' class="modal_dialog wide_modal block_buttons hidden">
    <form>
      <div id='aggregate-by-div' class='aggregate-only for-choosing-constituents'>
        <label for='aggregate-by-checkbox'>Aggregate by &nbsp;</label>
        <input id='aggregate-by-checkbox' type='checkbox' class='flipswitch' onchange='on_aggregate_by_change()'
          data-off-text="<?php echo group_label(); ?>" data-on-text="<?php echo subgroup_label(); ?>" />
      </div>

      <div id="new-round-common">
        <div>
          <label for='new-round-top'>Choose top &nbsp;</label>
          <input id='new-round-top' type='number' name="top" value="3" class='not-mobile' />
          <span id="new-round-top-racers" class='hidden follow-on-only'>&nbsp; racers</span>
        </div>

        <div id='bucketed-div'>
          <label for='bucketed-checkbox'>racers from &nbsp;</label>
          <input id='bucketed-checkbox' type='checkbox' class='flipswitch' name="bucketed"
            data-group-text="Each <?php echo group_label(); ?>"
            data-subgroup-text="Each <?php echo subgroup_label(); ?>"
            data-on-text="Each <?php echo subgroup_label(); ?>" data-off-text="Overall" />
        </div>
      </div>

      <div id='agg-classname-div' class='aggregate-only'>
        <label for='agg-classname'>Name for new round:</label>
        <input id='agg-classname' type='text' name="classname" value="Grand Finals" />
      </div>

      <div id='constituent-clip' class='aggregate-only for-choosing-constituents'>
        <div id='constituent-div'>
          <div id='constituent-rounds'></div>
          <div id='constituent-subgroups'></div>
        </div>
      </div>

      <input type="submit" value="Submit" />
      <input type="button" value="Cancel" onclick='g_new_round_modal_open = false; close_modal("#new-round-modal");' />
    </form>
  </div>

  <div id='unschedule_modal' class="modal_dialog hidden block_buttons">
    <p>Round <span id="unschedule_round"></span> for <span id="unschedule_class"></span>
      has a schedule, but no heats have been run. If you want to add or remove racers,
      you need to delete the schedule for this round. Is that what you would like to do?</p>
    <form>
      <input type="submit" value="Unschedule" />
      <input type="button" value="Cancel" onclick='close_modal("#unschedule_modal");' />
    </form>
  </div>


  <div id="purge_modal" class="modal_dialog wide_modal block_buttons hidden">
    <div id="purge_modal_inner">
      <form>
        <h3><span id="purge_round_name"></span> Round <span id="purge_round_no"></span></h3>
        <p>This round has <span id="purge_results_count"></span> heat(s) with results.</p>
        <input type="submit" value="Purge Results" />

        <p>&nbsp;</p>
        <input type="button" value="Cancel" onclick='close_modal("#purge_modal");' />
      </form>
    </div>
  </div>

  <div id="purge_confirmation_modal" class="modal_dialog block_buttons hidden">
    <form>
      <p>You are about to purge all the race results for this round.
        This operation cannot be undone.
        Are you sure that's what you want to do?</p>

      <input type="submit" value="Purge Results" />

      <p>&nbsp;</p>
      <input type="button" value="Cancel" onclick='close_secondary_modal("#purge_confirmation_modal");' />
    </form>
  </div>

  <div id='delete_round_modal' class="modal_dialog hidden block_buttons">
    <p>Round <span id="delete_round_round"></span> for <span id="delete_round_class"></span>
      has no schedule, and no heats have been run. To choose different racers for this round,
      you need to delete this round and generate a new one. Is that what you would like to do?</p>
    <form>
      <input type="submit" value="Delete Round" />
      <input type="button" value="Cancel" onclick='close_modal("#delete_round_modal");' />
    </form>
  </div>

  <div id='emergency_confirm_modal' class="modal_dialog emergency-modal hidden block_buttons">
    <div class="emergency-modal-header">
      <span class="emergency-modal-icon">🚨</span>
      <h3>Confirm Emergency Broadcast</h3>
    </div>
    <div class="emergency-modal-body">
      <p class="emergency-warning-text">
        <strong>This will immediately display an emergency message on:</strong>
      </p>
      <ul class="emergency-targets">
        <li>All kiosk displays</li>
        <li>All LED signs</li>
      </ul>
      <p class="emergency-preview-label">Message to broadcast:</p>
      <div class="emergency-preview-box">
        <span id="emergency-preview-message"></span>
      </div>
      <p class="emergency-persist-warning">
        ⚠️ This message will persist until you explicitly clear it.
      </p>
    </div>
    <div class="emergency-modal-buttons">
      <input type="button" id="emergency-confirm-yes" value="🚨 YES, BROADCAST NOW"
             onclick="confirm_emergency_broadcast()" />
      <input type="button" id="emergency-confirm-no" value="Cancel"
             onclick='close_modal("#emergency_confirm_modal");' />
    </div>
  </div>

  <div id='emergency_clear_confirm_modal' class="modal_dialog hidden block_buttons">
    <h3>Clear Emergency Broadcast?</h3>
    <p>This will remove the emergency message from all kiosks and LED signs.</p>
    <p>Are you sure the emergency situation has been resolved?</p>
    <div class="block_buttons">
      <input type="button" value="Yes, Clear Emergency"
             onclick="confirm_emergency_clear()" />
      <input type="button" value="Cancel"
             onclick='close_modal("#emergency_clear_confirm_modal");' />
    </div>
  </div>

  <div id='pull_forward_modal' class="modal_dialog wide_modal hidden block_buttons">
    <h3>Pull Forward — Fill Schedule Gaps</h3>
    <div id="pf-dropout-info" class="pf-section">
      <p><strong>Dropout:</strong> <span id="pf-dropout-name"></span>
        (<span id="pf-dropout-carnumber"></span>)
        — <span id="pf-gaps-count"></span> gap(s) to fill</p>
    </div>
    <div id="pf-cascade-preview" class="pf-section">
      <h4>Schedule Changes</h4>
      <table id="pf-moves-table" class="pf-table">
        <thead>
          <tr>
            <th>Fill Heat</th>
            <th>Lane</th>
            <th>Racer Moved</th>
            <th>From Heat</th>
          </tr>
        </thead>
        <tbody></tbody>
      </table>
    </div>
    <div id="pf-trailing-byes" class="pf-section hidden">
      <h4>Remaining Empty Lanes</h4>
      <p id="pf-byes-list"></p>
    </div>
    <div id="pf-warnings" class="pf-section hidden">
      <h4>Fairness Warnings</h4>
      <ul id="pf-warnings-list"></ul>
    </div>
    <div class="block_buttons">
      <input type="button" value="Accept" onclick="executePullForward(false);" />
      <input type="button" value="Accept + Announce" onclick="executePullForward(true);" />
      <input type="button" value="Cancel" onclick='close_modal("#pull_forward_modal");' />
    </div>
  </div>
</body>
</html>