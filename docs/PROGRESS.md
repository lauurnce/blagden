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
- [x] B6 Ingest: FIT, GPX and TCX readers; one cleaned table with timezone-aware UTC times; cleaning report; one-minute resampling without filled heart rate; summary command

## Day 4
- [x] B7 Core temperature and strain: ECTemp filter with sourced parameters, PSI, per-run strain summary with the limitation note, `strain` command, golden fixtures and their generator. Deferred: constants registry, per-minute confidence labels

## Day 5
- [x] B8 Heat stress forecast: Open-Meteo client with retries and disk cache, solar position, Liljegren WBGT, heat index on the PAGASA scale, risk labels, `race_morning` and its command; recorded responses; oracle tests against thermofeel. Deferred: venue presets

## Day 6
- [x] B9 Merged into B8 (WBGT, heat index and risk were built in the same phase). lwbgt oracle not added

## Day 7
- [x] B10 Heat-adjusted prediction: Riegel, manual and PaceBrain baselines with Riegel fallback; heat adjustment with range, flags and main driver; race-window WBGT; back-test script with a synthetic CSV

## Day 8
- [x] B11 Race-morning brief: Facts, English and Taglish templates, grounding check, optional LLM provider with template fallback, `brief` command, COPY_REVIEW.md; templates shipped in the wheel. Pending: Lawrence's copy approval
- [x] B11b CLI, charts and reports: analyze, forecast, predict and brief with Rich tables and --json; core temperature and WBGT charts as PNG and SVG; --report Markdown bundles; exit codes 1, 2, 3

## Day 9
- [x] B12 Core port: TypeScript ECTemp, PSI, solar, WBGT, heat index, risk, strain and race-morning table; browser ingest for GPX, TCX and FIT; golden parity for every module

## Day 10
- [x] B13 Browser demo: /demo with on-device analysis and privacy test, /forecast with cited venue presets, keyboard and axe AA checks, Playwright end-to-end tests. Deferred: brief view, CSP header, first Vercel deploy

## Day 11
- [ ] B14 Landing page, README, SCIENCE.md review, validation plan, release 0.1.0 (40 to 60)
