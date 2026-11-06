# Copy review: race-morning brief

Every user-facing string the brief templates can produce, in English and Taglish, for Lawrence's approval. The source of truth is `shared/brief_templates.json`; a test checks that this file quotes it exactly. Placeholders in braces are filled only from Facts (`blagden.brief.facts`).

Status of every string: **pending review**. Mark a row approved, or write the wording you want, and the template file will be updated to match.

## Points that need a decision

1. **Hydration reminder.** docs/SCIENCE.md has no sourced fluid guidance. The reminder only says when to use every aid station: from the time the humidity-corrected risk reaches "high" (Racinais 2015). No volumes or rates are given. Approve this, or ask for a sourced hydration section (for example the ACSM fluid replacement position stand) before release.
2. **Pace cap.** The cap is the even pace for the heat-adjusted point estimate. It is not split by kilometre, because nothing in SCIENCE.md supports a split.
3. **Heart-rate advice.** The second voice example ("back off if your heart rate passes 175 before km 15") is not used. No source in SCIENCE.md gives a heart-rate threshold, and the grounding check would reject any such number.
4. **"Cooler than usual".** The cool wording says "cooler start" and "cooler morning" but not "than usual", because Blagden has no climatology to compare with.
5. **Band names.** The risk band names come from the Racinais humidity-corrected levels, written as below.

## Sentences

Shown in the order they appear in a brief. Only the sentences whose condition holds are used.

### `start_hot_rise`

Used when: Start WBGT is 23 C or more and the humidity-corrected risk level rises during the race. {rise_time} is the first minute of the higher level, rounded down to 5 minutes.

- English: `Start is {start_time} at WBGT {start_wbgt}, already in the {start_band} band, and in the {rise_band} band by {rise_time}.`
- Taglish: `{start_time} ang start, WBGT {start_wbgt} na, nasa {start_band} band na agad, at {rise_band} na pagdating ng {rise_time}.`
- Status: pending review

### `start_hot_flat`

Used when: Start WBGT is 23 C or more and the level does not rise before the predicted finish.

- English: `Start is {start_time} at WBGT {start_wbgt}, in the {start_band} band for your whole race.`
- Taglish: `{start_time} ang start, WBGT {start_wbgt}, nasa {start_band} band buong takbo mo.`
- Status: pending review

### `start_cool_until`

Used when: Start WBGT is under 23 C (below the red flag) and reaches 23 C before the predicted finish.

- English: `Cooler start: WBGT stays under {cool_threshold} until {cool_until}.`
- Taglish: `Mas presko sa umpisa: WBGT below {cool_threshold} hanggang {cool_until}.`
- Status: pending review

### `start_cool_all`

Used when: Start WBGT is under 23 C and stays there until the predicted finish.

- English: `Cooler morning: WBGT stays under {cool_threshold} for your whole race.`
- Taglish: `Presko ngayong umaga: WBGT below {cool_threshold} buong takbo mo.`
- Status: pending review

### `pace`

Used when: A heat-adjusted prediction exists. {pace_cap} is the predicted time divided by the distance, the even pace for the point estimate.

- English: `Cap your pace at {pace_cap} per km, the pace for a heat-adjusted finish of {finish}, likely {finish_low} to {finish_high}.`
- Taglish: `Huwag bibilis sa {pace_cap} per km, ang pace para sa heat-adjusted na finish na {finish}, malamang {finish_low} hanggang {finish_high}.`
- Status: pending review

### `drink_from_km`

Used when: The humidity-corrected level reaches "high" during the race. {drink_km} is the last whole km before that time at the capped pace.

- English: `Drink at every station after km {drink_km}.`
- Taglish: `Uminom sa bawat water station pagkalampas ng km {drink_km}.`
- Status: pending review

### `drink_from_start`

Used when: The level is already "high" or worse at the start.

- English: `Drink at every station from the start.`
- Taglish: `Uminom sa bawat water station mula sa simula.`
- Status: pending review

### `heat_index`

Used when: Always, when the heat index is available. {hi_peak} is the highest hourly value in the race window, rounded to a whole degree.

- English: `Heat index peaks at {hi_peak} C, PAGASA {hi_category}.`
- Taglish: `Aabot sa {hi_peak} C ang heat index, PAGASA {hi_category}.`
- Status: pending review

### `extrapolated`

Used when: The prediction is flagged as extrapolated (WBGT above 25 C, or a non-elite runner slower than a 3:40 marathon equivalent).

- English: `This morning is hotter than the races the estimate was built on, so treat the range as rough.`
- Taglish: `Mas mainit ito kaysa sa mga karerang pinagbatayan ng estimate, kaya tantiya lang ang range.`
- Status: pending review

### `closing`

Used when: Always.

- English: `Training insight, not medical advice.`
- Taglish: `Training insight ito, hindi medical advice.`
- Status: pending review

## Band names

| Level (Racinais 2015) | English | Taglish | Status |
|---|---|---|---|
| below moderate | `lower-risk` | `lower-risk` | pending review |
| moderate | `moderate-risk` | `moderate-risk` | pending review |
| high | `high-risk` | `high-risk` | pending review |
| excessive | `excessive-risk` | `excessive-risk` | pending review |

## Example briefs

Rendered from the three test snapshots in `tests/data/briefs/`.

**hot_rise_half, English**

> Start is 5:00 AM at WBGT 24.7, already in the moderate-risk band, and in the high-risk band by 6:30 AM. Cap your pace at 6:00 per km, the pace for a heat-adjusted finish of 2:06:42, likely 2:03:05 to 2:10:54. Drink at every station after km 14. Heat index peaks at 31 C, PAGASA Caution. This morning is hotter than the races the estimate was built on, so treat the range as rough. Training insight, not medical advice.

**hot_rise_half, Taglish**

> 5:00 AM ang start, WBGT 24.7 na, nasa moderate-risk band na agad, at high-risk na pagdating ng 6:30 AM. Huwag bibilis sa 6:00 per km, ang pace para sa heat-adjusted na finish na 2:06:42, malamang 2:03:05 hanggang 2:10:54. Uminom sa bawat water station pagkalampas ng km 14. Aabot sa 31 C ang heat index, PAGASA Caution. Mas mainit ito kaysa sa mga karerang pinagbatayan ng estimate, kaya tantiya lang ang range. Training insight ito, hindi medical advice.

**cool_10k, English**

> Cooler start: WBGT stays under 23 until 6:45 AM. Cap your pace at 5:13 per km, the pace for a heat-adjusted finish of 0:52:10, likely 0:51:40 to 0:52:45. Heat index peaks at 28 C, PAGASA Caution. Training insight, not medical advice.

**cool_10k, Taglish**

> Mas presko sa umpisa: WBGT below 23 hanggang 6:45 AM. Huwag bibilis sa 5:13 per km, ang pace para sa heat-adjusted na finish na 0:52:10, malamang 0:51:40 hanggang 0:52:45. Aabot sa 28 C ang heat index, PAGASA Caution. Training insight ito, hindi medical advice.

**hot_flat_no_prediction, English**

> Start is 6:00 AM at WBGT 28.6, in the excessive-risk band for your whole race. Heat index peaks at 35 C, PAGASA Extreme Caution. Training insight, not medical advice.

**hot_flat_no_prediction, Taglish**

> 6:00 AM ang start, WBGT 28.6, nasa excessive-risk band buong takbo mo. Aabot sa 35 C ang heat index, PAGASA Extreme Caution. Training insight ito, hindi medical advice.
