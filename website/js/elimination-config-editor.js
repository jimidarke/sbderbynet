// Elimination Configuration Editor
// Manages the complete lifecycle of editing JSON configuration files  

var EliminationConfigEditor = (function() {
    var currentConfig = null;
    var currentFilename = null;
    var isLocked = false;
    var isDirty = false;
    var originalSchedulingRules = null;  // Preserve original scheduling_rules for round-trip
    var availableClasses = [];  // List of classes from database
    var labels = {  // Default labels, will be loaded from server
        partition: ['Age Group', 'Age Groups'],
        group: ['Group', 'Groups'],
        subgroup: ['Subgroup', 'Subgroups'],
        supergroup: ['Event', 'Events']
    };

    return {
        init: function() {
            var self = this;
            this.loadLabels();
            this.setupEventHandlers();
            this.checkDirectoryWritable();
            // Chain loadClasses -> loadConfigList to ensure classes are available for rendering
            this.loadClasses(function() {
                self.loadConfigList();
            });
        },

        loadLabels: function() {
            $.ajax({
                url: 'action.php',
                data: { query: 'poll', values: 'race-structure' },
                success: function(data) {
                    if (data.labels) {
                        labels = data.labels;
                        // Update any static label elements on the page
                        updatePageLabels();
                    }
                },
                error: function(xhr, status, error) {
                    console.error('Error loading labels:', error);
                }
            });
        },

        loadClasses: function(callback) {
            $.ajax({
                url: 'action.php',
                data: { query: 'class.list' },
                success: function(data) {
                    if (data.classes) {
                        availableClasses = data.classes;
                    }
                    if (typeof callback === 'function') {
                        callback();
                    }
                },
                error: function(xhr, status, error) {
                    console.error('Error loading classes:', error);
                    // Still call callback on error so UI isn't stuck
                    if (typeof callback === 'function') {
                        callback();
                    }
                }
            });
        },

        getAvailableClasses: function() {
            return availableClasses;
        },

        getLabels: function() {
            return labels;
        },

        // Get singular label for partition (e.g., "Age Group")
        getPartitionLabel: function() {
            return labels.partition ? labels.partition[0] : 'Age Group';
        },

        // Get plural label for partition (e.g., "Age Groups")
        getPartitionLabelPlural: function() {
            return labels.partition ? labels.partition[1] : 'Age Groups';
        },

        isLocked: function() {
            return isLocked;
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
    var classes = EliminationConfigEditor.getAvailableClasses();
    var partitionLabel = EliminationConfigEditor.getPartitionLabel();

    // Find matching class by: 1) classid, 2) class_name_pattern regex, 3) exact name match
    var matchedClassId = null;
    if (groupData.classid) {
        matchedClassId = groupData.classid;
    } else if (groupData.class_name_pattern) {
        try {
            var pattern = new RegExp(groupData.class_name_pattern, 'i');
            var match = classes.find(function(cls) { return pattern.test(cls.name); });
            if (match) matchedClassId = match.classid;
        } catch (e) {
            console.warn('Invalid class_name_pattern:', groupData.class_name_pattern);
        }
    }
    // Fallback: try exact name match
    if (!matchedClassId && groupData.name) {
        var nameMatch = classes.find(function(cls) {
            return cls.name.toLowerCase() === groupData.name.toLowerCase();
        });
        if (nameMatch) matchedClassId = nameMatch.classid;
    }

    var classOptions = classes.map(function(cls) {
        var selected = (matchedClassId == cls.classid) ? 'selected' : '';
        return '<option value="' + cls.classid + '" ' + selected + '>' +
               escapeHtml(cls.name) + ' (' + cls.count + ' racers)</option>';
    }).join('');

    var roundCount = groupData.rounds ? groupData.rounds.length : 0;
    var selectedClass = classes.find(function(cls) { return cls.classid == matchedClassId; });
    var racerCount = selectedClass ? selectedClass.count : 0;

    var html = `
        <div class="age-group-panel collapsed" data-group-key="${escapeHtml(groupKey)}">
            <div class="age-group-header">
                <h3>
                    <span class="age-group-name">${escapeHtml(groupData.name)}</span>
                    <span class="age-group-summary">(${roundCount} rounds, ${racerCount} racers)</span>
                    <button class="remove-age-group-btn" type="button">Remove</button>
                </h3>
            </div>
            <div class="age-group-body">
                <div class="form-row">
                    <label>Class:</label>
                    <select class="class-selector">
                        <option value="">-- Select a class --</option>
                        ${classOptions}
                    </select>
                </div>
                <div class="form-row">
                    <label>Lanes: <span class="help-icon" data-help="lanes">?</span></label>
                    <input type="number" class="lanes" value="${groupData.lanes || 3}" min="1" max="20" />
                </div>

                <h4>Rounds</h4>
                <div class="rounds-list"></div>
                <button class="add-round-btn" type="button">Add Round</button>
            </div>
        </div>
    `;
    // Hidden fields to store key and name (derived from class)
    // Group key is auto-generated from class name

    var $panel = $(html.trim());
    $('#age-groups-container').append($panel);

    // Setup event handlers
    $panel.find('.remove-age-group-btn').on('click', function(e) {
        e.stopPropagation();  // Prevent collapse toggle
        removeAgeGroup($panel);
    });

    $panel.find('.add-round-btn').on('click', function() {
        addRound(groupKey);
    });

    // Collapse/expand on header click
    $panel.find('.age-group-header').on('click', function(e) {
        // Don't toggle if clicking on the remove button
        if ($(e.target).closest('.remove-age-group-btn').length) return;
        $panel.toggleClass('collapsed');
    });

    // When class is selected, update header and summary
    $panel.find('.class-selector').on('change', function() {
        var selectedOption = $(this).find('option:selected');
        var className = selectedOption.text().replace(/ \(\d+ racers\)$/, '');
        var racerCount = selectedOption.text().match(/\((\d+) racers\)/);
        racerCount = racerCount ? racerCount[1] : '0';

        if (className && className !== '-- Select a class --') {
            $panel.find('.age-group-name').text(className);
            updateAgeGroupSummary($panel);
        }
        isDirty = true;
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
    // Strip leading number from round name for display in input
    var displayName = stripRoundNumber(roundData.round_name);
    var summaryText = buildRoundSummary(roundData);

    var html = `
        <div class="round-panel collapsed" data-sequence="${roundData.round_sequence}">
            <div class="round-header">
                <span class="round-drag-handle">☰</span>
                <span class="round-collapse-indicator">▼</span>
                <span class="round-title">
                    Round ${roundData.round_sequence}: ${escapeHtml(displayName)}
                </span>
                <span class="round-summary">${escapeHtml(summaryText)}</span>
                <button class="remove-round-btn" type="button">×</button>
            </div>
            <div class="round-body">
                <div class="form-row">
                    <label>Round Name:</label>
                    <input type="text" class="round-name" value="${escapeHtml(displayName)}"
                           placeholder="Preliminary" />
                    <small>Round number is prepended automatically</small>
                </div>
                <div class="form-row">
                    <label>Races Per Racer: <span class="help-icon" data-help="races-per-racer">?</span></label>
                    <select class="races-per-racer">
                        ${[1,2,3,4,5,6].map(n =>
                            `<option value="${n}" ${roundData.races_per_racer == n ? 'selected' : ''}>${n}</option>`
                        ).join('')}
                    </select>
                </div>
                <div class="form-row">
                    <label>Advancement Rule: <span class="help-icon" data-help="advancement-rule">?</span></label>
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
                    <label>Advance Count: <span class="help-icon" data-help="advance-count">?</span></label>
                    <input type="number" class="advance-count" value="${roundData.advance_count || 0}" min="0" />
                </div>
                <div class="form-row advance-percentage-row"
                     style="${roundData.advancement_rule === 'percentage' ? '' : 'display:none'}">
                    <label>Advance Percentage:</label>
                    <input type="number" class="advance-percentage" value="${roundData.advance_percentage || 0}" min="0" max="100" />
                    <small>Percentage of racers to advance to next round</small>
                </div>
                <div class="form-row">
                    <label>Scoring Method: <span class="help-icon" data-help="scoring-method">?</span></label>
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

    var $panel = $(html.trim());
    $(`[data-group-key="${ageGroupKey}"] .rounds-list`).append($panel);

    // Setup event handlers
    $panel.find('.remove-round-btn').on('click', function(e) {
        e.stopPropagation();
        removeRound($panel);
    });

    // Collapse/expand on header click
    $panel.find('.round-header').on('click', function(e) {
        // Don't toggle if clicking on drag handle or remove button
        if ($(e.target).closest('.round-drag-handle, .remove-round-btn').length) return;
        $panel.toggleClass('collapsed');
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
        updateRoundSummary($panel);
    });

    // Update summary when values change
    $panel.find('.races-per-racer, .advance-count, .advance-percentage, .scoring-method').on('change', function() {
        updateRoundSummary($panel);
    });

    // Update title when name changes
    $panel.find('.round-name').on('input', function() {
        var seq = $panel.attr('data-sequence');
        $panel.find('.round-title').text('Round ' + seq + ': ' + $(this).val());
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

    var usedKeys = {};  // Track keys to ensure uniqueness

    $('.age-group-panel').each(function() {
        var $panel = $(this);

        // Get class name for auto-generating key and name
        var $classSelector = $panel.find('.class-selector');
        var selectedOption = $classSelector.find('option:selected');
        var className = selectedOption.text().replace(/ \(\d+ racers\)$/, '');
        var classid = $classSelector.val();

        // Auto-generate key from class name, or use original key as fallback
        var originalKey = $panel.attr('data-group-key');
        var groupKey = className && className !== '-- Select a class --'
            ? slugify(className)
            : originalKey;

        // Ensure unique key by appending suffix if needed
        if (usedKeys[groupKey]) {
            var suffix = 2;
            while (usedKeys[groupKey + '_' + suffix]) suffix++;
            groupKey = groupKey + '_' + suffix;
        }
        usedKeys[groupKey] = true;

        var rounds = [];
        $panel.find('.round-panel').each(function(index) {
            var $round = $(this);
            var baseName = $round.find('.round-name').val();
            var sequence = index + 1;

            // Auto-prepend sequence number to round name
            var roundName = sequence + ' ' + baseName;

            var roundData = {
                round_sequence: sequence,
                round_name: roundName,
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

        // Use class name as display name
        var displayName = className && className !== '-- Select a class --'
            ? className
            : 'Unnamed Group';

        config.age_groups[groupKey] = {
            name: displayName,
            classid: classid ? parseInt(classid) : null,
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
    var partitionLabel = EliminationConfigEditor.getPartitionLabel();
    var partitionLabelLower = partitionLabel.toLowerCase();

    // Validate format name
    if (!$('#format-name').val().trim()) {
        errors.push('Format name is required');
    }

    // Validate age groups (partitions)
    if ($('.age-group-panel').length === 0) {
        errors.push('At least one ' + partitionLabelLower + ' is required');
    }

    $('.age-group-panel').each(function(index) {
        var $panel = $(this);
        var groupNum = index + 1;

        // Validate class selection (class name is used as display name and key)
        var classid = $panel.find('.class-selector').val();
        var selectedOption = $panel.find('.class-selector option:selected');
        var className = selectedOption.text().replace(/ \(\d+ racers\)$/, '');

        if (!classid || className === '-- Select a class --') {
            errors.push(partitionLabel + ' #' + groupNum + ' must have a class selected');
        }

        // Validate rounds
        var rounds = $panel.find('.round-panel');
        if (rounds.length === 0) {
            errors.push(partitionLabel + ' "' + (className || '#' + groupNum) + '" must have at least one round');
        }

        rounds.each(function() {
            var roundName = $(this).find('.round-name').val();
            if (!roundName || !roundName.trim()) {
                errors.push('All rounds must have a name');
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
    var partitionLabel = EliminationConfigEditor.getPartitionLabel();
    var groupKey = 'new_group_' + Date.now();
    var groupData = {
        name: 'New ' + partitionLabel,
        classid: null,
        lanes: 3,
        rounds: []
    };
    renderAgeGroup(groupKey, groupData);
    // Add a default round
    addRound(groupKey);

    // Expand the new group so user can edit it
    var $newPanel = $('[data-group-key="' + groupKey + '"]');
    $newPanel.removeClass('collapsed');
}

function addRound(ageGroupKey) {
    var $container = $(`[data-group-key="${ageGroupKey}"] .rounds-list`);
    var roundNum = $container.children().length + 1;

    // Suggest appropriate default name based on round number
    var defaultName = roundNum === 1 ? 'Preliminary' : 'Round ' + roundNum;

    var roundData = {
        round_sequence: roundNum,
        round_name: defaultName,  // No number prefix - auto-prepended on save
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

    // Expand the new round so user can edit it
    var $newRound = $container.find('.round-panel').last();
    $newRound.removeClass('collapsed');

    // Update age group summary
    updateAgeGroupSummary($container.closest('.age-group-panel'));
}

function removeRound($roundElement) {
    if (confirm('Remove this round?')) {
        var $container = $roundElement.closest('.rounds-list');
        var $ageGroupPanel = $container.closest('.age-group-panel');
        $roundElement.remove();
        renumberRounds($container);
        updateAgeGroupSummary($ageGroupPanel);
    }
}

function removeAgeGroup($ageGroupElement) {
    if (confirm('Remove this age group and all its rounds?')) {
        $ageGroupElement.remove();
    }
}

function renumberRounds($container) {
    $container.find('.round-panel').each(function(index) {
        var $panel = $(this);
        var seq = index + 1;
        $panel.attr('data-sequence', seq);
        var roundName = $panel.find('.round-name').val();
        // Update the title display
        $panel.find('.round-title').text('Round ' + seq + ': ' + roundName);
        // Update summary
        updateRoundSummary($panel);
    });
}

function initSortableRounds($container) {
    if (EliminationConfigEditor.isLocked()) return;

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
    $('.lanes').prop('readonly', disabled);
    $('.class-selector').prop('disabled', disabled);
    $('.round-name, .round-description, .advance-count, .advance-percentage').prop('readonly', disabled);
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

function updatePageLabels() {
    // Update the section header to use dynamic partition label (e.g., "Age Groups")
    var partitionLabelPlural = EliminationConfigEditor.getPartitionLabelPlural();
    $('#age-groups-section-header').text(partitionLabelPlural);
    $('#add-age-group-btn').text('Add ' + EliminationConfigEditor.getPartitionLabel());
}

// Helper: Strip leading number from round name (e.g., "1 Preliminary" -> "Preliminary")
function stripRoundNumber(name) {
    if (!name) return '';
    return name.replace(/^\d+\s*/, '');
}

// Helper: Build summary text for collapsed round view
function buildRoundSummary(roundData) {
    var races = roundData.races_per_racer || 1;
    var rule = roundData.advancement_rule || 'top_count';
    var parts = [races + ' race' + (races > 1 ? 's' : '')];

    if (rule === 'top_count' && roundData.advance_count) {
        parts.push('top ' + roundData.advance_count + ' advance');
    } else if (rule === 'percentage' && roundData.advance_percentage) {
        parts.push('top ' + roundData.advance_percentage + '% advance');
    } else if (rule === 'placement') {
        parts.push('final standings');
    }

    return parts.join(', ');
}

// Helper: Update round summary from current form values
function updateRoundSummary($panel) {
    var races = parseInt($panel.find('.races-per-racer').val()) || 1;
    var rule = $panel.find('.advancement-rule').val();
    var parts = [races + ' race' + (races > 1 ? 's' : '')];

    if (rule === 'top_count') {
        var count = parseInt($panel.find('.advance-count').val()) || 0;
        if (count > 0) parts.push('top ' + count + ' advance');
    } else if (rule === 'percentage') {
        var pct = parseInt($panel.find('.advance-percentage').val()) || 0;
        if (pct > 0) parts.push('top ' + pct + '% advance');
    } else if (rule === 'placement') {
        parts.push('final standings');
    }

    $panel.find('.round-summary').text(parts.join(', '));
}

// Helper: Update age group summary from current state
function updateAgeGroupSummary($panel) {
    var roundCount = $panel.find('.round-panel').length;
    var selectedOption = $panel.find('.class-selector option:selected');
    var racerMatch = selectedOption.text().match(/\((\d+) racers\)/);
    var racerCount = racerMatch ? racerMatch[1] : '0';

    $panel.find('.age-group-summary').text('(' + roundCount + ' rounds, ' + racerCount + ' racers)');
}

// Helper: Generate slug from class name (e.g., "Ages 6-8" -> "ages_6_8")
function slugify(text) {
    if (!text) return '';
    return text.toString()
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '_')  // Replace non-alphanumeric with underscore
        .replace(/^_+|_+$/g, '')      // Trim leading/trailing underscores
        .replace(/_+/g, '_');         // Collapse multiple underscores
}

// Field help tooltip definitions
var fieldHelp = {
    'races-per-racer': 'Number of times each racer competes in this round. Use 3 for preliminary rounds (once per lane), 1 for elimination brackets.',
    'advancement-rule': 'How racers qualify for next round:\n• Top Count: Specific number of racers advance\n• Percentage: % of field advances\n• Placement: Final round - determines 1st, 2nd, 3rd place',
    'advance-count': 'Exact number of racers who advance to the next round. Example: Top 27 advance from 73 in preliminary.',
    'scoring-method': 'How racer performance is evaluated:\n• Total Time: Sum of all race times\n• Best Time: Fastest single race\n• Average Time: Mean of all races\n• Placement: Position in heat determines rank',
    'lanes': 'Number of racing lanes on your track. Determines how many racers compete in each heat.'
};

// Tooltip display handler
function initHelpTooltips() {
    $(document).on('mouseenter', '.help-icon', function(e) {
        var helpKey = $(this).data('help');
        var helpText = fieldHelp[helpKey];
        if (!helpText) return;

        // Remove any existing tooltip
        $('.help-tooltip').remove();

        var $tooltip = $('<div class="help-tooltip"></div>')
            .text(helpText)
            .css({
                top: $(this).offset().top + 25,
                left: $(this).offset().left - 10
            });

        $('body').append($tooltip);
    });

    $(document).on('mouseleave', '.help-icon', function() {
        $('.help-tooltip').remove();
    });
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
    initHelpTooltips();
});
