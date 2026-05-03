<?php
// Public displays landing page - lists all kiosk displays marked as public.
// No authentication required.

require_once('inc/data.inc');
require_once('inc/kiosks.inc');

ensure_kiosk_public_column();

$public_kiosks = array();
try {
  $stmt = $db->query('SELECT address, name, page FROM Kiosks'
                     .' WHERE public = 1'
                     .' AND page IS NOT NULL'
                     .' AND page != \'\''
                     .' ORDER BY name, address');
  foreach ($stmt as $row) {
    $page = $row['page'];
    if ($page[0] == '!') {
      $page = substr($page, 1);
    }
    $page_parts = explode('#', $page, 2);
    $page_name = basename($page_parts[0], '.kiosk');

    $public_kiosks[] = array(
      'address' => $row['address'],
      'name' => $row['name'] ? $row['name'] : $page_name,
      'page_name' => $page_name
    );
  }
} catch (PDOException $p) {
  // Table may not exist yet
}

$event_name = read_raceinfo('event-name', 'SBDerbyNet');
?><!DOCTYPE html>
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title><?php echo htmlspecialchars($event_name); ?> - Live Displays</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #1a1a2e;
    color: #eee;
    min-height: 100vh;
    padding: 40px 20px;
  }
  .container { max-width: 800px; margin: 0 auto; }
  h1 {
    font-size: 2em;
    margin-bottom: 8px;
    color: #fff;
  }
  .subtitle {
    color: #888;
    margin-bottom: 40px;
    font-size: 1.1em;
  }
  .display-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
    gap: 16px;
  }
  .display-card {
    background: #16213e;
    border: 1px solid #0f3460;
    border-radius: 12px;
    padding: 24px;
    text-decoration: none;
    color: #eee;
    transition: transform 0.15s, border-color 0.15s;
  }
  .display-card:hover {
    transform: translateY(-2px);
    border-color: #4fc3f7;
  }
  .display-card h2 {
    font-size: 1.2em;
    margin-bottom: 6px;
  }
  .display-card .page-type {
    color: #4fc3f7;
    font-size: 0.85em;
    text-transform: capitalize;
  }
  .no-displays {
    text-align: center;
    padding: 60px 20px;
    color: #666;
  }
  .no-displays h2 { color: #888; margin-bottom: 12px; }
  .refresh-note {
    text-align: center;
    margin-top: 40px;
    color: #555;
    font-size: 0.85em;
  }
</style>
<meta http-equiv="refresh" content="30"/>
</head>
<body>
<div class="container">
  <h1><?php echo htmlspecialchars($event_name); ?></h1>
  <p class="subtitle">Live Race Displays</p>

<?php if (count($public_kiosks) > 0) { ?>
  <div class="display-grid">
<?php foreach ($public_kiosks as $kiosk) { ?>
    <a class="display-card" href="kiosk-public.php?address=<?php echo urlencode($kiosk['address']); ?>">
      <h2><?php echo htmlspecialchars($kiosk['name']); ?></h2>
      <span class="page-type"><?php echo htmlspecialchars(str_replace('-', ' ', $kiosk['page_name'])); ?></span>
    </a>
<?php } ?>
  </div>
<?php } else { ?>
  <div class="no-displays">
    <h2>No displays available</h2>
    <p>Public displays will appear here when enabled by the race coordinator.</p>
  </div>
<?php } ?>

  <p class="refresh-note">This page refreshes automatically.</p>
</div>
</body>
</html>
