<a href="https://blagden.vercel.app">
  <img src="docs/assets/blagden-hero.svg" width="100%" alt="Blagden banner: a runner on a Manila race morning as the sun rises, heart rate pulsing, and an estimated core temperature curve climbing past 39.0 C. Click to open the live demo.">
</a>

# Blagden

Heat intelligence for runners in the tropics: core temperature from your heart rate, race-morning WBGT for Metro Manila venues, and a heat-adjusted pace plan.

[![CI](https://github.com/lauurnce/blagden/actions/workflows/ci.yml/badge.svg)](https://github.com/lauurnce/blagden/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](pyproject.toml)
[![Live demo](https://img.shields.io/badge/demo-blagden.vercel.app-f0b35e.svg)](https://blagden.vercel.app)

The banner is animated. Click it, or open [blagden.vercel.app](https://blagden.vercel.app), to try the live demo: drop in a run file and watch the estimate build, minute by minute, on your own device.

<a href="https://blagden.vercel.app/demo"><img src="docs/screenshots/demo-readme.png" width="720" alt="The run file demo with a synthetic 30-minute run loaded: summary figures, the limitation note, and a chart of estimated core temperature and heart rate."></a>

## Why

A Manila race morning is often above 26 C with humidity over 80 percent before the gun goes off, and the sun is up within the first hour. In that air sweat evaporates slowly, so a pace that feels easy in the cool can push core temperature high. Blagden puts numbers on that for a runner: how hot your body likely ran, how hot race morning will be, and what pace that heat allows.

## The name

In January and April 1775, the physician Charles Blagden walked into a room heated above 260 F, about 127 C. Eggs beside the thermometer roasted hard in about twenty minutes. A beefsteak, with bellows blowing on it, was "pretty well done in thirteen minutes." Blagden walked out after eight minutes. He credited perspiration, "that cooling evaporation," with part of that. His host, George Fordyce, found the catch: in damp air, sweat cannot evaporate. A Manila race morning is the damp room. ([Blagden 1775](https://doi.org/10.1098/rstl.1775.0048), [free scan](https://archive.org/details/jstor-106218))

## Quickstart

You need [uv](https://docs.astral.sh/uv/). Install the command line tool from this repository:

```sh
uv tool install git+https://github.com/lauurnce/blagden@v0.1.0
blagden --help
```

Or work from a clone, using the synthetic run files that ship with the tests:

```sh
git clone https://github.com/lauurnce/blagden.git
cd blagden
uv sync
uv run blagden analyze tests/fixtures/synthetic_loop.gpx
```

**1. Estimate core temperature from a run file.** Real output for the synthetic 30-minute run:

```text
$ blagden analyze tests/fixtures/synthetic_loop.gpx
                synthetic_loop.gpx
┌────────────────────┬───────────────────────────┐
│ duration           │ 0:30:00                   │
│ distance           │ 5.02 km (computed)        │
│ heart rate         │ mean 147, max 174 bpm     │
│ minutes            │ 30 (missing heart rate 0) │
│ core temp start    │ 37.00 C (assumed)         │
│ core temp peak     │ 38.28 C at 0:29:00        │
│ minutes > 38.5 C   │ 0                         │
│ peak PSI           │ 6.5                       │
│ resting HR for PSI │ 70 bpm (default)          │
└────────────────────┴───────────────────────────┘
Note: Core temperature is estimated from heart rate alone with the ECTemp method. In 101 elite athletes exercising in heat it agreed with
measured core temperature within about +/- 0.45 C on average, but detected fewer than half of the readings above 39.0 C (de Korte et al.
2022). It is an indication of thermal strain, not a measurement, and not a basis for a safety decision.
```

**2. Forecast race-morning heat stress for a venue.** Bonifacio Global City, 04:00 to 08:00. Forecast values change as the date gets closer:

```text
$ blagden forecast --lat 14.550806 --lon 121.050972 --date 2026-11-15 --from 04:00 --to 08:00
                           Race morning 2026-11-15 (forecast), Manila time
┏━━━━━━━┳━━━━━━━┳━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┓
┃ hour  ┃ air C ┃ RH % ┃ heat index C ┃ PAGASA  ┃ WBGT C ┃ flag  ┃ WA 2020        ┃ humid-corrected ┃
┡━━━━━━━╇━━━━━━━╇━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━┩
│ 04:00 │ 26.4  │ 85   │ 29           │ Caution │ 24.8   │ red   │ Caution        │ moderate        │
│ 05:00 │ 26.5  │ 84   │ 29           │ Caution │ 24.8   │ red   │ Caution        │ moderate        │
│ 06:00 │ 26.9  │ 81   │ 30           │ Caution │ 24.9   │ red   │ Caution        │ moderate        │
│ 07:00 │ 27.6  │ 78   │ 31           │ Caution │ 27.5   │ red   │ Warning        │ high            │
│ 08:00 │ 28.4  │ 73   │ 32           │ Caution │ 29.1   │ black │ Severe Warning │ high            │
└───────┴───────┴──────┴──────────────┴─────────┴────────┴───────┴────────────────┴─────────────────┘
WBGT model error is about +/- 1 C. The heat index assumes shade, rest and a light wind; WBGT counts the sun on a globe and the evaporation
off a wick. On a sunny morning WBGT can sit in a higher band than the heat index suggests. Training insight, not a go or no-go decision.
Weather data by Open-Meteo.com (CC BY 4.0)
```

**3. Predict a heat-adjusted finish time.** A half marathon at BGC from a recent 55-minute 10 km:

```text
$ blagden predict --distance 21.0975 --recent-time 0:55:00 --recent-distance 10 \
    --race-date 2026-11-15 --lat 14.550806 --lon 121.050972
                                                  Prediction for 21.0975 km on 2026-11-15
┌────────────────────────────┬─────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ baseline                   │ 2:01:21 (riegel)                                                                                            │
│ heat-adjusted              │ 2:12:49                                                                                                     │
│ range                      │ 2:08:59 to 2:17:20                                                                                          │
│ race WBGT (time on course) │ 25.7 C                                                                                                      │
│ baseline WBGT              │ 10.0 C (assumed)                                                                                            │
│ level                      │ nonelite                                                                                                    │
│ extrapolated               │ yes                                                                                                         │
│ gun / predicted finish     │ 05:00 / 07:12                                                                                               │
│ main driver                │ Main driver: heat. The race WBGT 25.7 C is 15.7 C above the 10.0 C baseline (assumed); at 0.60% per C for   │
│                            │ non-elite runners that adds 0:11:27 (9.4%). This is beyond the conditions in the studies, so the range is   │
│                            │ wide.                                                                                                       │
└────────────────────────────┴─────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
WBGT model error is about +/- 1 C. The heat index assumes shade, rest and a light wind; WBGT counts the sun on a globe and the evaporation
off a wick. On a sunny morning WBGT can sit in a higher band than the heat index suggests. Training insight, not a go or no-go decision.
Weather data by Open-Meteo.com (CC BY 4.0)
```

Every command takes `--json` for machine-readable output, `--out` for PNG and SVG charts, and `--report` for a Markdown report. `blagden brief` writes the race-morning brief from the same numbers.
