// cb gets called with two arguments:
// a bool indicating whether the curr_deviceId was among the devices, and
// an array of <option> elements, one for each local video
// device.  For each option, the value is the deviceId for the device.
function video_devices(curr_deviceId, cb) {
  let options = [];
  let found_current = false;
  if (!navigator.mediaDevices) {
    cb(found_current, options);
  } else {
    navigator.mediaDevices.enumerateDevices()
      .then(devices => {
        devices.forEach(device => {
          if (device.kind == 'videoinput') {
            let opt = $("<option/>");
            opt.prop('value', device.deviceId)
              .text(device.label);
            if (curr_deviceId == device.deviceId) {
              opt.prop('selected', 'selected');
              found_current = true;
            }
            options.push(opt);
          }
        });
        cb(found_current, options);
      });
  }
}

// selectq is a jquery for the <select> element listing available devices
// function build_device_picker(selectq, include_remote, on_device_selection, not_found_callback = false) {
//   let selected = selectq.find(":selected").prop('value');
//   video_devices(
//     selected,
//     (found, options) => {
//       if (include_remote) {
//         options.push($("<option value='remote'>Remote Camera</option>"));
//       }
//       selectq.empty()
//         .append(options)
//         .off('input')
//         .on('input', event => { on_device_selection(selectq); });
//       if (!found && not_found_callback) {
//         // The previously-selected camera is no longer available.
//         not_found_callback();
//       }
//       selectq.trigger("create");
//       on_device_selection(selectq);
//     });
// }


// Update: As of 30-04-2025: 
function build_device_picker(selectq, include_remote, on_device_selection, not_found_callback = false) {
  let options = [];
  
  // Get HLS stream URL using existing read_raceinfo method
  // Check if g_hlsStreamUrl is defined before using it
  let hlsStreamUrl = typeof g_hlsStreamUrl !== 'undefined' ? g_hlsStreamUrl : null;
  console.log("HLS Stream URL:", hlsStreamUrl);
  
  if (hlsStreamUrl) {
      // Add HLS stream option at the top
      options.push($("<option value='hls-stream'>HLS Stream Camera</option>"));
      selectq.data('hls-url', hlsStreamUrl);
  }
  
  // Continue with existing device enumeration
  video_devices(
      selectq.find(":selected").prop('value'),
      (found, deviceOptions) => {
          options = options.concat(deviceOptions);
          if (include_remote) {
              options.push($("<option value='remote'>Remote Camera</option>"));
          }
          
          selectq.empty()
              .append(options)
              .off('input')
              .on('input', event => { on_device_selection(selectq); });
              
          // If HLS is available and no device is selected, default to HLS
          if (hlsStreamUrl && !found) {
              selectq.val('hls-stream');
          }
          
          selectq.trigger("create");
          on_device_selection(selectq);
      }
  );
}

