# Progress

Build steps B1 to B14. One build day per real day. Each step ends with a gate review before the next starts. Commit ranges are estimates inside the 50 to 90 target and never over 100 per Asia/Manila day.

## Day 1
- [x] B1 Project understanding: restatement, hard parts, assumptions, risks, open questions, non-goals
- [x] B2 Repository setup: license, gitignore, brief, decision log, progress checklist, first push
- [x] B3 Science specification: docs/SCIENCE.md with every method, equation, parameter and threshold sourced; decision entries for each recommendation
- [x] B4 Architecture and build plan: docs/ARCHITECTURE.md with modules, interfaces, data contracts, parity testing, PaceBrain assessment, testing, tooling, deployment, risks, build plan

## Day 2
- [x] B5 Scaffold: uv project, ruff, mypy, pytest, pre-commit, Makefile, CI; empty package modules; Typer CLI with version; Next.js app with strict TypeScript, Tailwind, eslint, prettier, vitest; synthetic GPX and TCX fixtures

## Day 3
- [ ] B6 Ingest and physiology: constants registry; .fit, .gpx and .tcx readers; 1-minute resampling and quality flags; ECTemp filter, PSI, confidence and caveats; golden fixtures and their generator (70 to 90)

## Day 4
- [ ] B7 Weather client, cache, venues and solar position; recorded Open-Meteo responses (45 to 65)

## Day 5
- [ ] B8 WBGT (Liljegren port), heat index on the PAGASA scale, risk labels; oracle tests against thermofeel and lwbgt (60 to 85)

## Day 6
- [ ] B9 Prediction: baseline predictors (Riegel, manual), runner level, heat adjustment with interval and flags (40 to 60)

## Day 7
- [ ] B10 Brief: facts model, shared templates, renderer, grounding check, optional LLM provider interface (35 to 45)
- [ ] B11 CLI and packaging: Typer commands with JSON output, wheel build, package smoke job (30 to 40)

## Day 8
- [ ] B12 Web scaffold and core port: Next.js, TypeScript port of the pure-math modules, parity tests against the golden fixtures (60 to 85)

## Day 9
- [ ] B13 Web demo: in-browser file analysis, forecast panel, brief view, CSP, Playwright end-to-end test, first Vercel deploy (55 to 80)

## Day 10
- [ ] B14 Landing page, README, SCIENCE.md review, validation plan, release 0.1.0 (40 to 60)
