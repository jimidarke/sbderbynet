// Assumes ajax-failure.inc has already established a global ajax error handler

// KioskPoller.start(address, kiosk_page) starts the polling loop; see inc/kiosk-poller.inc
//
// On each cycle, KioskPoller.param_callback gets invoked with the current param
// string; parameter-aware kiosk pages should assign KioskPoller.param_callback
// to track parameter changes.

var KioskPoller = (function(KioskPoller) {

  KioskPoller.param_callback = function(parameters) {
    // console.log("Params: " + param_string);
  };

  // Variables for broadcast message handling
  var current_broadcast_id = null;
  var broadcast_timeout = null;

  // Function to display broadcast message
  function show_broadcast_message(message_data) {
    // Remove any existing broadcast message
    hide_broadcast_message();

    // Create unique ID for this message
    var message_id = message_data.timestamp + '_' + message_data.message.length;
    
    // Don't show the same message twice
    if (current_broadcast_id === message_id) {
      return;
    }
    
    current_broadcast_id = message_id;

    // Create broadcast message overlay
    var broadcast_div = $('<div id="broadcast-message" style="' +
      'position: fixed; ' +
      'top: 0; ' +
      'left: 0; ' +
      'width: 100%; ' +
      'height: 20%; ' +
      'background-color: black; ' +
      'color: white; ' +
      'display: flex; ' +
      'align-items: center; ' +
      'justify-content: center; ' +
      'font-size: 2em; ' +
      'font-weight: bold; ' +
      'text-align: center; ' +
      'z-index: 9999; ' +
      'padding: 20px; ' +
      'box-sizing: border-box;' +
      '">' + 
      '<div>' + $('<div>').text(message_data.message).html() + '</div>' +
      '</div>');

    $('body').append(broadcast_div);

    // Auto-hide after duration
    broadcast_timeout = setTimeout(function() {
      hide_broadcast_message();
    }, message_data.duration * 1000);
  }

  // Function to hide broadcast message
  function hide_broadcast_message() {
    $('#broadcast-message').remove();
    if (broadcast_timeout) {
      clearTimeout(broadcast_timeout);
      broadcast_timeout = null;
    }
  }

  KioskPoller.start = function(address, kiosk_page) {
    var interval = setInterval(function() {
      $.ajax('action.php',
             {type: 'GET',
              data: {query: 'poll.kiosk',
                     address: address},
              success: function(data) {
                if (data["cease"]) {
                  clearInterval(interval);
                  window.location.href = '../index.php';
                  return;
                }
                var setting = data['kiosk-setting'];
                cancel_ajax_failure();
                $("#kiosk_name").text(setting.name);
                var page = setting.page;
                if (page != kiosk_page) {
                  console.log("Forcing a reload, because page (" + page
                              + ") != current kiosk_page (" + kiosk_page + ")");
                  location.reload(true);
                  return;
                }
	            if (setting.reload) {
                  console.log("Forcing a reload because it was explicitly requested.");
                  location.reload(true);
                  return;
                }
                var params_string = '{}';
                if (setting.params.length !== 0) {
                  console.log("setting.params=" + setting.params)
                  params_string = setting.params;
                }
                KioskPoller.param_callback(JSON.parse(params_string));
                
                // Handle broadcast message if present
                if (setting['broadcast-message']) {
                  show_broadcast_message(setting['broadcast-message']);
                }
              }
             });
    }, 5000);
  }

  return KioskPoller;
}(KioskPoller || {}));

