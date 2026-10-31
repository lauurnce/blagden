# Changelog

All notable changes to Blagden are listed here. The format follows Keep a Changelog, and versions follow Semantic Versioning.

## [0.1.0] - 2026-10-31

First release. Training insight, not medical advice.

### Added

- **Ingest.** Readers for .fit, .gpx and .tcx run files with heart rate; one cleaned table with timezone-aware UTC times; a cleaning report; one-minute resampling that never fills in missing heart rate.
- **Core temperature.** The ECTemp extended Kalman filter (Buller et al. 2013) with sourced parameters, and the Physiological Strain Index (Moran et al. 1998). A per-run strain summary with the limitation from de Korte et al. 2022 shown wherever a core temperature appears.
- **Heat stress forecast.** Open-Meteo client with retries and an on-disk cache; solar position; Liljegren WBGT; the heat index on the PAGASA scale; race flag bands, the ACSM 2007 table, World Athletics 2020 bands and a humidity-corrected risk; a race-morning table for any venue and hour window.
- **Heat-adjusted prediction.** Riegel baseline by default, an optional PaceBrain baseline with Riegel fallback, and a heat adjustment from Ely et al. 2007 and Mantzios et al. 2022 with a range, an extrapolated flag and the main driver.
- **Race-morning brief.** English and Taglish templates built only from computed numbers, a grounding check, and an optional, off-by-default LLM wording step with no provider SDK required.
- **CLI.** `analyze`, `forecast`, `predict`, `brief`, `summary` and `version`, with Rich tables, `--json`, PNG and SVG charts, and Markdown reports.
- **Web.** A TypeScript port of the core with golden parity tests against the Python reference; `/demo`, which analyses a run file on the device and never uploads it; `/forecast` with cited venue presets; a landing page at `/`, deployed at https://blagden.vercel.app.
- **Docs.** SCIENCE.md with every equation, parameter and threshold and its source; ARCHITECTURE.md; DECISIONS.md; a pre-registered validation plan; CITATION.cff.

### Known limitations

- The heart-rate method is less sensitive above 39.0 C core temperature.
- Predictions for recreational runners in Manila heat extrapolate beyond the published race data and are flagged as such.
- No acclimatisation term, no PSI strain bands, and no Content Security Policy yet.

[0.1.0]: https://github.com/lauurnce/blagden/releases/tag/v0.1.0
