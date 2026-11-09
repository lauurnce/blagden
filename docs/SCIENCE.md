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

## 4. Outdoor WBGT from forecast weather

### Purpose

Compute the wet bulb globe temperature at a race venue for each hour of the race window from forecast air temperature, humidity, wind, solar radiation and pressure (section 7), using the physics-based model of Liljegren et al. (2008). WBGT feeds the risk categories in section 5 and the heat adjustment in section 6.

### Definition

$$WBGT_{outdoor} = 0.7\,T_{nwb} + 0.2\,T_g + 0.1\,T_a$$

$$WBGT_{no\ sun} = 0.7\,T_{nwb} + 0.3\,T_g$$

Read from the NIOSH 2016 criteria document: "the calculation of the WBGT for indoors is WBGT = 0.7tnwb + 0.3tg and the calculation of the WBGT for outdoors is WBGT = 0.7tnwb + 0.2tg + 0.1ta." The same weighting is given by Parsons (2006) quoting ISO 7243, and by the OSHA Technical Manual. Status: VERIFIED. The ISO 7243 text itself was not accessible; the index originates with Yaglou and Minard (1957), whose paper was not read.

- $T_{nwb}$, natural wet bulb: "the temperature measured by a thermometer in which the sensor is covered by a wetted cotton wick and is exposed only to the natural prevailing air movement" (NIOSH). It is not the psychrometric wet bulb, which is aspirated and shaded. Lemke and Kjellstrom report the natural wet bulb "up to 1.5 C higher than the psychrometric wet bulb temperature indoors and nearly 10 C higher outdoors in the sun." The ISO sensor is a cylinder 6 +/- 1 mm in diameter and 30 +/- 5 mm long (Parsons).
- $T_g$, globe: the temperature at the centre of a matt black 150 mm copper sphere with emissivity 0.95 (NIOSH; Parsons quoting ISO 7243).
- $T_a$, dry bulb air temperature in the shade.

### The Liljegren model

Liljegren JC, Carhart RA, Lawday P, Tschopp S, Sharp R. Modeling the wet bulb globe temperature using standard meteorological measurements. Journal of Occupational and Environmental Hygiene 2008;5(10):645-655. https://doi.org/10.1080/15459620802310770 . The abstract states the model "is composed of separate submodels of the natural wet bulb and globe temperatures that are based on fundamental principles of heat and mass transfer, has no site-dependent parameters, and achieves an accuracy of better than 1 degree C based on comparisons with wet bulb globe temperature measurements at all depots." Status: abstract VERIFIED (primary); full text paywalled and not read. Model internals below were read from Liljegren's own C code (Argonne, "WBGT, Version 1.1", as redistributed in the mdljts/wbgt repository) and from two faithful ports (ECMWF thermofeel, PyWBGT). Lemke and Kjellstrom (2012) describe the equation structure and report that Liljegren's comparisons "varied by less than 1 C for 95% of the time".

Inputs: air temperature, relative humidity, barometric pressure, wind speed with its measurement height, global horizontal solar irradiance, the fraction of irradiance that is direct beam, and the solar zenith angle (from date, time, latitude and longitude).

Natural wet bulb submodel: steady-state energy balance on a wetted cylinder, solved by fixed-point iteration. Convection from a cylinder-in-crossflow Nusselt correlation, radiation from sun and surroundings, evaporation from the wick. Structure quoted by Lemke and Kjellstrom: "h(Ta-Tnwb) + eps_w(SR - sigma Tnwb^4) - kQ(Ps-Pw)/(Pa-Pw) = 0" where the terms are convection, radiation and evaporation. With no solar radiation the model treats the natural wet bulb as equal to the psychrometric wet bulb (Lemke and Kjellstrom).

Globe submodel: steady-state energy balance on a sphere with a sphere-in-air Nusselt correlation, solved iteratively.

| Constant | Value | Unit | Meaning | Read from | Status |
|---|---|---|---|---|---|
| EMIS_WICK | 0.95 | none | wick emissivity | wbgt.h; thermofeel | VERIFIED (code) |
| ALB_WICK | 0.4 | none | wick albedo | same | VERIFIED (code) |
| D_WICK | 0.007 | m | wick diameter | same | VERIFIED (code) |
| L_WICK | 0.0254 | m | wick length | same | VERIFIED (code) |
| EMIS_GLOBE | 0.95 | none | globe emissivity | same; PyWBGT | VERIFIED (code) |
| ALB_GLOBE | 0.05 | none | globe albedo | same | VERIFIED (code) |
| D_GLOBE | 0.0508 | m | globe diameter in the code (2 inch), not the 150 mm ISO globe | same | VERIFIED (code); whether the paper reconciles this with the 150 mm standard is UNVERIFIED |
| EMIS_SFC | 0.999 | none | ground emissivity | same | VERIFIED (code) |
| ALB_SFC | 0.45 | none | ground albedo | same | VERIFIED (code) |
| STEFANB | 5.6696e-8 | W per m2 per K4 | Stefan-Boltzmann constant as used in the code | wbgt.h | VERIFIED (code) |
| sphere Nusselt | $Nu = 2 + 0.6\,Re^{1/2}\,Pr^{1/3}$ | none | globe convection | thermofeel port | VERIFIED (code) |
| MIN_SPEED | 0.13 | m/s | floor on wind speed in the Reynolds number | wbgt.h; thermofeel; PyWBGT | VERIFIED (code) |
| REF_HEIGHT | 2.0 | m | height the wind is converted to | wbgt.h | VERIFIED (code) |
| CZA_MIN | 0.00873 | none | cosine of 89.5 degrees; below it the sun is treated as down | wbgt.h; thermofeel | VERIFIED (code) |
| NORMSOLAR_MAX | 0.85 | none | cap on measured over clear-sky irradiance when deriving the direct fraction | wbgt.h | VERIFIED (code) |
| direct fraction clamp | 0 to 0.9 | none | thermofeel clamps the direct-beam fraction to that range | thermofeel | VERIFIED (code) |
| CONVERGENCE, MAX_ITER | 0.02, 500 | deg C, count | iteration stop rules | wbgt.h | VERIFIED (code) |

Wind conversion. The code "estimate[s] 2-m wind speed for all stability conditions" with a power law $u_2 = u_z\,(2/z)^p$ whose exponent depends on a Pasquill-Gifford stability class derived from solar elevation, irradiance and wind, with reference "EPA-454/5-99-005, 2000, section 6.2.5". Exponent tables: urban {0.15, 0.15, 0.20, 0.25, 0.30, 0.30}, rural {0.07, 0.07, 0.10, 0.15, 0.35, 0.55} by stability class. Status: VERIFIED (code). It is not a logarithmic profile. thermofeel adds a KNMI floor of 0.62 m/s on the 10 m wind before scaling. Blagden uses the urban exponents for Metro Manila venues and the rural set for Clark, a Blagden choice.

Direct-beam fraction. Liljegren's code derives it from the ratio of measured to clear-sky irradiance. Blagden has the forecast direct and diffuse components (section 7), so the fraction is $f_{dir} = I_{direct} / (I_{direct} + I_{diffuse})$ on the horizontal plane, clamped to 0 to 0.9 and set to 0 when the sun is below 89.5 degrees zenith, as in thermofeel. Blagden choice, consistent with the code's definition of the fraction.

Solar zenith. Liljegren's code uses "the low precision formulas for the Sun's coordinates given in the Astronomical Almanac of 1990", cross-checked against Michalsky's (1988) program. Blagden implements the same formulas and tests them against the NREL Solar Position Algorithm via pvlib in the development test suite.

### Validation accuracy

| Source | Result | Status |
|---|---|---|
| Liljegren 2008 abstract | "better than 1 degree C" against measured WBGT at all depots | VERIFIED (primary abstract) |
| Lemke and Kjellstrom 2012 | differences "less than 1 C for 95% of the time" in Liljegren's comparisons; their own 4-day test in Nelson, New Zealand: RMSE 0.95 C | VERIFIED |
| Carter et al. 2020 (GeoHealth) | Liljegren-type model with station inputs versus a Kestrel 5400 at three Alabama sites: RMSE 0.97 to 1.32 C, bias 0.54 to 1.22 C | VERIFIED (secondary full text) |

A WBGT error of about 1 C is the same width as several of the risk bands in section 5, so Blagden shows the band and the number together, and states the error.

### Why the simplified approximation is wrong for outdoor races

The Australian Bureau of Meteorology approximation is $WBGT = 0.567\,T_a + 0.393\,e + 3.94$ with $e$ the vapour pressure in hPa. The Bureau's own page states: "Values for the black globe temperature and natural wet-bulb temperature cannot be accurately determined from a standard meteorological site", "Real variations of sunshine and wind are not taken into account", and "The formula is likely to overestimate the WBGT in cloudy or windy conditions, or when the sun is low or below the horizon." Lemke and Kjellstrom traced it to an indoor regression by Gagge and Nishi (1976) and concluded "the Australian Bureau of Meteorology formula quoted on their web site is incorrect." Kong and Huber (2022) compared it with Liljegren's model and wrote "sWBGT greatly overestimates heat stress in hot-humid areas" and "We recommend discontinuing the use of sWBGT"; their 2024 paper puts the peak of its bias at "an overestimation of approximately 5 C". Status: VERIFIED.

For a Manila race morning the sun goes from below the horizon to strong within the window, and the approximation cannot see that change. Blagden does not use it, not even as a fallback. When solar data are missing, Blagden reports no WBGT rather than an approximate one.

### Implementations surveyed

| Implementation | Language | Licence | Method | Maintained | Status |
|---|---|---|---|---|---|
| Liljegren C code (Argonne, redistributed in mdljts/wbgt) | C | UChicago Argonne notice: permissive with attribution and an acknowledgment clause, not public domain | full model | wrapper last commit 2017 | VERIFIED |
| ECMWF thermofeel 2.3.0 | Python | Apache-2.0 | `calculate_wbgt_liljegren` (full model, KNMI operational); also a Stull-plus-quartic hybrid and the BoM approximation; solar zenith from earthkit-meteo | yes, 2026-07 | VERIFIED |
| PyWBGT (Kong) | Cython | CC BY-NC-SA 4.0 | full model | last commit 2022-02 | VERIFIED |
| lwbgt 1.2.1 | C with Python and R bindings | Apache-2.0 and the Argonne notice | the original Argonne calculation, "bit for bit" under matched compiler settings | yes, 2026-10 | VERIFIED |
| kwodzicki/pywbgt 3.0.7 | Python and C | GPL-3.0 | Liljegren, Dimiceli, Bernard; solar position via pvlib | yes, 2026-07 | VERIFIED |
| HeatStress (Casanueva) | R | MIT | Liljegren with hard-coded pressure 1010 hPa, direct fraction 0.8 and no wind-height adjustment | light, 2026-11 | VERIFIED |
| pythermalcomfort | Python | MIT | ISO 7243 weighting only; needs measured natural wet bulb and globe | yes | VERIFIED |
| JavaScript or TypeScript Liljegren port | | | none found | | UNVERIFIED (absence) |

### Blagden's approach

Blagden ports the Liljegren method itself, in Python as the reference and in TypeScript for the browser (D-001), following the structure and constants of the Argonne code as read above. Reasons: no JavaScript port exists, the Python port keeps the core dependency-light, and both ports are checked against two independent oracles in the development test suite: thermofeel's `calculate_wbgt_liljegren` and lwbgt, which reproduces the Argonne code bit for bit. Agreement within 0.1 C across a grid of Manila-like conditions is the acceptance test. The Argonne acknowledgment is reproduced in the documentation because the port follows that code.

### Valid input ranges

- Air temperature 20 to 45 C, relative humidity 20 to 100 percent, pressure 950 to 1050 hPa, 10 m wind 0 to 20 m/s, irradiance 0 to 1200 W/m2. Outside these the result is flagged.
- Solar zenith at or beyond 89.5 degrees: sun treated as down.
- Iteration failure returns no value, as thermofeel does, never a guess.

### Limitations

- The globe in the model is 50.8 mm, the ISO globe is 150 mm. The validation against depot instruments stands, but whether and how the paper reconciles the two is not known until the paper is read.
- Forecast irradiance and wind are the least accurate inputs (section 7).
- The model is steady state; the real 150 mm globe takes up to 20 minutes to equilibrate (Lemke and Kjellstrom), so hourly values are the right resolution.
- Cloud is only represented through the forecast irradiance.
- Outdoor only; the Bernard method is recommended indoors and is out of scope.

### References

- NIOSH. Criteria for a recommended standard: occupational exposure to heat and hot environments. DHHS (NIOSH) Publication 2016-106. https://www.cdc.gov/niosh/docs/2016-106/pdfs/2016-106.pdf
- Parsons K. Heat stress standard ISO 7243 and its global application. Industrial Health 2006;44:368-379. https://www.jstage.jst.go.jp/article/indhealth/44/3/44_3_368/_pdf
- Yaglou CP, Minard D. Control of heat casualties at military training centers. AMA Archives of Industrial Health 1957;16(4):302-316. PMID 13457450 (not read)
- Liljegren JC, Carhart RA, Lawday P, Tschopp S, Sharp R. Modeling the wet bulb globe temperature using standard meteorological measurements. Journal of Occupational and Environmental Hygiene 2008;5(10):645-655. https://doi.org/10.1080/15459620802310770 (abstract read)
- Liljegren JC. WBGT Version 1.1, C source, Copyright 2008 UChicago Argonne LLC. https://raw.githubusercontent.com/mdljts/wbgt/master/src/wbgt.c and wbgt.h
- Lemke B, Kjellstrom T. Calculating workplace WBGT from meteorological data: a tool for climate change assessment. Industrial Health 2012;50:267-278. https://www.jniosh.johas.go.jp/en/indu_hel/doc/IH_50_4_267.pdf
- Kong Q, Huber M. Explicit calculations of wet bulb globe temperature compared with approximations and why it matters for labor productivity. Earth's Future 2022;10(3):e2021EF002334. https://doi.org/10.1029/2021EF002334 (abstract read)
- Kong Q, Huber M. GeoHealth 2024. https://doi.org/10.1029/2024GH001068 ; open text https://europepmc.org/article/PMC/PMC11439757
- Carter AW, et al. GeoHealth 2020. https://doi.org/10.1029/2019GH000231
- Australian Bureau of Meteorology. Thermal comfort observations (approximation and caveats). http://reg.bom.gov.au/info/thermal_stress/
- ECMWF thermofeel. https://github.com/ecmwf/thermofeel ; https://thermofeel.readthedocs.io/en/2.3.0/guide/heatforce/
- PyWBGT. https://github.com/QINQINKONG/PyWBGT
- lwbgt. https://github.com/zyf0717/lwbgt ; https://pypi.org/project/lwbgt/
- kwodzicki/pywbgt. https://github.com/kwodzicki/pywbgt
- HeatStress. https://github.com/anacv/HeatStress
- pythermalcomfort. https://github.com/CenterForTheBuiltEnvironment/pythermalcomfort
- OSHA Technical Manual, Section III Chapter 4. https://www.osha.gov/otm/section-3-health-hazards/chapter-4
- OSHA outdoor WBGT calculator (Liljegren algorithm). https://www.osha.gov/heat-exposure/wbgt-calculator
- EPA-454/5-99-005 (2000), section 6.2.5, cited by the Liljegren code for the wind profile (not read)

## 5. Heat risk categories for endurance events and the PAGASA heat index

### Purpose

Label the forecast WBGT (section 4) with published sports-medicine risk bands for road running, and show the PAGASA heat index category next to it because Filipino runners know that scale. The two indices measure different things: WBGT includes sun and wind and is meant for exertion; the heat index is a shade value for a resting person at a fixed light wind.

### WBGT guidance for road running

**ACSM position stand 2007** (Armstrong LE, Casa DJ, Millard-Stafford M, Moran DS, Pyne SW, Roberts WO. Exertional heat illness during training and competition. Medicine and Science in Sports and Exercise 2007;39(3):556-572). Read from a full-text copy of the article filed as a court exhibit. Table 2, "WBGT levels for modification or cancellation of workouts or athletic competition for healthy adults", column "Continuous Activity and Competition":

| WBGT (C) | WBGT (F) | Continuous activity and competition | Status |
|---|---|---|---|
| at or below 10.0 | at or below 50.0 | "Generally safe; EHS can occur associated with individual factors" | VERIFIED |
| 10.1 to 18.3 | 50.1 to 65.0 | "Generally safe; EHS can occur" | VERIFIED |
| 18.4 to 22.2 | 65.1 to 72.0 | "Risk of EHS and other heat illness begins to rise; high-risk individuals should be monitored or not compete" | VERIFIED |
| 22.3 to 25.6 | 72.1 to 78.0 | "Risk for all competitors is increased" | VERIFIED |
| 25.7 to 27.8 | 78.1 to 82.0 | "Risk for unfit, nonacclimatized individuals is high" | VERIFIED |
| 27.9 to 30.0 | 82.1 to 86.0 | "Cancel level for EHS risk" | VERIFIED |
| 30.1 to 32.2 and at or above 32.3 | 86.1 to 90.0 and at or above 90.1 | cells empty in the text extraction; the training columns read "Cancel or stop practice and competition" and "Cancel exercise" | UNVERIFIED for this column |

Text of the stand: "If the WBGT index is above 28 C (82 F), consideration should be given to canceling or rescheduling continuous competitive events until less stressful conditions prevail." Footnote f: "Differences of local climate and individual heat acclimatization status may allow activity at higher levels than outlined in the table, but athletes and coaches should consult with sports medicine staff and should be cautious when exceeding these limits." The 2007 table has no flag colours. Status: VERIFIED.

**Flag system (1996 ACSM distance-running stand, as used by race medicine and the IAAF).** The colour bands most race organisers use come from the 1996 stand "Heat and cold illnesses during distance running", read here through three sources that reproduce it: Roberts (2010) Table 1, Bermon and Adami (2019) Table 1 describing the IAAF Competition Medical Guidelines, and Grundstein et al. (2019) describing the International Institute for Race Medicine flags.

| Flag | WBGT (C) | WBGT (F) | Meaning (Bermon and Adami 2019) | Status |
|---|---|---|---|---|
| White | below 10 | below 50 | "Generally safe; EHS can occur associated with individual factors" (Roberts 2010 Table 1) | VERIFIED (secondary) |
| Green | 10 to 18 | 50 to 65 | "Risk low but still exists on the basis of risk factors" | VERIFIED (secondary) |
| Yellow | 18 to 23 | 65 to 73 | "Risk increases as event progresses through the day" | VERIFIED (secondary) |
| Red | 23 to 28 | 73 to 82 | "Everyone should be aware of injury potential; individuals at risk should not compete" | VERIFIED (secondary) |
| Black | above 28 | above 82 | "Consider rescheduling or delaying the event until safer conditions prevail; if the event must take place, be on high alert" | VERIFIED (secondary) |

The 1996 stand itself was not read; the bands are consistent across all three sources.

**World Athletics Competition Medical Guidelines, October 2020, second edition**, section 6.1, Table 1 "WBGT Heat Index and color coding system": "Below 21 C Almost Safe", "21 C to 25 C Caution", "25 C to 28 C Warning", "28 C to 30 C Severe Warning", "Above 30 C Danger". The text adds "The risk of heat illness increases above 21 C (70 F) and 50% relative humidity" and that for road races a banner shows "the WBGT/PET measured every 20 minutes on-site". Status: bands VERIFIED (primary); the colour of each band is a cell fill, not text, and is UNVERIFIED.

**Roberts WO 2010.** Determining a "do not start" temperature for a marathon on the basis of adverse outcomes. Medicine and Science in Sports and Exercise 2010;42(2):226-232. Read from a full-text copy. "The do not start WBGT for Twin Cities Marathon is 20.5 C on the basis of this model." "The risk of requiring medical attention and not finishing the race increases rapidly above 13 C (55.4 F) start WBGT." "Marathons in northern latitudes held in unexpectedly hot conditions when the participants are not acclimatized and the start WBGT is at or above 21 C often end in either race cancellation or an MCI." Status: VERIFIED. These numbers describe non-acclimatised northern populations and are recorded for contrast, not applied to Manila.

**Racinais et al. 2015 consensus**, Table 3, "Corrected estimation of the risk of exertional heat illness based on the WBGT taking into account that WBGT underestimates heat stress under high humidity", adapted from Gonzalez:

| Estimated risk | WBGT (C) at 50 percent RH | at 75 percent RH | at 100 percent RH | Status |
|---|---|---|---|---|
| Moderate | 24 | 20 | 18 | VERIFIED (primary, open access) |
| High | 28 | 26 | 24 | VERIFIED |
| Excessive | 33 | 29 | 28 | VERIFIED |

The consensus states: "WBGT might underestimate heat stress risk when sweat evaporation is restricted (ie, high humidity and/or low air movement)." This table is the only sourced guidance that adjusts for the humidity Manila mornings have, and Blagden shows it alongside the flags.

**ACSM Expert Consensus Statement on Exertional Heat Illness** (Roberts WO, Armstrong LE, Sawka MN, Yeargin SW, Heled Y, O'Connor FG. Current Sports Medicine Reports 2021;20(9):470-484, DOI 10.1249/JSR.0000000000000878; republished 2023;22(4):134-149). Full text not retrievable; a secondary summary says it adds three regional climate categories and keeps separate guidance for acclimatised and non-acclimatised participants. Status: UNVERIFIED; not used.

Conflicts between sources, recorded so the UI can be honest: the red band is 23 to 28 C in the flag system, while World Athletics 2020 has no such band and warns from 21 C; the cancel or black threshold is above 28 C in the flag system, "above 28 C" in the 2007 text, 27.9 to 30.0 C in the 2007 table, and above 30 C for "Danger" in World Athletics 2020; Roberts puts a do-not-start at 20.5 C for one northern marathon.

### Blagden's WBGT display (D-017)

1. Flag and band from the five-flag system above, attributed to the 1996 ACSM stand as reproduced by race medicine and the IAAF, because that is what race organisers and runners see at start lines.
2. The Racinais humidity-corrected risk (moderate, high, excessive) interpolated in relative humidity between the 50, 75 and 100 percent columns and shown as a second line, because Manila humidity is where plain WBGT under-reads.
3. The matching 2007 ACSM continuous-activity row text and the World Athletics 2020 band name, for organisers.
4. The WBGT value with its about 1 C model error (section 4) next to the band, so a value near a boundary is read as near a boundary.

### PAGASA heat index

Categories, read from PAGASA product pages (iHeatMAP and panahon.gov.ph) and the DOST announcement of iHeatMAP:

| Category | Heat index (C) | Colour (DOST 2025) | Effect (DOST 2025 English; PAGASA infographic in Filipino) | Status |
|---|---|---|---|---|
| Not hazardous | below 27 | | | VERIFIED (panahon.gov.ph) |
| Caution | 27 to 32 | yellow | "prolonged exposure and activity may result in fatigue. Continuing such activities could also lead to heat cramps." | VERIFIED |
| Extreme Caution | 33 to 41 | yellow-orange | "heat cramps and heat exhaustion are possible, and ongoing activity could result in heat stroke." | VERIFIED |
| Danger | 42 to 51 | red-orange | "heat cramps and heat exhaustion are likely, and heat stroke is probable with continued exposure" | VERIFIED |
| Extreme Danger | 52 and above | red | "heat stroke is imminent" | VERIFIED |

PAGASA's infographic notes: "Heat index values adapted from Steadman, 1979; classification threshold adapted from National Weather Services, National Oceanic and Atmospheric Administration (NWS-NOAA)." One DOST article gives the Extreme Caution band as 32 to 41 C; all PAGASA product pages give 33 to 41 C and are followed here. The categories are integer-bounded; Blagden rounds the heat index to the nearest whole degree before classifying, a Blagden choice.

Formula. A PAGASA lecture (Heat Index Monitoring and Early Warning System of DOST-PAGASA, 20 March 2024) states the heat index is "obtained by multiple regression analysis (from Steadman's table) carried out by Rothfusz (1990)" and that the "HI value has an error of +/- 1.3 degrees". The equation, read from the US National Weather Service page, with $T$ in degrees Fahrenheit and $RH$ in percent:

$$HI = -42.379 + 2.04901523\,T + 10.14333127\,RH - 0.22475541\,T\,RH - 0.00683783\,T^2 - 0.05481717\,RH^2 + 0.00122874\,T^2 RH + 0.00085282\,T\,RH^2 - 0.00000199\,T^2 RH^2$$

Adjustments: if $RH < 13$ and $80 \le T \le 112$, subtract $\frac{13 - RH}{4}\sqrt{\frac{17 - |T - 95|}{17}}$; if $RH > 85$ and $80 \le T \le 87$, add $\frac{RH - 85}{10}\cdot\frac{87 - T}{5}$. Procedure: first compute $HI_{simple} = 0.5\,(T + 61.0 + 1.2\,(T - 68.0) + 0.094\,RH)$ and average it with $T$; if that is 80 F or higher, apply the full regression with any adjustment, otherwise keep the simple result. "The Rothfusz regression is not valid for extreme temperature and relative humidity conditions beyond the range of data considered by Steadman." Status: equation and procedure VERIFIED (NWS page); the +/- 1.3 F error VERIFIED from Rothfusz's 1990 technical attachment, which also states the assumptions of a 5 knot wind, shade, and long trousers with a short-sleeved shirt.

What PAGASA publishes: a daily highest heat index for 77 stations, computed from station observations for the past five days and forecast for two days from ECMWF model output, stamped at 5:00 pm, with hourly forecasts on iHeatMAP. The product footnote states it "was designed for the general warm, dry season of the country" and is "most reliable in the absence of rainfall events." Blagden computes the heat index from the hourly forecast temperature and humidity at the venue with the equation above and labels it "heat index on the PAGASA scale", since it is not PAGASA's own published value. Status: VERIFIED for the published products; the exact observation hour behind the daily value is UNVERIFIED.

### Why the two scales disagree on a race morning

A Manila morning at 29 C and 85 percent humidity gives a heat index in the PAGASA Caution band, while the same air with sun on it gives a WBGT in the red or black flag band. The heat index assumes shade, rest and a fixed light wind; WBGT counts the sun on a globe and the evaporation off a wick. Blagden shows both and says this in one sentence.

### Valid input ranges and limitations

- Heat index: the regression is defined by the NWS procedure above and is not valid beyond Steadman's data; Blagden does not report a heat index below 27 C as a category other than "not hazardous".
- Flag thresholds come from temperate-climate guidance for non-acclimatised populations; footnote f of the 2007 stand allows local adaptation. Blagden shows the bands as published and does not shift them.
- Band widths are 5 C while the WBGT model error is about 1 C.
- Blagden gives training insight, not a go or no-go decision. The organiser view repeats the published text and does not add thresholds of its own.

### References

- Armstrong LE, Casa DJ, Millard-Stafford M, Moran DS, Pyne SW, Roberts WO. Exertional heat illness during training and competition. Medicine and Science in Sports and Exercise 2007;39(3):556-572. https://doi.org/10.1249/MSS.0b013e31802fa199 ; full-text copy read at https://kgrlaw.com/wp-content/uploads/2022/11/Exhibit-G-ACSM-Position-Stand-11.29.2022.pdf
- Roberts WO. Determining a "do not start" temperature for a marathon on the basis of adverse outcomes. Medicine and Science in Sports and Exercise 2010;42(2):226-232. Copy read at https://www.fisiologiadelejercicio.com/wp-content/uploads/2019/04/2010_Roberts_Determining-a-do-not-start-temperature-for-a-marathon-on-the-basis-of-adverse-outcomes.pdf
- Bermon S, Adami PE. Meteorological risks in Doha 2019 Athletics World Championships: health considerations from organizers. Frontiers in Sports and Active Living 2019. https://www.frontiersin.org/articles/10.3389/fspor.2019.00058/full
- Grundstein AJ, Hosokawa Y, Casa DJ, Stearns RL, Jardine JF. Frontiers in Sports and Active Living 2019. https://www.frontiersin.org/journals/sports-and-active-living/articles/10.3389/fspor.2019.00042/full
- World Athletics. Competition Medical Guidelines for World Athletics Series Events, second edition, October 2020. https://worldathletics.org/about-iaaf/documents/health-science
- Racinais S, et al. Consensus recommendations on training and competing in the heat. British Journal of Sports Medicine 2015;49:1164-1173. https://pmc.ncbi.nlm.nih.gov/articles/PMC4602249/
- Roberts WO, Armstrong LE, Sawka MN, Yeargin SW, Heled Y, O'Connor FG. ACSM expert consensus statement on exertional heat illness. Current Sports Medicine Reports 2021;20(9):470-484. https://doi.org/10.1249/JSR.0000000000000878 (not read)
- DOST-PAGASA iHeatMAP. https://src.panahon.gov.ph/pubfiles/cad/iaas/ihif_new.html ; heat index page https://bagong.pagasa.dost.gov.ph/weather/heat-index ; panahon.gov.ph heat index https://www.panahon.gov.ph/heat_index.html
- DOST. iHeatMap, an online monitoring guide for heat index, 21 April 2025. https://www.dost.gov.ph/knowledge-resources/news/86-2025-news/3971-iheatmap-an-online-monitoring-guide-for-heat-index.html
- DOST-PAGASA. Heat index monitoring and early warning system, lecture, 20 March 2024. https://pubfiles.pagasa.dost.gov.ph/climps/climateforum/speciallecture.pdf
- DOST-PAGASA. Official statement on creating extreme heat protocol, 12 April 2024. https://www.pagasa.dost.gov.ph/press-release/155
- US National Weather Service. The heat index equation. https://www.wpc.ncep.noaa.gov/html/heatindex_equation.shtml
- Rothfusz LP. The heat index "equation". NWS Technical Attachment SR 90-23, 1990. Copy at https://www.weather.gov/media/wrh/online_publications/TAs/ta9024.pdf
- Steadman RG. The assessment of sultriness, Part I. Journal of Applied Meteorology 1979;18:861-873 (not read; cited by PAGASA and NWS)

## 6. Running performance in heat

### Purpose

Turn a baseline finish-time prediction made for neutral weather into a prediction for the forecast WBGT, with an honest interval. Two parts: the baseline (Riegel or PaceBrain) and the heat adjustment. The adjustment is where the evidence is thinnest for Blagden's users, so this section states exactly what is sourced and where the model extrapolates.

### Baseline predictors

Riegel. The formula in common use is

$$T_2 = T_1 \left(\frac{D_2}{D_1}\right)^{1.06}$$

where $T_1$ is a known time over distance $D_1$ and $T_2$ the predicted time over $D_2$. Riegel's 1981 article states the underlying form $t = a x^b$ with $b$ = 1.06 for activities in the "endurance range" of 3.5 to 230 minutes, covering running, swimming and walking. Status: formula and exponent VERIFIED from a secondary source (Wikipedia, citing Riegel PS, American Scientist 1981;69(3):285-290, PMID 7235349); the primary article returned server errors and was not read. Riegel gives no uncertainty; the baseline interval for a Riegel prediction is therefore UNVERIFIED and must be supplied as a declared assumption, not a sourced value.

PaceBrain (github.com/lauurnce/pacebrain, MIT). A tabular neural network that takes weekly mileage, easy-run pace, longest recent run and race distance, and returns a finish time in minutes for 5, 10, 21.1 or 42.2 km. Its README states the models "are trained entirely on synthetic data and have never seen a real run", reports a validation mean absolute error of 4.12 minutes on that synthetic set, ships no weights, and makes no reference to weather. Status: VERIFIED from the repository README on 2026-11-09. Its output is taken as a neutral-weather baseline with no interval of its own.

### Evidence on heat and performance

| Source | Data | Weather index and range | Finding | Status |
|---|---|---|---|---|
| Ely MR, Cheuvront SN, Roberts WO, Montain SJ 2007 | 7 North American marathons, 140 race-years; top 3 and 25th, 50th, 100th, 300th place versus course record | WBGT 5.1 to 25 C in quartiles 5.1-10, 10.1-15, 15.1-20, 20.1-25 | top men slower than the course record by "1.7 +/- 1.5, 2.5 +/- 2.1, 3.3 +/- 2.0, and 4.5 +/- 2.3%" across the four quartiles; top women 3.2, 3.2, 3.8, 5.4 percent; "The 25th-, 50th-, 100th-, and 300th-place finishers slowed more than faster runners as WBGT increased"; "performance is more negatively affected for slower populations of runners" | VERIFIED (primary abstract); regression form and nomogram UNVERIFIED (full text not read) |
| Mantzios et al. 2022, restating Ely 2007 | | | "performance decrements of ~0.1%, ~0.3%, and ~0.6% for every degree increase in WBGT for elite men, elite women, and well-trained runners" | VERIFIED (secondary) |
| Montain SJ, Ely MR, Cheuvront SN 2007 (review) | same 140 race-years | WBGT | "performance times slow progressively as weather warms above 5-10 degrees C wet bulb globe temperature ... slower runners suffer a greater performance penalty than elite runners" | VERIFIED (primary abstract) |
| Mantzios K et al. 2022 | 1258 races, 7867 athletes, 1936 to 2019: marathon, 50 km and 20 km race walking, 10,000 m, 5000 m | WBGT -7 to 33 C; only 7 percent of races in high heat (23.1 to 28 C) and 1 percent above 28 C; marathon models exclude the 25th to 300th place runners | optimum "7.5 C-15 C WBGT"; "For every degree WBGT outside these optimum conditions, performance declined by 0.3%-0.4%"; heat slopes per 1 C WBGT: marathon 0.2 percent, 5000 m 0.3 percent, 10,000 m 0.04 percent, 20 km walk 0.4 percent, 50 km walk 1.1 percent; WBGT had higher predictive power (R2 0.11 to 0.47) than air temperature (R2 0.04 to 0.34) | VERIFIED (primary full text, open access) |
| El Helou N et al. 2012 | 6 major marathons 2001 to 2010, 1,791,972 finishers | air temperature 1.7 to 25.2 C (4 h race mean); no WBGT | air temperature the most predictive parameter; quadratic fit; optimum 3.8 to 9.9 C by level; speed loss at optimum +10 C: elite men 1.44 percent, median men 3.91 percent, third-quartile men 4.61 percent; at +15 C: 3.29, 9.26, 11.01 percent; at +20 C (beyond observed data): 6.0, 17.73, 21.42 percent; "at a population level, temperature causes its full effect whatever the initial capacity" | VERIFIED (primary full text and Table S3) |
| Knechtle B et al. 2019 | Boston 1972 to 2018, 580,990 results | air temperature; WBGT in bins up to 16 to 20 C | "+1 C: all finishers slower by 00:01:47; annual winners by 00:00:20"; WBGT increases "related to worsened performances" | VERIFIED (primary full text) |
| Vihma T 2010 | Stockholm 1980 to 2008 | air temperature | air temperature the strongest correlate (r 0.66 to 0.73, highest for slowest runners); slower runners more affected, extended to 4.7 h finishers | VERIFIED (primary abstract); slopes UNVERIFIED |
| Ely BR et al. 2009 | 17 competitive runners, 8 km time trials | WBGT about 13 C and about 27 C | running velocity not different above versus below 40 C rectal temperature | VERIFIED (primary abstract) |
| Racinais S et al. 2015 (consensus) | | | heat acclimatisation over 1 to 2 weeks is "the most important intervention"; no race-data quantification | VERIFIED (primary full text) |
| Comprehensive Physiology 2025 meta-regression (211 papers) | laboratory heat acclimation | | time trial performance improved "3.1% [1.8, 4.5]" | VERIFIED (primary abstract) |

No source quantifies the slowdown of recreational runners (finish times beyond about 3:40 for the marathon) against WBGT, and no source quantifies heat-acclimatised versus non-acclimatised populations in race data. Both are UNVERIFIED and are treated as gaps, not filled.

### Where extrapolation begins

- WBGT above 25 C: beyond Ely 2007. Mantzios 2022 reaches 33 C but with 1 percent of races above 28 C and no non-elite marathoners.
- Finish times beyond about 3:40 for the marathon, or the equivalent at other distances: outside every WBGT-based source.
- Air temperature above 25.2 C: beyond El Helou 2012; its +20 C cells are model extrapolation.

Metro Manila race mornings sit at roughly 25 to 30 C WBGT (section 4), so every Blagden prediction for a recreational runner is extrapolated on both axes and must say so.

### The v0.1 adjustment model

Point estimate:

$$T_{pred} = T_{base}\,\bigl(1 + k_L \cdot \max(0,\; W_{race} - W_{base})\bigr)$$

Interval:

$$T_{low} = T_{base,low}\,\bigl(1 + k_{L,low}\,\Delta W\bigr),\qquad
T_{high} = T_{base,high}\,\bigl(1 + k_{L,high}\,\Delta W_{\le 25} + 2\,k_{L,high}\,\Delta W_{> 25}\bigr)$$

where $\Delta W = \max(0, W_{race} - W_{base})$ is split into the part at or below 25 C WBGT and the part above it.

| Symbol | Value | Unit | Basis | Status |
|---|---|---|---|---|
| $W_{race}$ | forecast WBGT at the venue, averaged over the runner's expected time on course | deg C | section 4 | computed |
| $W_{base}$ | WBGT of the race the baseline time came from, when known (archive, section 7); otherwise 10 C, flagged | deg C | 10 C is the upper edge of Ely's coolest quartile and inside Mantzios's optimum | Blagden choice, flagged when defaulted |
| $k_{elite}$ | 0.0018 per C; range 0.0010 to 0.0030 | fraction per deg C | slope of Ely's top-men quartile means (1.7, 2.5, 3.3, 4.5 percent at quartile midpoints 7.5, 12.5, 17.5, 22.5 C): least-squares slope 0.184 percent per C, arithmetic on verified numbers; range from Mantzios's restatement for elite men and women | derived from VERIFIED values |
| $k_{nonelite}$ | 0.0060 per C; range 0.0040 to 0.0080 | fraction per deg C | 0.6 percent per C WBGT for well-trained runners (Mantzios restating Ely); range brackets El Helou's median-finisher air-temperature losses (0.4 to 0.6 percent per C over the first 15 C above optimum) and Knechtle's Boston all-finisher slope (about 0.7 percent per C of air temperature) | VERIFIED values from different indices; the combination is Blagden's |
| Level rule | elite if the baseline marathon-equivalent time is under 2:30:00, else non-elite | | Ely's elite group is the top three finishers; his well-trained group spans 2:14 to 3:40 | Blagden choice |
| Doubling above 25 C | the upper slope doubles for degrees above 25 C | | El Helou's quadratic fits show the per-degree loss roughly doubling from the +10 to +15 band to the +15 to +20 band (median men 1.07 to 1.69 percent per C); Blagden applies that shape to the upper bound only | Blagden choice, motivated by VERIFIED values |
| $T_{base,low}$, $T_{base,high}$ | from the predictor when it supplies an interval; otherwise a declared assumption passed in by the caller | min | PaceBrain reports MAE 4.12 min on synthetic data; Riegel has none | UNVERIFIED for Riegel |
| Distance dependence | none in v0.1 | | Mantzios's discipline slopes are elite-only and inconsistent in order (10,000 m smaller than 5000 m) | UNVERIFIED, so not modelled |
| Acclimatisation | none in v0.1 | | no race-data effect size exists | UNVERIFIED, so not modelled (D-004) |

Every prediction carries: `level`, `extrapolated` (true when $W_{race}$ > 25 C or the runner is non-elite with a marathon-equivalent above 3:40), `baseline_wbgt_defaulted`, and the interval. The brief (section 5 and the product spec) must never show the point estimate without the interval.

### Validation plan for later phases

Collect, with consent, for each club runner and race: the baseline prediction and its source, $W_{base}$, the venue WBGT from the archive at the start and at the runner's finish, and the actual finish time. Score the mean absolute error of $T_{pred}$ against $T_{base}$. Success means a lower error for the adjusted prediction and a calibrated interval (about 80 percent of results inside the 80 percent interval). The slopes above are the first things to refit.

### Limitations

- The adjustment is linear in WBGT; the sources show a continuous slowing but their functional forms (Ely's nomogram) could not be read.
- Slopes come from temperate marathons and from elite or well-trained runners; recreational runners in humid heat are not represented.
- Humidity is only in the model through WBGT. Sources using air temperature alone (El Helou, Knechtle, Vihma) were used for ranges, not for the point slope.
- PaceBrain's baseline is itself trained on synthetic data.
- Individual variation, hydration, pacing and acclimatisation are not modelled; Mantzios et al. list all of them as unmodelled modifiers.

### References

- Ely MR, Cheuvront SN, Roberts WO, Montain SJ. Impact of weather on marathon-running performance. Medicine and Science in Sports and Exercise 2007;39(3):487-493. https://doi.org/10.1249/mss.0b013e31802d3aba (abstract read; PMID 17473775)
- Montain SJ, Ely MR, Cheuvront SN. Marathon performance in thermally stressing conditions. Sports Medicine 2007;37(4-5):320-323. https://doi.org/10.2165/00007256-200737040-00012 (abstract read)
- Ely MR, Martin DE, Cheuvront SN, Montain SJ. Effect of ambient temperature on marathon pacing is dependent on runner ability. Medicine and Science in Sports and Exercise 2008. https://doi.org/10.1249/mss.0b013e3181788da9 (abstract read)
- Ely BR, Ely MR, Cheuvront SN, Kenefick RW, DeGroot DW, Montain SJ. Evidence against a 40 C core temperature threshold for fatigue in humans. Journal of Applied Physiology 2009. https://doi.org/10.1152/japplphysiol.00577.2009 (abstract read)
- Mantzios K, Ioannou LG, Panagiotaki Z, Ziaka S, Periard JD, Racinais S, Nybo L, Flouris AD. Effects of weather parameters on endurance running performance: discipline-specific analysis of 1258 races. Medicine and Science in Sports and Exercise 2022;54(1):153-161. https://doi.org/10.1249/MSS.0000000000002769 ; open text https://europepmc.org/article/PMC/PMC8677617
- El Helou N, Tafflet M, Berthelot G, Tolaini J, Marc A, Guillaume M, Hausswirth C, Toussaint JF. Impact of environmental parameters on marathon running performance. PLoS ONE 2012;7(5):e37407. https://doi.org/10.1371/journal.pone.0037407
- Knechtle B, et al. The role of weather conditions on running performance in the Boston Marathon from 1972 to 2018. PLoS ONE 2019;14(3):e0212797. https://doi.org/10.1371/journal.pone.0212797
- Vihma T. Effects of weather on the performance of marathon runners. International Journal of Biometeorology 2010;54:297-306. https://doi.org/10.1007/s00484-009-0280-x (abstract read)
- Racinais S, et al. Consensus recommendations on training and competing in the heat. British Journal of Sports Medicine 2015;49:1164-1173. https://doi.org/10.1136/bjsports-2015-094915
- Influence of exercise heat acclimation protocol characteristics on adaptation kinetics: a quantitative review with Bayesian meta-regressions. Comprehensive Physiology 2025. https://doi.org/10.1002/cph4.70017 (abstract read)
- Riegel PS. Athletic records and human endurance. American Scientist 1981;69(3):285-290. PMID 7235349 (not read; formula via https://en.wikipedia.org/wiki/Peter_Riegel)
- PaceBrain repository. https://github.com/lauurnce/pacebrain

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
