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
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>SoapboxDerbyNet — Open or create a sandbox</title>
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
    max-width: 1080px;
    margin: 0 auto;
    padding: 0 1em;
  }

  /* ---- Secondary header row: back-link + cloud pill ---- */
  .tp-subhead {
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 18px 0 8px;
    flex-wrap: wrap;
  }
  .tp-back {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    color: var(--color-brand, #023882);
    text-decoration: none;
    font-size: 14px;
    font-weight: 500;
    padding: 6px 10px;
    border-radius: 6px;
    transition: background 120ms ease;
  }
  .tp-back:hover { background: rgba(2,56,130,0.06); }
  .tp-back-arrow { font-size: 16px; line-height: 1; }
  .tp-subhead-spacer { flex: 1; }
  .tp-cloud-tag {
    display: inline-block;
    padding: 3px 10px;
    background: var(--color-accent, #F7D117);
    color: #1f2937;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    border-radius: 3px;
  }

  /* ---- Title block ---- */
  .tp-title {
    margin: 8px 0 6px;
    font-size: 28px;
    font-weight: 600;
    color: #111827;
    letter-spacing: -0.01em;
  }
  .tp-lede {
    color: #4b5563;
    margin: 0 0 24px;
    line-height: 1.5;
    font-size: 1rem;
  }

  /* ---- Two-column grid ---- */
  .tp-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 20px;
    margin-bottom: 32px;
  }
  @media (min-width: 760px) {
    .tp-grid {
      grid-template-columns: 1.15fr 1fr;
      align-items: start;
    }
  }
  /* On narrow screens, create comes first (most likely first-time action) */
  @media (max-width: 759px) {
    .tp-grid > .tp-col-create { order: -1; }
  }

  .tp-col {
    background: #fff;
    border: 1px solid #e5e7eb;
    border-radius: var(--radius-md, 8px);
    padding: 18px 20px 20px;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
  }
  .tp-col-existing { border-left: 4px solid var(--color-brand, #023882); }
  .tp-col-create   { border-left: 4px solid var(--color-accent, #F7D117); }

  .tp-col-head {
    margin: 0 0 4px;
    font-size: 1.0625rem;
    font-weight: 700;
    color: #111827;
    letter-spacing: -0.005em;
  }
  .tp-col-sub {
    margin: 0 0 14px;
    font-size: 13px;
    color: #6b7280;
  }

  /* ---- Logging-in collapsible ---- */
  .tp-help {
    margin: 4px 0 12px;
    font-size: 13px;
    color: #4b5563;
  }
  .tp-help summary {
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    color: var(--color-brand, #023882);
    font-weight: 500;
    list-style: none;
    padding: 4px 0;
    user-select: none;
  }
  .tp-help summary::-webkit-details-marker { display: none; }
  .tp-help summary::before {
    content: "▸";
    display: inline-block;
    font-size: 10px;
    transition: transform 150ms ease;
  }
  .tp-help[open] summary::before { transform: rotate(90deg); }
  .tp-help summary:hover { text-decoration: underline; }
  .tp-help-body {
    margin: 8px 0 4px;
    padding: 10px 12px;
    background: #fffbeb;
    border: 1px solid #fde68a;
    border-radius: var(--radius-sm, 4px);
    line-height: 1.5;
  }
  .tp-help-body code {
    background: #fef3c7;
    border: 1px solid #fde68a;
    color: #92400e;
    padding: 1px 6px;
    border-radius: 3px;
    font-family: ui-monospace, "SF Mono", Menlo, monospace;
    font-size: 12px;
    font-weight: 600;
  }

  /* ---- Tenant rows ---- */
  .tenants { margin: 0; }
  .tenant-row {
    display: flex;
    align-items: center;
    gap: var(--space-3, 12px);
    background: #fff;
    border: 1px solid #e5e7eb;
    border-radius: var(--radius-md, 8px);
    padding: 10px 14px;
    margin: 8px 0 0;
    transition: box-shadow 120ms ease, transform 120ms ease, border-color 120ms ease;
  }
  .tenant-row:first-child { margin-top: 0; }
  .tenant-row:hover {
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.06);
    transform: translateY(-1px);
    border-color: #cbd5e1;
  }
  .tenant-row .slug {
    flex: 1;
    font-family: ui-monospace, "SF Mono", Menlo, monospace;
    font-size: 15px;
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
    padding: 7px 14px;
    font-size: 13px;
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
    background: #fafbfc;
    border: 1px dashed #d1d5db;
    border-radius: var(--radius-md, 8px);
    padding: 14px;
    text-align: center;
    font-size: 14px;
  }
  .empty .arrow {
    display: inline-block;
    margin: 0 4px;
    color: var(--color-accent, #F7D117);
    font-weight: 700;
  }

  /* ---- Create form ---- */
  .tp-col-create label {
    display: block;
    margin: 8px 0 6px;
    font-size: 13px;
    color: #4b5563;
  }
  .tp-col-create input[type=text] {
    box-sizing: border-box;
    width: 100%;
    padding: 10px 12px;
    font-family: ui-monospace, "SF Mono", Menlo, monospace;
    font-size: 15px;
    border: 1px solid #d1d5db;
    border-radius: var(--radius-sm, 4px);
    background: #f9fafb;
    transition: border-color 120ms ease, box-shadow 120ms ease;
  }
  .tp-col-create input[type=text]:focus {
    outline: none;
    background: #fff;
    border-color: var(--color-brand, #023882);
    box-shadow: var(--focus-ring, 0 0 0 3px rgba(247, 209, 23, 0.55));
  }
  .tp-col-create input[type=submit] {
    margin-top: 14px;
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
  .tp-col-create input[type=submit]:hover {
    background: #034ab0;
    box-shadow: var(--shadow-button-hover, 0 2px 4px rgba(0,0,0,.22));
  }
  .tp-col-create input[type=submit]:focus-visible {
    outline: none;
    box-shadow: var(--shadow-button-hover, 0 2px 4px rgba(0,0,0,.22)),
                var(--focus-ring, 0 0 0 3px rgba(247, 209, 23, 0.55));
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
    margin: 4px 0 0;
  }
</style>
</head>
<body>
<?php make_banner('', /* back_button */ false); ?>

<div class="tp-shell">

<div class="tp-subhead">
  <a class="tp-back" href="/">
    <span class="tp-back-arrow" aria-hidden="true">&larr;</span>
    soapboxderbynet.com
  </a>
  <div class="tp-subhead-spacer"></div>
  <span class="tp-cloud-tag">Cloud Sandbox</span>
</div>

<h1 class="tp-title">Open or create a sandbox</h1>
<p class="tp-lede">Each sandbox is an isolated DerbyNet database on this cloud
server. Open one to continue, or start fresh.</p>

<div class="tp-grid">

  <section class="tp-col tp-col-existing">
    <h2 class="tp-col-head">Open an existing sandbox</h2>
    <p class="tp-col-sub">Pick up where someone left off &mdash; each sandbox keeps
      its own data.</p>

    <details class="tp-help">
      <summary>Logging in</summary>
      <div class="tp-help-body">
        On the login screen, pick any role
        (<b>RaceCoordinator</b>, <b>RaceCrew</b>, <b>Photo</b>) and use the
        password <code>derbynet</code>. The same password works for every
        role on this test site.
      </div>
    </details>

    <div class="tenants">
    <?php if (empty($tenants)) { ?>
      <p class="empty">No sandboxes yet. Start one
        <span class="arrow" aria-hidden="true">&rarr;</span></p>
    <?php } else {
      foreach ($tenants as $t) {
        $slug = htmlspecialchars($t['slug'], ENT_QUOTES, 'UTF-8');
        $created = htmlspecialchars(substr($t['created'], 0, 10), ENT_QUOTES, 'UTF-8');
        $kb = $t['size'] !== false ? round($t['size'] / 1024) : 0;
        ?>
        <div class="tenant-row">
          <div class="slug"><?php echo $slug; ?></div>
          <div class="meta"><?php echo $created; ?> &middot; <?php echo $kb; ?> KB</div>
          <form method="post" action="action.php">
            <input type="hidden" name="action" value="tenant-select.nodata"/>
            <input type="hidden" name="slug" value="<?php echo $slug; ?>"/>
            <input type="submit" value="Open"/>
          </form>
        </div>
    <?php } } ?>
    </div>
  </section>

  <section class="tp-col tp-col-create">
    <h2 class="tp-col-head">Start a new sandbox</h2>
    <p class="tp-col-sub">Independent database. Isolated from every other sandbox.</p>

    <?php if ($at_cap) { ?>
      <p class="cap-notice">This server is at the <?php echo TENANT_MAX; ?>-sandbox cap.
      Ask an administrator to remove an idle sandbox before creating a new one.</p>
    <?php } else { ?>
      <form id="create-form" method="post" action="action.php">
        <input type="hidden" name="action" value="tenant-create.nodata"/>
        <label for="slug-input">Sandbox name <span style="color:#9ca3af;font-weight:normal;">(lowercase, digits, hyphens &mdash; up to 32 chars)</span></label>
        <input type="text" id="slug-input" name="slug" pattern="[a-z0-9][a-z0-9-]{0,31}"
               maxlength="32" required autocomplete="off" autofocus/>
        <input type="submit" value="Create &amp; open"/>
        <div class="err" id="create-err"></div>
      </form>
    <?php } ?>
  </section>

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
