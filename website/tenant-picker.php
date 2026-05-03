<?php @session_start();

// Cloud-only landing page: pick (or create) a sandbox database before the
// rest of the app loads. Does NOT include inc/data.inc — runs without any DB.

require_once('inc/cloud-tenant.inc');
require_once('inc/banner.inc');

$cloud_mode = isset($_SERVER['DERBYNET_CLOUD_MODE']) ? $_SERVER['DERBYNET_CLOUD_MODE'] : '';
if ($cloud_mode === '') {
  http_response_code(404);
  echo "Not available on this deployment.";
  exit();
}

if (isset($_GET['switch'])) {
  clear_tenant_from_session();
  header('Location: tenant-picker.php');
  exit();
}

// If a valid tenant is already bound, nothing to pick — go to the dashboard.
if (current_tenant_slug() !== null && !isset($_GET['stay'])) {
  header('Location: index.php');
  exit();
}

$tenants = list_tenants();
$at_cap = count($tenants) >= TENANT_MAX;
?><!DOCTYPE html>
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>
<title>DerbyNet — Pick a Sandbox</title>
<link rel="stylesheet" type="text/css" href="css/jquery-ui.min.css"/>
<link rel="stylesheet" type="text/css" href="css/mobile.css"/>
<?php require('inc/stylesheet.inc'); ?>
<script type="text/javascript" src="js/jquery.js"></script>
<style>
  body {
    background: #f7f8fb;
    font-family: var(--font-stack, -apple-system, system-ui, sans-serif);
    color: #1f2937;
  }
  .tp-shell {
    max-width: 720px;
    margin: 24px auto 0;
    padding: 0 1em;
  }

  /* Cloud-mode pill, sits just below the banner */
  .tp-cloud-tag {
    display: inline-block;
    margin-bottom: 6px;
    padding: 3px 10px;
    background: var(--color-accent, #F7D117);
    color: #1f2937;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    border-radius: 3px;
  }
  .tp-shell h1 {
    margin: 4px 0 8px;
    font-size: 28px;
    font-weight: 600;
    color: #111827;
  }

  .lede {
    color: #4b5563;
    margin: 0 0 24px;
    line-height: 1.5;
  }

  .tp-section-heading {
    margin: var(--space-5, 32px) 0 var(--space-2, 8px);
    font-size: var(--fs-section, 1rem);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #6b7280;
    border-bottom: 1px solid #e5e7eb;
    padding-bottom: var(--space-2, 8px);
  }

  .tenants { margin: 0 0 var(--space-4, 20px); }

  .tenant-row {
    display: flex;
    align-items: center;
    gap: var(--space-3, 12px);
    background: #fff;
    border: 1px solid #e5e7eb;
    border-left: 4px solid var(--color-brand, #023882);
    border-radius: var(--radius-md, 8px);
    padding: 12px 16px;
    margin: 8px 0;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
    transition: box-shadow 120ms ease, transform 120ms ease,
                border-color 120ms ease;
  }
  .tenant-row:hover {
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);
    transform: translateY(-1px);
  }
  .tenant-row .slug {
    flex: 1;
    font-family: ui-monospace, "SF Mono", Menlo, monospace;
    font-size: 16px;
    font-weight: 600;
    color: #111827;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .tenant-row .meta {
    color: #6b7280;
    font-size: 12px;
    white-space: nowrap;
  }
  .tenant-row form { margin: 0; }
  .tenant-row input[type=submit] {
    padding: 8px 16px;
    font-size: 14px;
    font-weight: 500;
    color: #fff;
    background: var(--color-button-bg, #2a2d33);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: var(--radius-md, 8px);
    box-shadow: var(--shadow-button, 0 1px 2px rgba(0,0,0,.18));
    cursor: pointer;
    transition: background 120ms ease, box-shadow 120ms ease;
  }
  .tenant-row input[type=submit]:hover {
    background: var(--color-button-bg-hover, #3a3e46);
    box-shadow: var(--shadow-button-hover, 0 2px 4px rgba(0,0,0,.22));
  }
  .tenant-row input[type=submit]:focus-visible {
    outline: none;
    box-shadow: var(--shadow-button-hover, 0 2px 4px rgba(0,0,0,.22)),
                var(--focus-ring, 0 0 0 3px rgba(247, 209, 23, 0.55));
  }

  .empty {
    color: #6b7280;
    font-style: italic;
    background: #fff;
    border: 1px dashed #d1d5db;
    border-radius: var(--radius-md, 8px);
    padding: 16px;
    text-align: center;
    margin: 8px 0;
  }

  /* Create card */
  .create-box {
    background: #fff;
    border: 1px solid #e5e7eb;
    border-left: 4px solid var(--color-accent, #F7D117);
    border-radius: var(--radius-md, 8px);
    padding: 16px 20px;
    margin-top: 0;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
  }
  .create-box h2 {
    margin: 0 0 8px;
    font-size: 18px;
    font-weight: 600;
    color: #111827;
  }
  .create-box label {
    display: block;
    margin: 12px 0 6px;
    font-size: 13px;
    color: #4b5563;
  }
  .create-box input[type=text] {
    box-sizing: border-box;
    width: 100%;
    max-width: 360px;
    padding: 10px 12px;
    font-family: ui-monospace, "SF Mono", Menlo, monospace;
    font-size: 15px;
    border: 1px solid #d1d5db;
    border-radius: var(--radius-sm, 4px);
    background: #f9fafb;
    transition: border-color 120ms ease, box-shadow 120ms ease;
  }
  .create-box input[type=text]:focus {
    outline: none;
    background: #fff;
    border-color: var(--color-brand, #023882);
    box-shadow: var(--focus-ring, 0 0 0 3px rgba(247, 209, 23, 0.55));
  }
  .create-box input[type=submit] {
    margin-top: 12px;
    padding: 10px 18px;
    font-size: 15px;
    font-weight: 600;
    color: #fff;
    background: var(--color-brand, #023882);
    border: 1px solid var(--color-brand-dark, #012559);
    border-radius: var(--radius-md, 8px);
    box-shadow: var(--shadow-button, 0 1px 2px rgba(0,0,0,.18));
    cursor: pointer;
    transition: background 120ms ease, box-shadow 120ms ease;
  }
  .create-box input[type=submit]:hover {
    background: #034ab0;
    box-shadow: var(--shadow-button-hover, 0 2px 4px rgba(0,0,0,.22));
  }

  .err {
    color: #b91c1c;
    margin-top: 8px;
    min-height: 1.2em;
    font-size: 14px;
  }
  .cap-notice {
    color: #92400e;
    font-size: 13px;
    background: #fef3c7;
    border: 1px solid #fde68a;
    border-radius: var(--radius-sm, 4px);
    padding: 10px 12px;
    margin: 8px 0 0;
  }
</style>
</head>
<body>
<?php make_banner('', /* back_button */ false); ?>

<div class="tp-shell">
<span class="tp-cloud-tag">Cloud Sandbox</span>
<h1>Pick a Sandbox</h1>
<p class="lede">Each sandbox is an independent DerbyNet database on this cloud server.
Pick an existing one to continue working in it, or create a new one to start fresh.
Sandboxes are isolated from each other; nothing you do in one affects another.</p>

<h2 class="tp-section-heading">Existing Sandboxes</h2>
<div class="tenants">
<?php if (empty($tenants)) { ?>
  <p class="empty">No sandboxes yet. Create one below.</p>
<?php } else {
  foreach ($tenants as $t) {
    $slug = htmlspecialchars($t['slug'], ENT_QUOTES, 'UTF-8');
    $created = htmlspecialchars(substr($t['created'], 0, 10), ENT_QUOTES, 'UTF-8');
    $kb = $t['size'] !== false ? round($t['size'] / 1024) : 0;
    ?>
    <div class="tenant-row">
      <div class="slug"><?php echo $slug; ?></div>
      <div class="meta">created <?php echo $created; ?> &middot; <?php echo $kb; ?> KB</div>
      <form method="post" action="action.php">
        <input type="hidden" name="action" value="tenant-select.nodata"/>
        <input type="hidden" name="slug" value="<?php echo $slug; ?>"/>
        <input type="submit" value="Open"/>
      </form>
    </div>
<?php } } ?>
</div>

<h2 class="tp-section-heading">Create a New Sandbox</h2>
<div class="create-box">
  <h2 style="margin-top:0;">Start fresh</h2>
  <?php if ($at_cap) { ?>
    <p class="cap-notice">This server is at the <?php echo TENANT_MAX; ?>-sandbox cap.
    Ask an administrator to remove an idle sandbox before creating a new one.</p>
  <?php } else { ?>
    <form id="create-form" method="post" action="action.php">
      <input type="hidden" name="action" value="tenant-create.nodata"/>
      <label for="slug-input">Sandbox name (lowercase letters, digits, hyphens — up to 32 chars):</label>
      <input type="text" id="slug-input" name="slug" pattern="[a-z0-9][a-z0-9-]{0,31}"
             maxlength="32" required autocomplete="off" autofocus/>
      <input type="submit" value="Create &amp; open"/>
      <div class="err" id="create-err"></div>
    </form>
  <?php } ?>
</div>

</div><!-- /.tp-shell -->

<script>
$(function(){
  // The select form posts as a normal HTML form so the server can issue a 302.
  // The create form we hijack to surface JSON errors inline before redirecting.
  $('#create-form').on('submit', function(e) {
    e.preventDefault();
    $('#create-err').text('');
    $.post('action.php', $(this).serialize(), 'json')
      .done(function(resp) {
        if (resp && resp.outcome && resp.outcome.summary === 'success') {
          window.location = 'index.php';
        } else {
          var msg = resp && resp.outcome ? (resp.outcome.description || resp.outcome.summary) : 'Unknown error';
          $('#create-err').text(msg);
        }
      })
      .fail(function(xhr) {
        $('#create-err').text('Server error (' + xhr.status + ')');
      });
  });
});
</script>
</body>
</html>
