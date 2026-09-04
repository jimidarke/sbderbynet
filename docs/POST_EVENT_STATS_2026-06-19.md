# Post-Event Stats — 2026-06-19 Friday Practice (Ad-hoc Mode)

Snapshot captured **2026-06-26**. The St-Albert 2026 main event was rain-cancelled;
the **Friday-evening practice (2026-06-19)** ran in ad-hoc "come-as-you-are" mode and
was the only live racing. The cloud spectator page (token-gated) was kept **live until
2026-06-29** at the user's request (QR codes in the wild), so these numbers are a
point-in-time read of an event that is still being viewed.

**Nothing was changed to capture this** — read-only audit only. Token remains locked,
no log rotation forced, live system left as-is.

---

## 1. Race results (saved locally — complete)

Exported the evening of the practice (2026-06-19 20:52 local) to:

```
/home/jimi/derby-adhoc-results-2026-06-19/
  ├── adhoc_leaderboard_2026-06-19.csv   (67 racers)
  └── adhoc_results_2026-06-19.csv       (116 runs)
```

| File | Rows | Schema |
|------|------|--------|
| leaderboard | 67 racers | `age_group, pinny, best_time, total_runs` (best single time per age group) |
| results | 116 runs | `heat, lane, pinny, age_group, finishtime, status` (every run) |

Both are **PII-free** (pinny numbers only — per `feedback_public_stats_no_pii`).

**Data sanity:**
- Fastest *real* timed run = **20.329 s** (heat 45, pinny 76). All times climb from there.
- **No erroneous 11–12 s reads in the saved export** — checked explicitly; zero rows in the
  10.000–12.999 s band in either file.
- One `no_time` row (heat 45, pinny 99 — DNF/no-read) and at least one timeout-style
  ceiling value (99.999 s) are present; discount these in any podium math.

> Note: although the saved CSV is clean of the bad fast times, those reads **were** visible
> on the live spectator page during the practice (see feedback #4 below). The export and the
> live page were not identical.

---

## 2. Audience feedback (persisted JSONL — complete, nothing rotated away)

Source: `website/feedback-submit.php` → `/var/lib/derbynet/feedback/feedback.jsonl`
(host: `/opt/derbynet/production/data/feedback/feedback.jsonl`).
Standalone unauthenticated endpoint; never touches the race DB. Stores IP/UA for
forensic post-mortem only — never displayed.

Full dump archived locally: `tmp/derby-feedback-2026-06-26.jsonl`
(retrieve again any time via `scripts/derbyvps.sh feedback dump`).

**7 raw submissions, 5 unique devices.** Genuine audience notes (timestamps in MDT):

| When (MDT) | Note | Disposition |
|---|---|---|
| Mon Jun 15, 4:28 PM | "you guys are awesome" | pre-practice; positive |
| Fri Jun 19, 7:42 PM | "DIAGNOSTIC verify after fix - organizers may ignore" | **our own test entry** (curl/8.5.0, device `diag-verify-after-fix`) — ignore |
| Fri Jun 19, 7:43 PM | "This didn't suck" | positive |
| Fri Jun 19, 7:50 PM | "The 8s and 11s may not be accurate" | **timer-accuracy flag** (submitted ×2) |
| Fri Jun 19, 8:43 PM | "It's missing his fastest heat!" | **data-completeness flag** (submitted ×2) |

**Two actionable signals:**
- 🔴 *"The 8s and 11s may not be accurate"* — a spectator independently flagged the
  erroneous fast finish-timer reads (false-trigger / double-fire territory). Confirms the
  bad times were live-visible even though they were absent from the saved CSV.
- 🟡 *"It's missing his fastest heat!"* — a parent reported a racer's best run not showing in
  the My-Races view. Unverified: could be a real data-completeness gap, or that run was one
  of the discarded `no_time`/ceiling rows. Not yet checked against the Pi's `adhoc.sqlite3`.

(The double-submissions are the same device firing twice within ~2 s — the "one note per
person" gate is client-side localStorage only; the server records every POST by design.)

---

## 3. Spectator-page hits — ⚠️ PARTIAL (rotation gap over the peak)

**Gotcha:** Caddy access logs live only in Docker's `json-file` stdout, capped at
`max-size 10m × max-file 3` (~30 MB). On a busy site this rotates fast. At capture time the
**oldest retained access entry was 2026-06-20 15:36 UTC (~9:36 AM MDT Saturday)**.

➡️ **The Friday-3PM → Saturday-9:36AM window — the busiest stretch, during and right after
the practice — had already rotated out and is unrecoverable.** The feedback file survived
(real file); the hit logs did not (container stdout). **Friday peak attendance numbers are
gone.**

For the window that *was* still retained (Sat Jun 20 09:36 MDT → Fri Jun 26):

- **4,276 total requests**, of which **3,424 were `version.txt` freshness auto-polls**.
  Actual page loads: **457 `.html`**. 0 feedback POSTs in-window.
- **109 unique visitor IPs** across the ~6 days.
- Host: `live.soapboxderbynet.com` (token path `bea32bfcdd26bedf8303cc33`).

| Day | Requests | Unique visitors |
|---|---:|---:|
| Jun 20 (partial, from 09:36 MDT) | 1,633 | 30 |
| Jun 21 | 613 | 27 |
| Jun 22 | 1,405 | 30 |
| Jun 23 | 317 | 17 |
| Jun 24 | 126 | 19 |
| Jun 25 | 128 | 17 |
| Jun 26 (partial) | 54 | 10 |

**Takeaway:** even a week after the rain-cancelled main event, ~10–30 distinct devices/day
were still opening the QR page — supporting the decision to keep the token live to Jun 29.

---

## Follow-ups (not done — recorded for later)

- [ ] Verify the "missing fastest heat" complaint against the Pi `adhoc.sqlite3` (read-only).
- [ ] **Next event:** persist Caddy access logs outside Docker's 30 MB rotation (e.g. log to a
      bind-mounted file or bump `max-file`) so peak-attendance counts survive. The single
      biggest data loss here was the Friday-evening hit volume.
- [ ] Finish-timer accuracy: the spectator-flagged 8 s/11 s false reads remain an open
      hardware item for the next live run.
