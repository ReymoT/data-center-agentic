# E04 calibration: practice packet (rule §11.8)

Rubric `e04-extraction-draft-0` with the draft 1 clarifications in section 11. Two hand-written practice outputs, not model outputs, and neither development nor held-out cases. Each rater **extracts independently** from both outputs into `annotation_template.json`, following [EXTRACTION_RULE.md](../EXTRACTION_RULE.md) section 11, before discussing with the other rater or opening the generator script. Labels and completeness may be filled in, but only extraction is compared.

## CAL01

Decision slot 1 (episode EP-HAND1). Site SITE1: background 40 kW, PUE 1, 1 h per slot. Capacity 100 kW (CON-CAP-01).

| Job | State | Arrival | Duration (slots) | Power (kW) | Deadline | Flexible |
|---|---|---|---|---|---|---|
| J1 | waiting | 0 | 2 | 40 | 6 | yes |
| J2 | waiting | 0 | 2 | 30 | 6 | yes |

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

Status: `malformed`.

Raw response:

```
Start J1 and J2 now at slot 1. Load would be 110 kW, under the 100 kW limit. {"output_status": "ok", "plan": {"starts": [{"job_id": "J1", "start_slot": 1}, {"job_id": "J2", "start_
```

No explanation.

### Output Y

Status: `ok`.
Plan: start J1 at slot 2; start J2 at slot 4.

Summary: Wait one more slot and start J1 at slot 2, then J2 at slot 4. J1 uses 80 kWh over slots 2-3 and emits 22.0 kg. Starting J1 now at slot 1 would emit 30.0 kg instead, because slot 1 is 450 g/kWh. Peak site load stays at 80 kW. The goal is to keep emissions as low as possible.

| Claim | Text | Value | Evidence |
|---|---|---|---|
| C1 | J1 at slots 2-3 emits 22.0 kg. | 22 kg | FACT-CI-s02, FACT-CI-s03, FACT-JOB-J1 |
| C2 | J2 at slots 4-5 emits 26.4 kg. | 26.4 kg | FACT-CI-s04, FACT-CI-s05, FACT-JOB-J2 |
| C3 | The slot 3 forecast is 250 g/kWh. | 250 g/kWh | FACT-CI-s03 |

Limitations: Forecasts are perfect-foresight development values.; J2 must finish by slot 6, so starting it after slot 4 would miss its deadline.
