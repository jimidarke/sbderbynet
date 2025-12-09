// Elimination Tournament Management JavaScript  
// Tournament initialization is handled via the Tournament Setup section on racing-groups.php

var elimination_configs = [];

// Initialize elimination tournament functionality
function initialize_elimination_ui() {
    // Load available configurations
    load_elimination_configs();
}

// Load available elimination configurations
function load_elimination_configs() {
    $.ajax('action.php', {
        type: 'GET',
        data: {
            query: 'elimination.config.list'
        },
        success: function(data) {
            if (data.outcome && data.outcome.summary === 'success') {
                elimination_configs = data.configs;
                // Initialize tournament setup section if on racing-groups page
                init_tournament_setup_section();
            } else {
                console.error('Failed to load elimination configs:', data);
            }
        },
        error: function(xhr, status, error) {
            console.error('Error loading elimination configs:', error);
        }
    });
}

// ============================================================================
// Tournament Setup Section (racing-groups.php main page)
// ============================================================================

var tournament_setup_config = null;  // Currently selected config details
var tournament_setup_classes = [];   // List of classes with tournament status

// Initialize the tournament setup section
function init_tournament_setup_section() {
    var $configSelect = $('#global-tournament-config');
    if (!$configSelect.length) return;  // Not on racing-groups page

    // Populate config dropdown
    $configSelect.empty();
    $configSelect.append('<option value="">-- Select Format --</option>');

    elimination_configs.forEach(function(config) {
        $configSelect.append($('<option>', {
            value: config.file,
            text: config.name
        }));
    });

    // Handle config selection change
    $configSelect.off('change').on('change', function() {
        var configFile = $(this).val();
        if (configFile) {
            load_tournament_setup_config(configFile);
        } else {
            hide_tournament_class_assignments();
        }
    });
}

// Load config details and class assignments
function load_tournament_setup_config(configFile) {
    $.ajax('action.php', {
        type: 'GET',
        data: {
            query: 'elimination.config.detail',
            filename: configFile
        },
        success: function(data) {
            if (data.outcome && data.outcome.summary === 'success') {
                tournament_setup_config = data.config;
                show_tournament_config_details(data.config);
                load_classes_tournament_status(configFile);
            } else {
                console.error('Failed to load config:', data);
            }
        }
    });
}

// Show config details
function show_tournament_config_details(config) {
    var ageGroupCount = config.age_groups ? Object.keys(config.age_groups).length : 0;
    $('#config-description').text(config.description || 'No description');
    $('#config-age-groups-count').text(ageGroupCount);
    $('#tournament-config-details').removeClass('hidden');
}

// Load classes and their tournament status
function load_classes_tournament_status(configFile) {
    // First get the class list, then get tournament status
    $.ajax('action.php', {
        type: 'GET',
        data: { query: 'class.list' },
        success: function(classData) {
            if (!classData.classes) {
                console.error('No classes found');
                return;
            }

            // Now get tournament status for all classes
            $.ajax('action.php', {
                type: 'GET',
                data: { query: 'elimination.tournament.all-status' },
                success: function(statusData) {
                    var tournaments = (statusData.outcome && statusData.outcome.summary === 'success')
                        ? statusData.tournaments || {}
                        : {};

                    var classes = classData.classes.map(function(cls) {
                        var tournamentInfo = tournaments[cls.classid];
                        if (tournamentInfo) {
                            return {
                                classid: cls.classid,
                                name: cls.name,
                                count: cls.count,
                                tournament_active: true,
                                current_round: tournamentInfo.current_round,
                                total_rounds: tournamentInfo.total_rounds,
                                age_group_name: tournamentInfo.age_group_name
                            };
                        } else {
                            return {
                                classid: cls.classid,
                                name: cls.name,
                                count: cls.count,
                                tournament_active: false,
                                current_round: 0,
                                total_rounds: 0,
                                age_group_name: ''
                            };
                        }
                    });

                    tournament_setup_classes = classes;
                    render_class_tournament_table(classes, configFile);
                    show_tournament_class_assignments();
                },
                error: function() {
                    // If tournament status query fails, render with no status
                    var classes = classData.classes.map(function(cls) {
                        return {
                            classid: cls.classid,
                            name: cls.name,
                            count: cls.count,
                            tournament_active: false,
                            current_round: 0,
                            total_rounds: 0,
                            age_group_name: ''
                        };
                    });
                    tournament_setup_classes = classes;
                    render_class_tournament_table(classes, configFile);
                    show_tournament_class_assignments();
                }
            });
        },
        error: function(xhr, status, error) {
            console.error('Error loading classes:', error);
        }
    });
}

// Render the class-tournament assignment table
function render_class_tournament_table(classes, configFile) {
    var $tbody = $('#class-tournament-tbody');
    $tbody.empty();

    if (!classes || classes.length === 0) {
        $tbody.append('<tr><td colspan="4">No classes found</td></tr>');
        return;
    }

    var ageGroups = tournament_setup_config ? tournament_setup_config.age_groups : {};

    classes.forEach(function(cls) {
        var $row = $('<tr>').attr('data-classid', cls.classid);

        // Class name (with racer count)
        $row.append($('<td>').text(cls.name + ' (' + (cls.count || 0) + ')'));

        // Age group selector or locked display
        var $ageGroupCell = $('<td>');
        if (cls.tournament_active) {
            $ageGroupCell.text(cls.age_group_name || '-');
        } else {
            var $select = $('<select>')
                .addClass('age-group-select')
                .attr('data-classid', cls.classid);
            $select.append('<option value="">-- Select --</option>');

            // Try to find matching age group
            var suggestedKey = find_matching_age_group(cls.name, ageGroups);

            Object.keys(ageGroups).forEach(function(key) {
                var group = ageGroups[key];
                var roundCount = group.rounds ? group.rounds.length : 0;
                var label = group.name + ' (' + roundCount + 'r)';
                var $option = $('<option>', { value: key, text: label });
                if (key === suggestedKey) {
                    $option.prop('selected', true);
                }
                $select.append($option);
            });

            $ageGroupCell.append($select);
        }
        $row.append($ageGroupCell);

        // Status
        var $statusCell = $('<td>');
        if (cls.tournament_active) {
            $statusCell.addClass('status-active').text('Round ' + cls.current_round + '/' + cls.total_rounds);
        } else {
            $statusCell.addClass('status-pending').text('--');
        }
        $row.append($statusCell);

        // Action
        var $actionCell = $('<td>');
        if (cls.tournament_active) {
            $actionCell.append($('<span>').addClass('locked-label').text('Locked'));
        } else {
            var $btn = $('<button>')
                .addClass('init-btn')
                .text('Init')
                .attr('data-classid', cls.classid)
                .attr('data-classname', cls.name)
                .attr('data-config', configFile)
                .on('click', function() {
                    initialize_class_tournament($(this));
                });
            $actionCell.append($btn);
        }
        $row.append($actionCell);

        $tbody.append($row);
    });
}

// Find matching age group based on class name pattern
function find_matching_age_group(className, ageGroups) {
    for (var key in ageGroups) {
        var group = ageGroups[key];
        if (group.class_name_pattern) {
            try {
                var pattern = new RegExp(group.class_name_pattern, 'i');
                if (pattern.test(className)) {
                    return key;
                }
            } catch (e) {
                // Invalid pattern, skip
            }
        }
        // Also try exact name match
        if (group.name && group.name.toLowerCase() === className.toLowerCase()) {
            return key;
        }
    }
    return null;
}

// Initialize tournament for a specific class
function initialize_class_tournament($btn) {
    var classid = $btn.attr('data-classid');
    var className = $btn.attr('data-classname');
    var configFile = $btn.attr('data-config');
    var $row = $btn.closest('tr');
    var ageGroupKey = $row.find('.age-group-select').val();

    if (!ageGroupKey) {
        alert('Please select an age group for "' + className + '"');
        return;
    }

    var ageGroupName = tournament_setup_config.age_groups[ageGroupKey].name;
    var roundCount = tournament_setup_config.age_groups[ageGroupKey].rounds.length;

    var confirmMsg = 'Initialize tournament for "' + className + '"?\n\n' +
        'Age Group: ' + ageGroupName + '\n' +
        'Rounds: ' + roundCount + '\n\n' +
        'WARNING: This cannot be undone. Tournament rounds will be created immediately.';

    if (!confirm(confirmMsg)) {
        return;
    }

    $btn.prop('disabled', true).text('Initializing...');

    $.ajax('action.php', {
        type: 'POST',
        data: {
            action: 'elimination.tournament.initialize',
            classid: classid,
            config_file: configFile,
            age_group_key: ageGroupKey
        },
        success: function(data) {
            if (data.outcome && data.outcome.summary === 'success') {
                alert('Tournament initialized successfully for "' + className + '"!\n\nRounds and schedule structure created.');
                // Update the row directly to show initialized state
                update_row_after_init($row, ageGroupName, roundCount);
            } else {
                alert('Failed to initialize tournament: ' + (data.outcome ? data.outcome.description : 'Unknown error'));
                $btn.prop('disabled', false).text('Init');
            }
        },
        error: function(xhr, status, error) {
            alert('Error initializing tournament: ' + error);
            $btn.prop('disabled', false).text('Init');
        }
    });
}

// Update row after successful initialization
function update_row_after_init($row, ageGroupName, roundCount) {
    // Update age group cell - replace select with text
    var $ageGroupCell = $row.find('td').eq(1);
    $ageGroupCell.empty().text(ageGroupName);

    // Update status cell
    var $statusCell = $row.find('td').eq(2);
    $statusCell.removeClass('status-pending').addClass('status-active')
        .text('Round 1/' + roundCount);

    // Update action cell - replace button with locked label
    var $actionCell = $row.find('td').eq(3);
    $actionCell.empty().append($('<span>').addClass('locked-label').text('Locked'));
}

// Show/hide tournament class assignments section
function show_tournament_class_assignments() {
    $('#tournament-class-assignments').removeClass('hidden');
    $('#no-config-message').addClass('hidden');
}

function hide_tournament_class_assignments() {
    $('#tournament-class-assignments').addClass('hidden');
    $('#tournament-config-details').addClass('hidden');
    $('#no-config-message').removeClass('hidden');
}

// Initialize when document is ready
$(document).ready(function() {
    initialize_elimination_ui();
});