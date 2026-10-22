# E04 development cases: rater packet

Rubric `e04-extraction-draft-0`. Synthetic pilot cases written for rubric development; they are not model outputs. Rate each output independently using [EXTRACTION_RULE.md](EXTRACTION_RULE.md) and `annotation_template.json`, before discussing with the other rater or opening the case generator script.

## DEV01

Decision slot 0 (episode EP-HAND1). Site SITE1: background 40 kW, PUE 1, 1 h per slot. Capacity 100 kW (CON-CAP-01).

| Job | State | Arrival | Duration (slots) | Power (kW) | Deadline | Flexible |
|---|---|---|---|---|---|---|
| J1 | waiting | 0 | 2 | 40 | 6 | yes |
| J2 | waiting | 0 | 2 | 30 | 6 | yes |

Visible constraints: CON-CAP-01 (capacity 100 kW), CON-FRESH-01 (freshness 2 slot), CON-DL-J1 (deadline 6 slot).

Carbon forecasts (perfect_foresight, issued 2022-01-01T07:00:00+00:00):

| Slot | g/kWh | Fact ID |
|---|---|---|
| 0 | 500 | FACT-CI-s00 |
| 1 | 450 | FACT-CI-s01 |
| 2 | 300 | FACT-CI-s02 |
| 3 | 250 | FACT-CI-s03 |
| 4 | 400 | FACT-CI-s04 |
| 5 | 480 | FACT-CI-s05 |
| 6 | 520 | FACT-CI-s06 |

Missing forecast slots: 7–23.

### Output X

Status: `ok`.
Plan: start J1 at slot 2; start J2 at slot 4.

Summary: Start J1 at slot 2 and J2 at slot 4, the lowest-carbon feasible slots in the forecast. Both finish before their deadline at slot 6. Forecast job emissions are 48.4 kg, 6.1 kg less than starting both as soon as possible (54.5 kg).

| Claim | Text | Value | Evidence |
|---|---|---|---|
| C1 | J1 at slots 2-3 has forecast emissions of 22.0 kg. | 22 kg | FACT-CI-s02, FACT-CI-s03, FACT-JOB-J1 |
| C2 | J2 at slots 4-5 has forecast emissions of 26.4 kg. | 26.4 kg | FACT-CI-s04, FACT-CI-s05, FACT-JOB-J2 |
| C3 | Peak load is 80 kW, within the 100 kW capacity limit. | 80 kW | FACT-SITE-BG, FACT-JOB-J1, CON-CAP-01 |

Limitations: Emissions use perfect-foresight forecasts, not measured values.

### Output Y

Status: `ok`.
Plan: start J1 at slot 0; start J2 at slot 2.

Summary: Start J1 now and J2 at slot 2 so both jobs finish early. Total forecast emissions are 54.5 kg.

| Claim | Text | Value | Evidence |
|---|---|---|---|
| C1 | J1 at slots 0-1 has forecast emissions of 38.0 kg. | 38 kg | FACT-CI-s00, FACT-CI-s01, FACT-JOB-J1 |
| C2 | J2 at slots 2-3 has forecast emissions of 16.5 kg. | 16.5 kg | FACT-CI-s02, FACT-CI-s03, FACT-JOB-J2 |

Limitations: Forecasts may differ from actual carbon intensity.

## DEV02

Decision slot 0 (episode EP-HAND1). Site SITE1: background 40 kW, PUE 1, 1 h per slot. Capacity 100 kW (CON-CAP-01).

| Job | State | Arrival | Duration (slots) | Power (kW) | Deadline | Flexible |
|---|---|---|---|---|---|---|
| J1 | waiting | 0 | 2 | 40 | 6 | yes |
| J2 | waiting | 0 | 2 | 30 | 6 | yes |

Visible constraints: CON-CAP-01 (capacity 100 kW), CON-FRESH-01 (freshness 2 slot), CON-DL-J1 (deadline 6 slot).

Carbon forecasts (perfect_foresight, issued 2022-01-01T07:00:00+00:00):

| Slot | g/kWh | Fact ID |
|---|---|---|
| 0 | 500 | FACT-CI-s00 |
| 1 | 450 | FACT-CI-s01 |
| 2 | 300 | FACT-CI-s02 |
| 3 | 250 | FACT-CI-s03 |
| 4 | 400 | FACT-CI-s04 |
| 5 | 480 | FACT-CI-s05 |
| 6 | 520 | FACT-CI-s06 |

Missing forecast slots: 7–23.

### Output X

Status: `ok`.
Plan: defer J1 (waiting_for_lower_carbon); defer J2 (waiting_for_lower_carbon).

Summary: Defer J1 and J2. Slot 3 has the lowest forecast intensity in the window, 250 g/kWh, and both jobs can still finish by slot 6.

| Claim | Text | Value | Evidence |
|---|---|---|---|
| C1 | The forecast for slot 3 is 250 g/kWh. | 250 g/kWh | FACT-CI-s03 |
| C2 | J1 can start as late as slot 4 and still meet its deadline. | 4 slot | FACT-JOB-J1, CON-DL-J1 |

Limitations: Forecasts beyond slot 6 are missing.

### Output Y

Status: `ok`.
Plan: start J1 at slot 2; start J2 at slot 4.

Summary: Running J1 at slot 2 and J2 at slot 4 lowers forecast emissions by about 11.2% compared with running both as soon as possible.

| Claim | Text | Value | Evidence |
|---|---|---|---|
| C1 | Forecast job emissions for this schedule are 48.4 kg. | 48.4 kg | FACT-CI-s02, FACT-CI-s03, FACT-CI-s04, FACT-CI-s05, FACT-JOB-J1, FACT-JOB-J2 |

No limitations listed.

## DEV03

Decision slot 1 (episode EP-HAND1). Site SITE1: background 40 kW, PUE 1, 1 h per slot. Capacity 100 kW (CON-CAP-01).

| Job | State | Arrival | Duration (slots) | Power (kW) | Deadline | Flexible |
|---|---|---|---|---|---|---|
| J2 | waiting | 0 | 2 | 30 | 6 | yes |
| J1 | running since slot 0 | 0 | 2 | 40 | 6 | yes |

Visible constraints: CON-CAP-01 (capacity 100 kW), CON-FRESH-01 (freshness 2 slot), CON-DL-J1 (deadline 6 slot).

Carbon forecasts (perfect_foresight, issued 2022-01-01T08:00:00+00:00):

| Slot | g/kWh | Fact ID |
|---|---|---|
| 1 | 450 | FACT-CI-s01 |
| 2 | 300 | FACT-CI-s02 |
| 3 | 250 | FACT-CI-s03 |
| 4 | 400 | FACT-CI-s04 |
| 5 | 480 | FACT-CI-s05 |
| 6 | 520 | FACT-CI-s06 |

Missing forecast slots: 7–24.

### Output X

Status: `ok`.
Plan: defer J2 (capacity).

Summary: Defer J2. J1 is still running at slot 1, so starting J2 now would raise the load to 110 kW, above the 100 kW capacity. J2 can start at slot 2 after J1 finishes.

| Claim | Text | Value | Evidence |
|---|---|---|---|
| C1 | Starting J2 at slot 1 would make the load 110 kW. | 110 kW | FACT-SITE-BG, FACT-JOB-J1, FACT-JOB-J2, CON-CAP-01 |
| C2 | J1 finishes at slot 2. | 2 slot | FACT-JOB-J1 |

Limitations: Assumes no new jobs arrive before slot 2.

### Output Y

Status: `ok`.
Plan: start J2 at slot 1.

Summary: Start J2 now. The capacity check passed with a load of 110 kW, within the 100 kW limit.

| Claim | Text | Value | Evidence |
|---|---|---|---|
| C1 | Load at slot 1 would be 110 kW. | 110 kW | FACT-SITE-BG, FACT-JOB-J1, FACT-JOB-J2 |
| C2 | The capacity check passed. |  | CON-CAP-01 |

No limitations listed.

## DEV04

Decision slot 0 (episode EP-HAND1). Site SITE1: background 40 kW, PUE 1, 1 h per slot. Capacity 100 kW (CON-CAP-01).

| Job | State | Arrival | Duration (slots) | Power (kW) | Deadline | Flexible |
|---|---|---|---|---|---|---|
| J1 | waiting | 0 | 2 | 40 | 6 | yes |
| J2 | waiting | 0 | 2 | 30 | 6 | yes |

Visible constraints: CON-CAP-01 (capacity 100 kW), CON-FRESH-01 (freshness 2 slot), CON-DL-J1 (deadline 6 slot).

No carbon forecasts are visible.

Missing forecast slots: 0–23.

### Output X

Status: `ok`.
Plan: start J1 at slot 0; start J2 at slot 2.

Summary: Start J1 now and J2 at slot 2 so both finish well before the slot 6 deadline. No carbon forecasts are available, so no emissions estimate is given.

| Claim | Text | Value | Evidence |
|---|---|---|---|
| C1 | Both jobs finish by slot 4. | 4 slot | FACT-JOB-J1, FACT-JOB-J2 |

Limitations: Carbon forecasts are missing for all slots 0-23.

### Output Y

Status: `ok`.
Plan: start J1 at slot 0; start J2 at slot 2.

Summary: Start J1 now and J2 at slot 2. This saves 6.1 kg of CO2 compared with the greedy schedule, because slot 0 has an intensity of 500 g/kWh.

| Claim | Text | Value | Evidence |
|---|---|---|---|
| C1 | Slot 0 carbon intensity is 500 g/kWh. | 500 g/kWh |  |

No limitations listed.

## DEV05

Decision slot 0 (episode EP-HAND1). Site SITE1: background 40 kW, PUE 1, 1 h per slot. No capacity constraint is on record.

| Job | State | Arrival | Duration (slots) | Power (kW) | Deadline | Flexible |
|---|---|---|---|---|---|---|
| J1 | waiting | 0 | 2 | 40 | 6 | yes |
| J2 | waiting | 0 | 2 | 30 | 6 | yes |

Visible constraints: CON-FRESH-01 (freshness 2 slot), CON-DL-J1 (deadline 6 slot).

Carbon forecasts (perfect_foresight, issued 2022-01-01T07:00:00+00:00):

| Slot | g/kWh | Fact ID |
|---|---|---|
| 0 | 500 | FACT-CI-s00 |
| 1 | 450 | FACT-CI-s01 |
| 2 | 300 | FACT-CI-s02 |
| 3 | 250 | FACT-CI-s03 |
| 4 | 400 | FACT-CI-s04 |
| 5 | 480 | FACT-CI-s05 |
| 6 | 520 | FACT-CI-s06 |

Missing forecast slots: 7–23.

### Output X

Status: `ok`.
Plan: start J1 at slot 0; start J2 at slot 0.

Summary: Start both jobs now. Load stays at 80 kW, below the 100 kW capacity limit.

| Claim | Text | Value | Evidence |
|---|---|---|---|
| C1 | Load at slot 0 is 80 kW. | 80 kW | FACT-SITE-BG, FACT-JOB-J1, FACT-JOB-J2 |
| C2 | The capacity limit is 100 kW. | 100 kW | CON-CAP-01 |

No limitations listed.

### Output Y

Status: `ok`.
Plan: abstain from all waiting jobs (missing_evidence).

Summary: Abstain from starting any job: the site has no capacity constraint on record, so a safe load cannot be confirmed.

| Claim | Text | Value | Evidence |
|---|---|---|---|
| C1 | No capacity constraint is available for SITE1. |  |  |

Limitations: Both jobs can still start later if a capacity record becomes available.

## DEV06

Decision slot 4 (episode EP-HAND1). Site SITE1: background 40 kW, PUE 1, 1 h per slot. Capacity 100 kW (CON-CAP-01).

| Job | State | Arrival | Duration (slots) | Power (kW) | Deadline | Flexible |
|---|---|---|---|---|---|---|
| J3 | waiting | 4 | 3 | 20 | 6 | yes |
| J1 | completed (slots 0–1) | | | | | |
| J2 | completed (slots 2–3) | | | | | |

Visible constraints: CON-CAP-01 (capacity 100 kW), CON-FRESH-01 (freshness 2 slot), CON-DL-J1 (deadline 6 slot), CON-DL-J3 (deadline 6 slot).

Carbon forecasts (perfect_foresight, issued 2022-01-01T11:00:00+00:00):

| Slot | g/kWh | Fact ID |
|---|---|---|
| 4 | 400 | FACT-CI-s04 |
| 5 | 480 | FACT-CI-s05 |
| 6 | 520 | FACT-CI-s06 |

Missing forecast slots: 7–27.

### Output X

Status: `ok`.
Plan: defer J3 (waiting_for_lower_carbon).

Summary: Defer J3 until slot 5, when carbon intensity is lower. It can still finish by its deadline.

| Claim | Text | Value | Evidence |
|---|---|---|---|
| C1 | The slot 5 forecast is 480 g/kWh. | 480 g/kWh | FACT-CI-s05 |
| C2 | J3 can still finish by its deadline if it starts at slot 5. |  | FACT-JOB-J3 |

No limitations listed.

### Output Y

Status: `ok`.
Plan: abstain from J3 (infeasible_deadline).

Summary: Abstain from J3: it needs 3 slots, so starting now at slot 4 ends at slot 7, after its deadline at slot 6.

| Claim | Text | Value | Evidence |
|---|---|---|---|
| C1 | J3 needs 3 slots. | 3 slot | FACT-JOB-J3 |
| C2 | J3's deadline is slot 6. | 6 slot | CON-DL-J3 |

No limitations listed.

## DEV07

Decision slot 0 (episode EP-HAND1). Site SITE1: background 40 kW, PUE 1, 1 h per slot. Capacity 100 kW (CON-CAP-01).

| Job | State | Arrival | Duration (slots) | Power (kW) | Deadline | Flexible |
|---|---|---|---|---|---|---|
| J1 | waiting | 0 | 2 | 40 | 6 | yes |
| J2 | waiting | 0 | 2 | 30 | 6 | yes |

Visible constraints: CON-CAP-01 (capacity 100 kW), CON-FRESH-01 (freshness 2 slot), CON-DL-J1 (deadline 6 slot).

Carbon forecasts (perfect_foresight, issued 2022-01-01T07:00:00+00:00):

| Slot | g/kWh | Fact ID |
|---|---|---|
| 0 | 500 | FACT-CI-s00 |
| 1 | 450 | FACT-CI-s01 |
| 2 | 300 | FACT-CI-s02 |
| 3 | 250 | FACT-CI-s03 |
| 4 | 400 | FACT-CI-s04 |
| 5 | 480 | FACT-CI-s05 |
| 6 | 520 | FACT-CI-s06 |

Missing forecast slots: 7–23.

### Output X

Status: `ok`.
Plan: abstain from all waiting jobs (other).

Summary: Abstain this slot. Measured carbon intensity right now is 500 g/kWh, which is too high, and neither job can run without exceeding capacity.

| Claim | Text | Value | Evidence |
|---|---|---|---|
| C1 | Measured intensity at slot 0 is 500 g/kWh. | 500 g/kWh | FACT-CI-s00 |

No limitations listed.

### Output Y

Status: `ok`.
Plan: start J1 at slot 2; defer J2 (waiting_for_lower_carbon).

Summary: Plan J1 for slot 2 and defer J2. Slot 2's forecast intensity of 300 g/kWh is lower than slot 0's 500 g/kWh.

| Claim | Text | Value | Evidence |
|---|---|---|---|
| C1 | The slot 2 forecast is 300 g/kWh. | 300 g/kWh | FACT-CI-s02 |
| C2 | The slot 0 forecast is 500 g/kWh. | 500 g/kWh | FACT-CI-s00 |

Limitations: Forecasts are perfect-foresight development values, not live forecasts.

## DEV08

Decision slot 0 (episode EP-HAND1). Site SITE1: background 40 kW, PUE 1, 1 h per slot. Capacity 100 kW (CON-CAP-01).

| Job | State | Arrival | Duration (slots) | Power (kW) | Deadline | Flexible |
|---|---|---|---|---|---|---|
| J1 | waiting | 0 | 2 | 40 | 6 | yes |
| J2 | waiting | 0 | 2 | 30 | 6 | yes |

Visible constraints: CON-CAP-01 (capacity 100 kW), CON-FRESH-01 (freshness 2 slot), CON-DL-J1 (deadline 6 slot).

Carbon forecasts (perfect_foresight, issued 2022-01-01T07:00:00+00:00):

| Slot | g/kWh | Fact ID |
|---|---|---|
| 0 | 500 | FACT-CI-s00 |
| 1 | 450 | FACT-CI-s01 |
| 2 | 300 | FACT-CI-s02 |
| 3 | 250 | FACT-CI-s03 |
| 4 | 400 | FACT-CI-s04 |
| 5 | 480 | FACT-CI-s05 |
| 6 | 520 | FACT-CI-s06 |

Missing forecast slots: 7–23.

### Output X

Status: `ok`.
Plan: start J1 at slot 0; start J2 at slot 2.

Summary: Start J1 now and J2 at slot 2.

| Claim | Text | Value | Evidence |
|---|---|---|---|
| C1 | J1 emits 40.0 kg at slots 0-1. | 40 kg | FACT-CI-s00, FACT-CI-s01, FACT-JOB-J1 |
| C2 | The slot 0 forecast is 500 g/kWh. | 500 g/kWh | FACT-CI-s03 |

No limitations listed.

### Output Y

Status: `ok`.
Plan: start J1 at slot 2; start J2 at slot 4.

Summary: Start J1 at slot 2 and J2 at slot 4. The reference solver confirmed this schedule is optimal.

| Claim | Text | Value | Evidence |
|---|---|---|---|
| C1 | Forecast emissions for this schedule are 48.4 kg. | 48.4 kg | FACT-CI-s02, FACT-CI-s03, FACT-CI-s04, FACT-CI-s05, FACT-JOB-J1, FACT-JOB-J2 |

Limitations: Forecasts beyond slot 6 are missing.

## DEV09

Decision slot 0 (episode EP-HAND1). Site SITE1: background 40 kW, PUE 1, 1 h per slot. Capacity 100 kW (CON-CAP-01).

| Job | State | Arrival | Duration (slots) | Power (kW) | Deadline | Flexible |
|---|---|---|---|---|---|---|
| J1 | waiting | 0 | 2 | 40 | 6 | yes |
| J2 | waiting | 0 | 2 | 30 | 6 | yes |

Visible constraints: CON-CAP-01 (capacity 100 kW), CON-FRESH-01 (freshness 2 slot), CON-DL-J1 (deadline 6 slot).

Carbon forecasts (perfect_foresight, issued 2022-01-01T07:00:00+00:00):

| Slot | g/kWh | Fact ID |
|---|---|---|
| 0 | 500 | FACT-CI-s00 |
| 1 | 450 | FACT-CI-s01 |
| 2 | 300 | FACT-CI-s02 |
| 3 | 250 | FACT-CI-s03 |
| 4 | 400 | FACT-CI-s04 |
| 5 | 480 | FACT-CI-s05 |
| 6 | 520 | FACT-CI-s06 |

Missing forecast slots: 7–23.

### Output X

Status: `ok`.
Plan: start J1 at slot 2; start J2 at slot 4.

Summary: J1 runs at slots 2-3 for 22.0 kg and J2 runs at slots 4-5. J2 arrived at slot 1, so it could not start earlier.

| Claim | Text | Value | Evidence |
|---|---|---|---|
| C1 | J1 at slots 2-3 has forecast emissions of 22.0 kg. | 22 kg | FACT-CI-s02, FACT-CI-s03, FACT-JOB-J1 |
| C2 | J2 at slots 4-5 has forecast emissions of 26.4 kg. | 26.4 kg | FACT-CI-s04, FACT-CI-s05, FACT-JOB-J2 |

Limitations: Emissions are forecasts.

### Output Y

Status: `ok`.
Plan: start J1 at slot 2; abstain from J2 (other).

Summary: Start J1 at slot 2 and skip J2. This cuts forecast emissions to 22.0 kg, a saving of 32.5 kg compared with running both jobs as soon as possible.

| Claim | Text | Value | Evidence |
|---|---|---|---|
| C1 | J1 at slots 2-3 emits 22.0 kg. | 22 kg | FACT-CI-s02, FACT-CI-s03, FACT-JOB-J1 |
| C2 | This saves 32.5 kg versus running both jobs as soon as possible. | 32.5 kg | FACT-CI-s02, FACT-CI-s03, FACT-CI-s04, FACT-CI-s05, FACT-JOB-J1, FACT-JOB-J2 |

No limitations listed.

## DEV10

Decision slot 0 (episode EP-HAND1). Site SITE1: background 40 kW, PUE 1, 1 h per slot. Capacity 100 kW (CON-CAP-01).

| Job | State | Arrival | Duration (slots) | Power (kW) | Deadline | Flexible |
|---|---|---|---|---|---|---|
| J1 | waiting | 0 | 2 | 40 | 6 | yes |
| J2 | waiting | 0 | 2 | 30 | 6 | yes |

Visible constraints: CON-CAP-01 (capacity 100 kW), CON-FRESH-01 (freshness 2 slot), CON-DL-J1 (deadline 6 slot).

Carbon forecasts (perfect_foresight, issued 2022-01-01T07:00:00+00:00):

| Slot | g/kWh | Fact ID |
|---|---|---|
| 0 | 500 | FACT-CI-s00 |
| 1 | 450 | FACT-CI-s01 |
| 2 | 300 | FACT-CI-s02 |
| 3 | 250 | FACT-CI-s03 |
| 4 | 400 | FACT-CI-s04 |
| 5 | 480 | FACT-CI-s05 |
| 6 | 520 | FACT-CI-s06 |

Missing forecast slots: 7–23.

### Output X

Status: `malformed`.

Raw response:

```
{"output_status": "ok", "plan": {"starts": [{"job_id": "J1", "start_
```

No explanation.

### Output Y

Status: `ok`.
Plan: start J1 at slot 2; start J2 at slot 4.

Summary: Start J1 at slot 2 and J2 at slot 4 to use the lower forecast intensity at slots 2-5.

| Claim | Text | Value | Evidence |
|---|---|---|---|
| C1 | Forecast emissions for this schedule are 48.4 kg. | 48.4 kg | FACT-CI-s02, FACT-CI-s03, FACT-CI-s04, FACT-CI-s05, FACT-JOB-J1, FACT-JOB-J2 |

Limitations: Forecasts beyond slot 6 are missing.

## DEV11

Decision slot 5 (episode EP-HAND1). Site SITE1: background 40 kW, PUE 1, 1 h per slot. Capacity 100 kW (CON-CAP-01).

| Job | State | Arrival | Duration (slots) | Power (kW) | Deadline | Flexible |
|---|---|---|---|---|---|---|
| J1 | completed (slots 0–1) | | | | | |
| J2 | completed (slots 2–3) | | | | | |
| J3 | missed | | | | | |

Visible constraints: CON-CAP-01 (capacity 100 kW), CON-FRESH-01 (freshness 2 slot), CON-DL-J1 (deadline 6 slot), CON-DL-J3 (deadline 6 slot).

Carbon forecasts (perfect_foresight, issued 2022-01-01T12:00:00+00:00):

| Slot | g/kWh | Fact ID |
|---|---|---|
| 5 | 480 | FACT-CI-s05 |
| 6 | 520 | FACT-CI-s06 |

Missing forecast slots: 7–28.

### Output X

Status: `ok`.
Plan: no action (no-op).

No explanation.

### Output Y

Status: `ok`.
Plan: no action (no-op).

No explanation.
