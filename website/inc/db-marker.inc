<?php
// "Active database" marker — lets ad-hoc racing mode re-point the whole rig at a
// SEPARATE SQLite file without touching the official event DB. The selector
// cannot live inside any DB (it is the thing being switched), so it lives as a
// tiny text file on the Pi filesystem holding one absolute path.
//
// This file has NO database dependency, so it is safe to include from
// local/config-database.inc *before* $db exists. See docs/ADHOC.md.
//
// Race-day safety: any malformed / missing / out-of-bounds marker resolves back
// to the official DB. The marker can only ever select a *.sqlite3 file that
// already exists in the SAME directory as the official DB.

// Path of the marker file. Overridable (DERBYNET_ACTIVE_DB_MARKER) so the test
// harness can point it somewhere writable.
function dn_db_marker_path() {
  $m = getenv('DERBYNET_ACTIVE_DB_MARKER');
  if ($m === false || $m === '') {
    $m = isset($_SERVER['DERBYNET_ACTIVE_DB_MARKER']) ? $_SERVER['DERBYNET_ACTIVE_DB_MARKER'] : '';
  }
  return ($m !== '') ? $m : '/var/lib/derbynet/active-db';
}

// Is $candidate an acceptable active-DB path, given the official DB path?
// Allowlist: a real *.sqlite3 file living in the same directory as official,
// with no path-traversal tricks.
function dn_db_path_allowed($candidate, $official_path) {
  if (!is_string($candidate) || $candidate === '') return false;
  if (strpos($candidate, "\0") !== false || strpos($candidate, '..') !== false) return false;
  if (substr($candidate, -8) !== '.sqlite3') return false;
  if (rtrim(dirname($candidate), '/') !== rtrim(dirname($official_path), '/')) return false;
  return @is_file($candidate);
}

// Resolve which DB the rig should open right now. Returns $official_path unless
// the marker names a valid sibling .sqlite3 file.
function dn_resolve_active_db($official_path) {
  $marker = dn_db_marker_path();
  if (@is_readable($marker)) {
    $candidate = trim((string)@file_get_contents($marker));
    if (dn_db_path_allowed($candidate, $official_path)) {
      return $candidate;
    }
  }
  return $official_path;
}

// Point the marker at $path (an absolute DB path, or '' to clear → official).
// Returns true on success. Writes ATOMICALLY (temp file + fsync + rename) so a
// crash or concurrent reader can never observe a half-written / truncated marker
// (which would silently fail-safe to official and hide the switch).
function dn_set_active_db($path) {
  $marker = dn_db_marker_path();
  $content = ($path === '' || $path === null) ? "\n" : ($path . "\n");
  $tmp = $marker . '.tmp';

  $fh = @fopen($tmp, 'wb');
  if ($fh === false) {
    // Could not create the temp file (e.g. dir perms) — fall back to a direct
    // write rather than failing the switch outright.
    return @file_put_contents($marker, $content) !== false;
  }
  $ok = @fwrite($fh, $content);
  if ($ok !== false) {
    @fflush($fh);
    if (function_exists('fsync')) { @fsync($fh); }
  }
  @fclose($fh);
  if ($ok === false || !@rename($tmp, $marker)) {
    @unlink($tmp);
    return false;
  }
  return true;
}
?>
