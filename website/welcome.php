<?php

// Public splash page for soapboxderbynet.com — served at the bare host
// (Caddy redirects "/" to "/derbynet/welcome.php").
//
// Static HTML. No DB include, no session check, no JS. Just an overview of
// the project with a single primary CTA into the tenant picker.

$cloud_mode = isset($_SERVER['DERBYNET_CLOUD_MODE']) ? $_SERVER['DERBYNET_CLOUD_MODE'] : '';
?><!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>SoapboxDerbyNet — Race day, on one screen</title>
<meta name="description" content="A complete race-management system for soapbox derby events. Timing, brackets, kiosks, and spectator feeds, all coordinated by hardware that just works."/>
<link rel="icon" type="image/png" href="img/derbynet.png"/>
<link rel="stylesheet" type="text/css" href="css/global.css"/>
<style>
  :root {
    --w-navy-deep:  #011a3d;
    --w-navy:       #023882;
    --w-navy-soft:  #0c2b5e;
    --w-cream:      #f7f4ec;
    --w-cream-edge: #ece6d4;
    --w-ink:        #1c2433;
    --w-ink-soft:   #4b5566;
    --w-line:       rgba(255, 255, 255, 0.12);
  }

  html, body { margin: 0; padding: 0; }
  body {
    font-family: var(--font-stack, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif);
    color: var(--w-ink);
    background: var(--w-cream);
    line-height: 1.55;
    -webkit-font-smoothing: antialiased;
  }

  a { color: inherit; }
  img { display: block; max-width: 100%; height: auto; }

  /* ---------- Top bar ---------- */
  .w-top {
    background: var(--w-navy-deep);
    color: #fff;
    border-bottom: 2px solid var(--w-line);
  }
  .w-top-inner {
    max-width: 1180px;
    margin: 0 auto;
    padding: 14px 24px;
    display: flex;
    align-items: center;
    gap: 16px;
  }
  .w-wordmark {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    font-weight: 700;
    font-size: 17px;
    letter-spacing: 0.01em;
    text-decoration: none;
    color: #fff;
  }
  .w-wordmark img {
    width: 32px; height: 32px;
    border-radius: 6px;
    box-shadow: 0 0 0 1px rgba(255,255,255,0.12);
  }
  .w-wordmark .accent { color: var(--w-accent, #F7D117); }
  .w-top-spacer { flex: 1; }
  .w-top-link {
    color: rgba(255,255,255,0.86);
    text-decoration: none;
    font-size: 14px;
    font-weight: 500;
    padding: 6px 12px;
    border-radius: 6px;
    transition: color 120ms ease, background 120ms ease;
  }
  .w-top-link:hover { color: #fff; background: rgba(255,255,255,0.06); }

  /* ---------- Hero ---------- */
  .w-hero {
    position: relative;
    background:
      radial-gradient(120% 80% at 85% 20%, #144585 0%, var(--w-navy-deep) 60%),
      var(--w-navy-deep);
    color: #fff;
    overflow: hidden;
  }
  .w-hero::before {
    /* yellow starting-line stripe near top of the hero band */
    content: "";
    position: absolute;
    left: 0; right: 0; top: 0;
    height: 3px;
    background: var(--color-accent, #F7D117);
  }
  .w-hero-inner {
    max-width: 1180px;
    margin: 0 auto;
    padding: 72px 24px 64px;
    display: grid;
    grid-template-columns: 1.15fr 1fr;
    gap: 48px;
    align-items: center;
  }
  .w-eyebrow {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-family: ui-monospace, "SF Mono", Menlo, monospace;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--color-accent, #F7D117);
    margin: 0 0 18px;
  }
  .w-eyebrow .dot {
    width: 8px; height: 8px; border-radius: 50%;
    background: #4ade80;
    box-shadow: 0 0 0 4px rgba(74,222,128,0.18);
  }
  .w-h1 {
    margin: 0 0 18px;
    font-size: clamp(2.1rem, 4.6vw, 3.6rem);
    line-height: 1.05;
    letter-spacing: -0.015em;
    font-weight: 800;
    color: #fff;
  }
  .w-h1 .hl {
    color: var(--color-accent, #F7D117);
    /* underline that doesn't look like a link */
    background-image: linear-gradient(transparent 70%, rgba(247, 209, 23, 0.28) 70%);
    background-repeat: no-repeat;
    background-size: 100% 100%;
    padding: 0 2px;
  }
  .w-sub {
    margin: 0 0 28px;
    font-size: clamp(1.05rem, 1.35vw, 1.2rem);
    color: rgba(255,255,255,0.86);
    max-width: 36em;
  }
  .w-cta-row {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 16px;
    margin-top: 8px;
  }
  .w-cta {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: var(--color-accent, #F7D117);
    color: var(--w-navy-deep);
    font-weight: 700;
    font-size: 1.05rem;
    text-decoration: none;
    padding: 14px 22px;
    border-radius: 10px;
    box-shadow: 0 1px 0 rgba(0,0,0,0.10),
                0 6px 18px -6px rgba(247,209,23,0.55);
    transition: transform 120ms ease, box-shadow 120ms ease;
  }
  .w-cta:hover {
    transform: translateY(-1px);
    box-shadow: 0 1px 0 rgba(0,0,0,0.10),
                0 8px 22px -6px rgba(247,209,23,0.70);
  }
  .w-cta:focus-visible {
    outline: none;
    box-shadow: 0 0 0 3px rgba(247,209,23,0.55),
                0 6px 18px -6px rgba(247,209,23,0.55);
  }
  .w-cta-secondary {
    color: rgba(255,255,255,0.78);
    text-decoration: none;
    font-size: 0.95rem;
    border-bottom: 1px solid rgba(255,255,255,0.22);
    padding-bottom: 2px;
  }
  .w-cta-secondary:hover { color: #fff; border-color: #fff; }

  .w-hero-art {
    position: relative;
    justify-self: center;
  }
  .w-hero-art img {
    width: 100%;
    max-width: 440px;
    border-radius: 18px;
    box-shadow:
      0 0 0 1px rgba(255,255,255,0.10),
      0 30px 60px -20px rgba(0,0,0,0.55),
      0 10px 24px -8px rgba(0,0,0,0.40);
  }
  .w-timer {
    position: absolute;
    bottom: -14px;
    left: -14px;
    background: var(--w-navy-deep);
    border: 1px solid rgba(255,255,255,0.20);
    border-radius: 8px;
    padding: 8px 12px;
    font-family: ui-monospace, "SF Mono", Menlo, monospace;
    font-size: 14px;
    font-weight: 600;
    color: var(--color-accent, #F7D117);
    letter-spacing: 0.05em;
    box-shadow: 0 6px 14px -4px rgba(0,0,0,0.5);
  }
  .w-timer .label {
    display: block;
    font-size: 9px;
    letter-spacing: 0.18em;
    color: rgba(255,255,255,0.55);
    margin-bottom: 2px;
    font-weight: 500;
  }

  /* ---------- Features band ---------- */
  .w-features {
    background: var(--w-cream);
    padding: 72px 24px 56px;
    border-top: 1px solid var(--w-cream-edge);
  }
  .w-features-inner {
    max-width: 1180px;
    margin: 0 auto;
  }
  .w-features-head {
    text-align: center;
    margin: 0 auto 40px;
    max-width: 640px;
  }
  .w-section-eyebrow {
    font-family: ui-monospace, "SF Mono", Menlo, monospace;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--w-navy);
    margin: 0 0 10px;
  }
  .w-section-title {
    margin: 0 0 12px;
    font-size: clamp(1.5rem, 2.4vw, 2rem);
    font-weight: 700;
    letter-spacing: -0.01em;
    color: var(--w-ink);
  }
  .w-section-sub {
    margin: 0;
    color: var(--w-ink-soft);
    font-size: 1.05rem;
  }
  .w-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 20px;
  }
  .w-card {
    background: #fff;
    border: 1px solid var(--w-cream-edge);
    border-radius: 14px;
    padding: 22px 22px 24px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.03);
    transition: transform 160ms ease, box-shadow 160ms ease, border-color 160ms ease;
  }
  .w-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 18px -6px rgba(2,56,130,0.18);
    border-color: rgba(2,56,130,0.20);
  }
  .w-card-icon {
    width: 40px; height: 40px;
    border-radius: 10px;
    background: linear-gradient(180deg, #eaf0fa 0%, #dbe6f5 100%);
    color: var(--w-navy);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 14px;
  }
  .w-card-icon svg { width: 22px; height: 22px; }
  .w-card h3 {
    margin: 0 0 6px;
    font-size: 1.0625rem;
    font-weight: 700;
    color: var(--w-ink);
    letter-spacing: -0.005em;
  }
  .w-card p {
    margin: 0;
    color: var(--w-ink-soft);
    font-size: 0.95rem;
    line-height: 1.55;
  }

  /* ---------- Pinny lineup band ---------- */
  .w-lineup {
    background: var(--w-cream);
    padding: 8px 24px 64px;
  }
  .w-lineup-inner {
    max-width: 1180px;
    margin: 0 auto;
  }
  .w-lineup-cars {
    display: grid;
    grid-template-columns: repeat(6, 1fr);
    gap: 12px;
    align-items: end;
    padding: 24px 8px 0;
    border-top: 1px dashed rgba(2,56,130,0.18);
  }
  .w-lineup-cars img {
    width: 100%;
    max-width: 140px;
    margin: 0 auto;
    filter: drop-shadow(0 6px 6px rgba(0,0,0,0.10));
    transition: transform 200ms ease;
  }
  .w-lineup-cars img:hover { transform: translateY(-3px); }

  /* ---------- Closing CTA band ---------- */
  .w-close {
    background:
      radial-gradient(120% 80% at 15% 20%, #144585 0%, var(--w-navy-deep) 60%),
      var(--w-navy-deep);
    color: #fff;
    padding: 64px 24px;
    text-align: center;
  }
  .w-close-inner {
    max-width: 720px;
    margin: 0 auto;
  }
  .w-close h2 {
    margin: 0 0 14px;
    font-size: clamp(1.6rem, 2.6vw, 2.2rem);
    font-weight: 800;
    letter-spacing: -0.01em;
  }
  .w-close p {
    margin: 0 0 28px;
    color: rgba(255,255,255,0.86);
    font-size: 1.05rem;
  }

  /* ---------- Footer ---------- */
  .w-foot {
    background: var(--w-navy-deep);
    color: rgba(255,255,255,0.62);
    border-top: 1px solid var(--w-line);
    padding: 20px 24px;
    font-size: 13px;
  }
  .w-foot-inner {
    max-width: 1180px;
    margin: 0 auto;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 12px;
  }
  .w-foot a {
    color: rgba(255,255,255,0.86);
    text-decoration: none;
    border-bottom: 1px dotted rgba(255,255,255,0.3);
  }
  .w-foot a:hover { color: #fff; border-color: #fff; }
  .w-foot-spacer { flex: 1; }

  /* ---------- Responsive ---------- */
  @media (max-width: 960px) {
    .w-hero-inner {
      grid-template-columns: 1fr;
      padding: 56px 24px 48px;
      gap: 36px;
    }
    .w-hero-art { order: -1; }
    .w-hero-art img { max-width: 320px; }
    .w-grid { grid-template-columns: repeat(2, 1fr); }
    .w-lineup-cars { grid-template-columns: repeat(4, 1fr); }
    .w-lineup-cars > :nth-child(n+5) { display: none; }
  }

  @media (max-width: 560px) {
    .w-top-inner { padding: 12px 16px; }
    .w-hero-inner { padding: 44px 18px 40px; }
    .w-features { padding: 56px 18px 40px; }
    .w-lineup { padding: 4px 18px 48px; }
    .w-close { padding: 52px 18px; }
    .w-grid { grid-template-columns: 1fr; }
    .w-lineup-cars { grid-template-columns: repeat(3, 1fr); }
    .w-lineup-cars > :nth-child(n+4) { display: none; }
    .w-hero-art img { max-width: 260px; }
    .w-cta { width: 100%; justify-content: center; }
  }

  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { transition: none !important; }
  }
</style>
</head>
<body>

<header class="w-top">
  <div class="w-top-inner">
    <a class="w-wordmark" href="/">
      <img src="img/derbynet.png" alt=""/>
      <span>Soapbox<span class="accent">DerbyNet</span></span>
    </a>
    <div class="w-top-spacer"></div>
    <a class="w-top-link" href="tenant-picker.php">Open the App &rarr;</a>
  </div>
</header>

<main>

<section class="w-hero" aria-label="Introduction">
  <div class="w-hero-inner">
    <div class="w-hero-text">
      <p class="w-eyebrow"><span class="dot" aria-hidden="true"></span>Live &middot; soapboxderbynet.com</p>
      <h1 class="w-h1">The whole <span class="hl">race&nbsp;day</span>,<br/>on one screen.</h1>
      <p class="w-sub">
        Follow your racer, watch the brackets unfold, and catch every finish.
        SoapboxDerbyNet is the race system that connects timers, displays, and
        phones across the venue &mdash; coordinated by hardware that just works.
      </p>
      <div class="w-cta-row">
        <a class="w-cta" href="tenant-picker.php">
          Open the Race Console <span aria-hidden="true">&rarr;</span>
        </a>
        <a class="w-cta-secondary" href="#what">What you'll find inside</a>
      </div>
    </div>
    <div class="w-hero-art">
      <img src="Images/SoapBox/emblem.png" alt="Soap box derby illustration: kids racing wooden cars down a tree-lined street"/>
      <div class="w-timer" aria-hidden="true">
        <span class="label">LAST FINISH</span>
        01:23.456
      </div>
    </div>
  </div>
</section>

<section class="w-features" id="what" aria-label="What's inside">
  <div class="w-features-inner">
    <div class="w-features-head">
      <p class="w-section-eyebrow">What's inside</p>
      <h2 class="w-section-title">A full race-day operations stack.</h2>
      <p class="w-section-sub">Everything from the start gate to the awards table, talking
        to each other in real time.</p>
    </div>

    <div class="w-grid">
      <article class="w-card">
        <span class="w-card-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="13" r="8"/>
            <path d="M12 9v4l2.5 2.5"/>
            <path d="M9 1h6"/>
            <path d="M12 1v3"/>
          </svg>
        </span>
        <h3>Hardware-coordinated timing</h3>
        <p>Start gates, finish gates, and signs all talk over MQTT. No
          missed heats, no scribbling on clipboards.</p>
      </article>

      <article class="w-card">
        <span class="w-card-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M3 5h4l3 4-3 4H3z"/>
            <path d="M3 11h4l3 4-3 4H3z"/>
            <path d="M14 9h7"/>
            <path d="M14 15h7"/>
          </svg>
        </span>
        <h3>Tournament formats that fit</h3>
        <p>Round-robins, single- and double-elimination, configurable per
          class. Brackets generated from the schedule you actually run.</p>
      </article>

      <article class="w-card">
        <span class="w-card-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="4" width="18" height="13" rx="2"/>
            <path d="M8 21h8"/>
            <path d="M12 17v4"/>
            <path d="M7 9h10"/>
            <path d="M7 12h6"/>
          </svg>
        </span>
        <h3>Live kiosks &amp; LED signs</h3>
        <p>On-deck, standings, and emergency announcements broadcast to
          every screen and sign across the venue.</p>
      </article>

      <article class="w-card">
        <span class="w-card-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="7" y="2" width="10" height="20" rx="2"/>
            <path d="M11 18h2"/>
            <path d="M9 6h6"/>
          </svg>
        </span>
        <h3>Spectator stats &amp; My Races</h3>
        <p>Public, token-gated pages so families can follow a pinny from
          the bleachers, the car park, or three time zones over.</p>
      </article>

      <article class="w-card">
        <span class="w-card-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M4 14a6 6 0 0 1 12 0"/>
            <path d="M2 17h16"/>
            <path d="M18 7a4 4 0 0 1 4 4"/>
            <path d="M18 3a8 8 0 0 1 8 8"/>
            <circle cx="6" cy="20" r="1.5"/>
            <circle cx="14" cy="20" r="1.5"/>
          </svg>
        </span>
        <h3>Works on-site, syncs to the cloud</h3>
        <p>The race-day Pi runs the show even with no internet. This server
          is the always-on twin &mdash; for the spectator feed and remote
          standings.</p>
      </article>

      <article class="w-card">
        <span class="w-card-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M9 19c-4 .5-4-2-6-2.5"/>
            <path d="M15 22v-3a3 3 0 0 0-1-2.3c3-.3 6-1.3 6-6 0-1.2-.5-2.3-1.2-3.2.1-.3.5-1.6-.1-3.3 0 0-1-.3-3.2 1.2a11.2 11.2 0 0 0-6 0C7.2 3.4 6.2 3.7 6.2 3.7c-.6 1.7-.2 3 -.1 3.3A4.6 4.6 0 0 0 4.9 10.2c0 4.7 3 5.7 6 6a3 3 0 0 0-1 2.3V22"/>
          </svg>
        </span>
        <h3>Open source, built on DerbyNet</h3>
        <p>Forked from <a href="https://derbynet.org" target="_blank" rel="noopener">DerbyNet</a> by
          Jeff Piazza, extended for soapbox derby. MIT licensed.</p>
      </article>
    </div>
  </div>
</section>

<section class="w-lineup" aria-label="Race lineup">
  <div class="w-lineup-inner">
    <div class="w-lineup-cars" aria-hidden="true">
      <img src="Images/SoapBox/centuries/000-series.png" alt=""/>
      <img src="Images/SoapBox/centuries/100-series.png" alt=""/>
      <img src="Images/SoapBox/centuries/300-series.png" alt=""/>
      <img src="Images/SoapBox/centuries/500-series.png" alt=""/>
      <img src="Images/SoapBox/centuries/600-series.png" alt=""/>
      <img src="Images/SoapBox/centuries/800-series.png" alt=""/>
    </div>
  </div>
</section>

<section class="w-close" aria-label="Get started">
  <div class="w-close-inner">
    <h2>Spin up a sandbox and poke around.</h2>
    <p>Each sandbox is an isolated database on this server. Try the
      coordinator UI, generate a schedule, push a virtual heat through &mdash;
      nothing you do touches anyone else's data.</p>
    <a class="w-cta" href="tenant-picker.php">
      Open the Race Console <span aria-hidden="true">&rarr;</span>
    </a>
  </div>
</section>

</main>

<footer class="w-foot">
  <div class="w-foot-inner">
    <span>
      Built on <a href="https://github.com/jeffpiazza/derbynet" target="_blank" rel="noopener">DerbyNet</a>
      by Jeff Piazza
    </span>
    <span aria-hidden="true">&middot;</span>
    <span>MIT License</span>
    <div class="w-foot-spacer"></div>
    <span>soapboxderbynet.com</span>
  </div>
</footer>

</body>
</html>
