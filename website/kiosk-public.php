<?php
// Public kiosk display - read-only entry point for cloud-hosted viewing.
//
// Usage: kiosk-public.php?address=<kiosk-address>
//
// Only serves kiosk pages where the coordinator has enabled "Public Display".
// Does NOT write to the database (no kiosk registration, no last_contact updates).
// Does NOT require authentication.

require_once('inc/data.inc');
require_once('inc/kiosks.inc');

if (!isset($_GET['address'])) {
  header('Location: public-displays.php');
  exit();
}

$address = $_GET['address'];

// Look up the kiosk, but only if marked public
ensure_kiosk_public_column();
try {
  $stmt = $db->prepare('SELECT page, name, public FROM Kiosks WHERE address = :address');
  $stmt->execute(array(':address' => $address));
  $row = $stmt->fetch(PDO::FETCH_ASSOC);
  $stmt->closeCursor();
} catch (PDOException $p) {
  $row = false;
}

if (!$row || !$row['public'] || !$row['page']) {
  header('HTTP/1.1 403 Forbidden');
  echo '<!DOCTYPE html><html><head><title>Not Available</title>';
  echo '<style>body{font-family:sans-serif;text-align:center;padding:60px;background:#1a1a2e;color:#eee;}';
  echo 'h1{font-size:2em;}p{color:#aaa;}</style></head><body>';
  echo '<h1>Display Not Available</h1>';
  echo '<p>This kiosk display is not configured for public viewing.</p>';
  echo '<p><a href="public-displays.php" style="color:#4fc3f7;">View available displays</a></p>';
  echo '</body></html>';
  exit();
}

// Set up globals that kiosk pages expect
$g_kiosk_address = $address;
$g_kiosk_parameters_string = '';

function kiosk_parameters() {
  global $g_kiosk_parameters_string;
  return json_decode(empty($g_kiosk_parameters_string) ? '{}' : $g_kiosk_parameters_string, true);
}

// Parse page and parameters
$page = $row['page'];
if ($page[0] == '!') {
  $page = substr($page, 1);
}
$ex = explode('#', $page, 2);
if (count($ex) > 1) {
  $page = $ex[0];
  $g_kiosk_parameters_string = $ex[1];
}

// Security: confirm the page is under the kiosks directory
$self = dirname(realpath($_SERVER['SCRIPT_FILENAME']));
$resolved = realpath($self.'/'.$page);
$kiosks_dir = $self.DIRECTORY_SEPARATOR.'kiosks';
if (!$resolved || strpos($resolved, $kiosks_dir) !== 0) {
  header('HTTP/1.1 403 Forbidden');
  echo 'Invalid kiosk page.';
  exit();
}

session_write_close();
require($page);
?>
