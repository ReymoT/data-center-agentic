# Reimo D04/D05 Issue #60 custody handoff

November 10 operational update: [the v2 forecast-union amendment](NOV10_SELECTOR_CONTENT_AND_TRACE.md) supersedes the v1 selector/receipt version described below. Current code requires d04-held-custody-v2-forecast-union and sha256-rank-greedy-fixed-development-forecast-union-v2. The earlier v1 proposal and validation remain historical evidence, not current execution instructions. No real nonce or selection exists; Nisha must receive and pin the amended code before her private preparation. Source/custody and separate execution gates remain open.


Reimo produces D04 allocation tooling; Nisha independently receives private custody.
Reviewed base: `6e653e85c0432ffc135d11194914dade6173e6db`, instruction 1.28.
Task branch: `reimo/issue60-held-out-custody-review`. F02 1.0.0 is unchanged.
[Existing source evidence](../../data/D05_SOURCE_EVIDENCE.md) and
[the source acceptance audit](SOURCE_ACCEPTANCE_AUDIT.md) are separate
from this local implementation. No actual held-out selection, PrivateEpisode,
label, policy output, model call or freeze was produced.

## Implementation and exact PR files

- `dc_sustainability/data/held_out_custody.py`: evaluator-only, parameterized
  metadata preparation/verification and conditional interval comparison.
- `tests/data/test_held_out_custody.py`: synthetic authorization, metadata, privacy,
  development-preservation and conditional interval boundary tests.
- `docs/handoffs/ISSUE60_HELD_OUT_CUSTODY.md`: this B5 handoff, proposed protocol,
  safe reproduction and independent receiving requirements.

This PR targets main independently of the source-evidence PR. It uses only
existing merged development/source contracts and has no new cross-PR import,
local-document link or fixture dependency. Original combined local work and the
publication drafts are preserved outside this PR.

The 40 development IDs/dates/scenarios/seeds/groups/folds and v1/v2 content receipts
are unchanged. The new path reads `materialize_development.allocation()` and its
pinned checksums, not `propose_allocation()` or `proposed_records()`. Reusing the
joint allocator with a new date seed would silently change development selection;
that API is deliberately not used. Tests compare all 40 complete allocation records
to the original artifact and forbid calls to the joint allocator or source loader.
No changes to schemas, production indices, forecasts, policy/training modules,
shared instructions, I02 or Q10 records are proposed.

## Concrete parameter proposal — not adopted

No exact held-out pool/seed/job-root/algorithm/destination acceptance was located
in the inspected main and issue records. Development acceptance in #102/#112 is
not acceptance of held-out parameters. This proposal is published for review only, without exact private inputs or adoption.

| Parameter | Proposed value/rule | Accepted value |
|---|---|---|
| Candidate pool | Every valid 2022 date with day 15–28, all 12 months; sorted ISO dates (168 candidates) | Not recorded |
| Selection | `sha256-rank-greedy-fixed-development-v1`: rank by SHA256 canonical JSON `["d04-held-custody-v1", selection_seed, ISO_date]`, lexical date tie; skip any month already chosen or any complete 30-hour window intersecting fixed development/chosen windows; take six then sort chronologically | Not recorded |
| Selection seed | Proposed derivation: Nisha creates one private 256-bit nonce before any source/outcome inspection; seed = integer first 32 hex digits of D04 `digest(["d04-held-custody-v1", "selection", nonce_hex])` | Nonce and exact integer not instantiated or accepted |
| Job-seed root | Same private nonce, separate `"jobs"` domain in the above digest; distinct 128-bit integer, never 42/19 or either development root | Exact integer not instantiated or accepted |
| Episode seeds | First 16 hex digits of SHA256 `[version, job_root, SHA256([version, ISO_date, scenario])]`, interpreted as integer; normal variant retains parent's exact seed | Not recorded |
| IDs/groups | Opaque `EP-` + first 24 hex digits of SHA256 `[version,date,scenario]`; variant separate hash domain; source-hash/date related group as existing D04 | Not recorded |
| Custody path | A new `held-out-metadata-v1` child under Nisha's evaluator-only storage, outside every Git checkout/worktree/bare repository and outside producer/training sync trees | Actual absolute parent/path and platform capabilities not supplied |

This is a concrete deterministic protocol proposal; the missing private nonce,
exact root integers and absolute destination remain explicit required inputs.
No production defaults instantiate them. Keep them restricted when Nisha supplies
them; publish only the decision locator/status. If a prohibited/equal derived seed
occurs, fail and obtain an explicit protocol amendment; never silently retry.
A greedy shortfall likewise fails, without seed search or outcome-driven revision.
No date is ranked using carbon, jobs, labels or performance.

Coding decision owner: Reimo. Directly affected acceptance owner: Nisha for
selection/isolation/custody. Edison/Ved need agreement only if training/label
contracts or workload settings change; this tooling changes none. Any Q05 physical
mapping change affects Ved/Edison/Nisha/Matty and remains separately blocked.
Required checks: complete counts, invariant development receipt, union isolation,
parents, deterministic reproduction and leakage/storage receiving below.
Request time: **not sent**. Response deadline: **not started**. When Reimo sends
the exact restricted proposal, record real UTC time and +24 elapsed-hour deadline;
escalate unresolved shared choices to Matty within that interval. Existing #60
source clocks are retained; this local document does not reset them.

## Approval receipt and safe private preparation

Do not execute study selection until Reimo and Nisha accept the exact private
parameter record and destination. A JSON receipt is a binding integrity record,
not an authentication mechanism: the human recipient must authenticate the
referenced decisions and authorization checksum through an independent channel.
A fabricated receipt with nonempty strings is not approval. Tests use unmistakably
synthetic receipts; those are not study artifacts.

The API requires the following exact receipt keys:

```text
version: d04-held-custody-v1
scope: metadata_only_not_freeze_or_run
parameters:
  candidate_dates: sorted unique ISO date list
  selection_seed: explicit accepted integer, 0 <= seed < 2**128
  job_seed_root: separate explicit accepted integer, same range
  algorithm: sha256-rank-greedy-fixed-development-v1
destination: exact absolute NEW private directory
reimo_decision: authenticated exact approval locator
nisha_decision: authenticated exact approval locator
storage:
  platform: actual OS and storage provider/filesystem
  access_control: actual ACL/IAM/group/sync/backup capabilities and restrictions
  authorized_principals: exact permitted evaluator identities and administrators
  verification_record: independently recorded allow/deny/access test evidence
```

The candidate pool/seeds belong in that restricted receipt, not in a PR/Issue/log.
Nisha supplies an external canonical receipt digest (`splits.digest(receipt)`) after
authenticating it. The existing parent must be access-controlled before preparing
anything. Modes 0700/0600 are supplemental only. On Windows they do not establish
ACL isolation; on macOS they do not exclude machine administrators, backup agents,
cloud sync or another process under the same account. Actual storage is **unknown
and unverified** in this session; the test host is macOS with temporary synthetic
files, not approved evaluator storage.

After approval, in Nisha's restricted session only (pseudovariables are not defaults):

```python
from dc_sustainability.data.held_out_custody import prepare, verify

checksum = prepare(
    approved_receipt,
    authorization_sha256=independently_received_authorization_sha256,
    revision=reviewed_code_revision,
)
# Save checksum through Nisha's independent restricted checksum custody channel.
verify(
    approved_receipt,
    authorization_sha256=independently_received_authorization_sha256,
    revision=reviewed_code_revision,
    external_sha256=independently_saved_metadata_sha256,
)
```

Use the actual reviewed Git SHA plus recorded working-file hashes. No code SHA is
self-certifying approval. The file records environment/dependency versions, code
hashes, source URL/commit/path/hash, pinned development allocation files and v2
content-receipt commitment, algorithms, parameters, all 70 allocation records and
per-record canonical commitments. The combined union stays evaluator-only. Existing
public development artifacts remain the only development allowlist; no combined
manifest is exported to P03/P04. Source values/jobs/labels are not read/generated.
All episode content hashes remain null; allocation hashes are not content hashes.

`prepare` creates a new directory and writes only `metadata.json`, followed by
`complete.sha256` as the completion marker. Existing directories/files, partial
runs, Git ancestors (including worktree `.git` files and bare repositories), and
symlink aliases are rejected. No automatic cleanup/resume/overwrite is offered.
`verify` requires exactly those two regular nonsymlink files, the externally saved
checksum and byte-identical deterministic reconstruction. Missing/corrupt evidence,
invalid/missing parameters, wrong destination/revision or changed code/environment
fails closed. Same-environment verification is strict. Cross-environment replay
needs Nisha's separate comparison record; do not erase environment differences to
force acceptance. Checksum files next to metadata are not independent integrity
custody; independently saved checksum is mandatory.

No CLI/stdout/log metadata projection is provided. Restricted callers must suppress
tracebacks/interactive repr and avoid pytest locals or JSON logging on actual study
inputs. Only a checksum returns from `prepare`; do not publish it or its restricted
location without Nisha's agreement. The Python object/API is not an OS access-control
boundary; library code cannot isolate data from a caller holding evaluator credentials.
The parent directory must be stable against hostile concurrent rename/symlink
mutation; this implementation does not claim hardened multi-tenant filesystem
security, encryption, secret erasure or protection from machine administrators.
Use a dedicated evaluator account/storage boundary before actual use.

## Nisha's independent receiving record

Record platform/provider, OS/filesystem, principals/ACL/IAM policy, encryption and
key access if available, sync/backup inheritance and administrators. Demonstrate
with separate principals that the evaluator can read/write and P03/P04/development
accounts cannot list/read the directory or checksum store. Test actual storage,
not only mode bits. If accounts share credentials or storage cannot enforce the
boundary, reject custody and choose another authorized destination.

Independently, without relying on this implementation's isolation verdict:

1. Authenticate Reimo/Nisha decisions, exact sorted pool, seeds, algorithm/version,
   source identity and the externally protected authorization hash. Verify source
   identity from accepted provenance without opening held-out observations.
2. Read the pinned 40 development records; match IDs, seeds, dates, groups, 16/12/12
   folds and existing v2 content commitments. They must not change.
3. Reimplement SHA rank/greedy selection and seed derivation from the receipt;
   reproduce six distinct dates/months, four core scenarios and one normal variant
   each, 30 unique IDs, no collision with development. No seed retry.
4. Reconstruct all 30 physical slots per date in UTC. Independently compare all
   development/held-out intersections and related groups, including adjacent dates,
   day-14/day-15 tails, month transitions and year endpoints. Record both interval
   hypotheses; the generated report remains conditional on start labels while Q05
   is unresolved. Verify no transitive related group bridges partitions.
5. Match normal/variant window/group/seed exactly. At separately authorized content
   generation, require exact equality of jobs and realized carbon, with only forecast
   visibility changed; hash both contents and bind them to allocations. Metadata
   tests alone cannot certify equality of nonexistent private contents.
6. Verify the external checksum and reproduce metadata. Retain original bytes,
   dependency/code evidence and a separately protected checksum. For reproduction
   in another new directory, explicitly authorize that destination and compare the
   allocation/parameter commitments; whole-file hashes intentionally differ because
   the authorization embeds the destination. Never silently alter a signed receipt.
7. Check actual training inputs, fold maps, preprocessing/scalers and saved model
   manifests use only the fixed development allowlist. Library tests prove fixed
   metadata boundaries, not every future pipeline's real access. Do not give the
   combined manifest to training. Independently audit P03/P04 access paths and
   policy contexts before accepting no-leakage receiving.
8. Record pass/fail with exact artifact/checksum/code/environment and remaining
   conditions. Receive metadata only; do not freeze, generate PrivateEpisodes,
   run systems or open held-out outputs under this receipt.

The production overlap helper is reused as a technical check, not presented as
Nisha's independent scientific validator. It checks source-byte identities and
related groups; a re-exported/shifted dataset needs an authoritative source
crosswalk, not a different checksum treated as independence.

## Freeze-readiness checklist

| Gate | Current state / exact remaining acceptance |
|---|---|
| Development preservation | Implemented/tests compare fixed 40 records; historical receipts unchanged |
| Exact held-out selection | Proposed protocol only; Nisha supplies private nonce, exact roots and pool/algorithm agreement before selection |
| Authorized storage | No actual destination/platform/ACL evidence supplied; independent access tests and receipt acceptance required |
| Metadata custody | Tooling/synthetic tests only; actual approved metadata, external checksum and Nisha replay pending |
| Physical isolation | Conditional start-window checks only; B2 exporter evidence, affected-owner mapping agreement and independent union report required |
| Study forecasts | Preceding-row persistence is development-only. Nisha's same-hour-yesterday proposal remains unadopted; freeze needs an accepted method and isolation of its complete history footprint as well as the 30 scoring slots |
| Source meaning and rights | B1/B3 unresolved; B4 provisional; producer records/permissions and independent applicability review required |
| Workload scientific scope | Empirical calibration or explicitly accepted synthetic-only claim boundary, final distributions/seeds and affected consumers' agreement |
| Held-out content | Not authorized/generated; separate content-generation permission, parent/variant byte/content validation and actual immutable content hashes required |
| Q10/E04 | Agreed sampling implementation does not select this D04 cohort; extraction calibration/rules and independently frozen sample still required under #22 |
| I02/full freeze | Exact code/environment/source/model/ontology/prompt/solver/scoring settings, six-system I01 acceptance and Nisha receiving; none implied here |
| Evaluation execution | Separate explicit run authorization after scientific freeze; no held-out opening, policy execution or model calls authorized by this package |

## Historical combined-work validation record

See the final local results below. Tests use synthetic metadata only and the already
public development allocation. They do not reacquire source CSV or run held-out
policies. The initial sandboxed full suite encountered loopback-bind permission
errors; the authorized retry enables only the test fixture capability and does not
constitute external inference. No assertion was weakened to address that host limit.

Original local results: macOS, CPython 3.12.15, using
the existing local Python 3.12 environment; no dependency installation or portable/Windows
lock certification was performed.

| Check actually executed | Result |
|---|---|
| Full offline `python -m pytest tests -q --tb=short` after final code/test changes | **1,777 passed; 19 subtests passed**, 34.34 seconds |
| Focused data/contracts/training before the final generic-artifact regression | **806 passed; 19 subtests passed** |
| Custody + I02 freeze-manifest + Q10 sampling focused checks | **76 passed**; includes all 43 new custody cases |
| `python -m ruff check dc_sustainability scripts tests` | Passed |
| `python -m ruff format --check dc_sustainability scripts tests` | Passed, 184 files |
| `python scripts/validate_setup.py` | Passed, including local Markdown links and shared instruction consistency |
| `python scripts/validate_i02_freeze_manifest.py docs/i02/freeze-manifest.json` | Valid pre-freeze checklist: 12 pending, 5 blocked, 0 frozen; not readiness |
| `python -m compileall -q dc_sustainability scripts tests` | Passed |
| `python -m pip check` | No broken requirements |
| `python scripts/smoke_dependencies.py` | Imports, SHACL/SPARQL, tiny solver, classifier save/load and bounded offline graph route passed |
| `git diff --check` | Passed; new files also checked locally for trailing whitespace |
| Deterministic comparison regeneration, private metadata regeneration/external checksum and tamper/partial/path/seed faults | Passed in custody tests, synthetic receipts only |
| Immutable published development allocation/fold/content-receipt commitments | Matched pinned originals; no data/manifests development file changed |

The full offline retry required sandbox escalation for synthetic loopback HTTP
fixtures. The initial restricted run had 128 permission errors, not source or model
failures. The authorized retry passed; no external model service was used. The
initial I02 validator invocation omitted its required filename and was rerun
successfully with the exact command above. No assertions or source blockers were
weakened. No hosted CI, independent receiving, accepted study selection or scientific
freeze is claimed.

The validation above describes the original local preparation before separation.
Publication of two independent draft PRs is now authorized; merging, closing Issue
#60, contacting maintainers and study selection remain outside this authorization. Actual
private metadata creation is blocked on authenticated exact parameter/destination
agreement and storage verification; scientific content/freeze/run gates remain
separate. The Issue #60 receiving request remains a separate unsent draft. Source-maintainer
questions belong to the independent source PR; no maintainer contact is authorized.

## Independent PR publication validation

Refetched origin/main remains `6e653e85c0432ffc135d11194914dade6173e6db`.
Authenticated GitHub account: `ReymoT`; repository-local commit identity:
Reimo Tamme, `52417582+ReymoT@users.noreply.github.com`. No shared instruction
file, schema, production mapping, accepted development record or content receipt
is changed. The separate source PR is not an ancestor or a runtime/test dependency.

After separation, the custody branch's full offline suite passed **1,777 tests and
19 subtests** (36.74 seconds). Ruff lint/format (184 Python files), compilation,
setup/local-link validation, dependency consistency/smoke, I02-manifest validation
and staged whitespace checks passed. The generic-JSON artifact regression was
replaced with a direct year-boundary assertion so this PR does not depend on the
source PR's artifact; all 43 custody cases remain. Test seeds and receipt assertions
are explicitly synthetic, never accepted study inputs. No held-out selection,
PrivateEpisode, carbon observation, label, policy output, actual custody path or
evaluator secret is included. Public development receipts remain byte-identical.

The next authorized study-preparation step is to obtain authenticated exact
Reimo/Nisha parameter and storage decisions, including actual access tests. Only
then may Nisha prepare and independently verify restricted metadata. Content
generation, study forecasts, scientific freeze and execution require their
separate unresolved evidence/authorization gates. Silence is not approval.
