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

  // Function to get persisted broadcast state from localStorage
  function get_persisted_broadcast_state() {
    try {
      var state = localStorage.getItem('derbynet_broadcast_state');
      return state ? JSON.parse(state) : {};
    } catch (e) {
      return {};
    }
  }

  // Function to persist broadcast state to localStorage
  function persist_broadcast_state(message_id, expiration_time) {
    try {
      localStorage.setItem('derbynet_broadcast_state', JSON.stringify({
        message_id: message_id,
        expires: expiration_time
      }));
    } catch (e) {
      // localStorage might not be available, ignore
    }
  }

  // Function to clear persisted broadcast state
  function clear_persisted_broadcast_state() {
    try {
      localStorage.removeItem('derbynet_broadcast_state');
    } catch (e) {
      // localStorage might not be available, ignore
    }
  }

  // Function to display broadcast message
  function show_broadcast_message(message_data) {
    // Remove any existing broadcast message
    hide_broadcast_message();

    // Create unique ID for this message
    var message_id = message_data.timestamp + '_' + message_data.message.length;
    var current_time = Math.floor(Date.now() / 1000);
    
    // Check if this message has already been shown and not expired
    var persisted_state = get_persisted_broadcast_state();
    if (persisted_state.message_id === message_id && 
        persisted_state.expires && 
        current_time < persisted_state.expires) {
      // Message already shown and hasn't expired on this client
      return;
    }
    
    // Don't show the same message twice in current session
    if (current_broadcast_id === message_id) {
      return;
    }
    
    current_broadcast_id = message_id;
    
    // Calculate remaining time for display
    var remaining_time = message_data.expires - current_time;
    if (remaining_time <= 0) {
      // Message has already expired
      return;
    }
    
    // Persist this message state
    persist_broadcast_state(message_id, message_data.expires);

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

    // Auto-hide after remaining time (not original duration)
    broadcast_timeout = setTimeout(function() {
      hide_broadcast_message();
      // Clear persisted state when message expires
      clear_persisted_broadcast_state();
    }, remaining_time * 1000);
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
    // Clean up any expired broadcast state on page load
    var persisted_state = get_persisted_broadcast_state();
    var current_time = Math.floor(Date.now() / 1000);
    if (persisted_state.expires && current_time >= persisted_state.expires) {
      clear_persisted_broadcast_state();
    }
    
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

