<?php
/*
 * Copyright (C) 2025 Jimi Ford <jimiford@gmail.com>
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy of this software and 
 * associated documentation files (the "Software"), to deal in the Software without restriction, 
 * including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, 
 * and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, 
 * subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all copies or substantial 
 * portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT 
 * LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. 
 * IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, 
 * WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE 
 * SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

// Shared slideshow configuration system for kiosk templates
// Allows different kiosk types to specify folder paths and timing intervals

require_once('data.inc');

// Default slideshow configuration
function get_default_slideshow_config() {
    // Get slideshow duration from database settings, default to 10 seconds
    $duration_seconds = read_raceinfo('slideshow-duration', 10);
    $interval_ms = intval($duration_seconds) * 1000;
    
    return array(
        'folder' => '',  // Default to main slides folder
        'interval' => $interval_ms,  // Convert seconds to milliseconds
        'title' => 'DerbyNet Slideshow'
    );
}

// Get slideshow configuration for a specific kiosk type
function get_slideshow_config($kiosk_type = 'slideshow') {
    $config = get_default_slideshow_config();
    
    switch ($kiosk_type) {
        case 'intermission':
            $config['folder'] = 'intermission';
            // Use longer duration for intermission if not set specifically
            $intermission_duration = read_raceinfo('slideshow-duration-intermission');
            if ($intermission_duration !== false) {
                $config['interval'] = intval($intermission_duration) * 1000;
            } else {
                $config['interval'] = 30000;  // 30 seconds default for intermission
            }
            $config['title'] = 'Intermission';
            break;
        case 'sponsors':
            $config['folder'] = 'sponsors';
            // Use longer duration for sponsors if not set specifically
            $sponsors_duration = read_raceinfo('slideshow-duration-sponsors');
            if ($sponsors_duration !== false) {
                $config['interval'] = intval($sponsors_duration) * 1000;
            } else {
                $config['interval'] = 30000;  // 30 seconds default for sponsors
            }
            $config['title'] = 'Sponsors';
            break;
        case 'slideshow':
        default:
            // Use defaults from get_default_slideshow_config (which reads slideshow-duration)
            break;
    }
    
    return $config;
}

// Get the JavaScript configuration for a slideshow
function get_slideshow_js_config($kiosk_type = 'slideshow') {
    $config = get_slideshow_config($kiosk_type);
    return json_encode($config);
}
?>