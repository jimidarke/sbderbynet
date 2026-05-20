const assert = require('./assert.js');
const puppeteer = require('puppeteer');
const fakeAjax = require('./fake-ajax.js');

var root = 'http://localhost/derbynet';
if (process.argv.length > 2) {
  root = process.argv[2];
}
if (root.substring(0, 'http://'.length) != 'http://') {
  root = 'http://' + root;
}
if (root.substring(root.length - 1) == '/') {
  root = root.substring(0, root.length - 1);
}

var debugging = false;

fakeAjax.setDebugging(debugging);

var role = 'RaceCoordinator';
var password = 'doyourbest';

// Sample proposal returned by a dry-run pull-forward
var sampleProposal = {
  outcome: {code: 'success'},
  proposal: {
    dropout: {
      racerid: 20,
      name: 'Bob Smith',
      carnumber: '420',
      gaps_created: 2
    },
    moves: [
      {
        gap_heat: 5, gap_lane: 2,
        pulled_racerid: 17,
        racer_name: 'Justin Lee', carnumber: '435',
        source_heat: 7
      },
      {
        gap_heat: 7, gap_lane: 1,
        pulled_racerid: 31,
        racer_name: 'Alex Chen', carnumber: '445',
        source_heat: 9
      }
    ],
    trailing_byes: [
      {heat: 9, lane: 1}
    ],
    warnings: [
      {
        type: 'consecutive',
        racer_name: 'Justin Lee',
        carnumber: '435',
        heats: [4, 5]
      }
    ],
    heats_affected: [5, 7, 9]
  }
};

// Proposal with no moves (dropout from last heat)
var emptyProposal = {
  outcome: {code: 'success'},
  proposal: {
    dropout: {
      racerid: 50,
      name: 'Sam Wilson',
      carnumber: '480',
      gaps_created: 1
    },
    moves: [],
    trailing_byes: [
      {heat: 9, lane: 3}
    ],
    warnings: [],
    heats_affected: [9]
  }
};

// Proposal with no warnings or trailing byes
var cleanProposal = {
  outcome: {code: 'success'},
  proposal: {
    dropout: {
      racerid: 30,
      name: 'Kim Park',
      carnumber: '440',
      gaps_created: 1
    },
    moves: [
      {
        gap_heat: 6, gap_lane: 3,
        pulled_racerid: 22,
        racer_name: 'Derek Fox', carnumber: '450',
        source_heat: 8
      }
    ],
    trailing_byes: [],
    warnings: [],
    heats_affected: [6, 8]
  }
};

// Minimal poll JSON to set up coordinator page state
var basePollJson = {
  "current-heat": {
    "now_racing": true,
    "use_master_sched": false,
    "use_points": false,
    "classid": 5,
    "roundid": 5,
    "round": 1,
    "tbodyid": 5,
    "heat": 3,
    "number-of-heats": 9,
    "class": "Arrows"
  },
  "heat-results": [],
  "ready-aggregate": [],
  "racers": [
    {"lane": 1, "name": "John Doe", "carname": "", "carnumber": "405",
     "photo": "", "finishtime": "", "finishplace": ""},
    {"lane": 2, "name": "Bob Smith", "carname": "", "carnumber": "420",
     "photo": "", "finishtime": "", "finishplace": ""},
    {"lane": 3, "name": "Sally Brown", "carname": "", "carnumber": "410",
     "photo": "", "finishtime": "", "finishplace": ""}
  ],
  "timer-state": {"lanes": 3, "last_contact": 1526246081, "state": 3,
                  "icon": "img/status/ok.png", "message": "Staging",
                  "remote-start": false},
  "replay-state": {"last_contact": 0, "state": 1,
                   "icon": "img/status/not_connected.png",
                   "connected": false, "message": "NOT CONNECTED"},
  "classes": [
    {"classid": 5, "count": 9, "nrounds": 1, "ntrophies": -1,
     "name": "Arrows",
     "subgroups": [{"rankid": 5, "count": 9, "name": "Arrows"}]}
  ],
  "rounds": [
    {"roundid": 5, "classid": 5, "class": "Arrows", "round": 1,
     "roster_size": 9, "passed": 9, "unscheduled": 0,
     "heats_scheduled": 9, "heats_run": 2,
     "name": "Arrows, Round 1"}
  ]
};

puppeteer.launch({devtools: debugging, slowMo: 200}).then(async browser => {
  const all_pages = await browser.pages();
  const page = all_pages[0];
  page.setViewport({width: 1200, height: 1800});

  if (debugging) {
    page.on('console', msg => { console.log('REMOTE: ', msg._text); });
  }

  // Login as coordinator
  await page.goto(root + '/login.php');
  await page.evaluate(function (role, password) {
    window.handle_login(role, password);
  }, role, password);
  await page.waitForNavigation();

  await page.evaluateOnNewDocument(() => {
    window.phantom_testing = true;
  });

  await page.goto(root + '/coordinator.php');
  await fakeAjax.installOn(page);

  // Seed the coordinator page with poll data
  await page.evaluate(function(json) {
    process_coordinator_poll_json(JSON.parse(json));
  }, JSON.stringify(basePollJson));

  // Helper: wait for the pull-forward modal to be visible
  async function waitForModalOpen() {
    await page.waitForFunction(() => {
      return !$('#pull_forward_modal').closest('.modal_frame').hasClass('hidden')
          || !$('#pull_forward_modal').hasClass('hidden');
    });
  }

  // Helper: wait for all modals to close
  async function waitForModalsClosed() {
    await page.waitForFunction(() => {
      if ($(".modal_frame").not(".hidden").length > 0) {
        $(".modal_frame").addClass('hidden');
      }
      return $(".modal_frame").not(".hidden").length == 0;
    }, 100);
  }

  // ================================ Test 1: Modal populates correctly ================================
  console.log("Test 1: Modal populates correctly with proposal data");

  // Directly call populatePullForwardModal and show the modal
  await page.evaluate(function(proposal) {
    populatePullForwardModal(proposal);
    show_modal('#pull_forward_modal');
  }, sampleProposal.proposal);

  await waitForModalOpen();

  // Check dropout info
  var dropoutName = await page.$eval('#pf-dropout-name', el => el.textContent);
  assert.equal('Bob Smith', dropoutName);

  var dropoutCar = await page.$eval('#pf-dropout-carnumber', el => el.textContent);
  assert.equal('#420', dropoutCar);

  var gapsCount = await page.$eval('#pf-gaps-count', el => el.textContent);
  assert.equal('2', gapsCount);

  // Check moves table rows
  var moveRows = await page.evaluate(() => {
    var rows = [];
    $('#pf-moves-table tbody tr').each(function() {
      var cells = [];
      $(this).find('td').each(function() { cells.push($(this).text()); });
      rows.push(cells);
    });
    return rows;
  });

  assert.equal(2, moveRows.length);
  assert.equal('Heat 5', moveRows[0][0]);
  assert.equal('Lane 2', moveRows[0][1]);
  assert.equal('Justin Lee (#435)', moveRows[0][2]);
  assert.equal('Heat 7', moveRows[0][3]);
  assert.equal('Heat 7', moveRows[1][0]);
  assert.equal('Lane 1', moveRows[1][1]);
  assert.equal('Alex Chen (#445)', moveRows[1][2]);
  assert.equal('Heat 9', moveRows[1][3]);

  // Check trailing byes visible
  var byesVisible = await page.evaluate(() => !$('#pf-trailing-byes').hasClass('hidden'));
  assert.equal(true, byesVisible);

  var byesText = await page.$eval('#pf-byes-list', el => el.textContent);
  assert.equal('Heat 9 Lane 1', byesText);

  // Check warnings visible
  var warningsVisible = await page.evaluate(() => !$('#pf-warnings').hasClass('hidden'));
  assert.equal(true, warningsVisible);

  var warningItems = await page.evaluate(() => {
    var items = [];
    $('#pf-warnings-list li').each(function() { items.push($(this).text()); });
    return items;
  });
  assert.equal(1, warningItems.length);
  assert.includes('Justin Lee', warningItems[0]);
  assert.includes('consecutive', warningItems[0]);
  assert.includes('4', warningItems[0]);
  assert.includes('5', warningItems[0]);

  // Close modal for next test
  await page.evaluate(() => { close_modal('#pull_forward_modal'); });
  await waitForModalsClosed();

  console.log("  PASS");

  // ================================ Test 2: Empty proposal (no moves) ================================
  console.log("Test 2: Modal handles empty proposal (no available candidates)");

  await page.evaluate(function(proposal) {
    populatePullForwardModal(proposal);
    show_modal('#pull_forward_modal');
  }, emptyProposal.proposal);

  await waitForModalOpen();

  // Should show "no racers available" message
  var emptyRow = await page.evaluate(() => {
    return $('#pf-moves-table tbody tr td').first().text();
  });
  assert.equal('No racers available to pull forward', emptyRow);

  // Trailing byes should be visible
  var emptyByesVisible = await page.evaluate(() => !$('#pf-trailing-byes').hasClass('hidden'));
  assert.equal(true, emptyByesVisible);

  // Warnings should be hidden
  var emptyWarningsHidden = await page.evaluate(() => $('#pf-warnings').hasClass('hidden'));
  assert.equal(true, emptyWarningsHidden);

  await page.evaluate(() => { close_modal('#pull_forward_modal'); });
  await waitForModalsClosed();

  console.log("  PASS");

  // ================================ Test 3: Clean proposal (no warnings/byes) ================================
  console.log("Test 3: Modal hides warnings and byes sections when empty");

  await page.evaluate(function(proposal) {
    populatePullForwardModal(proposal);
    show_modal('#pull_forward_modal');
  }, cleanProposal.proposal);

  await waitForModalOpen();

  // Trailing byes should be hidden
  var cleanByesHidden = await page.evaluate(() => $('#pf-trailing-byes').hasClass('hidden'));
  assert.equal(true, cleanByesHidden);

  // Warnings should be hidden
  var cleanWarningsHidden = await page.evaluate(() => $('#pf-warnings').hasClass('hidden'));
  assert.equal(true, cleanWarningsHidden);

  // Should have exactly 1 move row
  var cleanMoveCount = await page.evaluate(() => $('#pf-moves-table tbody tr').length);
  assert.equal(1, cleanMoveCount);

  await page.evaluate(() => { close_modal('#pull_forward_modal'); });
  await waitForModalsClosed();

  console.log("  PASS");

  // ================================ Test 4: Cancel closes modal ================================
  console.log("Test 4: Cancel button closes modal without AJAX call");

  await page.evaluate(function(proposal) {
    populatePullForwardModal(proposal);
    show_modal('#pull_forward_modal');
  }, sampleProposal.proposal);

  await waitForModalOpen();

  // Click Cancel
  await page.evaluate(() => {
    $('#pull_forward_modal input[value="Cancel"]').click();
  });

  // Modal should close
  await waitForModalsClosed();

  console.log("  PASS");

  // ================================ Test 5: Accept triggers execute AJAX ================================
  console.log("Test 5: Accept button sends execute AJAX (no broadcast)");

  // Set up globals as showPullForwardModal would
  await page.evaluate(() => {
    g_pull_forward_roundid = 5;
    g_pull_forward_dropout_racerid = 20;
  });

  await page.evaluate(function(proposal) {
    populatePullForwardModal(proposal);
    show_modal('#pull_forward_modal');
  }, sampleProposal.proposal);

  await waitForModalOpen();

  // Uninstall fakeAjax temporarily to use a custom interceptor for this test,
  // since executePullForward calls location.reload() which we need to suppress
  await fakeAjax.uninstallOn(page);
  var executeResult = await page.evaluate(() => {
    return new Promise(function(resolve) {
      // Suppress location.reload
      var origReload = location.reload;
      location.reload = function() {};

      $.ajax = function(url, config) {
        resolve({
          url: url,
          type: config.type,
          action: config.data.action,
          roundid: config.data.roundid,
          dropout_racerid: config.data.dropout_racerid,
          dry_run: config.data['dry-run'],
          send_broadcast: config.data.send_broadcast
        });
        config.success({outcome: {code: 'success'}});
        location.reload = origReload;
      };

      $('#pull_forward_modal input[value="Accept"]').click();
    });
  });

  assert.equal('action.php', executeResult.url);
  assert.equal('POST', executeResult.type);
  assert.equal('schedule.pullforward', executeResult.action);
  assert.equal(5, executeResult.roundid);
  assert.equal(20, executeResult.dropout_racerid);
  assert.equal(false, executeResult.dry_run);
  assert.equal(0, executeResult.send_broadcast);

  await fakeAjax.installOn(page);
  await waitForModalsClosed();

  console.log("  PASS");

  // ================================ Test 6: Accept + Announce sends broadcast flag ================================
  console.log("Test 6: Accept + Announce sends broadcast flag");

  await page.evaluate(() => {
    g_pull_forward_roundid = 5;
    g_pull_forward_dropout_racerid = 20;
  });

  await page.evaluate(function(proposal) {
    populatePullForwardModal(proposal);
    show_modal('#pull_forward_modal');
  }, sampleProposal.proposal);

  await waitForModalOpen();

  await fakeAjax.uninstallOn(page);
  var broadcastResult = await page.evaluate(() => {
    return new Promise(function(resolve) {
      var origReload = location.reload;
      location.reload = function() {};

      $.ajax = function(url, config) {
        resolve({
          send_broadcast: config.data.send_broadcast
        });
        config.success({outcome: {code: 'success'}});
        location.reload = origReload;
      };

      $('#pull_forward_modal input[value="Accept + Announce"]').click();
    });
  });

  assert.equal(1, broadcastResult.send_broadcast);

  await fakeAjax.installOn(page);
  await waitForModalsClosed();

  console.log("  PASS");

  // ================================ Test 7: showPullForwardModal sends dry-run AJAX ================================
  console.log("Test 7: showPullForwardModal sends dry-run AJAX and opens modal");

  await fakeAjax.uninstallOn(page);
  var dryRunResult = await page.evaluate(function(response) {
    return new Promise(function(resolve) {
      $.ajax = function(url, config) {
        resolve({
          url: url,
          type: config.type,
          action: config.data.action,
          roundid: config.data.roundid,
          dropout_racerid: config.data.dropout_racerid,
          dry_run: config.data['dry-run']
        });
        config.success(response);
      };

      showPullForwardModal(20, 5);
    });
  }, sampleProposal);

  assert.equal('action.php', dryRunResult.url);
  assert.equal('POST', dryRunResult.type);
  assert.equal('schedule.pullforward', dryRunResult.action);
  assert.equal(5, dryRunResult.roundid);
  assert.equal(20, dryRunResult.dropout_racerid);
  assert.equal(true, dryRunResult.dry_run);

  // Modal should have opened with the proposal data
  await waitForModalOpen();
  var modalDropoutName = await page.$eval('#pf-dropout-name', el => el.textContent);
  assert.equal('Bob Smith', modalDropoutName);

  await page.evaluate(() => { close_modal('#pull_forward_modal'); });
  await waitForModalsClosed();
  await fakeAjax.installOn(page);

  console.log("  PASS");

  // ================================ Test 8: Undo button appears from poll data ================================
  console.log("Test 8: Undo button renders when poll includes pull-forward-undo");

  // Send poll data WITH undo state
  var pollWithUndo = JSON.parse(JSON.stringify(basePollJson));
  pollWithUndo['pull-forward-undo'] = {roundid: 5, dropout_racerid: 20};

  await page.evaluate(function(json) {
    process_coordinator_poll_json(JSON.parse(json));
  }, JSON.stringify(pollWithUndo));

  // Undo button should be present
  var undoButtonExists = await page.evaluate(() => {
    return $('.pull-forward-undo-button').length > 0;
  });
  assert.equal(true, undoButtonExists);

  var undoButtonText = await page.evaluate(() => {
    return $('.pull-forward-undo-button').val();
  });
  assert.equal('Undo Pull Forward', undoButtonText);

  console.log("  PASS");

  // ================================ Test 9: Undo button absent without poll data ================================
  console.log("Test 9: Undo button absent when poll has no pull-forward-undo");

  // Send poll data WITHOUT undo state
  await page.evaluate(function(json) {
    process_coordinator_poll_json(JSON.parse(json));
  }, JSON.stringify(basePollJson));

  var undoButtonGone = await page.evaluate(() => {
    return $('.pull-forward-undo-button').length === 0;
  });
  assert.equal(true, undoButtonGone);

  console.log("  PASS");

  // ================================ Test 10: Undo button triggers undo AJAX ================================
  console.log("Test 10: Undo button sends undo AJAX call");

  // Re-add the undo button via poll
  var pollWithUndo2 = JSON.parse(JSON.stringify(basePollJson));
  pollWithUndo2['pull-forward-undo'] = {roundid: 5, dropout_racerid: 20};

  await page.evaluate(function(json) {
    process_coordinator_poll_json(JSON.parse(json));
  }, JSON.stringify(pollWithUndo2));

  // Override confirm to auto-accept and capture the AJAX call
  await fakeAjax.uninstallOn(page);
  var undoResult = await page.evaluate(() => {
    return new Promise(function(resolve) {
      // Auto-confirm
      window._origConfirm = window.confirm;
      window.confirm = function() { return true; };

      var origReload = location.reload;
      location.reload = function() {};

      $.ajax = function(url, config) {
        resolve({
          url: url,
          type: config.type,
          action: config.data.action,
          roundid: config.data.roundid
        });
        config.success({outcome: {code: 'success'}});
        location.reload = origReload;
        window.confirm = window._origConfirm;
      };

      $('.pull-forward-undo-button').click();
    });
  });

  assert.equal('action.php', undoResult.url);
  assert.equal('POST', undoResult.type);
  assert.equal('schedule.pullforward.undo', undoResult.action);
  assert.equal(5, undoResult.roundid);

  await fakeAjax.installOn(page);

  console.log("  PASS");

  // ================================ Test 11: Modal re-population clears stale data ================================
  console.log("Test 11: Re-populating modal clears previous data");

  // First show with sample proposal (2 moves, warnings, byes)
  await page.evaluate(function(proposal) {
    populatePullForwardModal(proposal);
  }, sampleProposal.proposal);

  // Then re-populate with clean proposal (1 move, no warnings, no byes)
  await page.evaluate(function(proposal) {
    populatePullForwardModal(proposal);
    show_modal('#pull_forward_modal');
  }, cleanProposal.proposal);

  await waitForModalOpen();

  // Should only have 1 move now (not 2 from previous)
  var reuseCount = await page.evaluate(() => $('#pf-moves-table tbody tr').length);
  assert.equal(1, reuseCount);

  // Warnings should be hidden (clean proposal has none)
  var reuseWarnings = await page.evaluate(() => $('#pf-warnings').hasClass('hidden'));
  assert.equal(true, reuseWarnings);

  // Byes should be hidden
  var reuseByes = await page.evaluate(() => $('#pf-trailing-byes').hasClass('hidden'));
  assert.equal(true, reuseByes);

  // Dropout info should show new racer
  var reuseName = await page.$eval('#pf-dropout-name', el => el.textContent);
  assert.equal('Kim Park', reuseName);

  await page.evaluate(() => { close_modal('#pull_forward_modal'); });
  await waitForModalsClosed();

  console.log("  PASS");

  // ================================ Test 11b: gap-too-tight warning renders ================================
  console.log("Test 11b: gap-too-tight warning text includes gap and class-min");

  var gapWarningProposal = {
    dropout: {
      racerid: 42,
      name: 'Pat Reyes',
      carnumber: '442',
      gaps_created: 1
    },
    moves: [
      {
        gap_heat: 6, gap_lane: 2,
        pulled_racerid: 18,
        racer_name: 'Sam Lin', carnumber: '438',
        source_heat: 8
      }
    ],
    trailing_byes: [],
    warnings: [
      {
        type: 'gap-too-tight',
        racer_name: 'Sam Lin',
        carnumber: '438',
        gap: 3,
        min_heat_gap: 6,
        heats: [6, 9]
      }
    ],
    heats_affected: [6, 8]
  };

  await page.evaluate(function(proposal) {
    populatePullForwardModal(proposal);
    show_modal('#pull_forward_modal');
  }, gapWarningProposal);

  await waitForModalOpen();

  var gapWarningsVisible = await page.evaluate(() => !$('#pf-warnings').hasClass('hidden'));
  assert.equal(true, gapWarningsVisible);

  var gapWarningItems = await page.evaluate(() => {
    var items = [];
    $('#pf-warnings-list li').each(function() { items.push($(this).text()); });
    return items;
  });
  assert.equal(1, gapWarningItems.length);
  assert.includes('Sam Lin', gapWarningItems[0]);
  assert.includes('within 3', gapWarningItems[0]);          // gap value
  assert.includes('class minimum is 6', gapWarningItems[0]); // class min
  // Should NOT match the legacy "consecutive" phrasing
  if (gapWarningItems[0].indexOf('consecutive heats') !== -1) {
    throw new Error('gap-too-tight warning mis-rendered as consecutive: ' + gapWarningItems[0]);
  }

  await page.evaluate(() => { close_modal('#pull_forward_modal'); });
  await waitForModalsClosed();

  console.log("  PASS");

  // ================================================================
  // PAGE-DRIVEN TESTS — pull-forward.php (the primary entry point)
  // ================================================================

  // ---- Test 12: Coordinator renders "Pull Forward…" entry button ----
  console.log("Test 12: Coordinator renders Pull Forward... entry button on running round");

  // basePollJson has roundid=5 == current.roundid, heats_run=2 < heats_scheduled=9
  await page.evaluate(function(json) {
    process_coordinator_poll_json(JSON.parse(json));
  }, JSON.stringify(basePollJson));

  var entryButtonExists = await page.evaluate(() => {
    return $('.pull-forward-button').length > 0
      && $('.pull-forward-button').val() === 'Pull Forward…';
  });
  assert.equal(true, entryButtonExists);

  // Should NOT appear when all heats have run
  var pollAllDone = JSON.parse(JSON.stringify(basePollJson));
  pollAllDone.rounds[0].heats_run = pollAllDone.rounds[0].heats_scheduled;
  await page.evaluate(function(json) {
    process_coordinator_poll_json(JSON.parse(json));
  }, JSON.stringify(pollAllDone));

  var entryButtonGone = await page.evaluate(() => {
    return $('.pull-forward-button').length === 0;
  });
  assert.equal(true, entryButtonGone);

  console.log("  PASS");

  // ---- Test 13: Page handles "no active round" gracefully ----
  console.log("Test 13: pull-forward.php shows empty state when no roster present");

  // Navigate to the page with no active round (we simulate by setting globals
  // before the page's $(function) runs is hard; instead, navigate and inspect
  // what the server rendered for the current state).
  await page.goto(root + '/pull-forward.php');

  var emptyOrRoster = await page.evaluate(() => {
    return {
      hasEmpty: $('.pf-empty-state').length > 0,
      hasRoster: $('#pf-roster .pf-racer-row').length > 0,
      hasActions: !$('#pf-actions').hasClass('hidden'),
    };
  });
  // Either the empty state is shown OR a roster is shown — never both.
  // Action bar must not be visible until a racer is selected.
  assert.equal(false, emptyOrRoster.hasEmpty && emptyOrRoster.hasRoster);
  assert.equal(false, emptyOrRoster.hasActions);

  console.log("  PASS");

  // ---- Test 14: Roster rendering, selection fires dry-run, preview renders ----
  console.log("Test 14: Roster + selection + preview rendering on pull-forward.php");

  // Stub the page state so the roster has predictable racers.
  // pull-forward.js renders from g_pf_roster on $(function); we re-run after
  // injecting test data.
  await page.evaluate(function() {
    g_pf_has_active_round = true;
    g_pf_roster = [
      {racerid: 17, firstname: 'Justin', lastname: 'Lee', carnumber: '435', carname: '', unraced_heats: 4},
      {racerid: 20, firstname: 'Bob',    lastname: 'Smith', carnumber: '420', carname: '', unraced_heats: 2},
      {racerid: 31, firstname: 'Alex',   lastname: 'Chen',  carnumber: '445', carname: '', unraced_heats: 3}
    ];
    g_pf_roundid = 5;
    // Re-render roster (the original $(function) already ran on a possibly-
    // empty roster; clear and re-render to test against our injected data).
    $('#pf-roster').empty();
    $('#pf-page .pf-empty-state').remove();
    if ($('#pf-roster').length === 0) {
      $('body').append('<div id="pf-page"><div id="pf-roster"></div>' +
        '<div id="pf-preview" class="hidden"></div>' +
        '<div id="pf-error" class="hidden"></div>' +
        '<div id="pf-actions" class="pf-actions hidden">' +
          '<input type="button" class="pf-btn pf-btn-apply" value="Apply"/>' +
          '<input type="button" class="pf-btn pf-btn-announce" value="Apply + Announce"/>' +
          '<input type="button" class="pf-btn pf-btn-discard" value="Discard"/>' +
        '</div></div>');
    }
    renderRoster();
  });

  var rowOrder = await page.evaluate(() => {
    var out = [];
    $('#pf-roster .pf-racer-row').each(function() {
      out.push({
        racerid: $(this).attr('data-racerid'),
        car: $(this).find('.pf-car').text(),
        name: $(this).find('.pf-name').text(),
        badge: $(this).find('.pf-badge').text()
      });
    });
    return out;
  });
  assert.equal(3, rowOrder.length);
  // Roster passed in already car-sorted (server orders); JS preserves order.
  assert.equal('#435', rowOrder[0].car);
  assert.equal('Justin Lee', rowOrder[0].name);
  assert.includes('4', rowOrder[0].badge);

  // Capture the dry-run AJAX call when a racer row is tapped.
  var dryRunCall = await page.evaluate(function(response) {
    return new Promise(function(resolve) {
      $.ajax = function(url, config) {
        resolve({
          url: url,
          action: config.data.action,
          roundid: config.data.roundid,
          dropout_racerid: config.data.dropout_racerid,
          dry_run: config.data['dry-run']
        });
        config.success(response);
      };
      $('#pf-roster .pf-racer-row[data-racerid="20"]').trigger('click');
    });
  }, sampleProposal);

  assert.equal('action.php', dryRunCall.url);
  assert.equal('schedule.pullforward', dryRunCall.action);
  assert.equal(5, dryRunCall.roundid);
  assert.equal(20, dryRunCall.dropout_racerid);
  assert.equal(1, dryRunCall.dry_run);

  // Preview should now be rendered, action bar visible, row marked selected.
  var previewState = await page.evaluate(() => {
    return {
      previewShown: !$('#pf-preview').hasClass('hidden'),
      actionsShown: !$('#pf-actions').hasClass('hidden'),
      selected: $('#pf-roster .pf-racer-row.pf-selected').attr('data-racerid'),
      moveRows: $('#pf-preview .pf-moves-table tbody tr').length,
      hasByesSection: $('#pf-preview .pf-byes').length > 0,
      hasWarningsSection: $('#pf-preview .pf-warnings').length > 0,
      hasSideEffectNote: $('#pf-preview .pf-side-effect-note').length > 0,
      dropoutText: $('#pf-preview .pf-dropout-line').text()
    };
  });
  assert.equal(true, previewState.previewShown);
  assert.equal(true, previewState.actionsShown);
  assert.equal('20', previewState.selected);
  assert.equal(2, previewState.moveRows);
  assert.equal(true, previewState.hasByesSection);
  assert.equal(true, previewState.hasWarningsSection);
  assert.equal(true, previewState.hasSideEffectNote);
  assert.includes('Bob Smith', previewState.dropoutText);
  assert.includes('420', previewState.dropoutText);

  console.log("  PASS");

  // ---- Test 15: Re-selecting a different racer replaces preview ----
  console.log("Test 15: Re-selecting a different racer replaces the preview");

  await page.evaluate(function(response) {
    $.ajax = function(url, config) {
      config.success(response);
    };
    $('#pf-roster .pf-racer-row[data-racerid="31"]').trigger('click');
  }, cleanProposal);

  var afterReselect = await page.evaluate(() => {
    return {
      selected: $('#pf-roster .pf-racer-row.pf-selected').attr('data-racerid'),
      selectedCount: $('#pf-roster .pf-racer-row.pf-selected').length,
      dropoutText: $('#pf-preview .pf-dropout-line').text(),
      moveRows: $('#pf-preview .pf-moves-table tbody tr').length,
      hasByesSection: $('#pf-preview .pf-byes').length > 0,
      hasWarningsSection: $('#pf-preview .pf-warnings').length > 0
    };
  });
  assert.equal('31', afterReselect.selected);
  assert.equal(1, afterReselect.selectedCount);
  assert.includes('Kim Park', afterReselect.dropoutText);
  assert.equal(1, afterReselect.moveRows);
  assert.equal(false, afterReselect.hasByesSection);
  assert.equal(false, afterReselect.hasWarningsSection);

  console.log("  PASS");

  // ---- Test 16: no_gaps shows inline info, action bar stays hidden ----
  console.log("Test 16: no_gaps response shows inline info and hides actions");

  await page.evaluate(function() {
    $.ajax = function(url, config) {
      config.success({outcome: {code: 'no_gaps', description: 'Racer has no unraced heats'}});
    };
    $('#pf-roster .pf-racer-row[data-racerid="17"]').trigger('click');
  });

  var noGapsState = await page.evaluate(() => {
    return {
      previewHtml: $('#pf-preview').text(),
      actionsHidden: $('#pf-actions').hasClass('hidden'),
      hasInfo: $('#pf-preview .pf-info').length > 0
    };
  });
  assert.equal(true, noGapsState.hasInfo);
  assert.includes('No remaining heats', noGapsState.previewHtml);
  assert.equal(true, noGapsState.actionsHidden);

  console.log("  PASS");

  // ---- Test 17: Apply commits without broadcast and redirects ----
  console.log("Test 17: Apply commits with send_broadcast=0 and redirects with pf_committed=1");

  // Re-select a racer to enable the action bar.
  await page.evaluate(function(response) {
    $.ajax = function(url, config) { config.success(response); };
    $('#pf-roster .pf-racer-row[data-racerid="20"]').trigger('click');
  }, sampleProposal);

  var applyCall = await page.evaluate(function() {
    return new Promise(function(resolve) {
      var capturedHref = null;
      // Stub window.location assignment to a sentinel object that records href
      var fakeLoc = {};
      Object.defineProperty(fakeLoc, 'href', {
        set: function(v) { capturedHref = v; resolve({captured: capturedHref, ajax: window._pfApplyAjax}); }
      });
      try { window.location = fakeLoc; } catch (e) { /* read-only in some envs */ }

      $.ajax = function(url, config) {
        window._pfApplyAjax = {
          action: config.data.action,
          roundid: config.data.roundid,
          dropout_racerid: config.data.dropout_racerid,
          dry_run: config.data['dry-run'],
          send_broadcast: config.data.send_broadcast
        };
        // The success handler does `window.location = '...';` which triggers
        // the setter above and resolves the promise.
        config.success({outcome: {code: 'success'}});
      };

      $('.pf-btn-apply').trigger('click');
    });
  });

  assert.equal('schedule.pullforward', applyCall.ajax.action);
  assert.equal(5, applyCall.ajax.roundid);
  assert.equal(20, applyCall.ajax.dropout_racerid);
  assert.equal(0, applyCall.ajax.dry_run);
  assert.equal(0, applyCall.ajax.send_broadcast);
  assert.includes('coordinator.php', applyCall.captured);
  assert.includes('pf_committed=1', applyCall.captured);

  console.log("  PASS");

  // ---- Test 18: Apply + Announce sends send_broadcast=1 ----
  console.log("Test 18: Apply + Announce sends send_broadcast=1");

  // Reload the test scaffold so window.location is fresh.
  await page.goto(root + '/pull-forward.php');
  await page.evaluate(function() {
    g_pf_has_active_round = true;
    g_pf_roster = [
      {racerid: 20, firstname: 'Bob', lastname: 'Smith', carnumber: '420', carname: '', unraced_heats: 2}
    ];
    g_pf_roundid = 5;
    $('#pf-roster').empty();
    $('#pf-page .pf-empty-state').remove();
    if ($('#pf-roster').length === 0) {
      $('body').append('<div id="pf-page"><div id="pf-roster"></div>' +
        '<div id="pf-preview" class="hidden"></div>' +
        '<div id="pf-error" class="hidden"></div>' +
        '<div id="pf-actions" class="pf-actions hidden">' +
          '<input type="button" class="pf-btn pf-btn-apply" value="Apply"/>' +
          '<input type="button" class="pf-btn pf-btn-announce" value="Apply + Announce"/>' +
          '<input type="button" class="pf-btn pf-btn-discard" value="Discard"/>' +
        '</div></div>');
    }
    renderRoster();
  });

  var announceCall = await page.evaluate(function(response) {
    return new Promise(function(resolve) {
      // First the dry-run for selection
      $.ajax = function(url, config) { config.success(response); };
      $('#pf-roster .pf-racer-row[data-racerid="20"]').trigger('click');

      // Then capture the apply call
      var fakeLoc = {};
      Object.defineProperty(fakeLoc, 'href', {
        set: function(v) { resolve({captured: v, sb: window._sb}); }
      });
      try { window.location = fakeLoc; } catch (e) {}

      $.ajax = function(url, config) {
        window._sb = config.data.send_broadcast;
        config.success({outcome: {code: 'success'}});
      };
      $('.pf-btn-announce').trigger('click');
    });
  }, sampleProposal);

  assert.equal(1, announceCall.sb);

  console.log("  PASS");

  // ---- Test 19: Discard returns to coordinator with no AJAX ----
  console.log("Test 19: Discard returns to coordinator without committing");

  await page.goto(root + '/pull-forward.php');
  await page.evaluate(function() {
    g_pf_has_active_round = true;
    g_pf_roster = [
      {racerid: 20, firstname: 'Bob', lastname: 'Smith', carnumber: '420', carname: '', unraced_heats: 2}
    ];
    g_pf_roundid = 5;
    $('#pf-roster').empty();
    $('#pf-page .pf-empty-state').remove();
    if ($('#pf-roster').length === 0) {
      $('body').append('<div id="pf-page"><div id="pf-roster"></div>' +
        '<div id="pf-preview" class="hidden"></div>' +
        '<div id="pf-error" class="hidden"></div>' +
        '<div id="pf-actions" class="pf-actions hidden">' +
          '<input type="button" class="pf-btn pf-btn-apply" value="Apply"/>' +
          '<input type="button" class="pf-btn pf-btn-announce" value="Apply + Announce"/>' +
          '<input type="button" class="pf-btn pf-btn-discard" value="Discard"/>' +
        '</div></div>');
    }
    renderRoster();
  });

  var discardResult = await page.evaluate(function() {
    return new Promise(function(resolve) {
      var ajaxCalled = false;
      $.ajax = function() { ajaxCalled = true; };

      var fakeLoc = {};
      Object.defineProperty(fakeLoc, 'href', {
        set: function(v) { resolve({captured: v, ajaxCalled: ajaxCalled}); }
      });
      try { window.location = fakeLoc; } catch (e) {}

      $('.pf-btn-discard').trigger('click');
    });
  });

  assert.equal(false, discardResult.ajaxCalled);
  assert.includes('coordinator.php', discardResult.captured);
  assert.equal(false, /pf_committed/.test(discardResult.captured));

  console.log("  PASS");

  // ---- Test 20: ?pf_committed=1 triggers undo-button pulse class ----
  console.log("Test 20: pf_committed=1 query param pulses the Undo button on coordinator");

  await page.goto(root + '/coordinator.php?pf_committed=1');
  await fakeAjax.installOn(page);
  // Render poll with undo state set
  var pollWithUndo3 = JSON.parse(JSON.stringify(basePollJson));
  pollWithUndo3['pull-forward-undo'] = {roundid: 5, dropout_racerid: 20};
  await page.evaluate(function(json) {
    process_coordinator_poll_json(JSON.parse(json));
  }, JSON.stringify(pollWithUndo3));

  var pulseClassPresent = await page.evaluate(() => {
    return $('.pull-forward-undo-button').hasClass('pull-forward-undo-pulse');
  });
  assert.equal(true, pulseClassPresent);

  // The query param should have been stripped from the URL
  var urlAfterStrip = await page.evaluate(() => window.location.search);
  assert.equal(false, /pf_committed/.test(urlAfterStrip));

  console.log("  PASS");

  // ================================ Done ================================
  console.log("");
  console.log("============= All pull-forward UI tests passed =============");

  await browser.close();
}).catch(e => {
  console.error(e);
  process.exit(1);
});
