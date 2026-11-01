# Matty calibration submission

Matty supplied his completed CAL01 X/Y calibration on October 31, 2026 for #22.
The original is retained unchanged. Its SHA-256 (also its LF-normalized hash) is
`80efa6f62d3a53ad23113f3f3744cdfc0d9f77e916a533109fe7e41b00c2a29f`.

The normalized copy has SHA-256
`190afa623ecd236dd222d8c519d86588a300b4014a14c8eeee4cfe278c55ddc9`.
Only serialization fields changed: removed `restated_in_summary: null` from
non-claim assertions and converted their `supporting_cited_ids: null` to `[]`.
Those assertions have no citations. Text, labels, reference kinds, completeness,
notes and assertion IDs are unchanged. The normalized copy passes
`agreement.load_original` with the calibration cases: 5 raw assertions for X;
3 claims, 6 summary assertions and 3 limitations for Y.

Nisha's frozen extraction hash on #22 is
`525bb4a5748b374d31adbdbd07756320e9c1dd91b90168c30dfc21d3b55ddee8`.
Her file is not yet available in the repository. Next: obtain that exact file,
agree S/L/R matches, compare extraction only and resolve rule questions.
No comparison or held-out freeze is established by this submission.

Matty's notes identify these questions for the rule text:

1. How raw proposal facts are assessed when no parsed plan exists.
2. Whether reference_kind is omitted for energy with an unstated basis.
3. How FACT-JOB-J1/J2 map to the job records supplied in the packet.
4. Job-record deadlines as evidence when a separate deadline constraint is absent.
5. The finish-by deadline boundary used for duration calculations.

Preserve both originals. Any resulting clarification belongs in the rule text;
do not retrospectively replace either extraction. #22 remains open until this
comparison and the required clarification record are complete.
