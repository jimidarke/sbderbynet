// LED Sign Dashboard JavaScript
// Polls for LED sign status and handles zone assignment

var g_poll_interval = null;
var g_last_data_hash = null;

// Start polling when document is ready
$(document).ready(function() {
  poll_ledsigns();
  g_poll_interval = setInterval(poll_ledsigns, 2000);
});

// Force immediate poll
function poll_ledsigns_now() {
  poll_ledsigns();
}

// Poll for all LED signs
function poll_ledsigns() {
  $.ajax({
    type: 'GET',
    url: 'action.php',
    data: { query: 'poll.ledsign.all' },
    dataType: 'json',
    success: function(data) {
      if (data.ledsigns) {
        process_ledsign_data(data.ledsigns);
      }
    },
    error: function(jqXHR, textStatus, errorThrown) {
      console.error('LED sign poll failed:', textStatus, errorThrown);
    }
  });
}

// Process polled data and update UI
function process_ledsign_data(data) {
  // Check if data has changed (avoid unnecessary DOM updates)
  var data_hash = JSON.stringify(data);
  if (data_hash === g_last_data_hash) {
    return;
  }
  g_last_data_hash = data_hash;

  var signs = data.signs || [];
  var zones = data.zones || [];

  // Update stats
  var total = signs.length;
  var assigned = signs.filter(function(s) { return s.zone; }).length;
  var unassigned = total - assigned;

  $('#stats-total').text(total);
  $('#stats-assigned').text(assigned);
  $('#stats-unassigned').text(unassigned);

  // Update sign list
  update_sign_list(signs);

  // Update zone summary
  update_zone_summary(zones);
}

// Update the list of discovered signs
function update_sign_list(signs) {
  var container = $('#ledsign-list');

  if (signs.length === 0) {
    container.html(
      '<div class="no-signs">' +
      '<p>No LED signs discovered yet.</p>' +
      '<p>LED signs will appear here when they connect to the network.</p>' +
      '<p>Signs poll: <code>GET /ledsign.php?mac=AA:BB:CC:DD:EE:FF</code></p>' +
      '</div>'
    );
    return;
  }

  var html = '';
  signs.forEach(function(sign) {
    var cardClass = sign.zone ? 'assigned' : 'unassigned';
    var statusClass = sign.status === 'online' ? 'online' : 'offline';

    html += '<div class="ledsign-card ' + cardClass + '" data-mac="' + escapeHtml(sign.mac) + '">';
    html += '  <div class="ledsign-info">';
    html += '    <div class="ledsign-mac">';
    html += '      <span class="ledsign-status ' + statusClass + '"></span>';
    html += '      ' + escapeHtml(sign.mac);
    html += '    </div>';
    html += '    <div class="ledsign-details">';
    html += '      IP: ' + escapeHtml(sign.ip_address || 'unknown');
    html += '      | Firmware: ' + escapeHtml(sign.firmware_version || 'unknown');
    html += '      | ' + sign.age_seconds + 's ago';
    html += '    </div>';
    html += '  </div>';
    html += '  <div class="ledsign-zone-select">';
    html += '    <select onchange="handle_zone_change(this, \'' + escapeHtml(sign.mac) + '\')">';
    html += '      <option value="">-- Select Zone --</option>';

    g_ledsign_zones.forEach(function(zone) {
      var selected = (sign.zone === zone.id) ? ' selected' : '';
      html += '      <option value="' + escapeHtml(zone.id) + '"' + selected + '>';
      html += escapeHtml(zone.name);
      html += '</option>';
    });

    html += '    </select>';
    html += '  </div>';
    html += '</div>';
  });

  container.html(html);
}

// Update the zone assignment summary
function update_zone_summary(zones) {
  var container = $('#zone-summary');
  var html = '<h3>Zone Assignment Summary</h3>';

  zones.forEach(function(zone) {
    html += '<div class="zone-row">';
    html += '  <div class="zone-name">' + escapeHtml(zone.name) + '</div>';

    if (zone.assigned_mac) {
      html += '  <div class="zone-assigned">';
      html += '    <span class="ledsign-status ' + (zone.status || 'offline') + '"></span>';
      html += '    ' + escapeHtml(zone.assigned_mac);
      html += '  </div>';
    } else {
      html += '  <div class="zone-assigned unassigned">— not assigned —</div>';
    }

    html += '</div>';
  });

  container.html(html);
}

// Handle zone selection change
function handle_zone_change(select, mac) {
  var zone = $(select).val();

  $.ajax({
    type: 'POST',
    url: 'action.php',
    data: {
      action: 'ledsign.assign',
      mac: mac,
      zone: zone
    },
    dataType: 'json',
    success: function(data) {
      if (data.assignment) {
        // Update UI with new data
        process_ledsign_data({
          signs: data.assignment.signs,
          zones: data.assignment.zones
        });
      } else if (data.outcome && data.outcome.summary) {
        alert('Error: ' + data.outcome.summary);
        poll_ledsigns(); // Refresh to get correct state
      }
    },
    error: function(jqXHR, textStatus, errorThrown) {
      alert('Failed to assign zone: ' + textStatus);
      poll_ledsigns(); // Refresh to get correct state
    }
  });
}

// HTML escape helper
function escapeHtml(text) {
  if (!text) return '';
  var div = document.createElement('div');
  div.appendChild(document.createTextNode(text));
  return div.innerHTML;
}
