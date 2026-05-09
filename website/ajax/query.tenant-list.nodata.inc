<?php
// query=tenant-list.nodata — list available cloud sandboxes.
// No DB or auth required (the picker page itself is unauthenticated;
// gating is done by the .nodata bypass + cloud-mode check below).

require_once('inc/cloud-tenant.inc');

if (($_SERVER['DERBYNET_CLOUD_MODE'] ?? '') === '') {
  json_failure('not-cloud', 'Tenant selection is only available in cloud mode.');
  return true;
}

json_out('tenants', list_tenants());
json_out('max', TENANT_MAX);
json_success();
?>
