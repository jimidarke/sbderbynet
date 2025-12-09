// Elimination Tournament Management JavaScript

var current_class_id = null;
var elimination_configs = [];
var current_age_groups = [];
var suggested_age_group_key = null;

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
                populate_config_selector();
            } else {
                console.error('Failed to load elimination configs:', data);
            }
        },
        error: function(xhr, status, error) {
            console.error('Error loading elimination configs:', error);
        }
    });
}

// Populate the configuration selector dropdown
function populate_config_selector() {
    var select = $('#elimination_config_select');
    select.empty();
    select.append('<option value="">Select configuration...</option>');

    elimination_configs.forEach(function(config) {
        select.append($('<option>', {
            value: config.file,
            text: config.name + ' (v' + config.version + ')'
        }));
    });

    // Setup change handler to load age groups when config selected
    select.off('change').on('change', function() {
        var config_file = $(this).val();
        if (config_file && current_class_id) {
            load_age_groups_for_config(config_file, current_class_id);
        } else {
            hide_age_group_selector();
        }
    });
}

// Show elimination tournament section for a class
function show_elimination_tournament_for_class(classid) {
    current_class_id = classid;
    
    // Load tournament status for this class
    load_tournament_status(classid);
    
    // Show the elimination tournament section
    $('#elimination_tournament_extension').removeClass('hidden');
}

// Load tournament status for a class
function load_tournament_status(classid) {
    $.ajax('action.php', {
        type: 'GET',
        data: {
            query: 'elimination.tournament.status',
            classid: classid
        },
        success: function(data) {
            if (data.outcome && data.outcome.summary === 'success') {
                if (data.active) {
                    show_active_tournament(data.tournament);
                } else {
                    show_no_tournament();
                }
            } else {
                console.error('Failed to load tournament status:', data);
                $('#elimination_status_text').text('Error loading tournament status');
            }
        },
        error: function(xhr, status, error) {
            console.error('Error loading tournament status:', error);
            $('#elimination_status_text').text('Error loading tournament status');
        }
    });
}

// Show active tournament information
function show_active_tournament(tournament) {
    $('#elimination_status_text').text('Active tournament: ' + tournament.format_name);
    
    // Populate tournament info
    $('#tournament_format_name').text(tournament.format_name);
    $('#tournament_age_group').text(tournament.age_group_name);
    $('#tournament_current_round').text(tournament.current_round);
    $('#tournament_total_rounds').text(tournament.total_rounds);
    $('#tournament_round_name').text(tournament.current_round_name);
    $('#tournament_advancement_info').text(tournament.advancement_info);
    
    // Show tournament info, hide config selector
    $('#elimination_config_selector').addClass('hidden');
    $('#elimination_tournament_info').removeClass('hidden');
    
    // Enable/disable advance button based on round
    if (tournament.current_round >= tournament.total_rounds) {
        $('#advance_tournament_button').prop('disabled', true).val('Tournament Complete');
    } else {
        $('#advance_tournament_button').prop('disabled', false).val('Advance to Next Round');
    }
}

// Show no tournament state
function show_no_tournament() {
    $('#elimination_status_text').text('No active tournament');
    
    // Show config selector, hide tournament info
    $('#elimination_config_selector').removeClass('hidden');
    $('#elimination_tournament_info').addClass('hidden');
}

// Load age groups for selected configuration
function load_age_groups_for_config(config_file, classid) {
    $.ajax('action.php', {
        type: 'GET',
        data: {
            query: 'elimination.config.age-groups',
            config_file: config_file,
            classid: classid
        },
        success: function(data) {
            if (data.outcome && data.outcome.summary === 'success') {
                current_age_groups = data.age_groups;
                suggested_age_group_key = data.suggested_key;
                populate_age_group_selector(data);
                show_age_group_selector();
            } else {
                console.error('Failed to load age groups:', data);
                hide_age_group_selector();
            }
        },
        error: function(xhr, status, error) {
            console.error('Error loading age groups:', error);
            hide_age_group_selector();
        }
    });
}

// Populate the age group selector dropdown
function populate_age_group_selector(data) {
    var select = $('#elimination_age_group_select');
    select.empty();
    select.append('<option value="">Select age group for this class...</option>');

    data.age_groups.forEach(function(group) {
        var label = group.name + ' (' + group.rounds_count + ' rounds';
        if (group.expected_racers > 0) {
            label += ', ~' + group.expected_racers + ' racers';
        }
        label += ')';

        var option = $('<option>', {
            value: group.key,
            text: label
        });

        // Mark suggested option
        if (group.pattern_match && group.key === data.suggested_key) {
            option.text(label + ' ⭐ Suggested');
            option.attr('selected', 'selected');
        }

        select.append(option);
    });

    // Show info about pattern matching
    if (data.suggested_key) {
        $('#age_group_match_info').html(
            '<small style="color: green;">✓ Auto-detected "' +
            data.age_groups.find(g => g.key === data.suggested_key).name +
            '" based on class name pattern</small>'
        ).show();
    } else {
        $('#age_group_match_info').html(
            '<small style="color: orange;">⚠ No pattern match found for class "' +
            data.class_name + '". Please select manually.</small>'
        ).show();
    }
}

// Show age group selector
function show_age_group_selector() {
    $('#elimination_age_group_selector').removeClass('hidden');
}

// Hide age group selector
function hide_age_group_selector() {
    $('#elimination_age_group_selector').addClass('hidden');
    $('#age_group_match_info').hide();
}

// Initialize elimination tournament
function initialize_elimination_tournament() {
    var config_file = $('#elimination_config_select').val();
    var age_group_key = $('#elimination_age_group_select').val();

    if (!config_file) {
        alert('Please select a tournament configuration');
        return;
    }

    if (!age_group_key) {
        alert('Please select an age group for this class');
        return;
    }

    if (!current_class_id) {
        alert('No class selected');
        return;
    }

    // Confirm initialization
    var age_group_name = $('#elimination_age_group_select option:selected').text();
    if (!confirm('Initialize elimination tournament for this class?\n\nAge Group: ' + age_group_name + '\n\nThis will create tournament rounds and cannot be easily undone.')) {
        return;
    }

    $.ajax('action.php', {
        type: 'POST',
        data: {
            action: 'elimination.tournament.initialize',
            classid: current_class_id,
            config_file: config_file,
            age_group_key: age_group_key
        },
        success: function(data) {
            if (data.outcome && data.outcome.summary === 'success') {
                alert('Tournament initialized successfully!');
                load_tournament_status(current_class_id);
                hide_age_group_selector();
                // Refresh the racing groups display
                if (typeof update_group_displays === 'function') {
                    update_group_displays();
                }
            } else {
                alert('Failed to initialize tournament: ' + (data.outcome ? data.outcome.description : 'Unknown error'));
            }
        },
        error: function(xhr, status, error) {
            alert('Error initializing tournament: ' + error);
        }
    });
}

// Advance elimination tournament
function advance_elimination_tournament() {
    if (!current_class_id) {
        alert('No class selected');
        return;
    }
    
    // Confirm advancement
    if (!confirm('Advance tournament to the next round? This will process advancement based on current race results.')) {
        return;
    }
    
    $.ajax('action.php', {
        type: 'POST',
        data: {
            action: 'elimination.tournament.advance',
            classid: current_class_id
        },
        success: function(data) {
            if (data.outcome && data.outcome.summary === 'success') {
                alert('Tournament advanced to round ' + data.new_round + '!');
                load_tournament_status(current_class_id);
                // Refresh the racing groups display
                if (typeof update_group_displays === 'function') {
                    update_group_displays();
                }
            } else {
                alert('Failed to advance tournament: ' + (data.outcome ? data.outcome.description : 'Unknown error'));
            }
        },
        error: function(xhr, status, error) {
            alert('Error advancing tournament: ' + error);
        }
    });
}

// Hide elimination tournament section
function hide_elimination_tournament() {
    $('#elimination_tournament_extension').addClass('hidden');
    current_class_id = null;
}

// Hook into existing class editing functionality
function original_on_edit_class(event) {
    var list_item = $(event.target).closest("li");
    var classid = list_item.attr('data-classid');
    
    // Show elimination tournament section if this is a regular class (not aggregate)
    if (!list_item.hasClass('aggregate') && classid && classid !== '-1') {
        show_elimination_tournament_for_class(classid);
    } else {
        hide_elimination_tournament();
    }
}

// Initialize when document is ready
$(document).ready(function() {
    initialize_elimination_ui();
    
    // Hook into the class editing functionality
    // We need to override or extend the existing on_edit_class function
    if (typeof window.on_edit_class === 'function') {
        // Store the original function
        window.original_on_edit_class_impl = window.on_edit_class;
        
        // Override with our enhanced version
        window.on_edit_class = function(event) {
            // Call the original function first
            window.original_on_edit_class_impl(event);
            
            // Then add our elimination tournament functionality
            original_on_edit_class(event);
        };
    }
});