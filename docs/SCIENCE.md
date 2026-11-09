# Blagden science specification

This document records every method, equation, parameter and threshold that Blagden implements, together with its source. Code may not use a number that is not listed here with a reference.

## Conventions

- Each section has the same parts: purpose, equations, a parameter table (symbol, value, unit, source), valid input ranges, limitations, and references with DOI or URL.
- Every value is tagged VERIFIED when it was read from the cited source, or UNVERIFIED when it could not be confirmed from a source. UNVERIFIED values must not ship in code.
- Where the primary paper is paywalled, an open source that reproduces the equations is cited next to it, and the table states which one the value was read from.
- Equations use GitHub math syntax: inline `$...$` and display `$$...$$`.
- Units unless stated otherwise: temperature in degrees Celsius, heart rate in beats per minute, time in minutes, wind speed in metres per second, irradiance in watts per square metre, pressure in hectopascals.

## Sections

1. ECTemp: core temperature from sequential heart rate
2. ECTemp validation in elite athletes
3. Physiological Strain Index
4. Outdoor WBGT from forecast weather
5. Heat risk categories for endurance events and the PAGASA heat index
6. Running performance in heat
7. Weather data: Open-Meteo
8. Activity files: FIT, GPX and TCX
