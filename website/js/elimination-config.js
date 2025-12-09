// JavaScript for Elimination Configuration Interface

$(function() {
  load_elimination_configs();
  load_elimination_templates();
  
  // Set up event handlers
  $('#elimination-template-button').click(show_elimination_template_modal);
  $('#elimination-custom-button').click(function() {
    show_elimination_custom_modal();
  });
  
  $('#add-round-button').click(add_round_config);
  
  // Handle template modal form submission
  $('#elimination_template_modal form').submit(function(e) {
    e.preventDefault();
    apply_elimination_template();
  });
  
  // Handle custom modal form submission
  $('#elimination_custom_modal form').submit(function(e) {
    e.preventDefault();
    save_elimination_config();
  });
  
  // Handle template selection change
  $('#template-select').change(function() {
    show_template_description();
  });
});

function load_elimination_configs() {
  $.ajax({
    type: 'GET',
    url: 'action.php',
    data: { query: 'elimination.config.list' },
    success: function(data) {
      if (data.outcome && data.outcome.summary == 'success') {
        display_elimination_configs(data.configs || []);
      } else {
        console.warn('Failed to load elimination configs:', data);
        display_elimination_configs([]);
      }
    },
    error: function(xhr, status, error) {
      console.warn('Error loading elimination configs (endpoint may not exist):', error);
      display_elimination_configs([]);
    }
  });
}

function display_elimination_configs(configs) {
  var $container = $('#elimination-configs');
  $container.empty();
  
  if (configs.length === 0) {
    $container.append('<p class="instructions">No elimination configurations defined. Classes will use legacy triple elimination.</p>');
    return;
  }
  
  configs.forEach(function(config) {
    var $configDiv = $('<div class="elimination-config">');
    
    // Header with class name and status
    var $header = $('<div class="config-header">');
    $header.append('<h4 class="config-class-name">' + config.class_name + '</h4>');
    $header.append('<span class="config-status">Configured</span>');
    $configDiv.append($header);
    
    // Configuration details
    var $details = $('<div class="config-details">');
    $details.append('<p><strong>Configuration:</strong> ' + config.config_name + '</p>');
    
    if (config.rounds_count) {
      $details.append('<p><strong>Rounds:</strong> ' + config.rounds_count + '</p>');
    }
    
    // Show round details if available
    if (config.rounds && config.rounds.length > 0) {
      var roundsText = config.rounds.map(function(round, index) {
        return (index + 1) + '. ' + round.round_name + ' (' + round.runs_per_racer + ' run' + (round.runs_per_racer > 1 ? 's' : '') + ')';
      }).join('<br>');
      $details.append('<p><strong>Round Details:</strong><br>' + roundsText + '</p>');
    }
    
    $configDiv.append($details);
    
    // Action buttons
    var $buttons = $('<div class="config-buttons">');
    $buttons.append('<input type="button" value="Edit" onclick="edit_elimination_config(' + config.configid + ', ' + config.classid + ')"/>');
    $buttons.append('<input type="button" value="Delete" onclick="delete_elimination_config(' + config.configid + ')"/>');
    $configDiv.append($buttons);
    
    $container.append($configDiv);
  });
}

function load_elimination_templates() {
  $.ajax({
    type: 'GET',
    url: 'action.php',
    data: { query: 'elimination.templates' },
    success: function(data) {
      if (data.outcome && data.outcome.summary == 'success') {
        populate_template_select(data.templates || {});
      } else {
        console.warn('Failed to load elimination templates:', data);
        populate_template_select({});
      }
    },
    error: function(xhr, status, error) {
      console.warn('Error loading elimination templates (endpoint may not exist):', error);
      populate_template_select({});
    }
  });
}

function populate_template_select(templates) {
  var $select = $('#template-select');
  $select.empty();
  $select.append('<option value="">Choose a template...</option>');
  
  Object.keys(templates).forEach(function(key) {
    var template = templates[key];
    $select.append('<option value="' + key + '">' + template.name + '</option>');
  });
  
  // Store templates for later use
  window.elimination_templates = templates;
}

function show_template_description() {
  var templateKey = $('#template-select').val();
  var $description = $('#template-description');
  
  if (templateKey && window.elimination_templates && window.elimination_templates[templateKey]) {
    var template = window.elimination_templates[templateKey];
    $description.html('<p><strong>Description:</strong> ' + template.description + '</p>');
  } else {
    $description.empty();
  }
}

function show_elimination_template_modal() {
  // Get available classes
  var classes = get_available_classes();
  if (classes.length === 0) {
    alert('No racing groups available. Please create racing groups first.');
    return;
  }
  
  if (classes.length === 1) {
    $('#template_classid').val(classes[0].classid);
    $('#template-config-name').val(classes[0].class_name + ' Elimination');
  } else {
    // If multiple classes, let user choose
    var classOptions = classes.map(function(c) { 
      return c.classid + ': ' + c.class_name; 
    }).join('\n');
    var selection = prompt('Available racing groups:\n' + classOptions + '\n\nEnter class ID for elimination configuration:');
    if (!selection) return;
    $('#template_classid').val(selection);
    
    // Set default config name if we can find the class
    var selectedClass = classes.find(function(c) { return c.classid == selection; });
    if (selectedClass) {
      $('#template-config-name').val(selectedClass.class_name + ' Elimination');
    }
  }
  
  show_modal('#elimination_template_modal', '#template-config-name');
}

function show_elimination_custom_modal(configid, classid) {
  if (configid) {
    // Editing existing config
    load_config_for_editing(configid);
  } else {
    // Creating new config
    var classes = get_available_classes();
    if (classes.length === 0) {
      alert('No racing groups available. Please create racing groups first.');
      return;
    }
    
    $('#custom_configid').val('');
    $('#custom-config-name').val('');
    $('#rounds-list').empty();
    
    if (classid) {
      $('#custom_classid').val(classid);
    } else if (classes.length === 1) {
      $('#custom_classid').val(classes[0].classid);
      $('#custom-config-name').val(classes[0].class_name + ' Custom Elimination');
    } else {
      var classOptions = classes.map(function(c) { 
        return c.classid + ': ' + c.class_name; 
      }).join('\n');
      var selected_classid = prompt('Available racing groups:\n' + classOptions + '\n\nEnter class ID for elimination configuration:');
      if (!selected_classid) return;
      $('#custom_classid').val(selected_classid);
      
      // Set default config name if we can find the class
      var selectedClass = classes.find(function(c) { return c.classid == selected_classid; });
      if (selectedClass) {
        $('#custom-config-name').val(selectedClass.class_name + ' Custom Elimination');
      }
    }
    
    // Add default round
    add_round_config();
  }
  
  show_modal('#elimination_custom_modal', '#custom-config-name');
}

function get_available_classes() {
  // Get classes from the existing racing groups on the page
  var classes = [];
  
  // Get regular racing groups
  $("ul#all-groups > li.group").each(function() {
    var $li = $(this);
    var classid = $li.attr('data-classid');
    var className = $li.find('p.class-name').clone().children().remove().end().text().trim();
    
    if (classid && classid !== "-1" && className) {
      classes.push({
        classid: classid,
        class_name: className
      });
    }
  });
  
  // Get aggregate groups
  $("ul#aggregate-groups > li.aggregate").each(function() {
    var $li = $(this);
    var classid = $li.attr('data-classid');
    var className = $li.find('p.class-name').clone().children().remove().end().text().trim();
    
    if (classid && className) {
      classes.push({
        classid: classid,
        class_name: className + ' (Aggregate)'
      });
    }
  });
  
  return classes;
}

function add_round_config() {
  var $template = $('#elimination_round_template').clone();
  $template.attr('id', '').removeClass('hidden').addClass('round-config');
  
  var roundNumber = $('#rounds-list .round-config').length + 1;
  $template.find('.round-number').text('Round ' + roundNumber);
  
  // Set up delete button
  $template.find('.delete-round-button').click(function() {
    $template.remove();
    renumber_rounds();
  });
  
  $('#rounds-list').append($template);
}

function renumber_rounds() {
  $('#rounds-list .round-config').each(function(index) {
    $(this).find('.round-number').text('Round ' + (index + 1));
  });
}

function apply_elimination_template() {
  var classid = $('#template_classid').val();
  var template_key = $('#template-select').val();
  var config_name = $('#template-config-name').val();
  
  if (!classid || !template_key) {
    alert('Please select a class and template.');
    return;
  }
  
  $.ajax({
    type: 'POST',
    url: 'action.php',
    data: {
      action: 'elimination.config.template',
      classid: classid,
      template_key: template_key,
      config_name: config_name
    },
    success: function(data) {
      if (data.outcome && data.outcome.summary == 'success') {
        close_elimination_template_modal();
        load_elimination_configs();
        alert('Template applied successfully!');
      } else {
        alert('Failed to apply template: ' + (data.outcome ? data.outcome.description : 'Unknown error'));
      }
    },
    error: function(xhr, status, error) {
      alert('Error applying template: ' + error);
    }
  });
}

function save_elimination_config() {
  var classid = $('#custom_classid').val();
  var configid = $('#custom_configid').val();
  var config_name = $('#custom-config-name').val();
  
  if (!classid || !config_name) {
    alert('Please provide class ID and configuration name.');
    return;
  }
  
  var rounds_data = [];
  $('#rounds-list .round-config').each(function() {
    var $round = $(this);
    rounds_data.push({
      name: $round.find('.round-name').val(),
      runs_per_racer: parseInt($round.find('.runs-per-racer').val()),
      advancement_count: parseInt($round.find('.advancement-count').val()) || null,
      advancement_type: $round.find('.advancement-type').val(),
      advancement_criteria: $round.find('.advancement-criteria').val(),
      reset_previous_results: 1
    });
  });
  
  if (rounds_data.length === 0) {
    alert('Please add at least one round.');
    return;
  }
  
  $.ajax({
    type: 'POST',
    url: 'action.php',
    data: {
      action: 'elimination.config.save',
      classid: classid,
      configid: configid,
      config_name: config_name,
      rounds_data: JSON.stringify(rounds_data)
    },
    success: function(data) {
      if (data.outcome && data.outcome.summary == 'success') {
        close_elimination_custom_modal();
        load_elimination_configs();
        alert('Configuration saved successfully!');
      } else {
        alert('Failed to save configuration: ' + (data.outcome ? data.outcome.description : 'Unknown error'));
      }
    },
    error: function(xhr, status, error) {
      alert('Error saving configuration: ' + error);
    }
  });
}

function edit_elimination_config(configid, classid) {
  $.ajax({
    type: 'GET',
    url: 'action.php',
    data: { 
      query: 'elimination.config.list',
      classid: classid 
    },
    success: function(data) {
      if (data.outcome && data.outcome.summary == 'success' && data.config) {
        load_config_into_modal(data.config);
        show_elimination_custom_modal(configid, classid);
      } else {
        alert('Failed to load configuration for editing.');
      }
    },
    error: function(xhr, status, error) {
      alert('Error loading configuration: ' + error);
    }
  });
}

function load_config_into_modal(config) {
  $('#custom_configid').val(config.configid);
  $('#custom_classid').val(config.classid);
  $('#custom-config-name').val(config.config_name);
  
  $('#rounds-list').empty();
  
  config.rounds.forEach(function(round) {
    add_round_config();
    var $lastRound = $('#rounds-list .round-config:last');
    $lastRound.find('.round-name').val(round.round_name);
    $lastRound.find('.runs-per-racer').val(round.runs_per_racer);
    $lastRound.find('.advancement-count').val(round.advancement_count || '');
    $lastRound.find('.advancement-type').val(round.advancement_type);
    $lastRound.find('.advancement-criteria').val(round.advancement_criteria);
  });
}

function delete_elimination_config(configid) {
  if (!confirm('Are you sure you want to delete this elimination configuration?')) {
    return;
  }
  
  $.ajax({
    type: 'POST',
    url: 'action.php',
    data: { 
      action: 'elimination.config.delete',
      configid: configid 
    },
    success: function(data) {
      if (data.outcome && data.outcome.summary == 'success') {
        load_elimination_configs();
        alert('Configuration deleted successfully!');
      } else {
        alert('Failed to delete configuration: ' + (data.outcome ? data.outcome.description : 'Unknown error'));
      }
    },
    error: function(xhr, status, error) {
      alert('Error deleting configuration: ' + error);
    }
  });
}

function close_elimination_template_modal() {
  close_modal('#elimination_template_modal');
}

function close_elimination_custom_modal() {
  close_modal('#elimination_custom_modal');
}

// Use the existing modal functions from modal.js
// Don't redefine show_modal and close_modal