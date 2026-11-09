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

## 7. Weather data: Open-Meteo

### Purpose

Blagden needs an hourly forecast for a race venue and a matching historical archive for later validation. The variables are the inputs to the WBGT model in section 4 and to the heat index in section 5: air temperature, humidity, wind, solar radiation and pressure. Open-Meteo provides both without an API key under a non-commercial free tier. Every item below was read from the official documentation on 2026-11-09 unless marked otherwise.

### Endpoints

| Purpose | Endpoint | Status |
|---|---|---|
| Forecast, hourly, 7 days by default, up to 16 | `https://api.open-meteo.com/v1/forecast` | VERIFIED |
| Historical reanalysis: ERA5 0.25 deg from 1940, ERA5-Land 0.1 deg from 1950, ECMWF IFS 9 km from 2017; ERA5 updated daily with a 5 day delay | `https://archive-api.open-meteo.com/v1/archive` | VERIFIED |
| Archived forecasts (same models and parameters as the forecast API), coverage from about 2021 or 2022 | `https://historical-forecast-api.open-meteo.com/v1/forecast` | VERIFIED |

The documentation states: "Time always starts at 0:00 today and contains 168 hours. If &forecast_days=16 is set, up to 16 days of forecast can be returned."

### Variables

Hourly variable names, units and valid time, as given in the Hourly Parameter Definition table of the forecast documentation. Default units are shown; `wind_speed_unit=ms` switches wind to metres per second and `temperature_unit` and `precipitation_unit` exist as well.

| Variable | Unit | Valid time | Use in Blagden | Status |
|---|---|---|---|---|
| `temperature_2m` | deg C | instant | dry bulb for WBGT; heat index | VERIFIED |
| `relative_humidity_2m` | % | instant | WBGT; heat index | VERIFIED |
| `dew_point_2m` | deg C | instant | cross-check of humidity | VERIFIED |
| `wind_speed_10m` | km/h (m/s on request) | instant | WBGT, after conversion to 2 m (section 4) | VERIFIED |
| `shortwave_radiation` | W/m2 | preceding hour mean | global horizontal irradiance | VERIFIED |
| `direct_radiation` | W/m2 | preceding hour mean | direct beam fraction | VERIFIED |
| `diffuse_radiation` | W/m2 | preceding hour mean | direct beam fraction | VERIFIED |
| `shortwave_radiation_instant`, `direct_radiation_instant`, `diffuse_radiation_instant` | W/m2 | instant | irradiance at the hour mark | VERIFIED (names from the docs' instant-variable row and page controls) |
| `surface_pressure` | hPa | instant | psychrometrics in WBGT | VERIFIED |
| `pressure_msl` | hPa | instant | not used (sea level, not site) | VERIFIED |
| `cloud_cover`, `cloud_cover_low`, `cloud_cover_mid`, `cloud_cover_high` | % | instant | display only | VERIFIED |
| `precipitation` | mm | preceding hour sum | display only | VERIFIED |
| `weather_code` | WMO code | instant | display only | VERIFIED |
| `wet_bulb_temperature_2m` | UNVERIFIED | UNVERIFIED | not used; Blagden computes natural wet bulb itself | option exists in the request builder but has no row in the definition table |

Wind is offered at 10, 80, 120 and 180 m in the forecast API and at 10 and 100 m in the archive. There is no 2 m wind, and the documentation gives no height-conversion guidance. Conversion is Blagden's job and is specified in section 4.

Radiation convention, quoted from the documentation: "Most weather variables are given as an instantaneous value for the indicated hour. Some variables like precipitation are calculated from the preceding hour as an average or sum." and "All solar radiation parameters can be expressed as instantaneous values by accounting for the solar zenith angle at a specific moment."

### Time handling

- `timezone`: any name from the time zone database, or `auto`. Quoted: "The requested timezone 's UTC offset at request time is returned as utc_offset_seconds and used for ISO 8601 timestamps and daily boundaries throughout the response. Daylight saving time (DST) changes within the requested range are ignored." The Philippines observes no DST, so a fixed offset is exact for `Asia/Manila`.
- `timeformat`: `iso8601` (default, fixed offset) or `unixtime` (seconds since 1970-01-01 00:00 UTC).
- Ranges: `forecast_days` 0 to 16 (default 7), `past_days` 0 to 92, `start_date` and `end_date` as `yyyy-mm-dd`, `start_hour` and `end_hour` as `yyyy-mm-ddThh:mm`.
- 15-minute data (`minutely_15`) is native only in Central Europe and North America; elsewhere it is interpolated from hourly. For the Philippines it adds no information.

### Models

The default `best_match` combines models by region. The documented region table ends with "Everywhere else: Global models only", built on "a global backbone of DWD ICON, NOAA GFS and ECMWF IFS". The Philippines is not named in the documentation; its coverage by global models at 9 to 25 km resolution is inferred from that table and was confirmed by one live request for Manila on 2026-11-09, which returned data from the ECMWF, GFS, ICON, JMA GSM, CMA, GEM, UKMO and Meteo-France global models. Elevation is downscaled with a 90 m digital elevation model by default.

### Rate limits

Free tier, quoted from the terms: "Less than 10'000 API calls per day, 5'000 per hour and 600 per minute." The pricing page adds a monthly limit of 300,000 calls. Weighting: "Requests for data covering more than 10 weather variables or extending over a period of more than 2 weeks for a single location are considered multiple API calls", with fractional counting. Limits are "applied by IP addresses and application", and the terms warn: "If you are using providers like Vercel, Netlify, Render, or Google Sheets you might be rate-limited earlier then expected." A request from the runner's browser counts against the runner's address, not against one shared server.

### Terms and attribution

- Free API is for non-commercial use only, defined by reference to Creative Commons. Commercial examples given: "Websites or apps that have subscriptions or display advertisements."
- Data licence: CC BY 4.0. Required: "You must include a link next to any location Open-Meteo data are displayed", with the example `Weather data by Open-Meteo.com` linking to https://open-meteo.com/.
- No API key for non-commercial use. No warranty: "The accuracy and completeness of the data products and their uninterrupted provision are not guaranteed by Open-Meteo".
- CORS: the project README states "CORS supported". A live response on 2026-11-09 carried `access-control-allow-origin: *` (observed, not documented).

### Valid input ranges

Latitude and longitude in decimal degrees. Venue presets in Blagden are fixed coordinates in Metro Manila and Clark. Forecast horizon up to 16 days; race-morning briefs use the final 1 to 3 days before the race when forecasts are most skilful (skill statement is general meteorological practice, not an Open-Meteo claim).

### Limitations

- Global models at 9 to 25 km cannot resolve coastal and urban microclimates within Metro Manila. Treat venue-level WBGT as an area estimate.
- Solar radiation and wind are model fields and are the least certain inputs to WBGT.
- No 2 m wind; the conversion in section 4 adds uncertainty.
- ERA5 lags real time by 5 days, so validation against race results uses the archive, not the forecast.
- No uptime guarantee on the free tier.

### References

- Open-Meteo forecast API documentation: https://open-meteo.com/en/docs
- Historical weather API: https://open-meteo.com/en/docs/historical-weather-api
- Historical forecast API: https://open-meteo.com/en/docs/historical-forecast-api
- Terms: https://open-meteo.com/en/terms
- Licence: https://open-meteo.com/en/licence
- Pricing and limits: https://open-meteo.com/en/pricing
- Source and README: https://github.com/open-meteo/open-meteo
