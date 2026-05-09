<?php
// action=tenant-select.nodata — bind a sandbox slug to the current session.
// Slug arrives via $_POST and is validated; once accepted it lives in
// $_SESSION['tenant_slug'] and is the *only* trusted source thereafter.

require_once('inc/cloud-tenant.inc');

if (($_SERVER['DERBYNET_CLOUD_MODE'] ?? '') === '') {
  json_failure('not-cloud', 'Tenant selection is only available in cloud mode.');
  return true;
}

$slug = isset($_POST['slug']) ? $_POST['slug'] : '';

if (!valid_tenant_slug($slug)) {
  json_failure('invalid-slug', 'Sandbox name has invalid characters.');
  return true;
}
if (!tenant_exists($slug)) {
  json_failure('no-such-tenant', 'No sandbox named "' . htmlspecialchars($slug) . '".');
  return true;
}

if (!adopt_tenant_in_session($slug)) {
  json_failure('select-failed', 'Could not bind sandbox to session.');
  return true;
}

// If this came in as a regular HTML form post (no XHR header), redirect the
// browser to the dashboard so the user lands somewhere useful. AJAX callers
// see plain JSON success and navigate themselves.
$is_xhr = strtolower($_SERVER['HTTP_X_REQUESTED_WITH'] ?? '') === 'xmlhttprequest';
if (!$is_xhr) {
  header('Location: index.php');
  exit();
}

json_success();
?>
