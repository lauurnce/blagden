# Blagden: project brief

Heat intelligence for runners in the tropics.

## Problem

Race-time predictors assume mild weather. Riegel-style formulas and learned models such as PaceBrain are fitted to results from temperate races. In the humid heat of Metro Manila, runners slow down, lose pace control late in a race, and face a real risk of exertional heat illness. Runners can see the PAGASA heat index, but nothing turns the weather forecast plus their own heart rate into decisions about pace, timing and hydration.

## Users

- Primary: Filipino recreational runners, 5K to marathon, who train and race in Metro Manila heat and humidity.
- Secondary: race organizers choosing start times and planning medical coverage.

## Scope for v0.1

1. Read a run file (.fit, .gpx with heart rate, .tcx) and resample heart rate to 1-minute steps.
2. Estimate core body temperature across the run from heart rate alone with the ECTemp method (Buller et al. 2013, an extended Kalman filter), and compute the Physiological Strain Index (Moran et al. 1998) from the estimate and heart rate.
3. Forecast WBGT (wet bulb globe temperature) for a venue and time window, such as race morning 4 to 9 AM, from public forecast data, with risk categories from published sports-medicine guidance. Show the PAGASA heat index category next to it.
4. Predict a heat-adjusted finish time: a baseline from PaceBrain or a Riegel fallback, adjusted for forecast WBGT using published performance-versus-heat findings, with an uncertainty range.
5. Produce a race-morning brief in plain language (pace cap, where to back off, hydration reminders) built only from computed numbers. Template-based by default, with optional LLM wording that is checked so it cannot introduce numbers that were not computed.
6. Ship a Python library and CLI, a web demo that analyzes a run file inside the browser so the file never leaves the device, and a landing page.

## Non-goals for v0.1

- Medical diagnosis or safety guarantees.
- A watch app.
- Training plans.
- User accounts.
- Storing anyone's data.

## Success criteria

- The published methods are implemented faithfully. Every parameter is cited in docs/SCIENCE.md and covered by tests.
- Heat-adjusted predictions beat unadjusted ones on real race results. This is measured later with a running club; v0.1 ships the validation plan, the data schema and the scoring script.
- The landing page and README are accurate enough for a sports scientist and clear enough for a runner.

## Framing

Blagden gives training insight, not medical advice. Wherever a core temperature is shown, the product states that the heart-rate method is less sensitive above 39.0 C core temperature. Every equation, parameter and threshold traces to a cited source. Numbers that cannot be verified from a source are marked as unverified and do not ship.

## Privacy

Run files are processed locally or in the browser and are never uploaded. The only data that leaves the device is the race venue and time window sent to the forecast provider. Test fixtures are synthetic.

## The name

In 1774 and 1775 Charles Blagden, a physician who later became Secretary of the Royal Society, ran experiments in a room heated to about 127 C (260 F). Eggs left in the room roasted hard and a steak cooked in 13 minutes with bellows blowing on it, while the people inside stayed far cooler than the air. Blagden was among the first to state explicitly that sweating is how the body regulates its temperature.

The catch in Manila: in humid air sweat cannot evaporate well, so that cooling partly fails. Blagden the tool exists to measure how much.

Source: Blagden C. Experiments and observations in an heated room. Philosophical Transactions of the Royal Society, 1775. The figures above are to be checked against the primary text before they appear on the landing page.

## Constraints

- Core library: Python 3.12 or newer, package name blagden, managed with uv, tested with pytest.
- Web: Next.js (App Router, TypeScript, Tailwind) deployed on Vercel.
- Science first: sources in docs/SCIENCE.md; decisions in docs/DECISIONS.md; progress in docs/PROGRESS.md.
