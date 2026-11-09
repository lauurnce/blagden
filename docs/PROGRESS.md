# Progress

Build steps B1 to B14. One step per working session. Each step ends with a gate review before the next starts.

## Day 1
- [x] B1 Project understanding: restatement, hard parts, assumptions, risks, open questions, non-goals
- [x] B2 Repository setup: license, gitignore, brief, decision log, progress checklist, first push

## Day 2
- [ ] B3 Science specification: docs/SCIENCE.md with every method, equation, parameter and threshold sourced; decision entries for each recommendation

## Day 3
- [ ] B4 Python package scaffold: uv project, pyproject, pytest, ruff, CI, docs/ARCHITECTURE.md
- [ ] B5 Run file ingestion: .fit, .gpx and .tcx readers, 1-minute heart-rate resampling, quality flags, synthetic fixtures

## Day 4
- [ ] B6 Core temperature estimation: ECTemp extended Kalman filter with cited parameters and tests
- [ ] B7 Physiological Strain Index, per-minute confidence, and the above-39.0 C caveat on results

## Day 5
- [ ] B8 Forecast client: Open-Meteo hourly fields, venue presets, solar position
- [ ] B9 WBGT from forecast (Liljegren 2008), heat index on the PAGASA scale, sports-medicine risk categories

## Day 6
- [ ] B10 Baseline predictors: Riegel and the PaceBrain adapter as an optional extra
- [ ] B11 Heat-adjusted prediction with uncertainty range and extrapolation flag

## Day 7
- [ ] B12 Race-morning brief: templates, numeric validator, optional LLM wording, CLI

## Day 8
- [ ] B13 Web app: Next.js scaffold, TypeScript core port, golden parity tests, in-browser demo

## Day 9
- [ ] B14 Landing page, README, validation plan, SCIENCE.md review, release 0.1.0
