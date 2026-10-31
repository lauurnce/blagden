# Validation plan: heat-adjusted race predictions

Status: pre-registered. This plan is committed before any participant data exists. Any later change is recorded in the change log at the end, with its date and reason, before the results are looked at.

## 1. Question

Does Blagden's heat-adjusted finish-time prediction match real race results in Metro Manila heat better than the same prediction without the heat adjustment?

The heat adjustment (docs/SCIENCE.md section 6) extrapolates beyond the race data it is built on: recreational runners, WBGT above 25 C, or both. This study is the first test of it on the runners it is meant for.

## 2. Hypotheses

- H1 (primary). The absolute percentage error of the heat-adjusted prediction is smaller than that of the unadjusted baseline prediction, for the same runner and race.
- H2 (secondary). The actual finish time falls inside Blagden's predicted range at least half the time.
- H3 (secondary). The heat-adjusted prediction has a mean signed error within plus or minus 3 percent, that is, it is not consistently too fast or too slow.

The baseline is Riegel's formula from the runner's recent race (docs/SCIENCE.md section 6), which is Blagden's default. PaceBrain is not used in this study.

## 3. Who takes part

Members of Lawrence Panes's running club who:

- are 18 or older;
- plan to run a road race of 5 km, 10 km, 21.1 km or 42.2 km in Metro Manila or Clark during the study window;
- have an official result at another of those distances from the 12 weeks before the target race;
- agree to the consent wording in section 4.

Not included: anyone under 18; a race where the runner plans to pace someone else, run with an injury, or not race at full effort; trail races; a course that is changed by more than 5 percent of its distance on the day.

Each runner contributes one race to the primary analysis: their first eligible race in the window. Later races by the same runner are analysed separately as a secondary, descriptive set.

## 4. Consent wording

Read to or given to each runner before any data is collected. Consent is recorded as a yes in the club's sign-up form, with the date.

> Blagden is a training tool that estimates how heat may slow a race. I am testing whether its predictions match real results. If you take part, I will ask for one recent official race time, the race you plan to run next, and your official finish time afterwards. I will make a prediction before your race and keep it sealed. I will not show it to you until after the race, so that it does not change how you run.
>
> I will not ask for health information, heart rate files or GPS tracks. You can add notes about your race if you want to; this is optional. Your name is replaced by a random code, and the key that links the code to you stays on my computer and is never published. Published results will be in groups, with times rounded, so that no one can be picked out.
>
> Taking part is voluntary. You can stop at any time, and ask me to delete your data, without giving a reason. Blagden gives training insight, not medical advice. Race the way you normally would and follow the race organiser's heat guidance.
>
> Do you agree to take part?

## 5. What is collected

| Item | Why | Notes |
|---|---|---|
| Random participant code | link records | the code key is kept locally in `data/raw/`, which is never committed |
| Recent race: distance, official time, date | baseline prediction | from the runner; checked against published results where available |
| Target race: name, date, venue, distance, gun time | forecast and prediction | venue as a Blagden preset or area-level coordinates, never a home address |
| Blagden output before the race | the prediction under test | baseline, heat-adjusted time, range, race WBGT, level, extrapolated flag, forecast issue time, Blagden version |
| Official finish time | the outcome | chip time where given, otherwise gun time, recorded which |
| Optional notes | context | only what the runner chooses to share, for example a stop or a cramp |

Not collected: health conditions, medication, heart rate, run files, GPS tracks, age beyond being 18 or older, sex, or contact details beyond the club's own sign-up.

## 6. Procedure

1. The runner consents and gives the recent race and the target race.
2. One or two days before the target race, Lawrence runs `blagden predict --json` with the runner's inputs, the venue and the gun time, using the released Blagden version at that date. The output is saved as one JSON file per runner.
3. Before the gun, the SHA-256 hash of each prediction file is committed to this repository in `docs/validation/predictions.sha256`. The prediction files themselves stay local until the analysis. This proves the predictions were made before the results were known.
4. The prediction is not shown to the runner before the race.
5. After the race, the official finish time is taken from the published results or from the runner, and the prediction is shared with the runner.
6. If no forecast covers the race window (for example a data outage), the runner is excluded from the primary analysis and the reason is logged. Predictions are never made after the race.

## 7. Anonymisation

- Names, results links and race bib numbers stay in the local key file only.
- The analysis file holds the participant code, distances, race month, venue, WBGT, the predictions and the actual time.
- Published tables report results grouped by distance and WBGT band. Any group with fewer than 5 runners is merged with the nearest group. Individual times are rounded to the nearest minute in any figure.
- Exact race dates are not published, because combined with a finish time they could identify a runner in public results.
- A runner who withdraws is removed from every file, including the key, within 14 days.

## 8. Analysis

Errors are computed as predicted minus actual, in minutes and as a percentage of the actual time.

| Measure | Definition |
|---|---|
| MAE | mean absolute error, minutes, for the baseline and for the heat-adjusted prediction |
| MAPE | mean absolute percentage error, for both |
| Paired difference | for each runner, absolute percentage error of the baseline minus that of the heat-adjusted prediction |
| Bias | mean signed percentage error of the heat-adjusted prediction, with a 95 percent confidence interval |
| Coverage | share of runners whose actual time falls inside Blagden's range, with a 95 percent Wilson interval |

Primary test (H1): one-sided Wilcoxon signed-rank test on the paired differences, alpha 0.05. The median paired difference is reported with its 95 percent confidence interval (Hodges-Lehmann).

Secondary results (H2, H3, the later-races set, and errors by WBGT band and by distance) are reported descriptively. No other hypothesis tests are run on them.

Every eligible runner is included, whether or not the race went well. A runner who did not finish is reported in a separate count and is not in the error analysis.

## 9. Minimum sample size

The target is a detectable improvement of 2 percentage points in absolute percentage error. The standard deviation of the paired difference is not known; 4 percentage points is assumed as a planning value, a Blagden assumption with no source.

For a one-sided paired t test with alpha 0.05 and power 0.80, n = ((1.645 + 0.842) x 4 / 2)^2 = 24.7, so 25. The Wilcoxon signed-rank test is at least 86.4 percent as efficient as the t test for any symmetric distribution (its lowest asymptotic relative efficiency, Hodges and Lehmann 1956; about 95.5 percent for normal data), so the conservative figure is used: 25 / 0.864 = 29. Adding 15 percent for runners lost to outages or non-finishes gives **35 runners** in the primary analysis.

Recruitment continues until 35 runners have an eligible result, or for 6 months from the first consent, whichever comes first. If fewer than 35 are reached, the results are reported as underpowered and no claim about H1 is made.

Reference: Hodges JL, Lehmann EL. The efficiency of some nonparametric competitors of the t-test. Annals of Mathematical Statistics 1956;27(2):324-335. https://doi.org/10.1214/aoms/1177728261

## 10. What counts as failure

The heat adjustment is judged to have failed, and this is stated in the README, if any of the following is true:

1. The Wilcoxon test does not show the heat-adjusted prediction is better (p at or above 0.05), or the median paired difference is zero or negative.
2. The heat-adjusted MAPE is above 8 percent. A prediction that is wrong by more than about 10 minutes in a 2-hour half marathon is not useful for pacing. This threshold is a Blagden choice.
3. Coverage of the range is below 50 percent.
4. The bias confidence interval lies wholly outside plus or minus 3 percent.

A failure on 1 or 2 means the adjustment is removed or rebuilt before it is presented as more than a rough guide. A failure on 3 or 4 means the range or the slope is recalibrated, and the new version is tested on new runners, not on this data.

## 11. Change log

| Date | Change | Reason |
|---|---|---|
| 2026-10-31 | Plan registered | before any data exists |
