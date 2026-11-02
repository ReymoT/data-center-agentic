# Q22 decisions, synthetic custody receiving and combined status

Matty explicitly approved Nisha's six proposals after reviewing the submission
package and instructed implementation, custody receiving and status refresh.
Base main: `cf7bfbd6d1458f7e4e696d3804e3eadced01c71d`, instruction 1.28.

Both calibration originals are now published and hash-pinned; Nisha's file is
no longer missing. The reproduced comparison has 3 agreeing shared claims,
9 summary/limitation assertions only in Matty's file and 5 raw assertions only
in Matty's file. There are no S/L/R pairs to match because Nisha extracted none.
Kappa on the three shared claims is undefined. Original judgments are unchanged.

The [accepted rule clarification](../e04/EXTRACTION_RULE.md) records all six
decisions. Prospective per-unit coverage is enforced through the strict validator
and comparison CLI option; legacy originals/reports retain their old path.
This completes the calibration and clarification step without claiming improved
agreement. #22 can close after checks as implemented design/calibration work;
actual held-out sampling, source acceptance and freeze remain separately gated.

Custody receiving uses a synthetic receipt only. An independent test reconstructs
SHA ranking using standard-library functions, skips repeated months and independently
forms UTC timestamp sets for each complete 30-hour window. It reproduces the six
dates/30 records and verifies isolation against the fixed development windows.
Existing prepare/verify, tamper, junction/hard-link and interval regressions run too.
This is Matty technical receiving, not Nisha's actual-storage acceptance. No actual
private seed, destination, cohort or episode content is generated.

Current handoffs:

- Nisha: strict prospective annotation intake; actual storage/custody and final
  freeze/sample receiving remain. #95 held-out reliability and #16 verified course
  requirements remain open.
- Reimo/Ved: source investigation and custody tooling delivered in PR #148;
  #60 still needs authoritative facts and actual custody/scientific acceptance.
- Edison: real C/D artifacts and provenance still gate full I01; offline cache
  consumer receiving is completed in PR #144.
- Matty: R04 development draft/backup evidence prepared. Full I01/I04 and final
  release remain pending their real dependencies.

No model calls, real-corpus training, source permission or scientific freeze is
claimed. Task ownership and scientific run settings are unchanged.
