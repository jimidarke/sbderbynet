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
  } finally {
    umask($old_umask);
  }
  return true;
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
