<?php


function remove_fake_images($directory) {
    // Early return if directory is null or empty
    if (empty($directory)) {
        return;
    }
    
    // Type check to satisfy PHP deprecation warning
    if (!is_string($directory)) {
        return;
    }

    if (!is_dir($directory)) {
        return;
    }
    $dh = @opendir($directory);
    if ($dh !== false) {
        while (($filename = readdir($dh)) !== false) {
            if ($filename == '.' || $filename == '..') {
                continue;
            }
            $path = $directory.DIRECTORY_SEPARATOR.$filename;
            if (is_dir($path)) {
                remove_fake_images($path);
            } else if (preg_match("/^fake_[0-9]*\\.svg$/", $filename)) {
                @unlink($path);
            }
        }
        closedir($dh);
    }
}

function remove_fake_car_and_racer_images() {
  remove_fake_images(read_raceinfo('photo-directory'));
  remove_fake_images(read_raceinfo('car-photo-directory'));
}

?>