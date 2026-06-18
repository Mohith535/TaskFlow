# Changelog

All notable changes to TaskFlow. The project follows a phase-based roadmap —
see the README's "What's Built & What's Coming" for the bigger picture.

## v9.0.0 — Hardening & Themes

A milestone release: the dashboard becomes fully themeable, and the codebase gets a
security and quality pass.

### Added
- **Theme system** — four built-in themes (Midnight default, Terminal, Paper, Slate)
  plus a **custom theme builder** (live color pickers, save / reset), under
  **OPERATOR M → Theme**. The choice persists and is applied before first paint (no flash).
- Per-theme particle-background colour and data-visualisation tokens (`--viz-*`),
  including Slate's deliberately muted urgency colours for users who read high-alarm
  red as stress rather than signal.

### Changed
- **Web dashboard split into static assets** — CSS → `task_manager/static/dashboard.css`,
  JS → `task_manager/static/dashboard.js`; `web_ui.py` is now a thin HTML shell
  (~6,300 → ~860 lines).
- **Single source of truth** — the server now computes `pressure_level`, `is_overdue`,
  `duration_minutes`, and `priority_tier` and ships them in the API; the dashboard
  consumes them instead of re-deriving the same logic (with a safe local fallback).
- All colours moved to CSS custom properties / `color-mix()`, so themes drive rendering.

### Security & quality
- CSRF Origin + Host-header validation on mutating endpoints; a Content-Security-Policy
  on the dashboard; `/static/` path-traversal fix.
- Output escaping for user task content in the UI; safe link `href` schemes only.
- Hosts-file domain sanitisation; removed `shell=True` from the focus blocker.
- Removed the Google-Fonts CDN call — the **100% offline** promise is now verifiable
  (zero outbound network calls).
- Corrupt `tasks.json` now auto-restores from the newest good backup instead of
  silently resetting; `~/.taskflow` is created with private (0700) permissions on POSIX.
- New `taskflow doctor --repair` fixes non-standard duration values in place.
- Logging writes to `~/.taskflow/taskflow.log` (was a stray relative path);
  removed the redundant `setup.py` (`pyproject.toml` is the canonical packaging source).

## v8.5.0 — Phase 2 complete

- Daily Execution Path (energy-curve scheduling), Time Integrity Score,
  Focus Window Lock, and the weekly behavioural review + day-of-week analytics.
- Grouped `taskflow list`, humane overdue dates ("OVERDUE — Apr 27"), Control Center reorder.

## v8.0.0 — Phase 1 complete

- The full behavioral execution engine: duration estimation, soft/hard deadlines,
  the execution-pressure system, the Today view + 90-minute Now Window, missed-task
  forced confrontation, the postpone mirror, smart reminders, Recovery Mode, and
  task enrichment (notes / links / checklist).
