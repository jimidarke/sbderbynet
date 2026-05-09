// Font sizing for the now-racing main board is now done in pure CSS via
// `font-size: clamp(...)` in css/now-racing.css, driven by the --nlanes
// custom property set on <html> by the kiosk template. The historic
// JS reflow loop (75 ms setInterval) has been removed for Pi performance.
//
// FontAdjuster is kept as a no-op stub so existing call sites in
// now-racing.js (FontAdjuster.reset / FontAdjuster.table_resized) don't
// have to be changed.

var FontAdjuster = {
  start:         function() {},
  reset:         function() {},
  table_resized: function() {}
};
