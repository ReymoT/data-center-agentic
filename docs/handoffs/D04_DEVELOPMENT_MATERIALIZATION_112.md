# D04 #112 — development materialization handoff

Manager receiving update, October 31: the bounded materialization is preserved,
and the urgent causal persistence, portable receipt-verification and A02
portability/admission fixes are recorded in
[the manager unblock handoff](D04_A02_MANAGER_UNBLOCK_2026-10-31.md). The text
below is Reimo's original PR #130 handoff and remains historical evidence where
the manager update supersedes its forecast/receipt blockers.

**PARTIAL / BLOCKED for P04/O02 training readiness.** All 40 real development
PrivateEpisodes and their 40 canonical content hashes / 40 serialized-file hashes
are complete. The accepted IDs, dates, seeds, scenarios, windows and 16/12/12 folds
are unchanged. All 40 pass F02 round trips and 30-slot S01 replays; independent
regeneration is byte-identical. Real P03 collected 120 decisions but zero candidate
feature rows without an agreed source-derived forecast issuance path. No P04
training or held-out research episode generation was performed.

## Authority, baseline and publication scope

Owner Reimo; Nisha technical contact; Edison P04 and Ved O02 consumers. Re-read
published instruction 1.28, MASTER_REIMO, project/team/interface/decision records,
D03/S01/D04 handoffs and issues #112/#102/#60. Fetched current main is
`8f797f18a678293b66b6916718747285157d7208` (PR #129). The dedicated branch
`reimo/d04-materialization-112` has this exact base; no reconciliation is necessary.
The initial checkout contained only the seven #112 untracked files below and no
tracked edits. The previous task branch and all private artifacts are preserved.

The user explicitly authorizes this draft publication as Reimo. Authentication
was independently checked as `ReymoT` (ID 52417582), with repository push permission.
Local author is Reimo Tamme, `52417582+ReymoT@users.noreply.github.com`. This direct
human instruction controls this publication's identity; Matty's identity is not
used for Reimo's work. Shared instructions remain untouched.

Matty's #102 close comment 6486639018 records Nisha's custody acceptance, Edison's
training-fold acceptance and Ved's compatibility review before #108 merged at
`e4c7a8cbf5e936fb2056df47f6e860e7378fd5dd`. Historical proposed/unmaterialized fields
in #102 artifacts remain preserved. This draft does not close #112, resolve
scientific gates, authorize redistribution or claim receiving-member acceptance.

Only these seven files belong to the publication:

- `dc_sustainability/data/materialize_development.py`
- `scripts/check_d04_materialization.py`
- `tests/data/test_materialize_development.py`
- `data/manifests/d04-development-content-112-v1/receipt.json`
- `data/manifests/d04-development-content-112-v1/consumer-checks.json`
- `docs/handoffs/D04_DEVELOPMENT_MATERIALIZATION_112.md`
- `docs/handoffs/D04_MATERIALIZATION_112_PR_BODY.md`

## Source evidence, snapshot and hashes

The unchanged D01 adapter validated exact pinned SustainDC bytes: 8,760 rows,
upstream commit `a92b4755aca560e34a98d14028dda629eb968482`, source path
`data/CarbonIntensity/AZPS_NG_&_avgCI.csv`, original CSV SHA-256
`e05789a1dbf940e0554b0e8db42d84ed5cc0279d0050206fb048ba832ef24ef4`.
Acquisition is retrieval of that existing derived CSV, not historical regeneration
from EIA. Source rights, pollutant/system boundary, physical interval meaning,
exporter lineage and accounting/site suitability remain unresolved under #60/Q05.
The source URL and upstream commit are in the public receipt. No source CSV,
derived hourly data, realized-carbon arrays or complete episodes are in Git.

For each pinned allocation record the materializer uses exactly its recorded 30
indices, original source timestamps and values through existing D01 UTC/float
parsing. It calls D03 `generate_episode()` / `generate_jobs()` unchanged, with that
record's scenario and seed. There is no new sampling, substitution, date retry,
solver-based filtering or held-out input. Infeasible episodes retain D03's
intentionally impossible flexible job. Every episode has 24 decision + 6 completion
slots and exactly 30 private observations. PrivateJob metadata stays private.

CarbonSemantics is average factor, unresolved pollutant and interval convention,
and provisional slot mapping. Physical UTC interval endpoints remain null. Proposed
allocation boundaries are conditional metadata, not verified source semantics.
Private receipt entries preserve dates, indices, timestamps and related groups.

The snapshot uses documented 100 kW IT capacity including 40 kW background, PUE
1.2 and one-hour slots, plus Q04's agreed two-slot maximum forecast age. SourceRefs
resolve to the pinned D01 source and canonical LF hashes of the current assumptions
and Q04 records. No hand-example job-specific constraints are copied; timing and
nonflexibility remain in each generated Job. Snapshot canonical SHA-256:
`a2f245f044cf975c089c0084f1f3d128d5de498dabc05b0dff03ded8c16bb45e`.

Original #102 hashes remain unchanged:

| Hash kind | SHA-256 |
| --- | --- |
| manifest.json canonical LF file bytes | `2af72d8ed49801d64bd707cb1a9adc9e8b216ea7cd653dbb65c8ca3cf965cbb5` |
| fold-map.json canonical LF file bytes | `c54ef1c35dd39628bcc6c4f18fb3cc241a70f8cf94b1b9445d9ea02234531fac` |
| manifest canonical metadata | `f8f68ce57bfdb0f36e273316f0db6ed8b6b151fafff885aafcdf0b91a778dfa6` |
| private complete content receipt bytes | `fdb9daaa787f87bdda30487885efea427173b14c0eb378ace30f833afda42cca` |
| public checksum-only receipt bytes | `b8a58955bd4d2d7d160038065706dce1386e746aa25c1e2dcb165c4c50ac61e7` |

Each public entry binds its original `allocation_sha256` to
`episode_canonical_sha256` (F02 `PrivateEpisode.canonical_hash()`) and `file_sha256`
(actual sorted compact UTF-8 JSON plus final LF). Snapshot hashes are F02 canonical
hashes. Code hashes normalize CRLF to LF and preserve all other source bytes.
The original CSV hash covers its original bytes without normalization. These
checksums detect differences; they are not independent signatures, scientific
certification or evidence of redistribution permission.

Receipts retain F02 1.0.0, D03 `d03-provisional-v1`, exact distribution specification,
CPython 3.12.15, every installed dependency version and base revision plus relevant
canonical LF working-code hashes. `--code-revision` allows receipt replay after
publication without mislabeling its original baseline. A source/code/environment
mismatch fails verification rather than silently accepting a new receipt.

## Custody and authorized recipient steps

The user authorized local private custody under identifier
`reimo-authorized-local-d04-112-corpus-v2`. Reimo retains the existing 40 episode
files, full `content-receipt.json`, original CSV and acquisition report outside Git.
The actual machine-local directory was supplied privately in the session; it is
not a portable reproduction requirement or remotely accessible team artifact.
The verified corpus has not been overwritten or regenerated in place. A separate
independent corpus was compared file for file. Superseded earlier receipts remain
preserved and are not used for receiving checks.

POSIX directory/file modes are 0700/0600. Windows chmod is not an ACL guarantee:
a recipient must use an explicitly authorized parent directory with appropriate
Windows ACLs. Temporary local storage is not durable team hosting or off-device
backup. Reimo must preserve protected copies before temporary storage is cleared.

Edison and Ved can safely receive the checksum-only Git artifacts immediately.
To obtain actual source-derived content:

1. Obtain explicit authorization for the pinned input and a private local custody
   directory. Dataset-specific redistribution permission remains unresolved; this
   PR does not authorize Reimo to transfer the CSV or derived corpus to others.
2. If authorized to access the pinned source, acquire it independently using the
   explicit D01 command below, or use an already authorized exact-byte local input.
   The materializer and verifier perform no download. Missing/mismatched source
   bytes stop work; do not substitute fixtures or fill observations.
3. Recreate the recorded runtime and published code, generate into a new protected
   directory, and validate all episode hashes against the public receipt. A full
   receipt should also match only in the exact recorded environment/code baseline.
4. If private transfer rather than independent acquisition is desired, first
   establish applicable data permission and an agreed protected destination with
   Reimo/Nisha. No new remote custody destination or transfer has been authorized
   here. Validate receipt and every received file before loading into S01/P03/O02.
5. Keep the full corpus, original CSV and per-hour observations out of policy input,
   public issue/PR attachments, model features and CI artifacts. Share only the
   permitted checksums and aggregate receiving results until rights are established.

## Portable reproduction

Use CPython 3.12.15 and run from the published repository root. Select your own
absolute authorized private directory and environment directory outside Git;
none of Reimo's machine paths is required. Shell commands below use POSIX shell.
Use platform-equivalent environment activation on Windows while retaining the
same Python commands and a protected parent ACL. Keep existing outputs intact.

```sh
# Set these to your authorized local paths before running anything:
: "${D112_PRIVATE:?Set an existing authorized protected directory outside Git}"
: "${D112_ENV:?Set a new Python environment directory outside Git}"
export D112_PRIVATE
python3.12 -m venv "$D112_ENV"
D112_PY="$D112_ENV/bin/python"
D112_BASE=8f797f18a678293b66b6916718747285157d7208
# Reconstruct exact package versions from the permitted environment receipt.
"$D112_PY" - <<'PY'
import json, os, platform
from pathlib import Path
r = json.loads(Path('data/manifests/d04-development-content-112-v1/receipt.json').read_bytes())
assert platform.python_version() == r['environment']['python']
pins = Path(os.environ['D112_PRIVATE']) / 'environment-pins.txt'
with pins.open('x', encoding='utf-8', newline='\n') as stream:
    stream.write(''.join(f'{name}=={version}\n' for name, version in r['environment']['dependencies'].items()))
PY
"$D112_PY" -m pip install -r "$D112_PRIVATE/environment-pins.txt"
# Use an already authorized exact-byte local source at this path, or acquire explicitly below.
"$D112_PY" -m dc_sustainability.data.materialize_development "$D112_PRIVATE/AZPS.csv" "$D112_PRIVATE/corpus-new" --code-revision "$D112_BASE"
"$D112_PY" -m dc_sustainability.data.materialize_development "$D112_PRIVATE/AZPS.csv" "$D112_PRIVATE/corpus-new" --verify --code-revision "$D112_BASE"
"$D112_PY" scripts/check_d04_materialization.py "$D112_PRIVATE/AZPS.csv" "$D112_PRIVATE/corpus-new" --code-revision "$D112_BASE"
```

Export `D112_PRIVATE` for the Python environment-pin command. Exact package versions
are a reproduction record, not a portable wheel certification or permission to
change shared dependency settings. Do not use the candidate Windows wheel lock as
a macOS/Linux lock. Installation needs package access; corpus verification is offline.

Optional acquisition, **only after authorization to access this pinned input** and
only when both new paths are absent:

```sh
"$D112_PY" -m dc_sustainability.data.carbon_source "$D112_PRIVATE/AZPS.csv" --download --report "$D112_PRIVATE/acquisition.json"
```

This command explicitly retrieves only the recorded pinned URL, verifies the
original CSV checksum and structure, and saves exclusively. It grants no data
rights. The subsequent materialization validates that checksum again. To prove
independent regeneration, run into a second new directory with the same baseline
and environment, then `diff -qr` the two directories. Both original episode bytes
and full receipt must match. Do not remove an existing output to make a rerun pass.

Validate the regenerated output against the public record as well:

```sh
D112_CORPUS="$D112_PRIVATE/corpus-new"
export D112_CORPUS
"$D112_PY" - <<'PY'
import json, os
from pathlib import Path
from dc_sustainability.data import materialize_development as m
public = json.loads(Path('data/manifests/d04-development-content-112-v1/receipt.json').read_bytes())
root = Path(os.environ['D112_CORPUS'])
private = json.loads((root / 'content-receipt.json').read_bytes())
assert m.public_receipt(private, custody_id=public['custody_id']) == public
for entry in public['entries']:
    payload = (root / entry['content_path']).read_bytes()
    assert m.sha(payload) == entry['file_sha256']
print('PASS: public receipt and all 40 serialized-content hashes')
PY
```

Writers use canonical UTF-8/LF, exclusive non-overwriting files, a new private
directory and completion receipt written last. Verifier rejects partial/corrupt
files, missing/extra IDs, symlinks, changed allocation/source hashes and content
mismatches. An interrupted directory remains evidence; use a new destination.

## Actual consumer boundary and smallest remaining decision

All 40 stored files independently round-trip through F02 and complete 30 S01
steps with a trusted empty-start callback. State/Context expose arrived jobs only,
no private observations, fold labels, private metadata or future arrivals. This
callback tests the boundary; it is not a scheduling policy or trained model.

P03 accepted one real episode per scenario: **120 CollectedDecisions, zero usable
candidate rows**. Private observations were not converted into visible forecasts.
O02 accepted one waiting-job decision per scenario with a 0.1-second bound and
produced **zero training labels**. Current O01 reported `certified_infeasible` for
all four missing-forecast samples; that is preserved implementation evidence,
not accepted physical infeasibility. Ved should independently assess missing
evidence versus infeasibility handling. Do not turn those results into negatives.

A clearly labeled diagnostic-only forecast unit test proves nonempty P03 callback
compatibility and bounded O02 consumption; a forced unresolved solver result must
retain None labels and no training rows. Its synthetic issue schedule/values are
not exported or adopted as D01 forecasts.

The smallest remaining shared decision is an explicit D01-derived perfect-foresight
issuance/release adapter or agreed private forecast input: simulated issue time per
decision, trusted decision-time origin, horizon up to 24 slots clipped to 0–29,
source identity and freshness/required-coverage evidence. Edison and Ved verify
feature/label boundaries; Nisha verifies visibility, custody and leakage; Reimo
supplies the data adapter under the agreed path. Q04 already agrees maximum age
<=2 slots and whole-decision fallback; no scientific or freshness rule is reopened.
EP-HAND1's explicit synthetic issuance example is not a D04 adoption decision.

Edison can consume this bounded materialization for loading/simulation now after
authorized acquisition; usable O02 labels and P04 training remain blocked. Nisha
must independently verify receiving and later the actual private held-out union
isolation, without exposing held-out contents. Ved must independently verify
source/snapshot and O02 evidence handling. No receiving acceptance is invented.
Q05 source evidence and Q06 calibration/synthetic scientific scope, content freeze
and private held-out union isolation remain open.

## EP-HAND1 baseline investigation

The precise failing test is
`tests/agent/test_a02_authorization_preparation.py::test_episode_and_all_renderers_are_frozen_without_inventing_bounds`.
It was run independently on this branch and an unmodified detached current-main
Git worktree, both at `8f797f18a678293b66b6916718747285157d7208`:

```sh
python -m pytest tests/agent/test_a02_authorization_preparation.py::test_episode_and_all_renderers_are_frozen_without_inventing_bounds -q
```

Both fail at line 40 with identical expected/actual bundle-byte checksums:

- Expected by freeze manifest:
  `c7f05743bbb3055f8ae15b0f18f2548bdd57bb7fbff0e05eef4ae3b1eb529db3`.
- Actual committed bundle:
  `8bef36ace7bc4a3cf2debdce81c75edd87e175b20592a520a5449ec1fb0cddd6`.

PR #129's `f7d004e2c325d893be4349f11bb00b1ba7cd96c3` added the expected hash to the
freeze manifest. The bundle introduced by `1f3c732` already has the actual hash
above and is unchanged at current main. This independently reproduces a baseline
line-ending-sensitive freeze-record/bundle mismatch, not an interaction caused by #112.
A read-only hash experiment confirms the expected `c7f05743...` is exactly the
CRLF encoding of the committed LF bundle; no other byte changes are needed.
The repository workflow runs on Windows, so hosted results can differ from the
macOS LF baseline. Neither result certifies cross-platform frozen-byte portability.
The detached
main worktree remains unmodified. Frozen data, expectations and assertions were
not rewritten. Required hosted checks that encounter this failure remain red;
this draft must not be described as merge-ready while required checks fail.

## Publication validation record

Commands use the recorded CPython environment. Local logs are retained privately;
public evidence contains only permitted hashes, source references and aggregates.

- PASS 17 new materialization tests and existing D03/D04/F02/S01/P03/O02 focused
  suite: **846 passed, 19 subtests passed**.
- FAIL full offline suite: **1,641 passed, 1 failed, 19 subtests passed**;
  the baseline EP-HAND1 failure above. No skips or weakened assertions.
- PASS actual source/corpus verification: 40 unique accepted IDs, correct allocation
  bindings, seeds/scenarios/source indices, 30 actual observations each, 24+6
  horizons, F02 and full S01 replay.
- PASS independent regenerated episode and receipt bytes; read-only re-audit also
  compared all 41 preserved independent files and fresh in-memory regeneration.
- PASS unchanged aggregate consumer results: 120 decisions, zero feature rows.
- PASS Ruff lint/format, setup/documentation validator, compilation, dependency
  consistency/smoke and Git whitespace checks. Windows CI is checked separately;
  chmod assertions use each platform's actual mode semantics, not a POSIX ACL
  claim on Windows. No tests are skipped.
- PASS privacy audit of all seven publication files: no raw/derived CSV, episode
  content arrays, held-out allocation/seed/label artifacts, credentials or secrets.
  The only seeds in the receipt are already-public accepted development seeds.
- Hosted results are reported on the draft PR and in the publication response;
  no local check is represented as a hosted pass.

## Authorized draft publication

Title: **D04 #112: materialize 40 development PrivateEpisodes and provenance receipts**

Body: [D04_MATERIALIZATION_112_PR_BODY.md](D04_MATERIALIZATION_112_PR_BODY.md).
Related #112/#102/#60; no auto-closing keyword. The user explicitly authorized
staging only these seven files, committing, pushing and creating a draft. This
handoff records that authorized publication scope, not authorization to merge,
close #112, post comments or change shared instructions.

```sh
git diff --cached --check
git diff --cached --stat
git diff --cached
git commit -m 'D04: materialize 40 development episodes with provenance'
git push -u origin reimo/d04-materialization-112
gh pr create --draft --base main --head reimo/d04-materialization-112 --title 'D04 #112: materialize 40 development PrivateEpisodes and provenance receipts' --body-file docs/handoffs/D04_MATERIALIZATION_112_PR_BODY.md
```

The bounded materialization is available for review independently of P04 readiness.
Merge remains gated by required CI and receiving review; #112's full consumer
handoff remains PARTIAL / BLOCKED. No scientific acceptance, held-out freeze,
usable O02 labels or trained P04 policies are claimed.
