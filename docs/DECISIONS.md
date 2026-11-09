# Decision log

Each entry records the date, the decision, the reason and the alternatives considered. Newest entries go at the bottom.

## D-001 · 2026-11-09 · Browser demo runs a TypeScript port of the core

Decision: The pure-math core (heart-rate resampling, ECTemp filter, PSI, WBGT, heat index, baseline and heat-adjusted prediction) is ported to TypeScript for the web demo. Python is the reference implementation. Python generates golden JSON fixtures that both pytest and vitest assert against, and CI fails on any mismatch.

Reason: The run file must stay on the device, and the core algorithms are small. A port with parity tests keeps the page light on mobile data.

Alternatives considered: Pyodide running the Python package in the browser (rejected: a download in the 10 MB class with numpy). Server-side analysis (rejected: the file would leave the device).

## D-002 · 2026-11-09 · Baseline predictor is pluggable; Riegel is the default

Decision: Finish-time baselines come from a predictor interface. Riegel's formula is the built-in default. PaceBrain (github.com/lauurnce/pacebrain) is wrapped as an optional extra so that torch is never a hard dependency of the core library.

Reason: The core library should install in seconds and run anywhere. PaceBrain adds a learned baseline for users who have it.

Alternatives considered: torch as a hard dependency (rejected: install size and build time). Riegel only (rejected: loses the better baseline when available).

## D-003 · 2026-11-09 · Forecast data from Open-Meteo, fetched from the browser, with venue presets

Decision: Hourly forecast fields (temperature, humidity, wind, shortwave radiation, pressure) come from Open-Meteo. The web demo calls it directly from the browser. Users pick a venue from presets such as MOA grounds, BGC, UP Diliman, Filinvest City and Clark. Attribution is shown as required by the data license.

Reason: No API key, hourly resolution, the fields needed for a physics-based WBGT model, and browser access so no server sees the request together with a run file. PAGASA publishes no public hourly forecast API.

Alternatives considered: Keyed providers such as OpenWeather or Tomorrow.io (rejected for v0.1: key management and a server proxy). A server-side proxy (rejected: puts a server between the user and the forecast with no benefit).

## D-004 · 2026-11-09 · Heat adjustment from Ely 2007 and Mantzios 2022, with an extrapolation flag

Decision: Slowdown is modeled as a function of WBGT and baseline pace from Ely et al. 2007 for the marathon and Mantzios et al. 2022 for shorter distances. The uncertainty interval combines baseline uncertainty, between-study spread and an extrapolation penalty that grows with WBGT beyond the studied range. Every prediction carries an extrapolated flag. No numeric acclimatization term in v0.1.

Reason: The published data mostly cover temperate races with WBGT below about 25 C. Manila race mornings sit at 25 to 30 C. The product must say when it is extrapolating rather than hide it.

Alternatives considered: A single-study model (rejected: distance-specific effects differ). A numeric acclimatization factor (rejected for v0.1: no sourced effect size for this population and use case).

## D-005 · 2026-11-09 · Single repository

Decision: One repository holds the Python package at the root (src/blagden), the Next.js app in web/, and documentation in docs/.

Reason: Golden fixtures, documentation and releases stay in one place and one history.

Alternatives considered: Separate repositories for library and web (rejected: fixture sharing and versioning overhead). Python under a python/ folder (rejected: the library is the primary artifact).

## D-006 · 2026-11-09 · The 2022 elite-athlete validation is located before it is cited

Decision: The study reporting reduced sensitivity of heart-rate core temperature estimation above 39.0 C in elite athletes is located and read, and the citation is reviewed before it appears in code, docs or UI.

Reason: Science-first rule. No citation from memory.

Alternatives considered: Cite from memory (rejected).

## D-007 · 2026-11-09 · LLM wording is optional, provider-agnostic and off by default

Decision: The race-morning brief is template-based. An optional LLM pass rewrites the wording behind a provider setting (for example openai or anthropic) with no provider SDK as a hard dependency. A validator rejects any output containing a number that was not computed and falls back to the template. The feature is off by default and built in a late phase.

Reason: The brief must never invent numbers. The template path is sufficient for v0.1.

Alternatives considered: LLM-first brief (rejected: unverifiable numbers). No LLM at all (deferred, kept as the default behaviour).

## D-008 · 2026-11-09 · MIT license

Decision: The repository is licensed under the MIT License, copyright 2026 Lawrence Panes.

Reason: Simple, permissive, compatible with the dependencies planned.

Alternatives considered: Apache-2.0 (patent clause not needed here). AGPL-3.0 (would discourage reuse by clubs and organizers).

## D-009 · 2026-11-09 · Daily commit window is Asia/Manila time

Decision: The per-day commit count is measured against midnight Asia/Manila (UTC+8, no DST), computed explicitly rather than from the machine clock.

Reason: The count must not depend on the machine's timezone setting. macOS abbreviates Philippine Standard Time as PST, which is easy to mistake for Pacific time, so the window is derived from UTC plus eight hours.

Alternatives considered: Machine local time (works while the machine stays on Asia/Manila, but breaks silently if the timezone changes).
