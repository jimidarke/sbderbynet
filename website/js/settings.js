// 'use strict';

function on_lane_count_change() {
  $("#lanes-in-use").empty();
  var nlanes = $("#n-lanes").val();
  var mask = $("#unused-lane-mask").val();
  for (var i = 0; i < nlanes; ++i) {
    var bit = 1 << i;
    $("#lanes-in-use").append(" " + (i + 1) + ":");
    var img_src = (mask & bit) ? 'img/lane_closed.png' : 'img/lane_open.png';
    $("#lanes-in-use").append("<img data-bit='" + bit + "' src='" + img_src + "'/>");
  }

  // In case the lane count decreased, clear any higher-order bits as they're no
  // longer meaningful
  $("#unused-lane-mask").val(mask & ~(-1 << nlanes));

  $("#lanes-in-use img").on('click', on_lane_click);
}

function on_lane_click(event) {
  if ($("#unused-lane-mask").prop('disabled')) {
    return;
  }
  var mask = $("#unused-lane-mask").val();
  var target = $(event.currentTarget);
  var bit = target.attr('data-bit');
  mask ^= bit;
  target.attr('src', (mask & bit) ? 'img/lane_closed.png' : 'img/lane_open.png');

  $("#unused-lane-mask").val(mask);
  PostSettingChange($("#unused-lane-mask"));
}

function on_linger_time_change() {
  $("#now-racing-linger-ms").val($("#now-racing-linger-sec").val() * 1000);
  PostSettingChange($("#now-racing-linger-ms"));
  return false;
}

function on_max_runs_change() {
  $("#max-runs-per-car").val(document.getElementById('max-runs').checked ? 1 : 0);
  PostSettingChange($("#max-runs-per-car"));
}

function on_car_numbering_change(event) {
  var target = $(event.currentTarget);

  var by_segment = $("#number-by-segment").is(':checked') ? '100' : '0';
  if (target.attr('name') == 'number-by-segment') {
    // While handling the on-change event, :checked appears not to have been
    // updated yet, so reads opposite what it should.
    by_segment = target.is(':checked') ? '0' : '100';
  }

  var number_from = $("input[name='number-from']:checked").val();
  if (target.attr('name') == 'number-from') {
    number_from = target.val();
  }

  $("#car-numbering").val(by_segment + '+' + number_from);

  PostSettingChange($("#car-numbering"));
  return false;
}

function render_directory_status_icon(photo_dir_selector) {
  $.ajax('action.php',
    {
      type: 'GET',
      data: {
        query: 'file.stat',
        path: $(photo_dir_selector).val()
      },
      success: function (data) {
        console.log(data);
        var icon_span = $(photo_dir_selector + '_icon');
        var msg_para = $(photo_dir_selector + '_message');
        if (data.hasOwnProperty('stat')) {
          var stat = data.stat;
          if (!stat.isdir || !stat.readable) {
            icon_span.html('<img src="img/status/trouble.png"/>');
            msg_para.text('Directory does not exist or is not readable.');
          } else if (!stat.writable) {
            icon_span.html('<img src="img/status/readonly.png"/>');
            msg_para.text('Directory is not writable.');
          } else {
            icon_span.html('<img src="img/status/ok.png"/>');
            msg_para.text('');
          }
        } else {
          icon_span.html("");
          msg_para.text('');
        }
      }
    });
}

function browse_for_photo_directory(photo_dir_selector) {
  var photo_dir = $(photo_dir_selector);
  var val = photo_dir.val();
  if (val == '') {
    val = photo_directory_base();  // Defined in settings.php
  }
  show_choose_directory_modal(val, function (path) {
    photo_dir.val(path);
    photo_dir.change();
  });
}

function on_supergroup_label_change() {
  $("span.supergroup-label").text($("#supergroup-label").val().toLowerCase());
}
function on_partition_label_change() {
  $("span.partition-label").text($("#partition-label").val().toLowerCase());
}


// As of 26-03-2025
// ////////////////////////////////////
// Weight Display Settings Starts here
// ////////////////////////////////////

document.addEventListener("DOMContentLoaded", function () {
  function getSelectedWeightUnit() {
    return document.querySelector("input[name='weight-units']:checked")?.value || "kg";
  }

  function onWeightUnitChange() {
    let selectedUnit = getSelectedWeightUnit();
    localStorage.setItem("weightUnit", selectedUnit);
    console.log("Selected weight unit:", selectedUnit);
  }

  function applySavedWeightUnit() {
    let savedUnit = localStorage.getItem("weightUnit") || onWeightUnitChange();
    document.querySelector(`input[name='weight-units'][value='${savedUnit}']`).checked = true;
    PostSettingChange($("input[name='weight-units']:checked"));
  }

  document.querySelectorAll("input[name='weight-units']").forEach(radio => {
    radio.addEventListener("change", onWeightUnitChange);
  });
  // applySavedWeightUnit();
});



// ////////////////////////////////////
// Weight Display Settings Ends here
// ////////////////////////////////////


// PostSettingChange(input) responds to a change in an <input> element by
// sending an ajax POST request with the input element's current value.  Handles
// checkboxes, too.

var PostSettingChange;

(function () {
  var next_train = 0;
  var values = { action: 'settings.write' };

  function maybe_post() {
    if (next_train == 0) {
      next_train = setTimeout(function () {
        next_train = 0;
        var d = values;
        values = { action: 'settings.write' };

        console.log('POSTing ' + JSON.stringify(d));

        $.ajax('action.php',
          {
            type: 'POST',
            data: d,
            success: function (data) {
              if (data.outcome.summary == 'failure') {
                console.log(data);
                alert("Action failed: " + data.outcome.description);
              }
            },
            error: function (jqXHR, ajaxSettings, thrownError) {
              alert('Ajax error: ' + thrownError);
            }
          });
      }, 200);
    }
  }

  PostSettingChange = function (input) {
    if ($(input).hasClass('do-not-post')) {
      return;
    }
    var name = input.attr('name');
    if (typeof name == 'undefined' || name === false) {
      return;
    }

    if (input.attr('type') == 'checkbox') {
      values[name + '-checkbox'] = 'yes';
      if (input.is(':checked')) {
        values[name] = 1;
      } else {
        delete values[name];
      }

    } else if (input.attr('type') == 'radio') {
      if (input.is(':checked')) {
        values[name] = input.val();
      }
    } else if (input.attr('type') == 'number') {
      // It's possible to get an empty value from a number control, but that
      // causes problems in the database.
      values[name] = Number(input.val());
    } else {
      // For a radio input, the change event comes from the newly-selected value
      values[name] = input.val();
    }

    maybe_post();
  };

})();

$(function () {

  $("#n-lanes").on("keyup mouseup", on_lane_count_change);
  on_lane_count_change();

  $("#now-racing-linger-sec").on("keyup mouseup", on_linger_time_change);

  $("#supergroup-label").on("keyup mouseup", on_supergroup_label_change);
  $("#partition-label").on("keyup mouseup", on_partition_label_change);

  $("#number-from-101, label[for='number-from-101'], " +
    "#number-from-1, label[for='number-from-1'], " +
    "#number-by-segment, label[for='number-by-segment']")
    .on("keyup mouseup", on_car_numbering_change);

  $('#settings_form input, #settings_form select').on('change', function (e) {
    PostSettingChange($(this));
  });
  $('#settings_form input[type!="checkbox"]').on('input', function (e) {
    PostSettingChange($(this));
  });

  if ($("#photo-dir").length > 0) {
    render_directory_status_icon("#photo-dir");
    render_directory_status_icon("#car-photo-dir");
    render_directory_status_icon("#video-dir");
  }

  $("#photo-dir").on("change", function () { render_directory_status_icon("#photo-dir"); });
  $("#car-photo-dir").on("change", function () { render_directory_status_icon("#car-photo-dir"); });
  $("#video-dir").on("change", function () { render_directory_status_icon("#video-dir"); });

});

$(document).ready(function () {
  // $('#test-mode').on('change', function(e) {
  //     e.preventDefault();
  //     const $checkbox = $(this);
  //     const isTestMode = $checkbox.is(':checked');

  //     $.ajax({
  //         url: 'action.php',
  //         method: 'POST',
  //         dataType: 'json',
  //         data: {
  //             'action': 'settings.write',
  //             'test-mode-only': '1',
  //             'test-mode': isTestMode ? '1' : '0'
  //         },
  //         success: function(response) {
  //             if (response && response.status === 'success') {
  //                 console.log(`Successfully switched to ${response.mode} mode`);
  //                 alert(`Switched to ${response.mode} mode`);
  //                 // window.location.reload(); // Reload to reflect new database connection
  //             } else {
  //                 console.error('Server response:', response);
  //                 alert(response.message || 'Failed to switch database mode');
  //                 $checkbox.prop('checked', !isTestMode);
  //             }
  //         },
  //         error: function(xhr, status, error) {
  //             console.error('Ajax error:', {xhr, status, error});
  //             alert('Error switching database mode: ' + error);
  //             $checkbox.prop('checked', !isTestMode);
  //         }
  //     });
  // });


  // Update the test mode change handler
  $('#test-mode').on('change', function (e) {
    e.preventDefault();
    const $checkbox = $(this);
    const isTestMode = $checkbox.is(':checked');

    $.ajax({
      url: 'action.php',
      method: 'POST',
      dataType: 'json',
      data: {
        'action': 'settings.write',
        'test-mode-only': '1',
        'test-mode': isTestMode ? '1' : '0'
      },
      success: function (response) {
        if (response && response.status === 'success') {
          console.log(`Successfully switched to ${response.mode} mode`);
          if (response.settings) {
            updateFormFields(response.settings);
          }
          refreshDatabaseStatus();
          alert(`Switched to ${response.mode} mode`);
          window.location.reload();
        } else {
          console.error('Server response:', response);
          alert(response.message || 'Failed to switch database mode');
          $checkbox.prop('checked', !isTestMode);
        }
      },
      error: function (xhr, status, error) {
        console.error('Ajax error:', { xhr, status, error });
        alert('Error switching database mode: ' + error);
        $checkbox.prop('checked', !isTestMode);
      }
    });
  });
});
function refreshDatabaseStatus() {
  return new Promise((resolve, reject) => {
    console.log('Refreshing database status...');

    $.ajax({
      url: 'action.php',
      method: 'POST',
      dataType: 'json',
      data: {
        action: 'database.status',
      },
      success: function (response) {
        console.log('Database status response:', response);
        if (response.status == 'success') {
          console.log('Database status:', response);
          updateDatabaseStatusUI(response);
        } else {
          console.error('Database status check failed:', response.message);
          showError('Failed to check database status: ' + response.message);
        }
        resolve(response);
      },
      error: function (xhr, status, error) {
        console.error('Ajax error:', { xhr, status, error });
        showError('Error checking database status: ' + error);
        reject(error);
      },
    });
  });
}

function updateDatabaseStatusUI(data) {
  const statusHtml = `
      <div class="database-status">
          <div class="current-mode ${data.current.mode === 'test' ? 'test-mode' : 'prod-mode'}">
              <h3>Current Mode: ${data.current.mode.toUpperCase()}</h3>
              <p class="db-path">Database: ${data.current.path}</p>
              <p>Schema Version: ${data.current.schema_version}</p>
              ${data.warning ? `<p class="warning">${data.warning}</p>` : ''}
          </div>
          
          <div class="connection-details">
              <div class="production-status">
                  <h4>Production Database</h4>
                  <p>Path: ${data.production.path}</p>
                  <p>Status: ${getConnectionStatus(data.production)}</p>
              </div>
              
              <div class="test-status">
                  <h4>Test Database</h4>
                  <p>Path: ${data.test.path}</p>
                  <p>Status: ${getConnectionStatus(data.test)}</p>
              </div>
          </div>
          
          // <div class="directory-status">
          //     ${renderDirectoryStatus(data.directories)}
          // </div>
      </div>
  `;

  $('.database-status').html(statusHtml);
}

function getConnectionStatus(dbInfo) {
  if (!dbInfo.exists) return 'Not Found';
  if (!dbInfo.is_writable) return 'Not Writable';
  return dbInfo.connection_valid ? 'Connected' : 'Not Active';
}

function renderDirectoryStatus(directories) {
  return Object.entries(directories).map(([mode, dirs]) => `
      <div class="${mode}-directories">
          <h4>${mode.charAt(0).toUpperCase() + mode.slice(1)} Directories</h4>
          ${Object.entries(dirs).map(([name, info]) => `
              <div class="directory-item">
                  <span class="dir-name">${name}:</span>
                  <span class="dir-status ${info.exists && info.writable ? 'valid' : 'invalid'}">
                      ${info.exists ? (info.writable ? '✓' : '🔒') : '❌'}
                  </span>
              </div>
          `).join('')}
      </div>
  `).join('');
}

function showError(message) {
  $('.database-status').html(`
      <div class="error-message">
          ${message}
      </div>
  `);
}

// Add CSS
const styles = `
  .database-status {
      width: max-content;
      padding: 15px;
      margin: 10px 0;
      border: 1px solid #ddd;
      border-radius: 4px;
  }
  
  .test-mode { background-color: #fff3cd; }
  .prod-mode { background-color: #d1e7dd; }
  
  .warning {
      color: #856404;
      background-color: #fff3cd;
      padding: 10px;
      border-radius: 4px;
      margin: 10px 0;
  }
  
  .error-message {
      color: #721c24;
      background-color: #f8d7da;
      padding: 10px;
      border-radius: 4px;
  }
  
  .directory-item {
      display: flex;
      justify-content: space-between;
      padding: 2px 0;
  }
  
  .valid { color: #28a745; }
  .invalid { color: #dc3545; }
`;

// Add styles to document
const styleSheet = document.createElement('style');
styleSheet.textContent = styles;
document.head.appendChild(styleSheet);

// Initialize on page load
// $(document).ready(function() {
//   refreshDatabaseStatus();
//   // Refresh status every 30 seconds
//   setInterval(refreshDatabaseStatus, 30000);
// });

function updateFormFields(settings) {
  // Update checkbox fields
  $('input[type="checkbox"]').each(function () {
    const name = $(this).attr('name');
    if (settings[name] !== undefined) {
      $(this).prop('checked', settings[name] === '1');
    }
  });

  // Update text/number inputs
  $('input[type="text"], input[type="number"]').each(function () {
    const name = $(this).attr('name');
    if (settings[name] !== undefined) {
      $(this).val(settings[name]);
    }
  });

  // Update radio buttons
  $('input[type="radio"]').each(function () {
    const name = $(this).attr('name');
    if (settings[name] !== undefined) {
      $(this).prop('checked', $(this).val() === settings[name]);
    }
  });

  // Update select elements
  $('select').each(function () {
    const name = $(this).attr('name');
    if (settings[name] !== undefined) {
      $(this).val(settings[name]);
    }
  });
}