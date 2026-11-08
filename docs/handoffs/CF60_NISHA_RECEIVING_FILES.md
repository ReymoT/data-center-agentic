# Nisha's supplied CF60 receiving files

The four original files delivered by Matty on November 8 now support Nisha's
[accepted receiving PASS](https://github.com/ReymoT/data-center-agentic/pull/187#issuecomment-6717438876)
for broker commit c09167451d66cf51018f8eb30278abd700286f57.
They corroborate the existing acceptance. No new broker acceptance or study
execution is inferred from their arrival.

[The verification record](../evidence/cf60-nisha-file-verification.json) retains
raw SHA-256 hashes for all four files. Originals are unchanged:

- [Synthetic harness output](../evidence/cf60-nisha-2026-11-08/cf60-nisha-receiving.json)
- [Independent checking script](../evidence/cf60-nisha-2026-11-08/cf60_independent.py)
- [Command output](../evidence/cf60-nisha-2026-11-08/cf60-commands-output.txt)
- [Independent report](../evidence/cf60-nisha-2026-11-08/cf60-independent-report.json)

Matty compared the supplied harness JSON with the published producer output:
all fields match. After reading the script, he ran it in the separately pinned
archive and reproduced the supplied report exactly: 66 checks passed, no problems.
The script writes its report and temporarily patches the synthetic reader for
fault injection, restoring it afterward. It does not read a real CSV.

The report's commit field is a literal in the script, so that field alone does
not authenticate the executed checkout. The manager replay used the pinned
archive. Eligibility checking samples issue times every seven hours across the
year. The history-footprint calculation calls the production candidates()
function, so that part is not a wholly independent implementation. Matty also
checked all forty histories directly using interval arithmetic: start-labelled
reads span anchor minus five through anchor plus twenty-six, and end-labelled
reads span anchor minus four through anchor plus twenty-seven. Both matched
the supplied footprints, along with legacy reads and both scoring windows.

The command log records 18 broker tests, 153 focused passes with two skips, and
2,099 full-suite passes with three skips and 19 passing subtests. These are
Nisha's recorded results at the reviewed commit. The Windows symlink skips
supply no OS custody evidence. Her checking script is retained as an original
review artifact rather than adopted as production tooling.

Real-source acquisition, permissions, OS custody, selector amendment,
O02/Q08 and C/D compatibility, and scientific freeze remain separate gates.
The [comparison driver](CF60_COMPARISON_DRIVER.md) still requires exact permitted
private inputs and a single-use bounded authorization.
