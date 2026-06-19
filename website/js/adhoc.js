// Start-line marshal page for ad-hoc racing mode. Talks to:
//   action=adhoc.mode (on/off)  — build+switch / switch back
//   action=adhoc.heat           — form a heat from the 3 entered pinnies + arm
//   query=poll.coordinator      — live current-heat / lane / timer status
// See website/adhoc.php and docs/ADHOC.md.

var AdHoc = (function () {
  var pollTimer = null;
  var pollPeriod = (typeof g_update_period === 'number' && g_update_period > 0)
                   ? g_update_period : 1500;

  function msg(text, kind) {
    var $m = $('#adhoc-message');
    $m.text(text || '').removeClass('ok err');
    if (kind) $m.addClass(kind);
  }

  function updateModeUI() {
    var on = !!g_adhoc_mode;
    $('#adhoc-mode-bar').toggleClass('on', on).toggleClass('off', !on);
    $('#adhoc-mode-label').text(on ? 'AD-HOC MODE: ON' : 'AD-HOC MODE: OFF');
    $('#adhoc-warn-official').toggle(!on);
    $('#adhoc-arm').toggle(on);
    $('#adhoc-status').toggle(on);
    $('#adhoc-build-btn').toggle(!on);
    $('#adhoc-end-btn').toggle(on);
    if (!on) { $('#adhoc-built').text(''); }
  }

  function outcomeOk(data) {
    return data && data.outcome && data.outcome.summary === 'success';
  }
  function outcomeMsg(data) {
    return (data && data.outcome && data.outcome.description) || 'Request failed.';
  }

  function buildAndSwitch() {
    msg('Building ad-hoc roster…');
    $('#adhoc-build-btn').prop('disabled', true);
    $.post('action.php', { action: 'adhoc.mode', mode: 'on' }, null, 'json')
      .done(function (data) {
        if (outcomeOk(data)) {
          g_adhoc_mode = true;
          updateModeUI();
          var n = data.adhoc && data.adhoc.racers;
          msg('Ad-hoc mode ON' + (n != null ? (' — ' + n + ' racers loaded.') : '.'), 'ok');
          $('#adhoc-built').text('roster just built');
          $('#pinny1').focus();
          poll();
        } else {
          msg(outcomeMsg(data), 'err');
        }
      })
      .fail(function () { msg('Could not reach the server.', 'err'); })
      .always(function () { $('#adhoc-build-btn').prop('disabled', false); });
  }

  function endAndSwitch() {
    if (!window.confirm('End ad-hoc racing and switch back to the official database?')) return;
    $('#adhoc-end-btn').prop('disabled', true);
    $.post('action.php', { action: 'adhoc.mode', mode: 'off' }, null, 'json')
      .done(function (data) {
        if (outcomeOk(data)) {
          g_adhoc_mode = false;
          updateModeUI();
          msg('Back on the official database.', 'ok');
          poll();
        } else {
          msg(outcomeMsg(data), 'err');
        }
      })
      .fail(function () { msg('Could not reach the server.', 'err'); })
      .always(function () { $('#adhoc-end-btn').prop('disabled', false); });
  }

  function armHeat() {
    if (!g_adhoc_mode) { msg('Turn ad-hoc mode on first.', 'err'); return; }
    var payload = {
      action: 'adhoc.heat',
      pinny1: $('#pinny1').val(),
      pinny2: $('#pinny2').val(),
      pinny3: $('#pinny3').val()
    };
    $('#adhoc-arm-btn').prop('disabled', true);
    $.post('action.php', payload, null, 'json')
      .done(function (data) {
        if (outcomeOk(data)) {
          var h = data.adhoc_heat || {};
          msg('Heat ' + (h.heat != null ? h.heat : '') + ' armed — go!', 'ok');
          clearInputs();
          render(data); // poll fields are appended to the heat response
        } else {
          msg(outcomeMsg(data), 'err');
        }
      })
      .fail(function () { msg('Could not reach the server.', 'err'); })
      .always(function () { $('#adhoc-arm-btn').prop('disabled', false); });
  }

  function clearInputs() {
    $('#pinny1, #pinny2, #pinny3').val('');
    $('#pinny1').focus();
  }

  function render(data) {
    if (!data) return;
    var ch = data['current-heat'] || {};
    $('#adhoc-heat-num').text(ch.heat != null ? ('#' + ch.heat) : '');
    var racing = !!ch.now_racing;
    $('#adhoc-racing-badge')
      .text(racing ? 'RACING' : 'ready')
      .toggleClass('racing', racing);

    var racers = data.racers || [];
    var $tb = $('#adhoc-lanes tbody').empty();
    if (!racers.length) {
      $tb.append('<tr><td colspan="3" class="muted">No racers armed yet.</td></tr>');
    } else {
      racers.forEach(function (r) {
        var tr = $('<tr></tr>');
        tr.append($('<td class="lane"></td>').text('Lane ' + r.lane));
        tr.append($('<td class="pinny"></td>').text(r.carnumber));
        tr.append($('<td class="time"></td>').text(r.finishtime || (racing ? '…' : '')));
        $tb.append(tr);
      });
    }

    var ts = data['timer-state'] || {};
    var tmsg = ts.health_message || ts.message || '';
    if (ts.timers_online != null && ts.timers_required != null) {
      tmsg = tmsg + '  (' + ts.timers_online + '/' + ts.timers_required + ' finish timers online)';
    }
    $('#adhoc-timer').text(tmsg);
  }

  function poll() {
    if (!g_adhoc_mode) return;
    $.getJSON('action.php', { query: 'poll.coordinator' })
      .done(render)
      .always(function () {
        if (pollTimer) clearTimeout(pollTimer);
        pollTimer = setTimeout(poll, pollPeriod);
      });
  }

  function wirePinnyEnter() {
    $('#pinny1').on('keydown', function (e) { if (e.key === 'Enter') { e.preventDefault(); $('#pinny2').focus(); } });
    $('#pinny2').on('keydown', function (e) { if (e.key === 'Enter') { e.preventDefault(); $('#pinny3').focus(); } });
    $('#pinny3').on('keydown', function (e) { if (e.key === 'Enter') { e.preventDefault(); armHeat(); } });
  }

  function init() {
    updateModeUI();
    $('#adhoc-build-btn').on('click', buildAndSwitch);
    $('#adhoc-end-btn').on('click', endAndSwitch);
    $('#adhoc-arm-btn').on('click', armHeat);
    $('#adhoc-clear-btn').on('click', clearInputs);
    wirePinnyEnter();
    if (g_adhoc_mode) poll();
  }

  return { init: init };
})();

$(function () { AdHoc.init(); });
