<?php
//
// Shared guard for all website/virtual/* pages.
//
// Responsibilities:
//   - Refuse to render unless the stack is running in cloud mode. The local
//     Pi never serves these pages because installer/docker-cloud/Dockerfile.web
//     is the only image that copies website/virtual/* (defense in depth here
//     in case the file ever leaks into a Pi build).
//   - Require coordinator-level permission before showing any page that can
//     publish to the broker.
//
// Pages start with: require_once(__DIR__ . '/_guard.inc'); virtual_page_guard();

// PHP-FPM's CWD for /var/www/html/virtual/*.php is the virtual/ subdir,
// but inc/authorize.inc uses a CWD-relative `require_once('inc/...')`.
// chdir to the docroot first so those nested requires resolve.
chdir(__DIR__ . '/..');

require_once(__DIR__ . '/../inc/data.inc');
require_once(__DIR__ . '/../inc/authorize.inc');
require_once(__DIR__ . '/../inc/permissions.inc');

function virtual_page_guard() {
  if (!is_cloud_mode()) {
    http_response_code(404);
    echo "<!doctype html><meta charset=utf-8><title>Not Found</title>";
    echo "<h1>404 Not Found</h1>";
    echo "<p>Virtual hardware pages are only available on the cloud twin "
       . "(DERBYNET_CLOUD_MODE).</p>";
    exit;
  }
  if (!have_permission(CONTROL_RACE_PERMISSION)) {
    http_response_code(403);
    echo "<!doctype html><meta charset=utf-8><title>Forbidden</title>";
    echo "<h1>403 Forbidden</h1>";
    echo "<p>Sign in as a race coordinator to access virtual hardware.</p>";
    echo "<p><a href=\"" . htmlspecialchars($_SERVER['HTTP_REFERER'] ?? '/derbynet/')
       . "\">Back</a></p>";
    exit;
  }
}

// DIP-switch -> lane mapping mirrors derbyRace.py:getDIPName().
// The race server reads this from the JSON payload, not the topic.
function virtual_dip_for_lane($lane) {
  switch ((int)$lane) {
    case 1: return '1000';
    case 2: return '1001';
    case 3: return '1010';
    case 4: return '1011';
    default: return null;
  }
}
?>
