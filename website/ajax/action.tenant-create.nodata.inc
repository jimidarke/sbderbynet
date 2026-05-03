<?php
// action=tenant-create.nodata — provision a new sandbox SQLite database
// and bind it to the current session.

require_once('inc/cloud-tenant.inc');

if (($_SERVER['DERBYNET_CLOUD_MODE'] ?? '') === '') {
  json_failure('not-cloud', 'Tenant creation is only available in cloud mode.');
  return true;
}

$slug = isset($_POST['slug']) ? trim($_POST['slug']) : '';

if (!valid_tenant_slug($slug)) {
  json_failure('invalid-slug',
               'Sandbox name must be 1–32 chars: lowercase letters, digits, hyphens; first char alphanumeric.');
  return true;
}

if (tenant_count() >= TENANT_MAX) {
  json_failure('cap-reached',
               'This server is at the ' . TENANT_MAX . '-sandbox cap. Ask an admin to remove an idle sandbox.');
  return true;
}

if (is_dir(tenant_dir($slug))) {
  json_failure('already-exists', 'A sandbox named "' . htmlspecialchars($slug) . '" already exists.');
  return true;
}

try {
  create_tenant($slug);
} catch (PDOException $p) {
  json_failure('schema', 'Database setup failed: ' . $p->getMessage());
  return true;
} catch (RuntimeException $r) {
  json_failure('create', $r->getMessage());
  return true;
}

if (!adopt_tenant_in_session($slug)) {
  json_failure('select-failed', 'Created the sandbox but could not bind it to your session.');
  return true;
}

json_success();
?>
