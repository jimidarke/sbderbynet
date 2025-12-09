<?php
session_start(); 
require_once('inc/data.inc'); 
require_once('inc/authorize.inc');
session_write_close();
require_once('inc/banner.inc');
require_permission(SET_UP_PERMISSION);
?>
<!DOCTYPE html>
<html>
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>
    <title>Elimination Tournament Configuration Editor</title>
    <?php require('inc/stylesheet.inc'); ?>
    <link rel="stylesheet" type="text/css" href="css/elimination-config-editor.css" />
    <script type="text/javascript" src="js/jquery.js"></script>
    <script type="text/javascript" src="js/jquery-ui.min.js"></script>
    <script type="text/javascript" src="js/ajax-setup.js"></script>
    <script type="text/javascript" src="js/modal.js"></script>
    <script type="text/javascript" src="js/elimination-config-editor.js"></script>
</head>
<body>
<?php make_banner('Elimination Tournament Configuration', 'racing-groups.php'); ?>

<div id="config-editor-container">

    <!-- Config Selection -->
    <div class="editor-section">
        <div class="section-header">
            <h2>Configuration</h2>
            <div class="config-actions">
                <button id="new-config-btn" class="action-btn">New</button>
                <button id="clone-config-btn" class="action-btn">Clone</button>
                <button id="delete-config-btn" class="action-btn delete-btn">Delete</button>
            </div>
        </div>
        <select id="config-selector" class="config-select">
            <option value="">Loading configurations...</option>
        </select>
        <div id="lock-warning" class="warning-box">
            <strong>⚠ Read-Only:</strong>
            Tournament is active for classes: <span id="active-classes-list"></span>
        </div>
    </div>

    <!-- Metadata Section -->
    <div class="editor-section">
        <h2>Configuration Details</h2>
        <form id="config-form">
            <div class="form-row">
                <label for="format-name">Format Name *</label>
                <input type="text" id="format-name" required
                       placeholder="Soapbox Derby Triple Elimination" />
            </div>
            <div class="form-row">
                <label for="description">Description</label>
                <textarea id="description" rows="2"
                          placeholder="Standard soapbox derby elimination format"></textarea>
            </div>
        </form>
    </div>

    <!-- Age Groups Section (label is dynamic based on settings) -->
    <div class="editor-section">
        <div class="section-header">
            <h2 id="age-groups-section-header">Age Groups</h2>
            <button id="add-age-group-btn" class="action-btn">Add Age Group</button>
        </div>
        <div id="age-groups-container">
            <!-- Age groups rendered here by JavaScript -->
        </div>
    </div>

    <!-- Scheduling Rules Section -->
    <div class="editor-section">
        <h2>Scheduling Rules</h2>
        <div id="scheduling-rules-form">
            <p>These settings control how heats are generated for elimination tournaments.</p>

            <div class="form-row">
                <label for="heat-counts">Heat Counts:</label>
                <select id="heat-counts" name="heat-counts">
                    <option value="0">Zero</option>
                    <option value="50">Low (50)</option>
                    <option value="300">Medium (300)</option>
                    <option value="1000">Heavy (1000)</option>
                    <option value="10" selected>Custom (10)</option>
                </select>
                <small>Weight for distributing racers across heats</small>
            </div>

            <div class="form-row">
                <label for="group-weighted-cars">Group Weighted Cars:</label>
                <select id="group-weighted-cars" name="group-weighted-cars">
                    <option value="0">Zero</option>
                    <option value="50">Low (50)</option>
                    <option value="300">Medium (300)</option>
                    <option value="1000">Heavy (1000)</option>
                    <option value="100" selected>Custom (100)</option>
                </select>
                <small>Weight for keeping racers from same group together</small>
            </div>

            <div class="form-row">
                <label for="avoid-consecutive">Avoid Consecutive:</label>
                <select id="avoid-consecutive" name="avoid-consecutive">
                    <option value="0">Zero</option>
                    <option value="50">Low (50)</option>
                    <option value="300">Medium (300)</option>
                    <option value="5000" selected>Heavy (5000)</option>
                </select>
                <small>Weight for preventing racers from racing in back-to-back heats</small>
            </div>

            <div class="form-row">
                <label for="avoid-same-lane">Avoid Same Lane:</label>
                <select id="avoid-same-lane" name="avoid-same-lane">
                    <option value="0">Zero</option>
                    <option value="50">Low (50)</option>
                    <option value="300">Medium (300)</option>
                    <option value="1000">Heavy (1000)</option>
                    <option value="200" selected>Custom (200)</option>
                </select>
                <small>Weight for distributing racers across different lanes</small>
            </div>

            <div class="form-row">
                <label for="dnf-time">DNF Time (seconds):</label>
                <input type="number" id="dnf-time" value="99.000" step="0.001" min="0" />
                <small>Time assigned to racers who do not finish (DNF)</small>
            </div>

            <div class="form-row">
                <label for="auto-advancement">
                    <input type="checkbox" id="auto-advancement" checked />
                    Auto Advancement
                </label>
                <small>Automatically advance racers to next round when current round completes</small>
            </div>

            <div class="form-row">
                <label for="bracket-seeding">Bracket Seeding:</label>
                <select id="bracket-seeding">
                    <option value="time_based" selected>Time Based</option>
                    <option value="random">Random</option>
                </select>
                <small>Method for seeding racers into elimination brackets</small>
            </div>
        </div>
    </div>

    <!-- Save/Cancel Actions -->
    <div class="editor-footer">
        <button id="save-config-btn" class="primary-btn">Save Configuration</button>
        <button id="cancel-btn" class="secondary-btn"
                onclick="window.location.href='racing-groups.php'">Cancel</button>
    </div>

</div>

</body>
</html>
