// Pull-Forward dedicated page logic.
//
// Backed by globals from pull-forward.php:
//   g_pf_roundid           - integer roundid of the running round
//   g_pf_has_active_round  - boolean
//   g_pf_roster            - [{racerid, firstname, lastname, carnumber, carname, unraced_heats}]
//   g_pf_round_label       - display string for the running round
//
// AJAX endpoint: action.php?action=schedule.pullforward
//   Dry-run returns the proposal that an immediate execute would apply
//   (the algorithm is deterministic against current chart state).

var g_pf_selected_racerid = null;

$(function () {
  if (!g_pf_has_active_round || !Array.isArray(g_pf_roster) || g_pf_roster.length === 0) {
    return;
  }
  renderRoster();
});

function renderRoster() {
  var $roster = $('#pf-roster').empty();
  for (var i = 0; i < g_pf_roster.length; i++) {
    var r = g_pf_roster[i];
    var name = (r.firstname || '') + ' ' + (r.lastname || '');
    var $row = $('<div>')
      .addClass('pf-racer-row')
      .attr('data-racerid', r.racerid)
      .attr('role', 'button')
      .attr('tabindex', '0');
    $row.append($('<span>').addClass('pf-car').text('#' + r.carnumber));
    $row.append($('<span>').addClass('pf-name').text(name.trim() || '(no name)'));
    $row.append($('<span>').addClass('pf-badge')
      .text(r.unraced_heats + ' heat' + (r.unraced_heats === 1 ? '' : 's')));
    $row.on('click keydown', function (ev) {
      if (ev.type === 'keydown' && ev.which !== 13 && ev.which !== 32) return;
      ev.preventDefault();
      var rid = parseInt($(this).attr('data-racerid'), 10);
      pfSelectRacer(rid);
    });
    $roster.append($row);
  }
}

function pfSelectRacer(racerid) {
  g_pf_selected_racerid = racerid;
  $('#pf-roster .pf-racer-row').removeClass('pf-selected');
  $('#pf-roster .pf-racer-row[data-racerid="' + racerid + '"]').addClass('pf-selected');
  $('#pf-error').addClass('hidden').empty();
  $('#pf-preview').removeClass('hidden').html('<p class="pf-loading">Simulating…</p>');
  $('#pf-actions').addClass('hidden');

  $.ajax('action.php', {
    type: 'POST',
    data: {
      action: 'schedule.pullforward',
      roundid: g_pf_roundid,
      dropout_racerid: racerid,
      'dry-run': 1
    },
    success: function (data) {
      if (data && data.outcome && data.outcome.code === 'success' && data.proposal) {
        renderProposal(data.proposal);
        $('#pf-actions').removeClass('hidden');
        scrollIntoView('#pf-preview');
      } else {
        var code = data && data.outcome ? data.outcome.code : 'unknown';
        var msg  = data && data.outcome ? data.outcome.description : 'Unknown error';
        if (code === 'no_gaps') {
          $('#pf-preview').html(
            '<div class="pf-info"><strong>No remaining heats</strong>' +
            ' — this racer has already finished the round.</div>');
        } else {
          $('#pf-preview').html(
            '<div class="pf-error-inline">Could not generate preview: ' +
            $('<div>').text(msg).html() + '</div>');
        }
        $('#pf-actions').addClass('hidden');
      }
    },
    error: function () {
      $('#pf-preview').html(
        '<div class="pf-error-inline">Server error generating preview. ' +
        'Try again, or fall back to plain dropout from the coordinator page.</div>');
      $('#pf-actions').addClass('hidden');
    }
  });
}

function renderProposal(proposal) {
  var $p = $('#pf-preview').empty();

  var dropoutLine = $('<div>').addClass('pf-dropout-line');
  dropoutLine.append($('<span>').addClass('pf-dropout-label').text('Dropout: '));
  dropoutLine.append($('<strong>').text(proposal.dropout.name + ' (#' + proposal.dropout.carnumber + ')'));
  dropoutLine.append($('<span>').addClass('pf-dropout-gaps')
    .text(' — ' + proposal.dropout.gaps_created + ' gap' +
          (proposal.dropout.gaps_created === 1 ? '' : 's') + ' to fill'));
  $p.append(dropoutLine);

  var $movesSection = $('<div>').addClass('pf-section').append($('<h3>').text('Schedule Changes'));
  var $table = $('<table>').addClass('pf-moves-table');
  $table.append('<thead><tr>' +
    '<th>Fill Heat</th><th>Lane</th><th>Racer Moved</th><th>From Heat</th>' +
    '</tr></thead>');
  var $tbody = $('<tbody>');
  if (!proposal.moves || proposal.moves.length === 0) {
    $tbody.append('<tr><td colspan="4" class="pf-empty">No racers available to pull forward — all gaps will become empty lanes.</td></tr>');
  } else {
    for (var i = 0; i < proposal.moves.length; i++) {
      var m = proposal.moves[i];
      var $tr = $('<tr>');
      $tr.append($('<td>').text('Heat ' + m.gap_heat));
      $tr.append($('<td>').text('Lane ' + m.gap_lane));
      $tr.append($('<td>').text(m.racer_name + ' (#' + m.carnumber + ')'));
      $tr.append($('<td>').text('Heat ' + m.source_heat));
      $tbody.append($tr);
    }
  }
  $table.append($tbody);
  $movesSection.append($table);
  $p.append($movesSection);

  if (proposal.trailing_byes && proposal.trailing_byes.length > 0) {
    var byes = proposal.trailing_byes.map(function (b) {
      return 'Heat ' + b.heat + ' Lane ' + b.lane;
    }).join(', ');
    $p.append($('<div>').addClass('pf-section pf-byes')
      .append($('<h3>').text('Empty Lanes After Pull-Forward'))
      .append($('<p>').text(byes)));
  }

  if (proposal.warnings && proposal.warnings.length > 0) {
    var $warn = $('<div>').addClass('pf-section pf-warnings')
      .append($('<h3>').text('Fairness Warnings'));
    var $ul = $('<ul>');
    for (var j = 0; j < proposal.warnings.length; j++) {
      var w = proposal.warnings[j];
      var text;
      if (w.type === 'consecutive') {
        text = w.racer_name + ' (#' + w.carnumber + ') will race in consecutive heats ' +
               w.heats[0] + ' and ' + w.heats[1];
      } else if (w.type === 'gap-too-tight') {
        text = w.racer_name + ' (#' + w.carnumber + ') will race within ' +
               w.gap + ' heat(s) of their other race ' +
               '(heats ' + w.heats[0] + ' and ' + w.heats[1] +
               '; class minimum is ' + w.min_heat_gap + ')';
      } else {
        text = w.racer_name + ' (#' + w.carnumber + '): ' + w.type;
      }
      $ul.append($('<li>').text(text));
    }
    $warn.append($ul);
    $p.append($warn);
  }

  $p.append($('<div>').addClass('pf-side-effect-note')
    .text('Note: applying will also un-check inspection for the dropout racer ' +
          'so they cannot be re-scheduled by mistake. Use "Undo Pull Forward" ' +
          'on the coordinator page to revert if needed.'));
}

function pfApply(sendBroadcast) {
  if (!g_pf_selected_racerid) return;

  $('.pf-btn').prop('disabled', true);
  $('#pf-error').addClass('hidden').empty();

  $.ajax('action.php', {
    type: 'POST',
    data: {
      action: 'schedule.pullforward',
      roundid: g_pf_roundid,
      dropout_racerid: g_pf_selected_racerid,
      'dry-run': 0,
      send_broadcast: sendBroadcast ? 1 : 0
    },
    success: function (data) {
      if (data && data.outcome && data.outcome.code === 'success') {
        window.location = 'coordinator.php?pf_committed=1';
      } else {
        var msg = data && data.outcome ? data.outcome.description : 'Unknown error';
        showApplyError('Apply failed: ' + msg);
      }
    },
    error: function () {
      showApplyError('Server error during apply. Schedule was NOT changed. ' +
                     'Re-select the racer and try again.');
    }
  });
}

function showApplyError(msg) {
  $('.pf-btn').prop('disabled', false);
  $('#pf-error').removeClass('hidden').text(msg);
  scrollIntoView('#pf-error');
}

function pfDiscard() {
  window.location = 'coordinator.php';
}

function scrollIntoView(sel) {
  var el = $(sel).get(0);
  if (el && typeof el.scrollIntoView === 'function') {
    el.scrollIntoView({behavior: 'smooth', block: 'start'});
  }
}
