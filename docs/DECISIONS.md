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

## D-010 · 2026-11-09 · Open-Meteo request shape for race-morning WBGT

Decision: Request hourly values with `timezone=Asia/Manila`, `wind_speed_unit=ms`, and these variables: `temperature_2m`, `relative_humidity_2m`, `dew_point_2m`, `wind_speed_10m`, `surface_pressure`, `cloud_cover`, `shortwave_radiation_instant`, `direct_radiation_instant`, `diffuse_radiation_instant`. Compute WBGT at each hour mark from instantaneous values only, and interpolate between hour marks for display. Convert 10 m wind to 2 m in Blagden (section 4 of docs/SCIENCE.md). Use `surface_pressure`, not `pressure_msl`. Keep requests at or below 10 variables and 16 days so each counts as one call.

Reason: The documentation gives temperature, humidity, wind and pressure as instantaneous values at the indicated hour, while default radiation is the mean of the preceding hour. Mixing an instant temperature with a preceding-hour radiation mean would pair the wrong sun with the right air at dawn, when irradiance changes fastest. The instant radiation variables keep all inputs consistent at one moment. Philippine time has no daylight saving, so the fixed offset is exact. Open-Meteo's terms note that requests routed through Vercel may be rate-limited earlier, which supports the browser-direct call chosen in D-003.

Alternatives considered: Preceding-hour mean radiation with hour-ending labels (rejected: inconsistent with the instantaneous air variables). The provider's own `wet_bulb_temperature_2m` (rejected: undocumented unit and valid time in the definition table, and it is a psychrometric wet bulb, not the natural wet bulb that WBGT needs). 15-minute data (rejected: interpolated from hourly outside Europe and North America).

## D-011 · 2026-11-09 · ECTemp v0.1 uses the 2013 quadratic observation model

Decision: Implement the Buller et al. (2013) extended Kalman filter with the quadratic heart-rate model and the parameters in section 1 of docs/SCIENCE.md. The 2018 sigmoid observation model is recorded in the spec and deferred to a labelled variant.

Reason: Every quadratic parameter was read from three agreeing sources (a US Army patent reproducing the paper text and MATLAB appendix, an open-access paper co-authored by Buller, and independent code copies). The sigmoid's parameters are verified only from a patent, and the derivative the filter needs is garbled in the patent HTML. The authors state the sigmoid gives nearly identical estimates to the quadratic at higher temperatures, which is where running heart rates sit.

Alternatives considered: Sigmoid as default (rejected for now: derivative unverified). Re-fitted parameters for runners from the patent's elite-runner example (rejected: a single example, not a validated fit).

## D-012 · 2026-11-09 · ECTemp starting conditions

Decision: When no measured starting temperature is given, start at 37.0 C with variance 0.01, following the recommendation in Hunt et al. (2019). When the user supplies a measured starting temperature, start there with variance 0, as in the 2013 validation. Both are explicit parameters of the estimator.

Reason: The often-quoted 37.1 C default could not be verified from a primary source. With variance 0 and no measurement the gain is near zero for several minutes, so the estimate lags; the small non-zero variance recommended by the authors' group avoids that.

Alternatives considered: 37.1 C with variance 0 (rejected: unverified pairing). 37.0 C with variance 0.02 as used by de Korte et al. (2022) (acceptable; the Buller co-authored recommendation was preferred).

## D-013 · 2026-11-09 · Activity file parsers

Decision: Python reads FIT with fitdecode (MIT), GPX with gpxpy (Apache-2.0) plus a namespace lookup for the Garmin heart-rate extension, and TCX with the standard library XML parser. The browser reads FIT with fit-file-parser (MIT) and GPX and TCX with DOMParser using namespace-aware element lookups. The official Garmin FIT SDKs are not used.

Reason: The Garmin FIT Protocol License is non-sublicensable, forbids making the SDK available to third parties, and excludes safety-related applications; a bundled browser build would redistribute it. The MIT parsers implement the same published profile. TCX is small enough that a dependency adds more risk than code.

Alternatives considered: Garmin SDKs (rejected: licence). python-fitparse (rejected: maintainer points to fitdecode; last release 2020). @we-gold/gpxjs (rejected: keys extensions by prefix rather than namespace). tcx-js (rejected: licence file unavailable, no release since 2019).

## D-014 · 2026-11-09 · PSI is shown as a number without strain categories

Decision: Blagden computes the Physiological Strain Index from the ECTemp estimate and heart rate with the published ceilings of 39.5 C and 180 bpm, baselines of the filter's starting temperature and the user's resting heart rate (default 70 bpm, flagged), and displays the value on the 0 to 10 scale with the anchors "0 = no strain" and "10 = very high strain". No category labels are shown until the original 1998 table has been read. Values above 10 are shown as above scale. The result is labelled "estimated PSI from heart rate".

Reason: The original paper could not be read by automated means and the three secondary bandings disagree. Showing a label whose cut-points cannot be sourced would violate the science-first rule. The number itself rests on a formula confirmed by three independent sources.

Alternatives considered: Adopt the USARIEM slide banding attributed to its slide (possible later, once compared with the 1998 table). Skip PSI in v0.1 (rejected: the number is useful and sourced).

## D-015 · 2026-11-09 · Heat adjustment formula for v0.1

Decision: Predicted time = baseline time x (1 + k x max(0, race WBGT - baseline WBGT)). The slope k is 0.0018 per C for elite runners (baseline marathon-equivalent under 2:30) and 0.0060 per C for everyone else. The interval uses slope ranges 0.0010 to 0.0030 (elite) and 0.0040 to 0.0080 (non-elite), and the upper slope doubles for degrees above 25 C WBGT. Baseline WBGT is taken from the archive when the baseline race is known, otherwise 10 C with a flag. Every result carries level, extrapolation and default flags, and is never shown without its interval. No distance or acclimatisation terms.

Reason: The verified evidence is Ely 2007's quartile means for elite marathoners and the restated slopes for well-trained runners, Mantzios 2022's 0.3 to 0.4 percent per C outside the optimum, and El Helou 2012's accelerating air-temperature losses. A linear model with level-dependent slopes is the most that those numbers support. Recreational runners above 25 C WBGT are outside all of it, so the model widens rather than pretends.

Alternatives considered: Fit El Helou's quadratics directly (rejected: air temperature, not WBGT). Discipline-specific slopes from Mantzios (rejected: elite only and inconsistent in order). A fixed percentage per race (rejected: ignores how hot the morning is).

## D-016 · 2026-11-09 · WBGT by a Liljegren port checked against two oracles

Decision: Blagden implements the Liljegren et al. (2008) WBGT model itself in Python and TypeScript, following the constants and structure of the Argonne C code as recorded in section 4 of docs/SCIENCE.md. The direct-beam fraction comes from the forecast direct and diffuse components. Wind is converted from 10 m to 2 m with the code's stability-class power law. Solar position uses the Astronomical Almanac low-precision formulas the code uses, tested against pvlib's NREL algorithm. Development tests compare both ports with thermofeel's `calculate_wbgt_liljegren` and with lwbgt on a grid of Manila-like conditions, requiring agreement within 0.1 C. The Bureau of Meteorology approximation is not used at all. The Argonne acknowledgment is reproduced in the documentation.

Reason: No JavaScript implementation exists, so a port is unavoidable for the browser. A matching Python port keeps the two in lockstep through golden fixtures. thermofeel and lwbgt are maintained, permissively licensed and independent of each other, which makes them good oracles. The approximation ignores sun and wind, which change most during a race morning, and its authors and two peer-reviewed comparisons say not to use it outdoors.

Alternatives considered: Depend on thermofeel in the core (rejected: no browser path, and it pulls earthkit-meteo). Depend on PyWBGT (rejected: CC BY-NC-SA and unmaintained). Use the Bureau approximation as a fallback (rejected: biased by up to about 5 C in humid heat).

## D-017 · 2026-11-09 · Risk labels shown with WBGT and the heat index

Decision: WBGT is labelled with the five-flag system (white below 10 C, green 10 to 18, yellow 18 to 23, red 23 to 28, black above 28) attributed to the 1996 ACSM distance-running stand as reproduced by race medicine and the IAAF, plus the Racinais 2015 humidity-corrected risk (moderate, high, excessive, interpolated in relative humidity), plus the 2007 ACSM continuous-activity row text and the World Athletics 2020 band name for organisers. The heat index is computed with the NWS Rothfusz procedure, rounded to a whole degree, classified on PAGASA's bands (Caution 27 to 32, Extreme Caution 33 to 41, Danger 42 to 51, Extreme Danger 52 and above) and labelled "heat index on the PAGASA scale". Every label is shown with the number and the model error.

Reason: The flags are what runners see at start lines, and their thresholds are consistent across three independent reproductions. The Racinais table is the only sourced correction for the humidity Manila has. The 2007 table's hottest continuous-activity cells and the 2021 consensus statement could not be verified, so they are quoted where verified and otherwise left out. PAGASA's bands are verified from its own product pages; the formula behind them is the NWS regression, which PAGASA names.

Alternatives considered: World Athletics 2020 bands as primary (rejected: colours unverified and the scheme is less known to runners). ACSM 2021 or 2023 regional categories (rejected: text not retrievable). Shifting thresholds for an acclimatised tropical population (rejected: no sourced values).

## D-018 · 2026-11-09 · Architecture choices beyond the B4 proposal

Decision: Add a `blagden.constants` registry as the only home for sourced numbers, with no UNVERIFIED status and a literal-scan test. Put recording quality flags (gap, interpolated, pause, low support, cadence lock, out of range) on the ingest minute series, and add cadence, distance and segment id to the sample table. Split `weather` into I/O (client, cache) and pure math (solar, wbgt, heatindex, risk) plus venue presets. Port to TypeScript every pure-math module the browser needs (physio, solar, WBGT, heat index, risk, Riegel, heat adjustment, brief rendering), not only the filter. Keep brief templates and venue presets in shared JSON read by both languages, and generate `constants.ts` from the Python registry. Apply mypy strict to `predict` and `constants` as well as `physio` and `weather`.

Reason: The science-first rule needs a mechanical gate, which the registry and literal scan provide. Quality flags describe the recording, so they belong with ingest and travel with the series. The forecast panel runs in the browser (D-003), so its math must exist in TypeScript. Shared inputs and generated constants leave one place to change a number or a sentence. The strict-typing set is the set that is ported, where a type slip is a parity bug.

Alternatives considered: Constants scattered in each module with docstring citations (rejected: nothing enforces it). Quality flags inside physio (rejected: they are not physiology). Port only the filter and compute WBGT on a server route (rejected: contradicts D-003). Duplicate template text in each language (rejected: drift).

## D-019 · 2026-11-09 · Proposed: postpone the PaceBrain adapter to v0.2 (pending approval, would supersede D-002)

Proposal: v0.1 ships the `BaselinePredictor` seam with Riegel and a manual baseline only. The PaceBrain adapter is specified in docs/ARCHITECTURE.md section 5.3 and built in v0.2 once PaceBrain is trained on real runs.

Reason: PaceBrain's own model card states "Do not use these models to plan a real race"; its six inputs come from neither a run file nor a forecast; its dependencies (torch, pandas, scikit-learn, matplotlib, streamlit) are heavy for a 2,561-parameter network; no weights ship; and on its synthetic data the repository's log-linear baseline is twice as accurate. Cost of including it anyway: about 8 commits in B9 with an "experimental" label.

Status: awaiting Lawrence's answer at the B4 gate. Until then D-002 stands.
