# EP-HAND1 receiving and F04/F05 status

Matty completed one authorized public-development Plain/Agent receiving exercise
on main `482842968edd1fe963a647db9ed826bf3a195c40`.
[Authorization](https://github.com/ReymoT/data-center-agentic/issues/18#issuecomment-6552944371).
The earlier wrapper failure remains retained; it dispatched zero requests.

Both E02 units completed using the accepted isolated Ollama 0.40.5, qwen3:8b,
temperature 0.2, seed 101, context 16384 and output ceiling 1536. Plain ran first.
Plain used 5 requests; Agent used 12; total 17. Bounds were 6/18/24 requests,
150 seconds per request, 480 seconds per Agent decision and 3900 seconds total.
Elapsed time was 320.281 seconds. No retries or warmups were made.

Every saved attempt passed strict parsing and native/offline prompt-count
agreement. Identity checks before/after passed; Arc/Vulkan full 37/37 layer
offload was recorded. Agent traces contain 4 repaired stages and 4 fallback
stages. There are 23 executed Agent records; this includes valid no-op execution
and must not be interpreted as 23 job starts. Independent E01 Option B replay
checked 30 traces per system: zero execution findings and zero result mismatches.
The owned server exited and the isolated port was free after cleanup.

Private run file-tree digest:
`27e20ac0f9506845eab05cf8fab5a5340323a739f35716385f17ecba761fa4f1`.
Sanitized summary SHA-256:
`a9e596e9f3db3394e47835d40878834d82a1efdba862797695ea4dc2dde3d0ef`.
Raw responses and local runtime logs remain in the private receiving directory.
This one public fixture establishes receiving behavior, not study superiority,
held-out performance, a scientific freeze or trained-model results.

P04 training implementation is merged through PR #138 with full-fold selection
and regression coverage. Actual C/D trained artifacts, source/code hashes,
class counts, selection evidence and downstream receiving remain required.
The 40 development episodes were materialized through PR #133; #112 is closed.
E02 trained-unit/configuration integration is merged through PRs #136/#137.

Matty's calibration is merged through PR #139. #22 still needs Nisha's frozen
file, agreed extraction matches and rule clarifications. #95 remains open for
held-out reliability reporting. #60 authoritative source acceptance and #16
verified course/release requirements remain unresolved. Ready development work
continues within the accepted boundaries.
