// results-by-racer scroller.
//
// Renders a single placement-ordered list — last place at the top, 1st place
// at the bottom — that scrolls slowly upward in a seamless loop, revealing the
// winner only near the end of each cycle. CSS-drawn medals (shared component in
// css/kiosks.css), score per the configured scoring method, per-heat time chips.
//
// Lightweight for a Raspberry Pi 3B+: one CSS transform animation (GPU layer),
// one fetch per second, no animation libraries. Rebuilds the track only when the
// results actually change, so an unchanging scroll is never interrupted.
//
// Seamless loop: the track holds TWO identical copies of [rows + one-row gap].
// We measure one copy's height H, set --rr-shift = H, and animate the track
// translateY(0 -> -H) linear infinite. At the end the second copy sits exactly
// where the first began, so the wrap is invisible.

(function () {
  var POLL_MS    = 1000;
  var SPEED_PX_S = 26;     // scroll speed in px/s (lower = slower / more readable)
  var MIN_DUR    = 16;     // seconds
  var MAX_DUR    = 300;    // seconds

  var stage, track, roundEl, emptyEl;
  var lastKey = '';
  var lastTimeFormat = '%.3f';
  var roundLabel = '';
  var fontsReady = false;
  var pendingSnap = null;

  function numCar(r) { var n = parseInt(r.carnumber, 10); return isNaN(n) ? 0 : n; }

  function formatMs(ms, fmt) {
    if (ms === null || ms === undefined) return '----';
    var m = (fmt || '%.3f').match(/%[0-9]*\.(\d)f/);
    var dp = m ? parseInt(m[1], 10) : 3;
    return (ms / 1000).toFixed(dp);
  }

  // CSS medal disc for 1-3, ordinal pill for 4+, faint pill for unplaced.
  function placeNode(place) {
    var wrap = document.createElement('div');
    wrap.className = 'rr-place';
    var p = parseInt(place, 10);
    var el = document.createElement('span');
    if (!p || p < 1) {
      el.className = 'place-pill place-pill--unplaced';
      el.textContent = '—';
    } else if (p <= 3) {
      el.className = 'medal medal--' + (p === 1 ? 'gold' : p === 2 ? 'silver' : 'bronze');
      el.textContent = String(p);
    } else {
      el.className = 'place-pill';
      var v = p % 100, s = ['th', 'st', 'nd', 'rd'];
      var suf = s[(v - 20) % 10] || s[v] || s[0];
      el.innerHTML = p + '<sup>' + suf + '</sup>';
    }
    wrap.appendChild(el);
    return wrap;
  }

  function buildRow(r) {
    var row = document.createElement('div');
    row.className = 'rr-row';
    if (r.place === 1) row.classList.add('is-first');
    row.setAttribute('data-racerid', r.racerid);

    row.appendChild(placeNode(r.place));

    var pinny = document.createElement('div');
    pinny.className = 'rr-pinny';
    pinny.textContent = '#' + pinnyDisplay(r.carnumber);
    row.appendChild(pinny);

    var name = document.createElement('div');
    name.className = 'rr-name';
    name.textContent = r.name || '';
    row.appendChild(name);

    var score = document.createElement('div');
    score.className = 'rr-score';
    score.textContent = r.score_str || '--';
    row.appendChild(score);

    var heats = document.createElement('div');
    heats.className = 'rr-heats';
    var runs = r.runs || [];
    for (var i = 0; i < runs.length; i++) {
      var run = runs[i];
      var chip = document.createElement('span');
      chip.className = 'rr-chip';
      if (run.finished && r.best_ms !== null && run.time_ms === r.best_ms) chip.classList.add('rr-chip--best');
      if (!run.finished) chip.classList.add('rr-chip--pending');
      chip.textContent = run.finished ? formatMs(run.time_ms, lastTimeFormat) : '--';
      heats.appendChild(chip);
    }
    row.appendChild(heats);
    return row;
  }

  // Order last place (top) -> 1st place (bottom). Unplaced (no finished runs)
  // are "worst", pinned to the very top.
  function sortForScroll(racers) {
    return racers.slice().sort(function (a, b) {
      var pa = a.place, pb = b.place;
      var na = (pa === null || pa === undefined);
      var nb = (pb === null || pb === undefined);
      if (na && nb) return numCar(a) - numCar(b);
      if (na) return -1;
      if (nb) return 1;
      if (pa !== pb) return pb - pa;   // larger place number first (top)
      return numCar(a) - numCar(b);    // stable within a tie
    });
  }

  function buildCopy(racers) {
    var copy = document.createElement('div');
    copy.className = 'rr-scroll-copy';
    for (var i = 0; i < racers.length; i++) copy.appendChild(buildRow(racers[i]));
    var spacer = document.createElement('div');
    spacer.className = 'rr-row rr-spacer';   // one-row gap before the loop repeats
    copy.appendChild(spacer);
    return copy;
  }

  function rebuild(racers) {
    var ordered = sortForScroll(racers);
    track.style.animation = 'none';
    track.innerHTML = '';

    var first = buildCopy(ordered);
    track.appendChild(first);
    var h = first.getBoundingClientRect().height;   // one copy (rows + gap)
    track.appendChild(buildCopy(ordered));          // identical second copy

    var dur = Math.max(MIN_DUR, Math.min(MAX_DUR, h / SPEED_PX_S));
    track.style.setProperty('--rr-shift', h + 'px');
    void track.offsetHeight;                        // reflow so the restart is clean
    track.style.animation = 'rr-scroll ' + dur + 's linear infinite';

    stage.setAttribute('data-state', ordered.length ? 'ready' : 'empty');
    if (emptyEl) emptyEl.style.display = ordered.length ? 'none' : '';
  }

  // Fingerprint over place/score/runs so we only rebuild on a real change
  // (a rebuild restarts the scroll at the top).
  function key(racers) {
    var parts = [];
    for (var i = 0; i < racers.length; i++) {
      var r = racers[i];
      parts.push(r.racerid + ':' + r.place + ':' + r.score + ':' + r.runs_done);
    }
    return parts.join('|');
  }

  function apply(snap) {
    if (!snap || !snap.racers) return;
    lastTimeFormat = snap.time_format || lastTimeFormat;
    if (roundEl) roundEl.textContent = roundLabel || '';
    if (!fontsReady) { pendingSnap = snap; return; }   // measure only once fonts are loaded
    var k = key(snap.racers);
    if (k === lastKey) return;
    lastKey = k;
    rebuild(snap.racers);
  }

  function poll() {
    $.ajax('action.php', {
      type: 'GET',
      data: { query: 'poll.results' },
      cache: false,
      success: function (data) {
        if (data && data.cease) { window.location.href = '../index.php'; return; }
        if (data && data['current-heat']) {
          var ch = data['current-heat'];
          roundLabel = '🏆 ' + (ch['class'] ? ch['class'] + ' · ' : '') + 'Round ' + (ch.round || '');
        }
        if (data && data.racer_summaries) {
          apply({ racers: data.racer_summaries.racers || [], time_format: data.racer_summaries.time_format });
        }
      }
    });
  }

  function start() {
    stage = document.getElementById('rr-stage');
    track = document.getElementById('rr-scroll-track');
    roundEl = document.getElementById('rr-round');
    emptyEl = stage ? stage.querySelector('.rr-empty') : null;
    if (!stage || !track) return;

    if (document.fonts && document.fonts.ready) {
      document.fonts.ready.then(function () {
        fontsReady = true;
        if (pendingSnap) { var s = pendingSnap; pendingSnap = null; apply(s); }
      });
    } else {
      fontsReady = true;
    }

    poll();
    setInterval(poll, POLL_MS);

    var rT = null;
    window.addEventListener('resize', function () {
      if (rT) clearTimeout(rT);
      rT = setTimeout(function () { lastKey = ''; poll(); }, 250);
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
  else start();
})();
