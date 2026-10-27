# E05 agreement between the two original ratings, and the adjudication record

Task ID / Issue: E05, [issue #42](https://github.com/ReymoT/data-center-agentic/issues/42); Q10 analysis rules in [#22](https://github.com/ReymoT/data-center-agentic/issues/22) (Ved's A1: extraction agreement reported separately from label agreement, percent agreement and Cohen's kappa on assertions both raters found, undefined kappa reported as undefined).
Human owner / technical contacts if needed: Nisha Mahadev Kolekar (nkolekar-nk), E05 receiving lead; Matty (MattyAnd), E05 owner and second rater; Ved (vedp3705) for the analysis rules.
Objective: compare two unchanged original ratings files and produce an empty joint adjudication record, without deciding any label.
Base commit / branch: base `be87f58` on main; branch `nisha/e05-agreement`.

Changed paths:
- `dc_sustainability/evaluation/agreement.py` (new): `load_original`, `compare`, `cohens_kappa`, `summary`, `adjudication_record`, `validate_adjudication`.
- `scripts/compare_e05_ratings.py` (new): runs the comparison on two files and writes `agreement_report.json` and `adjudication.json`.
- `tests/evaluation/test_agreement.py` (new, 21 tests).
- `docs/handoffs/E05_AGREEMENT.md` (this file).

What it does:
- `load_original` refuses a file for another rubric, without a rater, with a missing, repeated or unknown output, or failing the complete structural check. Its SHA256 is taken over LF line endings, the way originals are committed, so a Windows checkout with CRLF conversion gives the published hash (Matty's working copy hashes to `ff05…` raw but `3b3e0c75…` as published).
- `compare` matches claim assertions by their shared F02 claim ID. Summary and limitation IDs are each rater's own numbering, so a match between them is a human judgement passed as explicit (a ID, b ID) pairs per output; unmatched ones are reported as found by one rater only. Each ID can be matched once.
- Reported separately: extraction agreement over summary/limitation assertions (both / only a / only b, agreement = both ÷ all, None when there are none); label agreement on all matched assertions and on claims only (n, agreed, percent, kappa); completeness agreement per part. Empty-queue no-ops are counted and left out. Kappa is None when there are no pairs or when chance agreement is 1.
- `adjudication_record` lists every disagreement undecided: label differences, one-sided assertions (keep with a label, or drop) and completeness differences. It is bound to both originals' hashes. `validate_adjudication` accepts it only with at least two adjudicators, the same originals and items, and a decision and rationale for every item. The originals are never edited.

Tests: hand-computed kappa (0.6875 on a five-pair example; exactly 0 when one of 32 claims differs and the other rater used one label); undefined kappa; hash taken from exact bytes and equal to the LF hash on a CRLF copy; incomplete or partial originals refused; extraction agreement with and without explicit matches; invalid or repeated matches refused; completeness per part; JSON report with None kept; adjudication items, acceptance when complete, and refusal when undecided, missing a rationale, with one adjudicator, bound to other originals, or with items changed.
- Mutation check: six deliberate bugs each made tests fail, and the code was restored: kappa without the (1 − pe) denominator, kappa never undefined, claims counted as extraction agreement, no-ops included, one adjudicator accepted, claims left unmatched.

Consumer check on the real originals (not committed; results to be posted by the raters): Nisha `cf8543ae…ef4b3` against Matty `3b3e0c75…6f16a`, both validated complete. 2 no-ops excluded. Claim labels: 32 matched, 24 agreed (75.0%), kappa 0.0, because one original uses a single label for every claim, so chance agreement equals observed agreement. Extraction: 0 matched, 0 only Nisha, 64 only Matty (57 summary, 7 limitation), agreement 0.0. Completeness agreement: decision 20/20, reason 18/20, evidence 18/20, limitations 19/20. The empty adjudication record has 77 items: 8 label, 64 extraction and 5 completeness.

Input and output contract/config versions: F02 1.0.0 and rubric `e04-extraction-draft-0`, unchanged.
Artifact locations and checksums: none committed. The originals are read only.

Exact reproduction commands:

```powershell
.venv\Scripts\python.exe -m pytest tests/evaluation/test_agreement.py -q
.venv\Scripts\python.exe scripts/compare_e05_ratings.py --a docs/e04/ratings/originals/E05_Nisha_2026-10-26.json --b docs/e04/ratings/originals/E05_Matty_2026-10-22.json --out-dir ..\e05-comparison
.venv\Scripts\python.exe -m pytest tests -q
.venv\Scripts\python.exe -m ruff check dc_sustainability scripts tests
.venv\Scripts\python.exe -m ruff format --check dc_sustainability scripts tests
```

Tests actually run and observed results: Windows 11, Python 3.12.10, hashed lock. Full suite 1,401 tests and 19 subtests passed (1,380 on main before); Ruff check/format, compileall, setup validation and pip check passed.

Limitations and open decisions:
- Matching summary/limitation assertions between raters is a human step; the raters supply the pairs before agreement is final. No text similarity is used.
- Supporting-citation choices and `restated_in_summary` are not yet compared; they feed coverage and precision and could be added.
- Kappa on labels can be 0 or undefined when labels are very unbalanced, as here; percent agreement and the counts are always reported with it.
- The adjudication record is a working file for the two raters; where it is published, and how adjudicated labels feed the final metrics, is Matty's E05 decision.

Receiving owner and consumer check: Matty, for E05 receiving and the adjudication session; Ved, to confirm the agreement statistics match A1.
