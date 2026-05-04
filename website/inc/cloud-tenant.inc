<?php
// Per-session tenant ("sandbox") database selection for the cloud VPS.
// Each tenant is an independent SQLite file under DERBYNET_TENANTS_DIR.
// Slug binds to the browser session; never trusted from request input
// after the initial pick.

define('TENANT_MAX', 50);
define('TENANT_SLUG_RE', '/^[a-z0-9][a-z0-9-]{0,31}$/');

function tenants_dir() {
  $d = isset($_SERVER['DERBYNET_TENANTS_DIR']) && $_SERVER['DERBYNET_TENANTS_DIR'] !== ''
       ? $_SERVER['DERBYNET_TENANTS_DIR']
       : '/var/lib/derbynet/tenants';
  return rtrim($d, DIRECTORY_SEPARATOR);
}

function valid_tenant_slug($s) {
  return is_string($s) && preg_match(TENANT_SLUG_RE, $s) === 1;
}

function tenant_dir($slug) {
  return tenants_dir() . DIRECTORY_SEPARATOR . $slug;
}

function tenant_db_path($slug) {
  return tenant_dir($slug) . DIRECTORY_SEPARATOR . 'derbynet.sqlite3';
}

function tenant_exists($slug) {
  return valid_tenant_slug($slug) && is_file(tenant_db_path($slug));
}

function list_tenants() {
  $base = tenants_dir();
  $out = array();
  if (!is_dir($base)) return $out;
  foreach (scandir($base) as $entry) {
    if ($entry === '.' || $entry === '..') continue;
    if (!valid_tenant_slug($entry)) continue;
    $db = tenant_db_path($entry);
    if (!is_file($db)) continue;
    $out[] = array(
      'slug' => $entry,
      'created' => @date('c', @filectime($db)),
      'size' => @filesize($db),
    );
  }
  usort($out, function($a, $b) { return strcmp($a['slug'], $b['slug']); });
  return $out;
}

function tenant_count() {
  return count(list_tenants());
}

// Provision a fresh tenant: mkdir, mkdir media subdirs, create empty SQLite,
// apply schema. Returns true on success, throws PDOException or RuntimeException
// on failure. Caller is responsible for slug validation BEFORE calling.
function create_tenant($slug) {
  if (!valid_tenant_slug($slug)) {
    throw new RuntimeException('invalid slug');
  }
  $dir = tenant_dir($slug);
  if (is_dir($dir)) {
    throw new RuntimeException('already exists');
  }
  $old_umask = umask(0);
  try {
    if (!@mkdir($dir, 0777, true)) {
      $e = error_get_last();
      throw new RuntimeException('mkdir failed: ' . ($e['message'] ?? $dir));
    }
    foreach (array('racers', 'cars', 'videos', 'logs', 'imagery', 'slides') as $sub) {
      @mkdir($dir . DIRECTORY_SEPARATOR . $sub, 0777, true);
    }
    $path = tenant_db_path($slug);
    $pdo = new PDO('sqlite:' . $path, '', '', array());
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    $pdo->setAttribute(PDO::ATTR_CASE, PDO::CASE_LOWER);
    @chmod($path, 0666);

    // Apply the standard schema. schema.inc uses globals $db, $dbtype and
    // calls expected_schema_version() / sql_file_path().
    require_once(dirname(__FILE__) . '/schema_version.inc');
    require_once(dirname(__FILE__) . '/sql-script.inc');
    global $db, $dbtype;
    $db = $pdo;
    $dbtype = 'sqlite';
    $script = include(dirname(__FILE__) . '/../sql/sqlite/schema.inc');
    if (!is_array($script)) {
      throw new RuntimeException('schema script missing');
    }
    foreach ($script as $stmt) {
      $pdo->exec($stmt);
    }
    apply_tenant_defaults($pdo, $slug);
  } finally {
    umask($old_umask);
  }
  return true;
}

// SBDerbyNet sandbox defaults — written after the stock schema bootstrap so
// they overlay or supplement schema.inc's INSERTs. Captured from the test01
// reference sandbox on 2026-05-03; update here when the canonical preset
// changes. Media paths are recomputed per tenant from the slug.
function tenant_default_raceinfo($slug) {
  $base = tenant_dir($slug);
  return array(
    // Track / scoring
    'lane_count'           => '3',
    'track-length'         => '500',
    'weight-units'         => 'kg',
    'name-style'           => '0',
    // Labels / branding
    'partition-label'      => 'Age Group',
    'supergroup-label'     => 'Event',
    'images-dir'           => 'SoapBox',
    // Display toggles (overlay schema.inc defaults)
    'photos-on-now-racing' => '0',
    'show-cars-on-deck'    => '0',
    'show-racer-photos-rr' => '0',
    'show-car-photos-rr'   => '0',
    'upload-videos'        => '1',
    // Scheduling weights
    'avoid-consecutive'    => '1000',
    'heat-counts'          => '300',
    // Per-tenant media paths
    'photo-directory'      => $base . '/racers/',
    'car-photo-directory'  => $base . '/cars/',
    'video-directory'      => $base . '/videos/',
    'slideshow-directory'  => $base . '/slides/',
  );
}

function apply_tenant_defaults(PDO $pdo, $slug) {
  $defaults = tenant_default_raceinfo($slug);
  $exists = $pdo->prepare('SELECT COUNT(*) FROM RaceInfo WHERE itemkey = :k');
  $insert = $pdo->prepare('INSERT INTO RaceInfo(itemkey, itemvalue) VALUES(:k, :v)');
  $update = $pdo->prepare('UPDATE RaceInfo SET itemvalue = :v WHERE itemkey = :k');
  foreach ($defaults as $key => $val) {
    $exists->execute(array(':k' => $key));
    if ($exists->fetchColumn() > 0) {
      $update->execute(array(':k' => $key, ':v' => $val));
    } else {
      $insert->execute(array(':k' => $key, ':v' => $val));
    }
  }
}

// Bind a (validated) slug to the current session, regenerating the session ID
// to defend against session-fixation across the privilege change.
function adopt_tenant_in_session($slug) {
  if (!tenant_exists($slug)) return false;
  // Drop role/permissions held against any previously-selected tenant.
  unset($_SESSION['role']);
  unset($_SESSION['permissions']);
  if (session_status() === PHP_SESSION_ACTIVE) {
    @session_regenerate_id(true);
  }
  $_SESSION['tenant_slug'] = $slug;
  return true;
}

function clear_tenant_from_session() {
  unset($_SESSION['tenant_slug']);
  unset($_SESSION['role']);
  unset($_SESSION['permissions']);
  if (session_status() === PHP_SESSION_ACTIVE) {
    @session_regenerate_id(true);
  }
}

function current_tenant_slug() {
  return isset($_SESSION['tenant_slug']) && tenant_exists($_SESSION['tenant_slug'])
         ? $_SESSION['tenant_slug']
         : null;
}
?>
