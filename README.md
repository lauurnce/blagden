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
