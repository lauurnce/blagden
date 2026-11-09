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

## 2. ECTemp validation in elite athletes

### Purpose

Record the independent validation of the heart-rate method in athletes exercising in heat, so that the limitations Blagden shows next to every core temperature estimate carry a citation and exact numbers. All items were read from the open-access primary text.

### Source

de Korte JQ, Veenstra BJ, van Rijswick M, Derksen EJK, Hopman MTE, Bongers CCWG, Eijsvogels TMH. A heart rate based algorithm to estimate core temperature responses in elite athletes exercising in the heat. Frontiers in Sports and Active Living 2022;4:882254. https://doi.org/10.3389/fspor.2022.882254 . PMID 35813051, PMCID PMC9256956. Status: VERIFIED (primary, full text read).

### Study design

| Item | Value | Status |
|---|---|---|
| Participants | 106 Dutch elite athletes completed the protocol; 101 in the analysed cohort (49 male, 52 female) after 3 sensor losses and 2 abnormal temperature curves | VERIFIED |
| Sports | 13 outdoor disciplines, grouped as endurance, mixed, power and skill | VERIFIED (group counts UNVERIFIED) |
| Conditions | "ambient temperature 31.6 +/- 1.0 C, relative humidity 74 +/- 5%, Wet Bulb Globe Temperature 28.6 +/- 0.8 C, ambient vapor pressure 3.45 kPa" | VERIFIED |
| Protocol | cycle ergometer: 20 min warm-up at about 70 percent of maximal heart rate, then workload increased by 5 percent every 3 min to volitional exhaustion; 44 min on average | VERIFIED |
| Reference temperature | ingestible telemetric capsule (myTemp) at 10 s intervals | VERIFIED |
| Heart rate | Polar V800 chest strap at 1 s intervals, reduced to one-minute means | VERIFIED |
| Algorithm | ECTemp with the sigmoid observation model (Looney 2018, Buller 2020), not the 2013 quadratic; coefficients not printed in the paper | VERIFIED |
| Start conditions | fixed start at 37.0 C with starting variance 0.02 | VERIFIED |

### Results

| Quantity | Value | Where in the paper | Status |
|---|---|---|---|
| Correlation, all observations | r = 0.86 | Results | VERIFIED |
| Systematic bias | 0.15 +/- 0.36 C (Results); 0.15 +/- 0.29 C (Abstract) | both; the two standard deviations disagree in the source | VERIFIED, discrepancy noted |
| 95 percent limits of agreement | +/- 0.45 C | Results and Abstract | VERIFIED |
| RMSE | 0.35 +/- 0.18 C | Results and Abstract | VERIFIED |
| Peak temperature agreement (range 37.6 to 40.4 C) | r = 0.57; bias -0.02 +/- 0.47 C; limits of agreement +/- 0.92 C; RMSE 0.47 C | Results | VERIFIED |
| Mean absolute error | not reported | | VERIFIED absent |

Classification performance by estimated-temperature threshold (Table 2, 5,025 observations):

| Threshold | Sensitivity | Status |
|---|---|---|
| 37.75 to 38.75 C | 73 to 96 percent, specificity 72 to 93 percent | VERIFIED |
| above 38.75 C | 73 percent | VERIFIED |
| above 39.0 C | 48 percent (Table 2); rounded to 50 percent in the Abstract; specificity 97 percent | VERIFIED, discrepancy noted |
| above 39.25 C | 13 percent | VERIFIED |
| above 39.5 C | 4 percent | VERIFIED |
| above 39.75 C | 0 percent | VERIFIED |

Quoted finding: "a low to very-low sensitivity (50-0%) for Tc-est thresholds >39.0 C, due to a high prevalence of false-negative observations."

### Authors' explanation and conclusion

- "the assumption of a fixed relationship between the cardiovascular and thermoregulatory system captured by two single parameters (i.e., HR and Tc)" and "the use of a single input parameter (i.e., HR) contains insufficient information to reflect the cumulative thermoregulatory and cardiovascular effects of prolonged exercise in the heat."
- Dehydration shifts the relationship: "if the HR - Tc relationship changes, for example due to the redistribution of blood flow and maintenance of blood pressure following dehydration, ECTemp will likely underestimate or overestimate Tc".
- Conclusion: "the ECTemp algorithm should in its current form, not solely be used to identify (elite) athletes at risk for heat-related disorders due to low sensitivity and high false-negative rate in the upper end of the Tc spectrum." It "can provide a valuable and representative indication of thermal strain in the low- to mid-range of Tc values (37.75-38.75 C)".

### What Blagden shows

Wherever a core temperature estimate is displayed, Blagden states: the estimate is from heart rate alone; in 101 elite athletes exercising in heat the method agreed with measured core temperature within about +/- 0.45 C on average, but detected fewer than half of the observations above 39.0 C; it is an indication of thermal strain, not a measurement, and not a basis for a safety decision. The citation is this paper.

### Valid input ranges and limitations

- The validation covers an incremental cycling test of about 44 minutes in a laboratory at 31.6 C and 74 percent humidity, in elite athletes. Recreational runners, longer durations, outdoor sun and wind, and dehydration over a marathon are outside the validated setting.
- High temperatures were underrepresented in the data: "Especially higher Tc values are underrepresented."
- The reference capsule may lag esophageal temperature at the start of exercise and after intensity changes.
- The paper used the sigmoid variant; Blagden v0.1 uses the quadratic (section 1, D-011). The authors of the sigmoid state the two give nearly identical estimates at higher temperatures, so the high-temperature limitation is taken to apply to both.
- Cooling and recovery were not studied in this paper.

### References

- de Korte JQ et al. Frontiers in Sports and Active Living 2022;4:882254. https://doi.org/10.3389/fspor.2022.882254 ; full text https://www.frontiersin.org/articles/10.3389/fspor.2022.882254/full
- Buller MJ et al. 2013 and Looney DP et al. 2018, Buller MJ et al. 2020: see section 1.

## 3. Physiological Strain Index

### Purpose

Summarise combined thermal and cardiovascular strain on a 0 to 10 scale from core temperature and heart rate relative to a resting baseline. In Blagden the core temperature input is the ECTemp estimate from section 1, so the result is an estimated PSI and inherits the limitations of sections 1 and 2.

### Source status

The primary paper (Moran, Shitzer and Pandolf 1998) is listed as free to read by the publisher but returned access errors to automated requests. Only its abstract was read, through Europe PMC. The equation, input definitions and ceilings below were read from peer-reviewed secondary sources that cite the 1998 paper and from a USARIEM presentation by Buller. The original category table could not be read, so the strain bands are UNVERIFIED.

### Equation

$$PSI_t = 5\,\frac{T_{c,t} - T_{c,0}}{39.5 - T_{c,0}} + 5\,\frac{HR_t - HR_0}{180 - HR_0}$$

Each term contributes 0 to 5 points, "then summed to represent physiological strain on a 10-point scale (0 = no strain, 10 = very high strain)" (Notley et al. 2018). The abstract states: "The index rates the physiological strain on a universal scale of 0-10."

### Parameters

| Symbol | Value | Unit | Meaning | Read from | Status |
|---|---|---|---|---|---|
| 39.5 | 39.5 | deg C | upper limit of rectal temperature: "39.5 indicates that the upper limit of rectal temperature is 39.5 C" | Sun and Dong 2022; Buller USARIEM slides | VERIFIED (secondary) |
| 180 | 180 | bpm | upper limit of heart rate: "180 indicates that the upper limit of the heart rate is 180 bpm" | same | VERIFIED (secondary) |
| 5, 5 | 5 | points | weight of each system | Notley et al. 2018 | VERIFIED (secondary) |
| $T_{c,t}$, $T_{c,0}$ | | deg C | rectal temperature at time t and at time 0 (pre-exposure baseline) | Ko et al. 2020 | VERIFIED (secondary) |
| $HR_t$, $HR_0$ | | bpm | heart rate at time t and at time 0 | Ko et al. 2020 | VERIFIED (secondary) |
| Strain bands | five labels no or little, low, moderate, high, very high | | cut-points differ between sources: a USARIEM slide gives below 5 low, 5 to 6 moderate, 7 to 8 high, 9 to 10 very high, above 10 extreme; a patent table attributed to Moran 1998 pairs 0 to 1, 2 to 3, 4 to 5, 6 to 7, 8 to 9; a 2026 paper uses 0 to 2.9, 3 to 6.9, 7 to 10 | three secondary sources | UNVERIFIED |

### Inputs in Blagden

These are Blagden's conventions, recorded because published implementations silently vary the baselines and ceiling:

- $T_{c,t}$ is the ECTemp estimate for minute t (section 1).
- $T_{c,0}$ is the filter's starting temperature (37.0 deg C by default, or the measured start the user supplied).
- $HR_0$ is the user's resting heart rate. When none is supplied, 70 bpm is used and the result is flagged as using a default baseline. Bernard et al. (2026) fix the same convention: "baseline Tre and HR were taken as 36.5 C and 70 bpm".
- The ceilings 39.5 deg C and 180 bpm are not changed per user in v0.1.
- Negative values are reported as 0. Values above 10 are reported as above scale rather than clamped, since the formula exceeds 10 whenever heart rate passes 180 bpm or the estimate passes 39.5 deg C.

### Valid input ranges

- "The index is suitable in instances in which rectal temperature ranges from 36.5 to 39.5 C and heart rate is between 60 and 180 beats per minute" (Notley et al. 2018).
- Development data: 100 men exercising at 40 deg C and 40 percent relative humidity, walking at 1.34 m/s on a 2 percent grade for 120 min; validation on 7 men in protective clothing (1998 abstract). The abstract states validity still needs "extending ... to women and other age groups".

### Estimated core temperature inside PSI

Using the heart-rate estimate in place of measured temperature is established in field use by the method's authors. A USARIEM presentation reports agreement between PSI from estimated and from measured temperature of bias 0.05 and limits of agreement +/- 1.00 PSI units, and an independent check on 30 US Marines of -0.01 +/- 1.20. The temperature error of about +/- 0.6 deg C therefore becomes roughly +/- 1 point on the 10-point scale. Buller et al. (2025), on 5,080 Marine recruits, report that "Estimated core temperature only identified 23.3% of EHIs" (exertional heat illnesses), while a skin-temperature adapted index identified 86.7 percent. Heart rate also enters both terms when the temperature is itself estimated from heart rate, so the two terms are not independent; this is a structural observation about the combination, not a finding from a source.

### Limitations

- The category bands are unverified until the 1998 table is read. Blagden v0.1 shows the number and the two scale anchors only (D-014).
- Fixed ceilings misrepresent some groups. Buller et al. (2023) found end-of-exercise PSI "too-high" for elite athletes (11.4 +/- 0.8) and "too-low" for workers in encapsulating clothing, and proposed an adaptive critical temperature using skin temperature, which Blagden does not have.
- Male-only development and validation samples.
- Baseline conventions differ across papers; Blagden pins its own above and labels a default baseline when used.
- All limitations of sections 1 and 2 apply, including low sensitivity above 39.0 deg C.

### References

- Moran DS, Shitzer A, Pandolf KB. A physiological strain index to evaluate heat stress. American Journal of Physiology 1998;275(1):R129-R134. https://doi.org/10.1152/ajpregu.1998.275.1.R129 . PMID 9688970. Abstract read via Europe PMC; full text not read.
- Ko Y, et al. Journal of Physiological Anthropology 2020;39:10 (reproduces the equation and input definitions). https://pmc.ncbi.nlm.nih.gov/articles/PMC7158155/
- Sun and Dong 2022 (ceiling definitions). https://pmc.ncbi.nlm.nih.gov/articles/PMC9367783/
- Notley SR, Flouris AD, Kenny GP. On the use of wearable physiological monitors to assess heat strain during occupational heat stress. Applied Physiology, Nutrition, and Metabolism 2018. Copy read at https://togetherforsaferroads.org/wp-content/uploads/sites/341/notley-et-al-2018-on-the-use-of-wearable-physiological-monitors-to-assess-heat-strain-during-occupational-heat-stress.pdf
- Buller MJ. Real-time PSI assessment (USARIEM presentation). https://nrt.org/sites/58/files/RT%20PSI%20Assessment%20-%20M.%20Buller.pdf
- Bernard et al. 2026 (fixed baselines 36.5 C and 70 bpm). https://pmc.ncbi.nlm.nih.gov/articles/PMC13166069/
- Buller MJ, Atkinson E, Driver K, Tharion WJ, Ely BR, Cheuvront SN, Charkoudian N. Individualized monitoring of heat illness risk: novel adaptive physiological strain index. Physiological Measurement 2023;44(10). https://doi.org/10.1088/1361-6579/acf991 (abstract read)
- Buller MJ et al. Skin temperature adapted physiological strain index (aPSI) predicts exertional heat illness. Physiological Measurement 2025;46(11). https://doi.org/10.1088/1361-6579/ae05ae (abstract read)
- Buller MJ, Welles AP, Friedl KE. Wearable physiological monitoring for human thermal-work strain optimization. Journal of Applied Physiology 2018;124(2):432-441. https://doi.org/10.1152/japplphysiol.00353.2017 (abstract read)
- US Patent US11564579B2 (PSI table attributed to Moran 1998; row alignment unverified). https://patents.google.com/patent/US11564579B2/en

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

## 8. Activity files: FIT, GPX and TCX

### Purpose

Read heart rate, time and position from the three common export formats and produce the one-minute heart-rate series that section 1 needs. This section fixes where each value lives, its type and unit, and which parsing libraries Blagden uses. Field types for FIT were read from Garmin's own SDK profile source; GPX and TCX details were read from the published XML schemas; licences were read from each project's LICENSE file.

### FIT (Garmin)

Record messages (global message number 20) hold the time series. The documentation states: "Records contain timestamps with a one-second resolution, although devices may store data at a lower rate. Devices may also use the Smart Recording technique resulting in Record messages being recorded at irregular time intervals." Only the timestamp and one other value are required per record.

| Field | Base type | Scale, offset | Unit | Notes | Status |
|---|---|---|---|---|---|
| `timestamp` (field 253) | uint32 | 1, 0 | s | seconds since the FIT epoch 1989-12-31 00:00:00 UTC; Unix seconds = value + 631065600 | VERIFIED |
| `heart_rate` | uint8 | 1, 0 | bpm | invalid value 0xFF means missing | VERIFIED |
| `position_lat`, `position_long` | sint32 | 1, 0 | semicircles | degrees = semicircles x 180 / 2^31 | unit VERIFIED (profile); formula VERIFIED only from a Garmin developer forum reply, consistent with the sint32 range |
| `distance` | uint32 | 100, 0 | m | stored in centimetres | VERIFIED |
| `speed` | uint16 | 1000, 0 | m/s | stored in mm/s | VERIFIED |
| `enhanced_speed` (field 73) | uint32 | 1000, 0 | m/s | wider range than `speed` | VERIFIED |
| `altitude` | uint16 | 5, 500 | m | | VERIFIED |
| `enhanced_altitude` (field 78) | uint32 | 5, 500 | m | | VERIFIED |
| `cadence` | uint8 | 1, 0 | rpm | | VERIFIED |

Scale and offset rule, quoted from the protocol document: "the binary quantity is divided by the scale factor and then the offset is subtracted, yielding a floating point quantity." Invalid markers: uint8 0xFF, uint16 0xFFFF, sint32 0x7FFFFFFF, uint32 0xFFFFFFFF. A `timestamp` below 0x10000000 is a relative count, not an epoch value.

Time zone: the `activity` message carries `local_timestamp` (type `local_date_time`, seconds since the FIT epoch in local time). The offset is local minus UTC. "Not all manufacturers include the Local Timestamp property, so it should always be checked for a valid value before using", and the documented fallback is a time zone lookup from the first record's GPS position. There is no record-level local time field.

Sport: `session.sport` and `lap.sport` are enums where 1 = running; `sub_sport` has 1 = treadmill, 2 = street, 3 = trail, 4 = track.

Recording modes: "Smart Recording aims to reduce file size by only recording messages when a significant change in a value is detected. Every Second Recording records the messages to the file every second". Pauses are marked by timer events, not by gaps alone: "devices will use Timer events to indicate when the recording of data has been paused and then restarted."

Developer fields exist (protocol 2.0): `developer_data_id` (message 207) and `field_description` (message 206) describe custom fields that may appear in records.

### GPX 1.1

Namespace `http://www.topografix.com/GPX/1/1`. A track point `trkpt` carries required attributes `lat` and `lon`, "always in decimal degrees, and always in WGS84 datum", with ranges -90 to 90 and -180 to below 180. Child `ele` is elevation in metres. Child `time` is `xsd:dateTime`: "Date and time in are in Univeral Coordinated Time (UTC), not local time! Conforms to ISO 8601". Child `extensions` accepts any element from another namespace. A `trkseg` is one continuous span; the schema says to start a new segment where GPS reception was lost.

Heart rate lives in the Garmin TrackPointExtension, matched by namespace URI (the `gpxtpx:` prefix is a document convention):

| Namespace | Element | Type | Status |
|---|---|---|---|
| `http://www.garmin.com/xmlschemas/TrackPointExtension/v1` | `hr` | `BeatsPerMinute_t`, unsignedByte, minimum 1 | VERIFIED |
| same | `cad` | unsignedByte, maximum 254 | VERIFIED |
| same | `atemp` | degrees Celsius | VERIFIED |
| `http://www.garmin.com/xmlschemas/TrackPointExtension/v2` | `hr`, `cad` as v1, plus `speed`, `course`, `bearing` | | VERIFIED |

### TCX (Training Center Database v2)

Namespace `http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2`. A `Trackpoint` has `Time` (`xsd:dateTime`, the only required child), optional `Position` with `LatitudeDegrees` and `LongitudeDegrees` (doubles, same ranges as GPX), `AltitudeMeters`, `DistanceMeters`, `HeartRateBpm/Value` (unsignedByte, minimum 1), `Cadence` (maximum 254), `SensorState` and `Extensions`. The schema gives no documentation for `Time`; the zone comes from the `xsd:dateTime` designator in the file. `Activity` has a required `Sport` attribute with values Running, Biking, Other. `Lap` has a required `StartTime` and holds `TotalTimeSeconds`, `DistanceMeters`, optional average and maximum heart rate, and `Track` elements.

Run cadence and speed sit in the ActivityExtension v2 namespace `http://www.garmin.com/xmlschemas/ActivityExtension/v2`, element `TPX` with `Speed`, `RunCadence` and `Watts`. The `ns3:` prefix seen in exports is not normative.

### One-minute series for section 1

The ECTemp rule (section 1): "Where data had sampling rates more frequent than the one minute intervals the mean of all values occurring in that minute was used" and "Where the sampling rate was greater than one minute, values were linearly interpolated." Blagden applies it as follows. These are Blagden's choices, not source values:

- Minute bins start at the first valid sample and are aligned to the device clock in UTC.
- A sample counts only when heart rate is present and valid (not 0xFF, not absent, within 25 to 250 bpm).
- Within a recording segment, a minute with no valid sample is filled by linear interpolation when the gap is 5 minutes or shorter; longer gaps and timer pauses get no observation, so the filter runs its time update only, and the minutes are flagged.
- Each minute records how many samples it averaged; a minute with fewer than 3 samples is flagged as low support.

### Libraries

| Library | Language | Licence (from LICENSE file) | Latest release | Notes | Status |
|---|---|---|---|---|---|
| fitdecode | Python | MIT | 0.11.0, 2025-08 | FIT decode incl. developer fields; recommended by the python-fitparse maintainer | VERIFIED |
| python-fitparse | Python | MIT | 1.2.0, 2020-09 | maintainer states limited time and points to fitdecode | VERIFIED |
| garmin-fit-sdk | Python | FIT Protocol License Agreement (not OSI) | 21.221.0, 2026-11 | decode only; see licence below | VERIFIED |
| gpxpy | Python | Apache-2.0 | 1.6.2, 2023-11 (repo active 2026-11) | extensions kept as ElementTree elements; no built-in heart-rate accessor, read `hr` by namespace | VERIFIED |
| python-tcxparser | Python | BSD-2-Clause (per GitHub and PyPI classifiers; file text is unlabelled BSD) | 2.4.0, 2025-03 | minimal | VERIFIED |
| tcxreader | Python | MIT | 0.4.11, 2025-03 | per-point hr, position, time, TPX speed | VERIFIED |
| fit-file-parser | TypeScript | MIT | 6.2.7, 2026-10 | Node 20+; developer fields; metres and m/s by default | VERIFIED |
| @garmin/fitsdk | JavaScript | FIT Protocol License Agreement (not OSI) | 21.221.0, 2026-11 | see licence below | VERIFIED |
| @we-gold/gpxjs | TypeScript | MIT | 1.2.1, 2026-10 | keys extension children by prefix such as `gpxtpx:hr`, not by namespace URI | VERIFIED |
| gpxparser | JavaScript | MIT | 3.0.8, 2021-06 | no extension support | VERIFIED |
| tcx-js | TypeScript | UNVERIFIED (repository gone; registry says MIT) | 1.0.1, 2019 | not recommended | UNVERIFIED |
| Browser DOMParser | built in | none | | `getElementsByTagNameNS` resolves Garmin namespaces independent of prefix | VERIFIED |

### Garmin FIT SDK licence

The Python and JavaScript SDKs ship an identical LICENSE.txt, the "Flexible and Interoperable Data Transfer (FIT) Protocol License Agreement". Quoted terms: the grant is "a non-exclusive, royalty-free, non-transferable, non-sublicensable, limited license to use the Licensed Technology for Licensee's internal business purposes"; the licensee may not "distribute, publish, transfer or otherwise make available the Licensed Technology ... to any third party for any reason" except as set out in the agreement; may not distribute it under a licence that requires source disclosure; and may not use it in "hazardous environments, systems or applications, any safety response systems or other safety-critical applications". The licence is not on the OSI list and is identified in package metadata as `LicenseRef-FIT-Protocol-License-Agreement`. Whether an MIT project may depend on it is a legal question with no authoritative source; what is certain is that a bundled browser build would redistribute the SDK. Blagden does not use it.

### Valid input ranges

- Heart rate 1 to 254 bpm by schema; Blagden accepts 25 to 250 bpm and flags the rest.
- Latitude -90 to 90, longitude -180 to below 180, decimal degrees, WGS84.
- Timestamps must be non-decreasing; duplicates are dropped.
- Files without any heart rate are rejected with a clear message, since section 1 cannot run.

### Limitations

- Smart Recording leaves few samples per minute during steady running; the minute mean is then noisy. The low-support flag carries this forward.
- No format marks optical versus chest-strap heart rate or sensor dropouts. Quality flags are Blagden's own (section 1 limitations).
- FIT files may lack `local_timestamp`; GPX times are UTC; TCX zone depends on the designator. Blagden stores UTC and derives local time from the venue or a zone lookup.
- The semicircle conversion is verified from a Garmin forum reply, not a documentation article.

### References

- Garmin FIT protocol: https://developer.garmin.com/fit/protocol/
- Garmin FIT activity file type: https://developer.garmin.com/fit/file-types/activity/
- Garmin FIT cookbook, date and time: https://developer.garmin.com/fit/cookbook/datetime/
- Garmin FIT cookbook, decoding activity files: https://developer.garmin.com/fit/cookbook/decoding-activity-files/
- Garmin FIT cookbook, developer data: https://developer.garmin.com/fit/cookbook/developer-data/
- Garmin FIT profile source (Python SDK): https://raw.githubusercontent.com/garmin/fit-python-sdk/main/garmin_fit_sdk/profile.py
- Garmin FIT Protocol License Agreement: https://raw.githubusercontent.com/garmin/fit-python-sdk/main/LICENSE.txt
- Semicircle conversion (Garmin developer forum): https://forums.garmin.com/developer/fit-sdk/f/discussion/280125/record-the-latitude-and-longitude-format-of-the-message
- GPX 1.1 schema: https://www.topografix.com/GPX/1/1/gpx.xsd
- Garmin TrackPointExtension v1: https://www8.garmin.com/xmlschemas/TrackPointExtensionv1.xsd ; v2: https://www8.garmin.com/xmlschemas/TrackPointExtensionv2.xsd
- Garmin TrainingCenterDatabase v2: https://www8.garmin.com/xmlschemas/TrainingCenterDatabasev2.xsd ; ActivityExtension v2: https://www8.garmin.com/xmlschemas/ActivityExtensionv2.xsd
- fitdecode: https://github.com/polyvertex/fitdecode ; python-fitparse: https://github.com/dtcooper/python-fitparse ; gpxpy: https://github.com/tkrajina/gpxpy ; python-tcxparser: https://github.com/vkurup/python-tcxparser ; tcxreader: https://github.com/alenrajsp/tcxreader
- fit-file-parser: https://github.com/jimmykane/fit-parser ; @garmin/fitsdk: https://github.com/garmin/fit-javascript-sdk ; @we-gold/gpxjs: https://github.com/We-Gold/gpxjs ; gpxparser: https://github.com/Luuka/GPXParser.js
- DOMParser: https://developer.mozilla.org/en-US/docs/Web/API/DOMParser
- OSI licence list: https://opensource.org/licenses
