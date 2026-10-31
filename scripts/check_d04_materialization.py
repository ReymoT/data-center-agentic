"""Verify the real pinned D04 corpus and bounded S01/P03/O02 consumers offline.

Requires an explicitly authorized private source and corpus, never downloads data.
Output is aggregate evidence only. Forecasts use the development-only causal
persistence adapter and remain provisional pending Q05/Q06 scientific acceptance.
"""

import argparse
import json
import subprocess
import sys
from collections import Counter
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dc_sustainability import schemas as s  # noqa: E402
from dc_sustainability.data import materialize_development as m  # noqa: E402
from dc_sustainability.reference.labels import label_episode  # noqa: E402
from dc_sustainability.simulator import SchedulingSimulator  # noqa: E402
from dc_sustainability.training.collect import collect_decisions  # noqa: E402


def approve_empty(state, context):
    """Trusted no-start callback for bounded simulator/collection checks, not a policy."""
    return s.ApprovedActions(
        episode_id=state.episode_id,
        slot=state.current_slot,
        state_version=state.state_version,
        plan_hash="a" * 64,
        check_id="CHK-D04-BOUNDARY",
        starts=(),
    )


def check(source, directory, revision):
    corpus = m.verify(source, directory, revision=revision)
    manifest, folds = m.allocation()
    source_rows, _ = m.carbon.load_source(source)
    records = {r["episode_id"]: r for r in manifest["records"]}
    assert len(corpus) == 40 and {e.episode_id for e in corpus} == set(folds)
    samples_by_scenario = {}
    for episode in corpus:
        record = records[episode.episode_id]
        assert s.PrivateEpisode.from_jsonable(episode.to_jsonable()) == episode
        assert (episode.scenario_id, episode.seed, episode.split) == (
            record["scenario"],
            record["seed"],
            "development",
        )
        assert (episode.n_decision_slots, episode.n_completion_slots) == (24, 6)
        assert episode.jobs == m.scenarios.generate_jobs(
            record["scenario"], seed=record["seed"], split="development"
        )
        assert len(episode.realized_carbon) == 30
        for slot, (observation, index) in enumerate(
            zip(episode.realized_carbon, record["window"]["proposed_physical_indices"], strict=True)
        ):
            assert observation.valid_slot == slot
            assert (observation.observed_at_utc, observation.value) == source_rows[index]
            assert (
                observation.source_id == "SRC-D01" and observation.source_sha256 == m.carbon.SHA256
            )
            assert observation.valid_from_utc is observation.valid_to_utc is None
        simulator = SchedulingSimulator(allow_completion_starts=False)
        simulator.reset(episode)
        for _ in range(30):
            state = simulator.state()
            context = s.Context.build(state, episode.snapshot, representation="flat")
            s.assert_no_private_keys(state.to_jsonable())
            s.assert_no_private_keys(context.to_jsonable())
            assert all(j.arrival_slot <= state.current_slot for j in state.waiting_jobs)
            assert not state.carbon_facts  # private actuals did not become forecasts
            simulator.step(approve_empty(state, context))
        assert simulator.state().current_slot == 30
        samples_by_scenario.setdefault(episode.scenario_id, episode)
    collected_count, feature_rows, label_results = 0, 0, []
    for scenario, episode in sorted(samples_by_scenario.items()):
        # Use only the allocation's PROPOSED origin for diagnostic slot bookkeeping.
        # It is not a verified physical interval bound or a forecast issue time.
        start = episode.realized_carbon[0].observed_at_utc
        forecasts = m.persistence_forecasts(source, episode.episode_id)
        decisions = collect_decisions(
            episode,
            decision_time_utc=lambda slot: start + timedelta(hours=slot),
            approve=approve_empty,
            forecasts_by_slot=forecasts,
        )
        assert len(decisions) == 30 and any(d.rows for d in decisions)
        collected_count += len(decisions)
        feature_rows += sum(len(d.rows) for d in decisions)
        representative = next(d for d in decisions if d.rows)
        bounded = label_episode((representative,), time_limit_s=0.1)[0]
        training_rows = bounded.training_rows()
        if bounded.solver_result.status == "certified_optimal":
            assert training_rows
        else:
            assert not training_rows
        label_results.append(
            {
                "scenario": scenario,
                "status": bounded.solver_result.status,
                "labels": len(bounded.labels),
                "training_rows": len(training_rows),
            }
        )
    if not any(result["training_rows"] for result in label_results):
        raise AssertionError("bounded receiving produced no usable O02 training rows")
    return {
        "status": "BOUNDED DEVELOPMENT RECEIVING READY",
        "episodes": len(corpus),
        "valid_content_hashes": 40,
        "fold_counts": dict(Counter(folds.values())),
        "source_sha256": m.carbon.SHA256,
        "f02_round_trips": 40,
        "s01_full_30_slot_replays": 40,
        "p03_collected_decisions": collected_count,
        "p03_feature_rows": feature_rows,
        "o02_bounded_results": label_results,
        "forecast_adapter": "causal persistence from the immediately preceding source row; "
        "provisional development use only",
        "o02_limitation": "Bounded labels remain development evidence only. Source semantics, "
        "rights, held-out isolation and scientific freeze are unresolved.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("corpus", type=Path)
    parser.add_argument("--code-revision", help="base revision from the content receipt")
    parser.add_argument("--output", type=Path, help="exclusive aggregate JSON output")
    args = parser.parse_args()
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if args.code_revision:
        revision = args.code_revision
    payload = json.dumps(check(args.source, args.corpus, revision), sort_keys=True, indent=2) + "\n"
    if args.output:
        with args.output.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(payload)
    else:
        print(payload, end="")


if __name__ == "__main__":
    main()
