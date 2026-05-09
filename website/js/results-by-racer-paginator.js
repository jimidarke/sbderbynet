// results-by-racer paginator.
//
// Builds racer cards from /action.php?query=poll.results, sorts by car
// number, paginates to fit the viewport, and auto-advances every 8s with a
// 400ms cross-fade.
//
// When new finishes land, the current page is held a beat so spectators see
// the update in place, and the paginator jumps to the page that contains
// the changed racer.
//
// Lightweight on purpose: pure DOM, one fetch per second, no animation
// libraries. Targets a Raspberry Pi running Chromium.

(function () {
  var POLL_MS         = 1000;
  var ADVANCE_MS      = 8000;
  var FADE_MS         = 400;
  var CARD_HEIGHT_VH  = 18;   // approximate; one card per ~18% of viewport
  var MIN_CARDS       = 3;
  var MAX_CARDS       = 8;

  var stage     = null;
  var indicator = null;
  var pages     = [];          // array of arrays of racers
  var pageEls   = [];          // array of <div class="rr-page"> elements
  var currentPageIdx = 0;
  var advanceTimer  = null;
  var lastSnapshotKey = '';
  var lastTimeFormat  = '%.3f';
  var roundLabel      = '';

  // Format a millisecond integer using a printf-style %.Nf pattern.
  function formatMs(ms, fmt) {
    if (ms === null || ms === undefined) return '----';
    var match = (fmt || '%.3f').match(/%\.(\d)f/);
    var dp = match ? parseInt(match[1], 10) : 3;
    return (ms / 1000).toFixed(dp);
  }

  function cardsPerPage() {
    var available = window.innerHeight - 64 /* banner */ - 40 /* padding+indicator */;
    var cardPx    = (CARD_HEIGHT_VH / 100) * window.innerHeight;
    var n = Math.floor(available / cardPx);
    if (n < MIN_CARDS) n = MIN_CARDS;
    if (n > MAX_CARDS) n = MAX_CARDS;
    return n;
  }

  function chunk(arr, size) {
    var out = [];
    for (var i = 0; i < arr.length; i += size) out.push(arr.slice(i, i + size));
    return out;
  }

  function buildCard(racer, bestMsAcrossRacer) {
    var card = document.createElement('div');
    card.className = 'rr-card';
    card.setAttribute('data-racerid', racer.racerid);

    // Identity
    var identity = document.createElement('div');
    identity.className = 'rr-identity';
    var photo = document.createElement('div');
    photo.className = 'rr-photo';
    if (racer.photo) {
      photo.style.backgroundImage = "url('" + racer.photo.replace(/'/g, "%27") + "')";
    } else {
      photo.classList.add('no-photo');
      photo.textContent = '#' + racer.carnumber;
    }
    var car = document.createElement('div');
    car.className = 'rr-car';
    car.textContent = '#' + racer.carnumber;
    var name = document.createElement('div');
    name.className = 'rr-name';
    name.textContent = racer.name || '';
    identity.appendChild(photo);
    identity.appendChild(car);
    identity.appendChild(name);

    // Stats
    var stats = document.createElement('div');
    stats.className = 'rr-stats';

    var bestLabel = document.createElement('div');
    bestLabel.className = 'rr-best-label';
    bestLabel.textContent = 'Best';
    var best = document.createElement('div');
    best.className = 'rr-best';
    best.textContent = formatMs(racer.best_ms, lastTimeFormat);

    var avgLabel = document.createElement('div');
    avgLabel.className = 'rr-avg-label';
    avgLabel.textContent = 'Average';
    var avg = document.createElement('div');
    avg.className = 'rr-avg';
    avg.textContent = formatMs(racer.avg_ms, lastTimeFormat);

    var progress = document.createElement('div');
    progress.className = 'rr-progress';
    var progressLabel = document.createElement('span');
    progressLabel.textContent = (racer.runs_done || 0) + ' / ' + (racer.runs_total || 0) + ' runs';
    progress.appendChild(progressLabel);
    for (var i = 0; i < (racer.runs_total || 0); i++) {
      var d = document.createElement('span');
      d.className = 'rr-dot' + (i < (racer.runs_done || 0) ? ' is-done' : '');
      progress.appendChild(d);
    }

    stats.appendChild(bestLabel);
    stats.appendChild(best);
    stats.appendChild(avgLabel);
    stats.appendChild(avg);
    stats.appendChild(progress);

    // Runs
    var runs = document.createElement('div');
    runs.className = 'rr-runs';
    var rs = racer.runs || [];
    for (var j = 0; j < rs.length; j++) {
      var r = rs[j];
      var row = document.createElement('div');
      row.className = 'rr-run';
      if (!r.finished) row.classList.add('is-pending');
      if (r.finished && r.time_ms === racer.best_ms) row.classList.add('is-best');

      var lbl = document.createElement('span');
      lbl.className = 'rr-run-label';
      lbl.textContent = 'Run ' + (j + 1);

      var laneTag = document.createElement('span');
      laneTag.className = 'rr-run-label';
      laneTag.style.opacity = '0.7';
      laneTag.textContent = 'Lane ' + r.lane;

      var t = document.createElement('span');
      t.className = 'rr-run-time';
      t.textContent = r.finished ? formatMs(r.time_ms, lastTimeFormat) : '----';

      row.appendChild(lbl);
      row.appendChild(laneTag);
      row.appendChild(t);
      runs.appendChild(row);
    }

    card.appendChild(identity);
    card.appendChild(stats);
    card.appendChild(runs);
    return card;
  }

  function snapshotKey(racers) {
    // A compact fingerprint: car# + best_ms + runs_done per racer.
    var parts = [];
    for (var i = 0; i < racers.length; i++) {
      var r = racers[i];
      parts.push(r.carnumber + ':' + r.best_ms + ':' + r.runs_done);
    }
    return parts.join('|');
  }

  function rebuildPages(racers) {
    // Sort by car number (numeric where possible, else lexical).
    racers.sort(function (a, b) {
      var an = parseInt(a.carnumber, 10);
      var bn = parseInt(b.carnumber, 10);
      if (!isNaN(an) && !isNaN(bn) && an !== bn) return an - bn;
      return String(a.carnumber).localeCompare(String(b.carnumber));
    });

    pages = chunk(racers, cardsPerPage());

    // Wipe prior pages.
    for (var i = 0; i < pageEls.length; i++) {
      if (pageEls[i] && pageEls[i].parentNode) {
        pageEls[i].parentNode.removeChild(pageEls[i]);
      }
    }
    pageEls = [];

    // Build new pages.
    for (var p = 0; p < pages.length; p++) {
      var pageEl = document.createElement('div');
      pageEl.className = 'rr-page';
      pageEl.style.gridTemplateRows = 'repeat(' + cardsPerPage() + ', 1fr)';
      for (var c = 0; c < pages[p].length; c++) {
        pageEl.appendChild(buildCard(pages[p][c]));
      }
      stage.appendChild(pageEl);
      pageEls.push(pageEl);
    }

    var empty = stage.querySelector('.rr-empty');
    if (empty) empty.style.display = pages.length ? 'none' : '';
    stage.setAttribute('data-state', pages.length ? 'ready' : 'empty');
  }

  function showPage(idx) {
    if (!pageEls.length) return;
    if (idx < 0) idx = pageEls.length - 1;
    if (idx >= pageEls.length) idx = 0;
    for (var i = 0; i < pageEls.length; i++) {
      pageEls[i].classList.toggle('is-current', i === idx);
    }
    currentPageIdx = idx;
    updateIndicator();
  }

  function updateIndicator() {
    if (!indicator) return;
    if (pages.length <= 1) {
      indicator.classList.remove('is-visible');
      indicator.textContent = '';
      return;
    }
    var label = 'Page ' + (currentPageIdx + 1) + ' / ' + pages.length;
    if (roundLabel) label += ' · ' + roundLabel;
    indicator.textContent = label;
    indicator.classList.add('is-visible');
  }

  function startAutoAdvance() {
    stopAutoAdvance();
    if (pages.length <= 1) return;
    advanceTimer = setInterval(function () {
      showPage(currentPageIdx + 1);
    }, ADVANCE_MS);
  }

  function stopAutoAdvance() {
    if (advanceTimer) {
      clearInterval(advanceTimer);
      advanceTimer = null;
    }
  }

  function pageContaining(racerid) {
    for (var p = 0; p < pages.length; p++) {
      for (var c = 0; c < pages[p].length; c++) {
        if (pages[p][c].racerid === racerid) return p;
      }
    }
    return -1;
  }

  function diffChangedRacerIds(prevRacers, nextRacers) {
    var prevById = {};
    for (var i = 0; i < prevRacers.length; i++) {
      prevById[prevRacers[i].racerid] = prevRacers[i];
    }
    var changed = [];
    for (var j = 0; j < nextRacers.length; j++) {
      var n = nextRacers[j];
      var p = prevById[n.racerid];
      if (!p || p.runs_done !== n.runs_done || p.best_ms !== n.best_ms) {
        changed.push(n.racerid);
      }
    }
    return changed;
  }

  var lastRacersForDiff = [];

  function applySnapshot(snapshot) {
    if (!snapshot || !snapshot.racers) return;
    lastTimeFormat = snapshot.time_format || lastTimeFormat;
    roundLabel = snapshot.round_label || roundLabel;

    var racers = snapshot.racers;
    var key = snapshotKey(racers);
    if (key === lastSnapshotKey) return;     // no change
    var changedIds = diffChangedRacerIds(lastRacersForDiff, racers);
    lastSnapshotKey = key;
    lastRacersForDiff = racers.slice();

    rebuildPages(racers);

    // If we know which racer just changed, jump to that page; otherwise stay.
    var jumpIdx = currentPageIdx;
    if (changedIds.length === 1) {
      var p = pageContaining(changedIds[0]);
      if (p >= 0) jumpIdx = p;
    }
    showPage(jumpIdx);

    // Highlight changed cards briefly.
    if (changedIds.length) {
      for (var i = 0; i < pageEls.length; i++) {
        var cards = pageEls[i].querySelectorAll('.rr-card');
        for (var c = 0; c < cards.length; c++) {
          var rid = parseInt(cards[c].getAttribute('data-racerid'), 10);
          if (changedIds.indexOf(rid) >= 0) {
            cards[c].classList.add('is-changed');
            (function (el) {
              setTimeout(function () { el.classList.remove('is-changed'); }, 4000);
            })(cards[c]);
          }
        }
      }
    }

    // Restart advance timer so the user gets a full cycle on the (possibly new) page.
    startAutoAdvance();
  }

  function poll() {
    $.ajax('action.php', {
      type: 'GET',
      data: { query: 'poll.results' },
      cache: false,
      success: function (data) {
        if (data && data.cease) {
          window.location.href = '../index.php';
          return;
        }
        if (data && data['current-heat']) {
          var ch = data['current-heat'];
          roundLabel = (ch['class'] ? ch['class'] + ' · ' : '')
                       + 'Round ' + (ch.round || '');
        }
        if (data && data.racer_summaries) {
          applySnapshot({
            racers: data.racer_summaries.racers || [],
            time_format: data.racer_summaries.time_format,
            round_label: roundLabel
          });
        }
      }
    });
  }

  function start() {
    stage = document.getElementById('rr-stage');
    indicator = document.getElementById('rr-pageindicator');
    if (!stage) return;

    poll();
    setInterval(poll, POLL_MS);

    // On resize, rebuild pages so cards-per-page recalculates.
    var resizeT = null;
    window.addEventListener('resize', function () {
      if (resizeT) clearTimeout(resizeT);
      resizeT = setTimeout(function () {
        if (lastRacersForDiff.length) {
          rebuildPages(lastRacersForDiff.slice());
          showPage(0);
          startAutoAdvance();
        }
      }, 200);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start);
  } else {
    start();
  }
})();
