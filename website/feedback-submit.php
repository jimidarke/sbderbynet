<?php
// Audience-feedback sink for the public spectator pages.
//
// This is a deliberately STANDALONE, unauthenticated endpoint. It does NOT
// include the DerbyNet session/DB/authorization stack — it never touches the
// race database, so a flood or failure here cannot affect racing. The public
// feedback page (stats-gen template-feedback.html) POSTs here via Caddy, which
// reverse-proxies live.<host>/<TOKEN>/feedback-submit → /feedback-submit.php.
//
// Every submission is appended (no dedup) to a JSONL file so the organizers can
// do a manual post-mortem and, e.g., spot one device/IP spamming. The soft
// "one note per person" gate lives in the browser (localStorage); the server
// trusts nothing and records each POST with its own timestamp. The client IP
// and User-Agent are stored for that forensic post-mortem only — these pages
// never display them. See docs/PUBLIC_STATS.md.

header('Content-Type: application/json');
header('Cache-Control: no-store');

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
  http_response_code(405);
  echo json_encode(['error' => 'method_not_allowed']);
  exit;
}

// --- Parse input: JSON body (what the page sends) or form fields as fallback.
$raw = file_get_contents('php://input');
$in = json_decode($raw, true);
if (!is_array($in)) { $in = $_POST; }

$device_id = isset($in['device_id']) ? (string)$in['device_id'] : '';
$text      = isset($in['text'])      ? (string)$in['text']      : '';

// device_id is a client-minted id (UUID or fallback). Keep it tame: a bounded
// set of url-safe chars, length-capped. Empty/garbage → reject.
$device_id = preg_replace('/[^A-Za-z0-9_.\-]/', '', $device_id);
$device_id = substr($device_id, 0, 64);

// text: strip control chars (keep ordinary spaces/newlines stripped too — a
// single line keeps the JSONL tidy), collapse, then hard-cap at 150 chars to
// match the textarea limit regardless of what the client actually sent.
$text = preg_replace('/[\x00-\x1F\x7F]+/u', ' ', $text);
$text = trim($text);
if (function_exists('mb_substr')) {
  $text = mb_substr($text, 0, 150, 'UTF-8');
} else {
  $text = substr($text, 0, 150);
}

if ($device_id === '' || $text === '') {
  http_response_code(400);
  echo json_encode(['error' => 'missing_fields']);
  exit;
}

// --- Resolve a writable data dir. derbynet-web mounts derbynet_data RW at
// /var/lib/derbynet and sets DERBYNET_DATA_DIR; fall back to that path.
$data_dir = $_SERVER['DERBYNET_DATA_DIR'] ?? getenv('DERBYNET_DATA_DIR') ?: '/var/lib/derbynet';
$fb_dir   = rtrim($data_dir, '/') . '/feedback';
$fb_file  = $fb_dir . '/feedback.jsonl';

if (!is_dir($fb_dir)) {
  @mkdir($fb_dir, 0775, true);
}

// Disk-abuse backstop: a generous cap far above any plausible real event
// (~hundreds of thousands of notes). Past it, accept-but-drop so we never
// error-loop a spammer or fill the volume. We intentionally do NOT rate-limit
// per device/IP — capturing the repeats is the whole point of this log.
$MAX_BYTES = 50 * 1024 * 1024;
if (is_file($fb_file) && filesize($fb_file) >= $MAX_BYTES) {
  echo json_encode(['status' => 'ok']); // pretend success; quietly dropped
  exit;
}

// Client IP: behind Caddy, REMOTE_ADDR is the proxy, so prefer the left-most
// X-Forwarded-For hop (the real spectator). For a forensic-only field that's
// fine even though XFF is client-influenceable.
$ip = $_SERVER['REMOTE_ADDR'] ?? '';
if (!empty($_SERVER['HTTP_X_FORWARDED_FOR'])) {
  $parts = explode(',', $_SERVER['HTTP_X_FORWARDED_FOR']);
  $ip = trim($parts[0]);
}
$ua = substr($_SERVER['HTTP_USER_AGENT'] ?? '', 0, 400);

$record = [
  'ts'        => gmdate('c'),            // UTC ISO-8601; post-mortem can localize
  'device_id' => $device_id,
  'text'      => $text,
  'ip'        => $ip,
  'ua'        => $ua,
];

$line = json_encode($record, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES) . "\n";

if (@file_put_contents($fb_file, $line, FILE_APPEND | LOCK_EX) === false) {
  http_response_code(500);
  echo json_encode(['error' => 'write_failed']);
  exit;
}

echo json_encode(['status' => 'ok']);
