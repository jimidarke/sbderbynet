// Elimination Configuration Editor
// Manages the complete lifecycle of editing JSON configuration files

var EliminationConfigEditor = (function() {
    var currentConfig = null;
    var currentFilename = null;
    var isLocked = false;
    var isDirty = false;
    var originalSchedulingRules = null;  // Preserve original scheduling_rules for round-trip

    return {
        init: function() {
            this.loadConfigList();
            this.setupEventHandlers();
            this.checkDirectoryWritable();
        },

        checkDirectoryWritable: function() {
            // Check if config directory is writable (optional enhancement)
            // Could add AJAX call to check permissions
        },

        loadConfigList: function() {
            $.ajax({
                url: 'action.php',
                data: { query: 'elimination.config.list' },
                success: function(data) {
                    if (data.outcome && data.outcome.summary === 'success') {
                        populateConfigSelector(data.configs || []);
                    } else {
                        console.error('Failed to load config list:', data);
                    }
                },
                error: function(xhr, status, error) {
                    console.error('Error loading config list:', error);
                    alert('Failed to load configuration list. Check console for details.');
                }
            });
        },

        loadConfig: function(filename) {
            if (!filename) {
                this.createNew();
                return;
            }

            $.ajax({
                url: 'action.php',
                data: {
                    query: 'elimination.config.detail',
                    filename: filename
                },
                success: function(data) {
                    if (data.outcome && data.outcome.summary === 'success') {
                        currentConfig = data.config;
                        currentFilename = data.filename;
                        isLocked = data.locked || false;
                        renderConfigForm(data.config);
                        updateLockStatus(data.locked, data.active_classes || []);
                        isDirty = false;
                    } else {
                        alert('Failed to load configuration: ' + (data.outcome ? data.outcome.description : 'Unknown error'));
                    }
                },
                error: function(xhr, status, error) {
                    alert('Error loading configuration: ' + error);
                }
            });
        },

        saveConfig: function() {
            if (isLocked) {
                alert('Cannot save: tournament is active for this configuration');
                return;
            }

            if (!validateConfig()) {
                return;  // Validation errors already displayed
            }

            var configData = serializeFormToConfig();
            var operation = currentFilename ? 'update' : 'create';

            $.ajax({
                url: 'action.php',
                type: 'POST',
                data: {
                    action: 'elimination.config.save',
                    operation: operation,
                    filename: currentFilename,
                    config_json: JSON.stringify(configData)
                },
                success: function(data) {
                    if (data.outcome && data.outcome.summary === 'success') {
                        isDirty = false;
                        currentFilename = data.filename;
                        showSuccessMessage('Configuration saved successfully');
                        EliminationConfigEditor.loadConfigList();
                        // Reload config to ensure we have server version
                        EliminationConfigEditor.loadConfig(data.filename);
                    } else {
                        alert('Save failed: ' + (data.outcome ? data.outcome.description : 'Unknown error'));
                    }
                },
                error: function(xhr, status, error) {
                    alert('Error saving configuration: ' + error);
                }
            });
        },

        createNew: function() {
            if (isDirty && !confirm('Discard unsaved changes?')) {
                return;
            }

            currentConfig = getDefaultConfig();
            currentFilename = null;
            isLocked = false;
            isDirty = false;
            renderConfigForm(currentConfig);
            updateLockStatus(false, []);
            $('#config-selector').val('');
        },

        cloneConfig: function() {
            if (!currentFilename) {
                alert('Please load a configuration first');
                return;
            }

            var newName = prompt('Enter name for cloned configuration:', currentConfig.format_name + ' (Copy)');
            if (!newName) return;

            $.ajax({
                url: 'action.php',
                type: 'POST',
                data: {
                    action: 'elimination.config.clone',
                    source_filename: currentFilename,
                    new_name: newName
                },
                success: function(data) {
                    if (data.outcome && data.outcome.summary === 'success') {
                        showSuccessMessage('Configuration cloned successfully');
                        EliminationConfigEditor.loadConfigList();
                        // Load the new cloned config
                        if (data.filename) {
                            EliminationConfigEditor.loadConfig(data.filename);
                        }
                    } else {
                        alert('Clone failed: ' + (data.outcome ? data.outcome.description : 'Unknown error'));
                    }
                },
                error: function(xhr, status, error) {
                    alert('Error cloning configuration: ' + error);
                }
            });
        },

        deleteConfig: function() {
            if (!currentFilename) {
                alert('No configuration loaded');
                return;
            }

            if (!confirm('Delete configuration "' + currentFilename + '"?\n\nThis action will create a backup but cannot be easily undone.')) {
                return;
            }

            $.ajax({
                url: 'action.php',
                type: 'POST',
                data: {
                    action: 'elimination.config.delete',
                    filename: currentFilename
                },
                success: function(data) {
                    if (data.outcome && data.outcome.summary === 'success') {
                        showSuccessMessage('Configuration deleted');
                        EliminationConfigEditor.createNew();
                        EliminationConfigEditor.loadConfigList();
                    } else {
                        alert('Delete failed: ' + (data.outcome ? data.outcome.description : 'Unknown error'));
                    }
                },
                error: function(xhr, status, error) {
                    alert('Error deleting configuration: ' + error);
                }
            });
        },

        setupEventHandlers: function() {
            $('#config-selector').on('change', function() {
                var filename = $(this).val();
                EliminationConfigEditor.loadConfig(filename);
            });

            $('#save-config-btn').on('click', function() {
                EliminationConfigEditor.saveConfig();
            });

            $('#new-config-btn').on('click', function() {
                EliminationConfigEditor.createNew();
            });

            $('#clone-config-btn').on('click', function() {
                EliminationConfigEditor.cloneConfig();
            });

            $('#delete-config-btn').on('click', function() {
                EliminationConfigEditor.deleteConfig();
            });

            $('#add-age-group-btn').on('click', function() {
                addAgeGroup();
            });

            // Track changes for dirty flag
            $('#config-form').on('change input', 'input, select, textarea', function() {
                isDirty = true;
            });

            // Warn on navigation with unsaved changes
            window.addEventListener('beforeunload', function(e) {
                if (isDirty) {
                    e.preventDefault();
                    e.returnValue = '';
                }
            });
        },

        addAgeGroup: function() {
            addAgeGroup();
        }
    };
})();

// Helper functions

function populateConfigSelector(configs) {
    var $select = $('#config-selector');
    $select.empty();
    $select.append('<option value="">Create New Configuration...</option>');

    configs.forEach(function(config) {
        $select.append('<option value="' + config.file + '">' + config.name + '</option>');
    });
}

function renderConfigForm(config) {
    // Store original scheduling rules to preserve fields not in UI
    originalSchedulingRules = config.scheduling_rules ? JSON.parse(JSON.stringify(config.scheduling_rules)) : null;

    // Render metadata
    $('#format-name').val(config.format_name || '');
    $('#description').val(config.description || '');
    $('#version').val(config.version || '1.0');

    // Render age groups
    $('#age-groups-container').empty();
    if (config.age_groups) {
        Object.keys(config.age_groups).forEach(function(groupKey) {
            var group = config.age_groups[groupKey];
            renderAgeGroup(groupKey, group);
        });
    }

    // Render scheduling rules
    if (config.scheduling_rules) {
        renderSchedulingRules(config.scheduling_rules);
    }

    // Update disabled states based on lock status
    updateFormLockState();
}

function renderAgeGroup(groupKey, groupData) {
    var html = `
        <div class="age-group-panel" data-group-key="${escapeHtml(groupKey)}">
            <div class="age-group-header">
                <h3>
                    <span class="age-group-name">${escapeHtml(groupData.name)}</span>
                    <button class="remove-age-group-btn" type="button">Remove</button>
                </h3>
            </div>
            <div class="age-group-body">
                <div class="form-row">
                    <label>Age Group Key:</label>
                    <input type="text" class="group-key" value="${escapeHtml(groupKey)}" />
                    <small>Lowercase letters, numbers, and underscores only</small>
                </div>
                <div class="form-row">
                    <label>Display Name:</label>
                    <input type="text" class="group-name" value="${escapeHtml(groupData.name)}" />
                </div>
                <div class="form-row">
                    <label>Class Name Pattern (regex):</label>
                    <input type="text" class="class-pattern" value="${escapeHtml(groupData.class_name_pattern)}" />
                    <small>Matches class names like: ${escapeHtml(groupData.name)}</small>
                </div>
                <div class="form-row">
                    <label>Expected Racers:</label>
                    <input type="number" class="expected-racers" value="${groupData.expected_racers || 0}" min="0" />
                </div>
                <div class="form-row">
                    <label>Lanes:</label>
                    <input type="number" class="lanes" value="${groupData.lanes || 3}" min="1" max="20" />
                </div>

                <h4>Rounds</h4>
                <div class="rounds-list"></div>
                <button class="add-round-btn" type="button">Add Round</button>
            </div>
        </div>
    `;

    var $panel = $(html);
    $('#age-groups-container').append($panel);

    // Setup event handlers
    $panel.find('.remove-age-group-btn').on('click', function() {
        removeAgeGroup($panel);
    });

    $panel.find('.add-round-btn').on('click', function() {
        addRound(groupKey);
    });

    // Render rounds for this age group
    if (groupData.rounds && groupData.rounds.length > 0) {
        groupData.rounds.forEach(function(round) {
            renderRound(groupKey, round);
        });
    }

    // Make rounds sortable
    initSortableRounds($panel.find('.rounds-list'));
}

function renderRound(ageGroupKey, roundData) {
    var html = `
        <div class="round-panel" data-sequence="${roundData.round_sequence}">
            <div class="round-header">
                <span class="round-drag-handle">☰</span>
                <span class="round-title">
                    Round ${roundData.round_sequence}: ${escapeHtml(roundData.round_name)}
                </span>
                <button class="remove-round-btn" type="button">×</button>
            </div>
            <div class="round-body">
                <div class="form-row">
                    <label>Round Name:</label>
                    <input type="text" class="round-name" value="${escapeHtml(roundData.round_name)}"
                           placeholder="1 Preliminary" />
                    <small>Must start with a number for proper sequencing</small>
                </div>
                <div class="form-row">
                    <label>Races Per Racer:</label>
                    <select class="races-per-racer">
                        ${[1,2,3,4,5,6].map(n =>
                            `<option value="${n}" ${roundData.races_per_racer == n ? 'selected' : ''}>${n}</option>`
                        ).join('')}
                    </select>
                </div>
                <div class="form-row">
                    <label>Advancement Rule:</label>
                    <select class="advancement-rule">
                        <option value="top_count" ${roundData.advancement_rule === 'top_count' ? 'selected' : ''}>
                            Top Count
                        </option>
                        <option value="percentage" ${roundData.advancement_rule === 'percentage' ? 'selected' : ''}>
                            Percentage
                        </option>
                        <option value="placement" ${roundData.advancement_rule === 'placement' ? 'selected' : ''}>
                            Placement (Final Round)
                        </option>
                    </select>
                </div>
                <div class="form-row advance-count-row"
                     style="${roundData.advancement_rule === 'placement' || roundData.advancement_rule === 'percentage' ? 'display:none' : ''}">
                    <label>Advance Count:</label>
                    <input type="number" class="advance-count" value="${roundData.advance_count || 0}" min="0" />
                </div>
                <div class="form-row advance-percentage-row"
                     style="${roundData.advancement_rule === 'percentage' ? '' : 'display:none'}">
                    <label>Advance Percentage:</label>
                    <input type="number" class="advance-percentage" value="${roundData.advance_percentage || 0}" min="0" max="100" />
                    <small>Percentage of racers to advance to next round</small>
                </div>
                <div class="form-row">
                    <label>Scoring Method:</label>
                    <select class="scoring-method">
                        <option value="total_time" ${roundData.scoring_method === 'total_time' ? 'selected' : ''}>
                            Total Time
                        </option>
                        <option value="best_time" ${roundData.scoring_method === 'best_time' ? 'selected' : ''}>
                            Best Time
                        </option>
                        <option value="average_time" ${roundData.scoring_method === 'average_time' ? 'selected' : ''}>
                            Average Time
                        </option>
                        <option value="placement" ${roundData.scoring_method === 'placement' ? 'selected' : ''}>
                            Placement
                        </option>
                    </select>
                </div>
                <div class="form-row">
                    <label>Description:</label>
                    <textarea class="round-description" rows="2">${escapeHtml(roundData.description || '')}</textarea>
                </div>
            </div>
        </div>
    `;

    var $panel = $(html);
    $(`[data-group-key="${ageGroupKey}"] .rounds-list`).append($panel);

    // Setup event handlers
    $panel.find('.remove-round-btn').on('click', function() {
        removeRound($panel);
    });

    $panel.find('.advancement-rule').on('change', function() {
        var rule = $(this).val();
        var $countRow = $panel.find('.advance-count-row');
        var $percentRow = $panel.find('.advance-percentage-row');

        if (rule === 'placement') {
            $countRow.hide();
            $percentRow.hide();
        } else if (rule === 'percentage') {
            $countRow.hide();
            $percentRow.show();
        } else {  // top_count
            $countRow.show();
            $percentRow.hide();
        }
    });
}

function renderSchedulingRules(rules) {
    var heatOrdering = rules.heat_ordering || {};

    $('#heat-counts').val(heatOrdering.heat_counts || 10);
    $('#group-weighted-cars').val(heatOrdering.group_weighted_cars || 100);
    $('#avoid-consecutive').val(heatOrdering.avoid_consecutive || 5000);
    $('#avoid-same-lane').val(heatOrdering.avoid_same_lane || 200);
    $('#dnf-time').val(rules.dnf_time || 99.000);
    $('#auto-advancement').prop('checked', rules.auto_advancement !== false);
    $('#bracket-seeding').val(rules.bracket_seeding || 'time_based');
}

function serializeFormToConfig() {
    var config = {
        format_name: $('#format-name').val(),
        description: $('#description').val(),
        version: $('#version').val(),
        age_groups: {},
        scheduling_rules: serializeSchedulingRules()
    };

    $('.age-group-panel').each(function() {
        var $panel = $(this);
        var groupKey = $panel.find('.group-key').val();

        var rounds = [];
        $panel.find('.round-panel').each(function(index) {
            var $round = $(this);
            var roundData = {
                round_sequence: index + 1,
                round_name: $round.find('.round-name').val(),
                races_per_racer: parseInt($round.find('.races-per-racer').val()),
                advancement_rule: $round.find('.advancement-rule').val(),
                scoring_method: $round.find('.scoring-method').val(),
                description: $round.find('.round-description').val()
            };

            // Add advance_count or advance_percentage based on advancement_rule
            if (roundData.advancement_rule === 'top_count') {
                roundData.advance_count = parseInt($round.find('.advance-count').val()) || 0;
            } else if (roundData.advancement_rule === 'percentage') {
                roundData.advance_percentage = parseInt($round.find('.advance-percentage').val()) || 0;
            } else if (roundData.advancement_rule === 'placement') {
                roundData.advance_count = 0;  // Finals always have 0
            }

            rounds.push(roundData);
        });

        config.age_groups[groupKey] = {
            name: $panel.find('.group-name').val(),
            class_name_pattern: $panel.find('.class-pattern').val(),
            expected_racers: parseInt($panel.find('.expected-racers').val()) || 0,
            lanes: parseInt($panel.find('.lanes').val()) || 3,
            rounds: rounds
        };
    });

    return config;
}

function serializeSchedulingRules() {
    // Start with original scheduling rules to preserve fields not in UI
    var rules = originalSchedulingRules ? JSON.parse(JSON.stringify(originalSchedulingRules)) : {};

    // Update fields from UI
    rules.heat_ordering = {
        heat_counts: parseInt($('#heat-counts').val()) || 10,
        group_weighted_cars: parseInt($('#group-weighted-cars').val()) || 100,
        avoid_consecutive: parseInt($('#avoid-consecutive').val()) || 5000,
        avoid_same_lane: parseInt($('#avoid-same-lane').val()) || 200
    };
    rules.dnf_time = parseFloat($('#dnf-time').val()) || 99.000;
    rules.auto_advancement = $('#auto-advancement').prop('checked');
    rules.bracket_seeding = $('#bracket-seeding').val() || 'time_based';

    return rules;
}

function validateConfig() {
    var errors = [];

    // Validate format name
    if (!$('#format-name').val().trim()) {
        errors.push('Format name is required');
    }

    // Validate age groups
    if ($('.age-group-panel').length === 0) {
        errors.push('At least one age group is required');
    }

    $('.age-group-panel').each(function() {
        var $panel = $(this);
        var groupKey = $panel.find('.group-key').val();

        if (!groupKey.match(/^[a-z0-9_]+$/)) {
            errors.push('Age group key "' + groupKey + '" must contain only lowercase letters, numbers, and underscores');
        }

        // Validate rounds
        var rounds = $panel.find('.round-panel');
        if (rounds.length === 0) {
            errors.push('Age group "' + groupKey + '" must have at least one round');
        }

        rounds.each(function() {
            var roundName = $(this).find('.round-name').val();
            if (!roundName.match(/^\d+/)) {
                errors.push('Round name "' + roundName + '" must start with a number');
            }
        });
    });

    if (errors.length > 0) {
        alert('Validation errors:\n\n' + errors.join('\n'));
        return false;
    }

    return true;
}

function addAgeGroup() {
    var groupKey = 'age_group_' + Date.now();
    var groupData = {
        name: 'New Age Group',
        class_name_pattern: '^(New Group).*$',
        expected_racers: 0,
        lanes: 3,
        rounds: []
    };
    renderAgeGroup(groupKey, groupData);
    // Add a default round
    addRound(groupKey);
}

function addRound(ageGroupKey) {
    var $container = $(`[data-group-key="${ageGroupKey}"] .rounds-list`);
    var roundNum = $container.children().length + 1;
    var roundData = {
        round_sequence: roundNum,
        round_name: roundNum + ' Round ' + roundNum,
        races_per_racer: 1,
        advancement_rule: 'top_count',
        advance_count: 0,
        advance_percentage: 0,
        scoring_method: 'total_time',
        description: ''
    };
    renderRound(ageGroupKey, roundData);

    // Reinit sortable after adding
    initSortableRounds($container);
}

function removeRound($roundElement) {
    if (confirm('Remove this round?')) {
        var $container = $roundElement.closest('.rounds-list');
        $roundElement.remove();
        renumberRounds($container);
    }
}

function removeAgeGroup($ageGroupElement) {
    if (confirm('Remove this age group and all its rounds?')) {
        $ageGroupElement.remove();
    }
}

function renumberRounds($container) {
    $container.find('.round-panel').each(function(index) {
        $(this).attr('data-sequence', index + 1);
        var roundName = $(this).find('.round-name').val();
        // Update the title display
        $(this).find('.round-title').text('Round ' + (index + 1) + ': ' + roundName);
    });
}

function initSortableRounds($container) {
    if (isLocked) return;

    if ($container.hasClass('ui-sortable')) {
        $container.sortable('destroy');
    }

    $container.sortable({
        handle: '.round-drag-handle',
        update: function(event, ui) {
            renumberRounds($(this));
        }
    });
}

function updateLockStatus(locked, activeClasses) {
    isLocked = locked;

    if (locked) {
        $('#lock-warning').show();
        $('#active-classes-list').text(activeClasses.join(', '));
        $('#delete-config-btn').prop('disabled', true);
    } else {
        $('#lock-warning').hide();
        $('#delete-config-btn').prop('disabled', false);
    }

    updateFormLockState();
}

function updateFormLockState() {
    var disabled = isLocked;

    // Disable/enable form elements
    $('#format-name, #description, #version').prop('readonly', disabled);
    $('.group-key, .group-name, .class-pattern, .expected-racers, .lanes').prop('readonly', disabled);
    $('.round-name, .round-description, .advance-count').prop('readonly', disabled);
    $('.races-per-racer, .advancement-rule, .scoring-method').prop('disabled', disabled);
    $('.remove-age-group-btn, .remove-round-btn, .add-round-btn').prop('disabled', disabled);
    $('#add-age-group-btn, #save-config-btn').prop('disabled', disabled);
    $('#heat-counts, #group-weighted-cars, #avoid-consecutive, #avoid-same-lane').prop('disabled', disabled);
    $('#auto-advancement, #bracket-seeding, #dnf-time').prop('disabled', disabled);

    // Update drag handles
    if (disabled) {
        $('.round-drag-handle').addClass('disabled');
        $('.rounds-list').sortable('disable');
    } else {
        $('.round-drag-handle').removeClass('disabled');
        $('.rounds-list').sortable('enable');
    }
}

function getDefaultConfig() {
    // Reset original scheduling rules for new config
    originalSchedulingRules = null;

    return {
        format_name: 'New Elimination Configuration',
        description: '',
        version: '1.0',
        age_groups: {},
        scheduling_rules: {
            heat_ordering: {
                heat_counts: 10,
                group_weighted_cars: 100,
                avoid_consecutive: 5000,
                avoid_same_lane: 200
            },
            preliminary_requirements: {
                races_per_racer: 3,
                allow_partial_heats: true,
                minimum_racers_per_heat: 1,
                comment: "Each racer must get exactly 3 races in preliminary - partial heats with <3 racers are acceptable"
            },
            dnf_time: 99.000,
            auto_advancement: true,
            bracket_seeding: 'time_based'
        }
    };
}

function showSuccessMessage(message) {
    alert(message);  // Simple alert for now, could be enhanced with toast notification
}

function escapeHtml(text) {
    if (!text) return '';
    return text.toString()
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

// Initialize on document ready
$(function() {
    EliminationConfigEditor.init();
});
