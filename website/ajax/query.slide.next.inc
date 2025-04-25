<?php

require_once('inc/name-mangler.inc');
require_once('inc/path-info.inc');
require_once('inc/photo-config.inc');
require_once('inc/schema_version.inc');

function url_for_cropped(&$row, $column_name, &$repository)
{
    return $repository->url_for_file($row[$column_name], $row['racerid'], RENDER_CROPPED);
}

if (!function_exists('next_slides')) {
    function next_slides($current_slide, $subdir = '')
    {
        $slides_dir = 'slides/';
        if (!empty($subdir)) {
            $slides_dir .= $subdir . '/';
        }

        $slides = array();
        if (is_dir($slides_dir)) {
            foreach (scandir($slides_dir) as $file) {
                if (strtolower(pathinfo($file, PATHINFO_EXTENSION)) === 'png') {
                    $slides[] = $file;
                }
            }
            sort($slides); // Alphabetical order
        }

        if (empty($slides)) {
            return array();
        }

        // If no current slide, return the first slide
        if (empty($current_slide)) {
            return array($slides[0]);
        }

        // Find current slide and return the next one
        $current_index = array_search($current_slide, $slides);
        if ($current_index === false || $current_index >= count($slides) - 1) {
            return array($slides[0]); // Loop back to the first slide
        }

        return array($slides[$current_index + 1]);
    }
}
$done = false;

// The three "modes" for the slide show are 'title', 'slide', and 'racer'.
// 'title' isn't really a mode that the client would ask for, but it's a useful
// way to represent a request for the title slide.  'slide' mode explicitly
// assumes the client wants slides other than the title slide, and 'racer' mode
// is looking for racer photos.
//
// A 'title' mode query would always produce a title slide.  A 'slide' mode
// request tries to give the next slide alphabetically after the 'file'
// argument; if there isn't one, then we advance to 'racer' mode.  'racer' mode
// tries to return information about the next racer in racerid order; if there
// isn't one, then we cycle back around to 'title' mode and give a title slide.
$mode = isset($_GET['mode']) ? $_GET['mode'] : 'slide';
$subdir = '';
if (isset($_GET['subdir']) && is_acceptable_subdir($_GET['subdir'])) {
    $subdir = $_GET['subdir'];
    json_out('subdir', $subdir);
}

// Only handle slide mode now
if ($mode == 'slide' || $mode == 'title') {
    $current_file = isset($_GET['file']) ? $_GET['file'] : '';
    $results = next_slides($current_file, $subdir);

    if (count($results) > 0) {
        json_out('photo', array(
            'photo' => 'slide.php/' . ($subdir ? $subdir . '/' : '') . rawurlencode($results[0]),
            'next' => array(
                'mode' => 'slide',
                'file' => $results[0]
            )
        ));
        $done = true;
    }
}

// If no slides found, show title slide
if (!$done) {
    json_out('photo', array(
        'photo' => 'slide.php/title',
        'title' => true,
        'next' => array(
            'mode' => 'slide',
            'file' => ''
        )
    ));
}
?>