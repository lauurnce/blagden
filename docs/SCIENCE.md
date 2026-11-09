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

## 1. ECTemp: core temperature from sequential heart rate

### Purpose

Estimate core body temperature $CT_t$ minute by minute from heart rate alone, using the extended Kalman filter published by Buller et al. (2013). This is the only physiological estimate Blagden makes from a run file. Everything downstream (the Physiological Strain Index in section 3, the limitations shown to the user) depends on it.

### Source status

The 2013 paper in Physiological Measurement is paywalled, and only its abstract could be read. Every equation and parameter below was read from three independent places that agree with one another: US patent US10702165B2 (assignee US Army), whose description reproduces the 2013 model development text and its MATLAB appendix; Hunt et al. (2019), an open-access paper co-authored by Buller that restates the six equations; and several independent open-source implementations. Values are tagged VERIFIED on that basis. Equation numbering as printed in the journal is not known and is not used here.

### Equations

Heart rate is reduced to one-minute means. Where samples are more frequent than one per minute the mean of the minute is used; where they are less frequent, values are linearly interpolated (patent text).

Time update (state model). Core temperature is modelled as a random walk:

$$\hat{CT}_t = CT_{t-1}$$

$$\hat{v}_t = v_{t-1} + \gamma^2$$

Observation model. Heart rate is a quadratic function of core temperature plus Gaussian noise:

$$HR_t = b_2\,CT_t^2 + b_1\,CT_t + b_0 + g,\qquad g \sim N(0,\sigma^2)$$

Linearisation (derivative of the observation model at the predicted state):

$$c_t = 2 b_2\,\hat{CT}_t + b_1 = -9.1428\,\hat{CT}_t + 384.4286$$

Kalman gain:

$$k_t = \frac{\hat{v}_t\,c_t}{c_t^2\,\hat{v}_t + \sigma^2}$$

Measurement update:

$$CT_t = \hat{CT}_t + k_t\left(HR_t - \left(b_2\,\hat{CT}_t^2 + b_1\,\hat{CT}_t + b_0\right)\right)$$

$$v_t = (1 - k_t\,c_t)\,\hat{v}_t$$

### Parameters

| Symbol | Value | Unit | Meaning | Read from | Status |
|---|---|---|---|---|---|
| $a_1$, $a_0$ | 1, 0 | none, deg C | time-update coefficients (identity) | US10702165B2; Hunt 2019 | VERIFIED |
| $\gamma$ | 0.022 | deg C per minute (standard deviation) | process noise | US10702165B2 text and MATLAB appendix; Hunt 2019 | VERIFIED, see note 1 |
| $\gamma^2$ | 0.000484 | deg C squared | variance added per minute | same | VERIFIED |
| $b_0$ | -7887.1 | bpm | observation intercept | US10702165B2; Hunt 2019; independent code copies | VERIFIED |
| $b_1$ | 384.4286 | bpm per deg C | observation linear term | same | VERIFIED |
| $b_2$ | -4.5714 | bpm per deg C squared | observation quadratic term | same | VERIFIED |
| $\sigma$ | 18.88 | bpm (standard deviation) | observation noise; "mean standard deviation for the binned heart rate = 18.88 +/- 3.78" | US10702165B2; Hunt 2019 | VERIFIED |
| $\sigma^2$ | 356.4544 | bpm squared | gain denominator term | same | VERIFIED |
| $\Delta t$ | 1 | minute | time step | US10702165B2; USARIEM product page | VERIFIED |
| $CT_0$, $v_0$ with a measured start | measured value, 0 | deg C, deg C squared | "the initial variance was set to zero indicating high confidence in these values" | US10702165B2 | VERIFIED |
| $CT_0$, $v_0$ with no measurement | 37.0, 0.01 | deg C, deg C squared | "set an initial ECTemp (e.g., a resting deep body temperature of 37.0 C) and set v = 0.01" | Hunt 2019 (Buller co-author) | VERIFIED (secondary) |
| $CT_0$ = 37.1 | 37.1 | deg C | often quoted default; attributed by Falcone 2024 to Buller 2015 (Ergonomics), which could not be read | Falcone 2024 | UNVERIFIED |

Note 1. The same patent gives $\gamma$ = 0.022 in the model-fitting text and in the MATLAB appendix, but its figure captions for an elite-runner example refer to "the original Tcore variance gamma = 0.024". The fitting text and code are taken as authoritative. The discrepancy is recorded here so it is not rediscovered later.

Derived quantities (arithmetic from the verified coefficients, not read from a source): the observation quadratic peaks at $CT = -b_1 / (2 b_2)$ = 42.04 deg C, where it predicts 194.4 bpm. Above that temperature the model predicts heart rate falling with temperature, which the authors call incorrect (US12426839B2). At a constant heart rate the estimate converges to the temperature that solves $b_2 CT^2 + b_1 CT + b_0 = HR$ on the rising branch, for example about 38.0 deg C for 120 bpm, 39.0 deg C for 152 bpm, and 39.3 deg C for 160 bpm.

### Valid input ranges

- Heart rate as one-minute means, in beats per minute, from a chest or wrist sensor. The development data used an Equivital EQ02 sensor; the authors do not say "chest strap".
- Development data: 17 male US Army volunteers (age 23 +/- 4 years), 24 to 36 deg C air temperature, 42 to 97 percent relative humidity, core temperatures 36.0 to 40.0 deg C. Validation: 83 volunteers, 150 sessions, more than 52,000 observations, across laboratory and field studies with varied clothing, hydration and acclimation.
- Stated validity in later work: acceptable up to 38.5 deg C in protective clothing (Hunt 2019); tracked measured temperature up to 40.0 deg C in a hot group of Royal Marines recruits (Buller 2020, abstract).
- Heart rates above 194 bpm cannot map to a higher temperature in this model, and estimates below 36 deg C require heart rates below 27 bpm (US12426839B2).

### Validation statistics (2013)

| Quantity | Value | Read from | Status |
|---|---|---|---|
| Bias | -0.03 +/- 0.32 deg C | 2013 abstract | VERIFIED (primary abstract) |
| 95 percent limits of agreement | +/- 0.63 deg C | 2013 abstract | VERIFIED (primary abstract) |
| Weighted mean RMSE | 0.30 +/- 0.13 deg C | US10702165B2; USARIEM page | VERIFIED |
| Reference comparison | esophageal versus rectal methods average limits of agreement of +/- 0.58 deg C | 2013 abstract | VERIFIED |

### Limitations

- Population: young, fit, mostly male soldiers. The model has "no adjustment for height, weight, body composition, fitness, or age" (US10702165B2). Performance is expected to degrade as fitness deviates from the training data (US12426839B2).
- Heart rate is the only input. In running, heart rate is driven by pace as well as heat, so the estimate rises toward the steady-state temperature for the sustained heart rate whatever the true core temperature is doing. Falcone et al. (2024) report that heart-rate models "overestimate CT for very high work rates" and underestimate at low work rates.
- The authors state the assumption of normally distributed heart rate "has the effect of slightly under and over estimating the rate of rise of core body temperature for low and high core body temperatures respectively" (US10702165B2).
- Sensitivity above 39.0 deg C is low in elite athletes (de Korte et al. 2022, section 2). That finding was obtained with the sigmoid variant below, which the authors describe as giving nearly identical estimates to the quadratic at higher temperatures, so it is taken to apply to both.
- Starting value: with $v_0 = 0$ the gain is tiny at first and the estimate barely moves for several minutes. A start without a measurement should use the small non-zero variance recommended by Hunt et al. (2019).
- The patent reports a larger process noise ($\gamma$ = 0.043) fitted to elite distance runners. No parameter has been fitted to recreational runners in humid heat; Blagden does not individualise parameters in v0.1.

### Later revisions and the choice for v0.1

Looney et al. (2018) replaced the quadratic with a generalised logistic (sigmoid) observation model to improve resting estimates. The fitted form, read from US patent US12426839B2 (Buller and Looney), is

$$HR_t = 41 + \frac{152}{\left(1 + 0.06\,e^{-0.89\,(\hat{CT}_t - 37.84)}\right)^{1/0.07}}$$

with the time update, process noise and observation noise unchanged. The abstract reports a smaller resting bias (-0.04 vs -0.19 deg C) and RMSE (0.26 vs 0.35 deg C) and states that the sigmoid produces "nearly identical estimates to the original quadratic equation at higher CT". The typeset form of its derivative is garbled in the patent HTML and has not been verified; the full text of Looney 2018 could not be read. Status: parameters VERIFIED (patent), derivative UNVERIFIED.

Blagden v0.1 implements the 2013 quadratic model. Reasons: every parameter is verified from three agreeing sources; running heart rates sit far above the resting range where the sigmoid differs; and the sigmoid derivative needed by the filter is not yet verified. The sigmoid is recorded here so it can be added as a labelled variant once its derivative is checked against the patent PDF or the Looney paper.

Related later work, recorded for completeness: Buller et al. (2020) found the estimate tracked measured temperature up to 40.0 deg C in a hot group but overestimated in a warm group (bias 0.34 deg C) and proposed a correction factor (abstract only). Buller et al. (2023, 2025) introduced an adaptive Physiological Strain Index that uses skin temperature as well; it needs a sensor Blagden does not have.

### References

- Buller MJ, Tharion WJ, Cheuvront SN, Montain SJ, Kenefick RW, Castellani J, Latzka WA, Roberts WS, Richter M, Jenkins OC, Hoyt RW. Estimation of human core temperature from sequential heart rate observations. Physiological Measurement 2013;34(7):781-798. https://doi.org/10.1088/0967-3334/34/7/781 (abstract read; full text paywalled)
- US Patent US10702165B2, Estimation of human core temperature from sequential heart rate observations. https://patents.google.com/patent/US10702165B2/en (reproduces the 2013 model text and MATLAB appendix)
- Hunt AP, Buller MJ, Maley MJ, Costello JT, Stewart IB. Validity of a noninvasive estimation of deep body temperature when wearing personal protective equipment during exercise and recovery. Military Medical Research 2019;6:20. https://doi.org/10.1186/s40779-019-0208-7 ; open text at https://pmc.ncbi.nlm.nih.gov/articles/PMC6567444/
- Looney DP, Buller MJ, Gribok AV, Leger JL, Potter AW, Rumpler WV, Tharion WJ, Welles AP, Friedl KE, Hoyt RW. Estimating resting core temperature using heart rate. Journal for the Measurement of Physical Behaviour 2018;1(2):79-86. https://doi.org/10.1123/jmpb.2017-0003 (abstract read)
- US Patent US12426839B2 (Buller, Looney), sigmoid observation model. https://patents.google.com/patent/US12426839B2/en
- Buller MJ, Delves SK, Fogarty AL, Veenstra BJ. On the real-time prevention and monitoring of exertional heat illness in military personnel. Physiological Measurement 2020;41:065011. https://doi.org/10.1088/1361-6579/ab934b (abstract read)
- Buller MJ, Tharion WJ, Duhamel CM, Yokota M. Real-time core body temperature estimation from heart rate for first responders wearing different levels of personal protective equipment. Ergonomics 2015;58(11):1830-1841. https://doi.org/10.1080/00140139.2015.1036792 (abstract read)
- Falcone T, et al. Biphasic Kalman filter for core temperature estimation. Frontiers in Public Health 2024;12:1219595. https://doi.org/10.3389/fpubh.2024.1219595
- USARIEM, Core body temperature algorithm product page. https://usariem.health.mil/index.cfm/research/products/cbt_algorithm

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
