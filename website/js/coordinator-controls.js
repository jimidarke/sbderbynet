// Requires dashboard-ajax.js

// g_current_heat_racers remembers who the racers in the current heat
// are, so the modal for manual heat result s can be populated when 
// displayed.
g_current_heat_racers = new Array();

// Processing a response from coordinator_poll can force the isracing
// flipswitch to change state.  We don't want that change to trigger
// an ajax request to update the database: if we get a little bit out
// of sync with the database, it'll put us into a feedback cycle that
// never ends.
//
// Use this boolean to mark changes induced programmatically, as
// opposed to user input.
g_updating_current_round = false;

// If any of the "new round" modals is open, we don't want to be
// rewriting all the controls.  This boolean tells whether we have the
// modal open.
g_new_round_modal_open = false;

// Each time a polling result arrives, we update this array describing the
// rounds that have completed.  If the user clicks on the "Add New Round"
// button, this array is used to populate both the choose_new_round_modal and
// the new_round_modal dialogs.
g_completed_rounds = [];

// Roundids of an aggregate rounds
g_aggregate_rounds = [];
// {classid:, class:, by-subgroup:} for each aggregate class for which a
// first round could be created
g_ready_aggregate_classes = [];

// Controls for current racing group:

function handle_start_race_button() {
  $.ajax(g_action_url, {
    type: "POST",
    data: { action: "timer.remote-start" },
  });
}

function handle_isracing_change(event, scripted) {
  if (!g_updating_current_round) {
    $.ajax(g_action_url, {
      type: "POST",
      data: {
        action: "heat.select",
        now_racing: $("#is-currently-racing").prop("checked") ? 1 : 0,
      },
      success: function (json) {
        process_coordinator_poll_json(json);
      },
    });
  }
}
$(function () {
  $("#is-currently-racing").on("change", handle_isracing_change);
});

function handle_skip_heat_button() {
  $.ajax(g_action_url, {
    type: "POST",
    data: { action: "heat.select", heat: "next" },
    success: function (json) {
      process_coordinator_poll_json(json);
    },
  });
}

function handle_previous_heat_button() {
  $.ajax(g_action_url, {
    type: "POST",
    data: { action: "heat.select", heat: "prev" },
    success: function (json) {
      process_coordinator_poll_json(json);
    },
  });
}

// Manual start trigger for when hardware start timer is unavailable
function handle_manual_start_trigger() {
  $.ajax(g_action_url, {
    type: "POST",
    data: {
      action: "timer-message",
      message: "STARTED",
    },
    success: function (data) {
      console.log("Manual race start triggered");
    },
    error: function (xhr, status, error) {
      alert("Failed to trigger race start: " + error);
    },
  });
}

function handle_rerun(button) {
  var rerun_type = $(button).attr("data-rerun");
  // rerun_type values are: 'none', recoverable, available, current
  if (rerun_type == "current" || rerun_type == "available") {
    $.ajax(g_action_url, {
      type: "POST",
      data: {
        action: "heat.rerun",
        heat: rerun_type == "current" ? "current" : "last",
      },
      success: function (data) {
        process_coordinator_poll_json(data);
      },
    });
  } else if ((rerun_type = "recoverable")) {
    $.ajax(g_action_url, {
      type: "POST",
      data: { action: "heat.reinstate" },
      success: function (data) {
        process_coordinator_poll_json(data);
      },
    });
  }
}

// Controls for Replay
function handle_test_replay() {
    // Check if using HLS stream
    const devicePicker = $("#device-picker");
    if (devicePicker.val() === 'hls-stream') {
        const hlsUrl = devicePicker.data('hls-url');
        if (!hlsUrl) {
            console.error('No HLS stream URL configured');
            return;
        }
    }
    
    $.ajax(g_action_url, { 
        type: "POST", 
        data: { action: "replay.test" } 
    });
}

function trigger_replay() {
  $.ajax(g_action_url, { type: "POST", data: { action: "replay.trigger" } });
}

// Present the modal for entering manual heat results.
//
// If should_trigger_replay is true, and there aren't any existing results for
// this heat, then trigger a replay event as we're present the manual results
// modal.
function on_manual_results_button_click(should_trigger_replay) {
  // g_current_heat_racers: lane, name, carnumber, finishtime, finishplace
  var racer_table = $("#manual_results_modal table");
  racer_table.empty();
  // TODO Show place instead of time if using points
  racer_table.append(
    "<tr><th>Lane</th><th>Racer</th><th>Car</th><th>Time</th></tr>"
  );
  var any_results = false;
  for (var i = 0; i < g_current_heat_racers.length; ++i) {
    var racer = g_current_heat_racers[i];
    racer_table.append(
      "<tr><td>" +
      racer.lane +
      "</td>" +
      "<td>" +
      racer.name +
      "</td>" +
      "<td>" +
      racer.carnumber +
      "</td>" +
      "<td><input class='lane-time' type='number' step='0.00001'" +
      " name='lane" +
      racer.lane +
      "'" +
      " value='" +
      racer.finishtime +
      "'/>" +
      "</td>" +
      "</tr>"
    );
    if (racer.finishtime) {
      any_results = true;
    }
  }

  if (any_results) {
    $("#discard-results").removeClass("hidden");
  } else {
    if (should_trigger_replay) {
      trigger_replay();
    }
    $("#discard-results").addClass("hidden");
  }

  show_modal("#manual_results_modal", function (event) {
    handle_manual_results_submit();
    return false;
  });
}

function handle_manual_results_submit() {
  close_modal("#manual_results_modal");
  $.ajax(g_action_url, {
    type: "POST",
    data: $("#manual_results_modal form").serialize(),
    success: function (data) {
      process_coordinator_poll_json(data);
    },
  });
}

function handle_discard_results_button() {
  close_modal("#manual_results_modal");
  $.ajax(g_action_url, {
    type: "POST",
    // TODO: There's a risk that the coordinator form gets
    // grossly out of sync with the database, such that the
    // identification of 'current' heat is different from what
    // the user chose.  If current-heat changes while
    // manual-results dialog is open, maybe close the dialog
    // and start over?
    data: { action: "result.delete", roundid: "current", heat: "current" },
    success: function (data) {
      process_coordinator_poll_json(data);
    },
  });
}

// Controls for racing rounds

function show_schedule_modal(roundid) {
  console.log("show_schedule_modal called for roundid:", roundid);
  
  // Check if this round is part of an elimination tournament
  check_elimination_tournament_status(roundid, function(is_elimination, round_data) {
    console.log("Elimination tournament status:", is_elimination);
    
    if (is_elimination && round_data && round_data.races_per_racer) {
      // For elimination tournaments, skip the modal and schedule directly
      console.log("Elimination tournament detected - skipping modal, using races_per_racer:", round_data.races_per_racer);
      
      // Schedule directly with the value from JSON configuration
      handle_schedule_submit(roundid, round_data.races_per_racer, true);
      return;
    }
    
    // For non-elimination tournaments, show the normal modal
    prepare_normal_schedule_modal();
    
    // Show the modal
    show_modal("#schedule_modal", function (event) {
      var nTimesPerLane = $("#schedule_num_rounds").val();
      
      handle_schedule_submit(
        roundid,
        nTimesPerLane,
        $("input[clicked='true']", $(event.target)).attr("data-race") == "true"
      );
      return false;
    });
  });
}

function prepare_elimination_schedule_modal() {
  // Disable the dropdown and show explanation for elimination tournaments
  $("#schedule_num_rounds").prop("disabled", true);
  $("#schedule_modal p").html("Elimination tournament - race count determined by hardcoded configuration.");
  
  // Add visual indicator that this is an elimination tournament
  $("#schedule_modal").addClass("elimination-tournament-modal");
  
  console.log("Elimination tournament detected - dropdown disabled, using hardcoded parameters");
}

function prepare_normal_schedule_modal() {
  // Enable the dropdown for normal racing
  $("#schedule_num_rounds").prop("disabled", false);
  $("#schedule_modal p").html("How many times should each racer appear in each lane?");
  
  // Remove elimination tournament styling
  $("#schedule_modal").removeClass("elimination-tournament-modal");
}

function check_elimination_tournament_status(roundid, callback) {
  console.log("Checking elimination tournament status for roundid:", roundid);
  
  // Get the classid for this round directly from the database
  $.ajax(g_action_url, {
    type: 'GET', 
    data: {
      query: 'poll.coordinator'
    },
    success: function(data) {
      console.log("Coordinator poll response for round lookup");
      var classid = null;
      
      // Find classid from rounds data in coordinator poll
      if (data.rounds) {
        for (var i = 0; i < data.rounds.length; i++) {
          if (data.rounds[i].roundid == roundid) {
            classid = data.rounds[i].classid;
            console.log("Found classid:", classid, "for roundid:", roundid);
            break;
          }
        }
      }
      
      if (classid) {
        // Check if this class has an active elimination tournament
        console.log("Checking elimination tournament status for classid:", classid);
        $.ajax(g_action_url, {
          type: 'GET',
          data: {
            query: 'elimination.tournament.status',
            classid: classid
          },
          success: function(tournamentData) {
            console.log("Tournament status response:", tournamentData);
            var isElimination = tournamentData.outcome && 
                               tournamentData.outcome.summary === 'success' && 
                               tournamentData.active;
            console.log("Is elimination tournament:", isElimination);
            
            if (isElimination && tournamentData.tournament) {
              // The API returns races_per_racer directly in the tournament info
              if (tournamentData.tournament.races_per_racer) {
                console.log("Found elimination tournament with races_per_racer:", tournamentData.tournament.races_per_racer);
                callback(true, {
                  races_per_racer: tournamentData.tournament.races_per_racer,
                  round_name: tournamentData.tournament.current_round_name
                });
              } else {
                console.log("Elimination tournament found but no races_per_racer data");
                callback(true, null);
              }
            } else {
              callback(isElimination, null);
            }
          },
          error: function(xhr, status, error) {
            console.log("Error checking tournament status:", status, error);
            // If we can't check, assume it's not an elimination tournament
            callback(false, null);
          }
        });
      } else {
        console.log("Could not find classid for roundid:", roundid, "in coordinator poll");
        // If we can't find the classid, assume it's not an elimination tournament
        callback(false, null);
      }
    },
    error: function(xhr, status, error) {
      console.log("Error getting coordinator poll:", status, error);
      callback(false, null);
    }
  });
}

// There are two different submit buttons for the schedule_modal, depending on
// whether we want to start racing immediately or not.  mark_clicked() runs as an
// onclick handler so we can distinguish between the two submit buttons.
function mark_clicked(submit_js) {
  $("input[type=submit]", submit_js.parents("form")).removeAttr("clicked");
  submit_js.attr("clicked", "true");
  return true; // Control now passes to show_schedule_modal's callback,
  // and then handle_schedule_submit
}

function handle_schedule_submit(roundid, n_times_per_lane, then_race) {
  close_modal("#schedule_modal");
  $.ajax(g_action_url, {
    type: "POST",
    data: {
      action: "schedule.generate",
      roundid: roundid,
      n_times_per_lane: n_times_per_lane,
    },
    success: function (data) {

      if (data.outcome.summary === "failure" && data.outcome.code === "unregistered_racers") {
        alert(data.outcome.description); // Display unregistered racers
        return; // Prevent further actions
      }

      process_coordinator_poll_json(data);


      // process_coordinator_poll_json(data);
      // console.log(data);

      // // Check for unregistered racers in the rounds
      // const unregisteredRounds = data.rounds.filter(
      //   (round) => round.registered < round.passed
      // );
      // if (unregisteredRounds.length > 0) {
      //   alert(
      //     `The following rounds have unregistered racers:\n` +
      //       unregisteredRounds
      //         .map(
      //           (round) =>
      //             `- ${round.name}: Registered ${round.registered}, Passed ${round.passed}`
      //         )
      //         .join("\n")
      //   );
      // }

      // // Handle other conditions (e.g., no heats scheduled)
      // const noHeatsRounds = data.rounds.filter(
      //   (round) => round.heats_scheduled === 0 && round.passed > 0
      // );
      // if (noHeatsRounds.length > 0) {
      //   alert(
      //     `The following rounds have no heats scheduled:\n` +
      //       noHeatsRounds.map((round) => `- ${round.name}`).join("\n")
      //   );
      // }

      if (then_race && data.outcome.summary == "success") {
        handle_race_button(roundid);
      }
    },
  });
}

function handle_reschedule_button(button, roundid) {
  g_poll_pending = true; // Stop polling while we're adjusting
  $(button)
    .prop("disabled", true)
    .parent()
    .find(".adjustment-in-progress-message")
    .removeClass("hidden");
  $.ajax(g_action_url, {
    type: "POST",
    data: { action: "schedule.reschedule", roundid: roundid },
    success: function (json) {
      $(button).prop("disabled", false);
      process_coordinator_poll_json(json);
    },
    complete: function (jqxhr, text_status) {
      // Resume polling, whatever the outcome.
      g_poll_pending = false;
    },
  });
}

function handle_race_button(roundid) {
  $.ajax(g_action_url, {
    type: "POST",
    data: { action: "heat.select", roundid: roundid, heat: 1, now_racing: 1 },
    success: function (json) {
      console.log(json);
      process_coordinator_poll_json(json);
    },
  });
}

function handle_unschedule_button(roundid, classname, round) {
  $("#unschedule_round").text(round);
  $("#unschedule_class").text(classname);
  show_modal("#unschedule_modal", function (event) {
    close_modal("#unschedule_modal");
    $.ajax(g_action_url, {
      type: "POST",
      data: { action: "schedule.unschedule", roundid: roundid },
      success: function (data) {
        process_coordinator_poll_json(data);
      },
    });
    return false;
  });
}

function handle_delete_round_button(roundid, classname, round) {
  $("#delete_round_round").text(round);
  $("#delete_round_class").text(classname);
  show_modal("#delete_round_modal", function (event) {
    close_modal("#delete_round_modal");
    $.ajax(g_action_url, {
      type: "POST",
      data: { action: "roster.delete", roundid: roundid },
      success: function (data) {
        process_coordinator_poll_json(data);
      },
    });
    return false;
  });
}

function handle_make_changes_button(roundid) {
  $.ajax(g_action_url, {
    type: "POST",
    data: { action: "heat.select", roundid: roundid, heat: 1, now_racing: 0 },
    success: function (json) {
      process_coordinator_poll_json(json);
    },
  });
}

function handle_purge_button(roundid, heats_run) {
  var control_group = $('div[data-roundid="' + roundid + '"]');
  $("#purge_round_name").text(control_group.find(".roundclass").text());
  $("#purge_round_no").text(control_group.find(".roundno").text());
  $("#purge_results_count").text(heats_run);
  show_modal("#purge_modal", function (event) {
    close_modal("#purge_modal");
    show_secondary_modal("#purge_confirmation_modal", function (event) {
      close_secondary_modal("#purge_confirmation_modal");
      $.ajax("action.php", {
        type: "POST",
        data: { action: "database.purge", purge: "results", roundid: roundid },
        success: function (data) {
          coordinator_poll();
        },
      });
      return false;
    });
    return false;
  });
}

function show_choose_new_round_modal() {
  populate_new_round_modals();

  // There's no submit, or even a form, in this modal; just a bunch
  // of buttons with their own actions:
  //
  // - handle_new_round_follow_on to create a follow-on round to an existing round
  // - handle_new_round_aggregate_class to create a first round for an existing aggregate class
  // - handle_new_round_make_aggregate to create an aggregate round ("Grand Final")
  show_modal("#choose_new_round_modal", function (event) {
    return false;
  });
}

// When the "aggregate-by" checkbox changes, slide to hide or show
// constituent-rounds div
function on_aggregate_by_change() {
  $("#constituent-rounds").css(
    "margin-left",
    $("#aggregate-by-checkbox").is(":checked") ? "-500px" : "0px"
  );
  update_bucketed_checkbox(!$("#aggregate-by-checkbox").is(":checked"));
}

function update_bucketed_checkbox(for_group) {
  $("#bucketed-checkbox").attr(
    "data-on-text",
    $("#bucketed-checkbox").attr(
      for_group ? "data-group-text" : "data-subgroup-text"
    )
  );
  flipswitch_refresh($("#bucketed-checkbox"));
}

// Create a follow-on round to an existing round.
function handle_new_round_follow_on(roundid) {
  console.log("follow-on for roundid=" + roundid); // TODO
  close_modal_leave_background("#choose_new_round_modal");
  $("#new-round-modal div").removeClass("hidden");
  $(".aggregate-only").addClass("hidden");
  $("#new-round-modal #new_round_roundid").val(roundid);

  update_bucketed_checkbox(/* for_group */ false);
  $("#new-round-modal #bucketed-checkbox")
    .prop("checked", false)
    .trigger("change", true)
    .toggleClass(
      "hidden",
      !g_use_subgroups && g_aggregate_rounds.includes(roundid)
    );

  show_modal("#new-round-modal", function (event) {
    on_submit_new_round_follow_on(roundid);
    return false;
  });
}

function on_submit_new_round_follow_on(roundid) {
  close_modal("#new-round-modal");
  $.ajax(g_action_url, {
    type: "POST",
    data: {
      action: "roster.new",
      roundid: roundid,
      top: Number($("#new-round-top").val()),
      bucketed: $("#bucketed-checkbox").prop("checked") ? 1 : 0,
    },
    success: function (data) {
      process_coordinator_poll_json(data);
    },
  });
}

// Manufacture a new aggregate round (ephemeral aggregate class) from top
// finishers in several completed rounds.
function handle_new_round_make_aggregate() {
  close_modal_leave_background("#choose_new_round_modal");
  $("#new-round-modal div").removeClass("hidden");
  $("#aggregate-by-div").toggleClass("hidden", !g_use_subgroups);
  if (!g_use_subgroups) {
    $("#aggregate-by-checkbox").prop("checked", false);
  } else if (
    g_completed_rounds.length == 1 &&
    g_completed_rounds[0].subgroups.length > 1
  ) {
    console.log("single round completed");
    // Single round completed
    $("#aggregate-by-checkbox").prop("checked", true);
    flipswitch_refresh($("#aggregate-by-checkbox"));
    on_aggregate_by_change();
  }

  update_bucketed_checkbox(/* for_group */ true);

  g_new_round_modal_open = true;
  show_modal("#new-round-modal", function (event) {
    on_submit_new_round_make_aggregate();
    return false;
  });
}

function on_submit_new_round_make_aggregate() {
  g_new_round_modal_open = false;
  close_modal("#new-round-modal");
  $.ajax(g_action_url, {
    type: "POST",
    data:
      "action=roster.new&" +
      $("#new-round-common input").serialize() +
      "&" +
      $("#agg-classname-div input").serialize() +
      "&" +
      ($("#aggregate-by-checkbox").is(":checked")
        ? $("#constituent-subgroups input").serialize()
        : $("#constituent-rounds input").serialize()),
    success: function (data) {
      process_coordinator_poll_json(data);
    },
  });
}

// Create first round for a pre-defined aggregate class
function handle_new_round_aggregate_class(classid, by_subgroup) {
  close_modal_leave_background("#choose_new_round_modal");
  $("#new-round-modal div").removeClass("hidden");
  $("div.for-choosing-constituents").addClass("hidden");
  $("#agg-classname-div").addClass("hidden");
  g_new_round_modal_open = true;

  update_bucketed_checkbox(/* for_group */ !by_subgroup);

  show_modal("#new-round-modal", function (event) {
    on_submit_new_round_aggregate_class(classid);
    return false;
  });
}

function on_submit_new_round_aggregate_class(classid) {
  close_modal("#new-round-modal");
  g_new_round_modal_open = false;

  $.ajax(g_action_url, {
    type: "POST",
    data: {
      action: "roster.new",
      classid: classid,
      top: $("#new-round-top").val(),
      bucketed: $("#bucketed-checkbox").prop("checked") ? 1 : 0,
    },
    success: function (data) {
      process_coordinator_poll_json(data);
    },
  });
}

function show_replay_settings_modal() {
  show_modal("#replay_settings_modal", function (event) {
    handle_replay_settings_submit();
    return false;
  });
}

function handle_replay_settings_submit() {
  close_modal("#replay_settings_modal");
  $.ajax(g_action_url, {
    type: "POST",
    data: $("#replay_settings_modal form").serialize(),
    success: function (data) {
      process_coordinator_poll_response(data);
    },
  });
}

function handle_master_next_up() {
  $.ajax(g_action_url, {
    type: "POST",
    data: { action: "heat.select", heat: "next-up", now_racing: 0 },
    success: function (json) {
      process_coordinator_poll_json(json);
    },
  });
}

function handle_stop_testing() {
  $.ajax(g_action_url, {
    type: "POST",
    data: { action: "timer.test", "test-mode": 0 },
  });
}

function handle_start_playlist() {
  $.ajax(g_action_url, { type: "POST", data: { action: "playlist.start" } });
}

function populate_new_round_modals() {
  // Each round in completed_rounds is the highest round for its class and all
  // its heats have been run.
  var completed_rounds = g_completed_rounds.slice(0); // Copy the array

  var add_aggregate =
    completed_rounds.length > 1 ||
    // A subgroup-based aggregate round could run after a single round involving
    // multiple subgroups.
    (g_use_subgroups &&
      completed_rounds.length == 1 &&
      completed_rounds[0].subgroups.length > 1);

  var modal = $("#choose_new_round_modal");
  modal.empty();
  var constituent_rounds_div = $("#constituent-rounds").empty();
  var constituent_subgroups_div = $("#constituent-subgroups").empty();
  while (completed_rounds.length > 0) {
    var roundno = completed_rounds[0].round;
    modal.append("<h3>Add Round " + (roundno + 1) + "</h3>");
    var i = 0;
    while (i < completed_rounds.length) {
      if (completed_rounds[i].round == roundno) {
        var round = completed_rounds[i];
        console.log(round);
        // For completed rounds, offer a button to generate a follow-on round
        var button = $('<input type="button"/>');
        button.attr("value", round["class"]);
        // Although syntactically it looks like a new round variable is created
        // each time through the loop, it's actually just one variable that's
        // reused/assigned each time.  Capturing that reused variable in the on-click
        // function won't work, so, we need to record the current roundid on
        // the button itself.
        button.attr("data-roundid", round.roundid);
        button.on("click", function (event) {
          handle_new_round_follow_on($(this).attr("data-roundid"));
        });
        modal.append(button);

        // A completed round can also be incorporated into a new aggregate round
        constituent_rounds_div.append(
          $('<div class="flipswitch-div"></div>')
            .append(
              $('<label class="aggregate-label"/>')
                .attr("for", "classid_" + round.classid)
                .text(round["class"])
            )
            .append(
              $('<input type="checkbox" class="flipswitch" checked="checked"/>')
                .attr("id", "classid_" + round.classid)
                .attr("name", "classid_" + round.classid)
            )
        );

        // A completed round gives subgroups to choose from
        for (var ri = 0; ri < round.subgroups.length; ++ri) {
          var subgroup = round.subgroups[ri];

          constituent_subgroups_div.append(
            $('<div class="flipswitch-div"></div>')
              .append(
                $('<label class="aggregate-label"/>')
                  .attr("for", "rankid_" + subgroup.rankid)
                  .text(subgroup.name)
              )
              .append(
                $(
                  '<input type="checkbox" class="flipswitch" checked="checked"/>'
                )
                  .attr("id", "rankid_" + subgroup.rankid)
                  .attr("name", "rankid_" + subgroup.rankid)
              )
          );
        }

        completed_rounds.splice(i, 1);
      } else {
        ++i;
      }
    }
  }

  if (add_aggregate) {
    modal.append("<h3>Add Aggregate Round</h3>");
    for (var i = 0; i < g_ready_aggregate_classes.length; ++i) {
      // If there's only one round completed, then only by-subgroup aggregates
      // could possibly be next.
      if (
        completed_rounds.length > 1 ||
        g_ready_aggregate_classes[i]["by-subgroup"]
      ) {
        var agg = g_ready_aggregate_classes[i];
        var button = $('<input type="button"/>');
        button.attr("value", agg["class"]);
        button.attr("data-classid", agg.classid);
        button.attr("data-by-subgroup", agg["by-subgroup"]);
        button.on("click", function (event) {
          handle_new_round_aggregate_class(
            $(this).attr("data-classid"),
            $(this).attr("data-by-subgroup")
          );
        });
        modal.append(button);
      }

      // Aggregate rounds ready for scheduling can also be incorporated as
      // non-racing constituents for a new aggregate round.
      if (!g_ready_aggregate_classes[i]["by-subgroup"]) {
        var id = "classid_" + g_ready_aggregate_classes[i]["classid"];
        constituent_rounds_div.append(
          $('<div class="flipswitch-div"></div>')
            .append(
              $('<label class="aggregate-label"/>')
                .attr("for", id)
                .text(g_ready_aggregate_classes[i]["class"])
            )
            // leave these unchecked by default
            .append(
              $('<input type="checkbox" class="flipswitch"/>')
                .attr("id", id)
                .attr("name", id)
            )
        );
      }
    }
    var button = $('<input type="button" value="Aggregate Round"/>');
    button.on("click", function (event) {
      handle_new_round_make_aggregate();
    });
    modal.append(button);

    flipswitch($("#constituent-div").find("input[type='checkbox']"));
  }

  modal.append("<h3>&nbsp;</h3>");
  modal.append(
    '<input type="button" value="Cancel"' +
    " onclick='close_modal(\"#choose_new_round_modal\");'/>"
  );
}

function handle_racing_mode_activation(json) {
  if (json.success === false && json.code === "unregistered_racers") {
    alert(json.error); // Display the error message
    return;
  }

  // Proceed with racing mode activation
  if (json.success) {
    console.log("Racing mode activated successfully.");
  }
}

function handleRacerDropout(racerid, roundid) {
  if (confirm('Are you sure you want to remove this racer? This action cannot be undone.')) {
    $.ajax('action.php', {
      type: 'POST',
      data: {
        action: 'racer.dropout',
        racerid: racerid,
        roundid: roundid
      },
      success: function (data) {
        if (data.outcome.code == 'success') {
          // Reload current round display
          location.reload();
        } else {
          alert('Failed to remove racer: ' + data.outcome.description);
        }
      },
      error: function () {
        alert('Server error while processing racer dropout');
      }
    });
  }
}


// function to init the HLS stream
function initVideoSource(selectq) {
  const deviceId = selectq.find(':selected').prop('value');
  
  if (deviceId === 'hls-stream') {
      const hlsUrl = selectq.data('hls-url');
      const videoElement = document.getElementById("preview");
      
      // Stop any existing streams
      if (videoElement.srcObject) {
          videoElement.srcObject.getTracks().forEach(track => track.stop());
      }
      
      // Initialize HLS stream
      initHLSStream(videoElement, hlsUrl);
      return true;
  }
  
  // Continue with existing device handling
  return false;
}

//////////////////////////////////////////////////////////////////////////
// Scene selector functionality for coordinator page
//////////////////////////////////////////////////////////////////////////

function setup_scenes_select_control_coordinator() {
  $("#scenes-select-coordinator").empty();
  $("#scenes-select-coordinator").append($("<option/>")
                                         .attr('value', -1)
                                         .html("&nbsp;"));
  for (var i = 0; i < g_all_scenes.length; ++i) {
    var scene = g_all_scenes[i];
    $("#scenes-select-coordinator").append($("<option/>")
                                           .attr('value', scene.sceneid)
                                           .text(scene.name));
  }

  $("#scenes-select-coordinator")
    .on('change', on_scene_change_coordinator)
    .val(g_current_scene == '' ? -1 : g_current_scene)
    .trigger('change', /*synthetic*/true);
}

// synthetic=false if user triggered scene change
function on_scene_change_coordinator(event, synthetic) {
  if (!synthetic) {
    var val = $("#scenes-select-coordinator").val();
    $.ajax(g_action_url,
           {type: 'POST',
            data: {action: 'scene.apply',
                   sceneid: val},
            success: function(data) {
              if (data.hasOwnProperty('current-scene')) {
                g_current_scene = data['current-scene'];
                $("#scenes-select-coordinator")
                  .val(g_current_scene == '' ? -1 : g_current_scene);
                update_scene_status_message();
              }
            },
           });
  }
}

function update_scene_status_message() {
  var current_scene_name = "";
  if (g_current_scene != '') {
    for (var i = 0; i < g_all_scenes.length; ++i) {
      if (g_all_scenes[i].sceneid == g_current_scene) {
        current_scene_name = g_all_scenes[i].name;
        break;
      }
    }
  }
  $("#scenes-status-message-coordinator")
    .text(current_scene_name ? "Scene: " + current_scene_name : "No scene selected");
}

$(function() { 
  setup_scenes_select_control_coordinator();
  update_scene_status_message();
});

//////////////////////////////////////////////////////////////////////////
// Broadcast message functionality for coordinator page
//////////////////////////////////////////////////////////////////////////

function handle_broadcast_message() {
  var message = $("#broadcast-message-coordinator").val().trim();
  
  if (message === '') {
    alert('Please enter a message to broadcast.');
    return;
  }
  
  if (message.length > 255) {
    alert('Message is too long. Maximum 255 characters allowed.');
    return;
  }
  
  // Disable the button to prevent multiple submissions
  $("#broadcast-submit-coordinator").prop('disabled', true).val('Sending...');
  
  $.ajax(g_action_url, {
    type: 'POST',
    data: {
      action: 'broadcast.message',
      message: message,
      duration: 30  // Default 30 seconds duration
    },
    success: function(data) {
      if (data.outcome && data.outcome.summary === 'success') {
        alert('Broadcast message sent successfully: "' + message + '"');
        $("#broadcast-message-coordinator").val(''); // Clear the input field
      } else {
        alert('Failed to send broadcast message: ' + (data.outcome ? data.outcome.description : 'Unknown error'));
      }
    },
    error: function(xhr, status, error) {
      alert('Error sending broadcast message: ' + error);
    },
    complete: function() {
      // Re-enable the button
      $("#broadcast-submit-coordinator").prop('disabled', false).val('Send');
    }
  });
}

// Allow Enter key to submit the broadcast message
$(function() {
  $("#broadcast-message-coordinator").on('keypress', function(e) {
    if (e.which === 13) { // Enter key
      handle_broadcast_message();
    }
  });
});