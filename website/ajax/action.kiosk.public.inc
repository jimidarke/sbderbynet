<?php
// Set the public visibility flag for a kiosk display.
// $_POST['address'] identifies the kiosk
// $_POST['public'] = 1 (visible on cloud) or 0 (local only)

require_once('inc/kiosks.inc');

if (have_permission(CONTROL_RACE_PERMISSION)) {
  ensure_kiosk_public_column();
  $stmt = $db->prepare('UPDATE Kiosks SET public = :public WHERE address = :address');
  $stmt->execute(array(':public' => $_POST['public'] ? 1 : 0,
                        ':address' => $_POST['address']));
  json_success();
  json_out('kiosks', all_kiosks());
  json_out('kiosk-pages', all_kiosk_pages());
} else {
  json_not_authorized();
}
?>
