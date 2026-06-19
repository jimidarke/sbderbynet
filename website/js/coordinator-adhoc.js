// Ad-hoc racing controls for the coordinator dashboard. The card, top strip and
// modal are PHP-rendered only while the live DB is the ad-hoc DB, so these
// handlers only ever run in ad-hoc mode. They reuse the same machinery as the
// Manual Results modal: show_modal()/close_modal(), g_action_url, the form
// serialize() POST, and process_coordinator_poll_json() for the refresh.

// Open the "set up next group" modal: clear prior entries + error, then show it.
function on_adhoc_setup_click() {
  $("#manual_heat_modal .adhoc-pinny-input").val("");
  $("#manual_heat_modal .adhoc-age-select").val("");
  $("#adhoc_lock_error").addClass("hidden").text("");
  show_modal("#manual_heat_modal", function (event) {
    return on_adhoc_lock_submit();
  });
  setTimeout(function () {
    $("#manual_heat_modal .adhoc-pinny-input").first().trigger("focus");
  }, 50);
}

// Validate client-side (immediate feedback), then POST. The server
// (adhoc_arm_heat) re-validates all-or-nothing and is the source of truth.
function on_adhoc_lock_submit() {
  var err = $("#adhoc_lock_error");
  err.addClass("hidden").text("");

  var seen = {};
  var count = 0;
  var bad = null;
  $("#manual_heat_modal tbody tr").each(function () {
    var pinny = $.trim($(this).find(".adhoc-pinny-input").val());
    var age = $(this).find(".adhoc-age-select").val();
    if (pinny === "") return;                 // blank lane = bye
    if (!/^\d+$/.test(pinny) || parseInt(pinny, 10) <= 0) {
      bad = "Pinny '" + pinny + "' is not a number.";
      return;
    }
    if (!age) {
      bad = "Pinny " + parseInt(pinny, 10) + ": choose an age group.";
      return;
    }
    var key = String(parseInt(pinny, 10));
    if (seen[key]) {
      bad = "Pinny " + key + " entered twice in one heat.";
      return;
    }
    seen[key] = true;
    count++;
  });

  if (bad) { err.text(bad).removeClass("hidden"); return false; }
  if (count === 0) { err.text("Enter at least one pinny.").removeClass("hidden"); return false; }

  close_modal("#manual_heat_modal");
  $.ajax(g_action_url, {
    type: "POST",
    data: $("#manual_heat_modal form").serialize(),
    success: function (data) {
      if (data && data.outcome && data.outcome.summary !== "success") {
        alert("Could not lock in the heat: " +
              (data.outcome.description || "unknown error"));
      }
      if (typeof process_coordinator_poll_json === "function") {
        process_coordinator_poll_json(data);
      }
    },
    error: function () {
      alert("Could not reach the server to lock in the heat.");
    }
  });
  return false;
}

// Exit ad-hoc mode (clear the marker, back to the official DB) and go home.
function adhoc_exit() {
  if (!confirm("Exit Ad-Hoc racing and return to the official event database?")) return;
  $.ajax(g_action_url, {
    type: "POST",
    data: { action: "adhoc.mode", mode: "off" },
    success: function (data) {
      if (data && data.outcome && data.outcome.summary === "success") {
        window.location = "index.php";
      } else {
        alert("Could not exit ad-hoc mode: " +
              ((data && data.outcome && data.outcome.description) || "unknown error"));
      }
    },
    error: function () {
      alert("Could not reach the server to exit ad-hoc mode.");
    }
  });
}
