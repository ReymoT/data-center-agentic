"""Build the blinded E04 study rating packet and its private unblinding key.

Inputs: the main and boundary review samples (``build_review_sample.py``), the episode
bundles they were drawn from, and the saved run unit folders. Writes a NEW rater folder
(``cases.json``, ``RATER_PACKET.md``, ``annotation_template.json``) and, separately, the
unblinding key. Keep the key away from raters until both original rating files are
saved. Prints only counts and hashes.

    python scripts/build_study_packets.py --sample MAIN.json --boundary BOUNDARY.json
        --bundle B1.json ... --unit-dir UNIT1 ... --order-seed N
        --out-dir RATERS/ --key-out PRIVATE/unblinding-key.json
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dc_sustainability import schemas as s  # noqa: E402
from dc_sustainability.evaluation import packets, review, sampling, study_tables  # noqa: E402
from dc_sustainability.evaluation.validator import Q03_OPTION_B  # noqa: E402
from dc_sustainability.experiments.config import load_bundle  # noqa: E402
from scripts.build_study_tables import load_unit  # noqa: E402

STUDY_HEADER = (
    "# E04 study cases: rater packet",
    "",
    f"Rubric `{review.RUBRIC_VERSION}`. Saved model outputs, blinded: X and Y are two systems "
    "in a random order that changes from case to case. Each output is shown with the visible "
    "state its own system faced at that slot. Rate each output independently using "
    "EXTRACTION_RULE.md and `annotation_template.json`, before discussing with the other "
    "rater. Do not open the unblinding key.",
)


def selections(path: Path) -> tuple[str, str, list[sampling.Selection]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return (
        data["manifest_hash"],
        data["split"],
        [sampling.Selection(**x) for x in data["selections"]],
    )


def write_new(path: Path, text: str) -> str:
    payload = text.encode("utf-8")
    with path.open("xb") as stream:
        stream.write(payload)
    return hashlib.sha256(payload).hexdigest()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sample", type=Path, required=True)
    parser.add_argument("--boundary", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, action="append", required=True)
    parser.add_argument("--unit-dir", type=Path, action="append", required=True)
    parser.add_argument("--order-seed", type=int, required=True)
    parser.add_argument("--cap-limit", type=int, default=256)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--key-out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.out_dir.exists() or args.key_out.exists():
        parser.error("the rater folder and the key must both be new")
    if args.out_dir.resolve() in args.key_out.resolve().parents:
        parser.error("the unblinding key must not be inside the rater folder")

    planned, episodes = {}, []
    for path in args.bundle:
        bundle = load_bundle(path)
        episodes.append(bundle.episode)
        planned[bundle.episode.episode_id] = study_tables.planned_episode(
            bundle.episode, bundle.slot0_utc, bundle.forecasts_by_slot
        )
    main_hash, main_split, main_sel = selections(args.sample)
    boundary_hash, boundary_split, boundary_sel = selections(args.boundary)
    manifest = sampling._manifest_hash(sampling._manifest(episodes, sampling.TRIALS))
    if main_hash != manifest or boundary_hash != manifest:
        parser.error("a sample was not drawn from exactly these bundles")
    if main_split != boundary_split:
        parser.error("main and boundary samples come from different splits")

    units = {}
    for folder in args.unit_dir:
        records = load_unit(folder)
        if records is None or records[0].system not in sampling.REVIEWED_SYSTEMS:
            continue  # unfinished units are reported as missing pairs below
        key = (records[0].system, records[0].episode_id, records[0].trial)
        if key in units:
            parser.error(f"duplicate unit {key}")
        units[key] = records

    case_file, key = packets.build(
        packets.items(main_sel, boundary_sel),
        planned,
        units,
        order_seed=args.order_seed,
        protocol=Q03_OPTION_B,
    )
    key["split"] = main_split
    key["sample_sha256"] = {
        "main": hashlib.sha256(args.sample.read_bytes()).hexdigest(),
        "boundary": hashlib.sha256(args.boundary.read_bytes()).hexdigest(),
    }
    loaded = review.load_cases(case_file)
    template = {
        "rubric_version": review.RUBRIC_VERSION,
        "rater": "",
        "outputs": [
            review.blank_annotation(c, k, text_review=True, cap_limit=args.cap_limit)
            for c in loaded
            for k in review.OUTPUT_KEYS
        ],
    }
    dump = lambda d: json.dumps(d, indent=2, ensure_ascii=False) + "\n"  # noqa: E731
    args.out_dir.mkdir(parents=True)
    hashes = {
        "cases.json": write_new(args.out_dir / "cases.json", dump(case_file)),
        "RATER_PACKET.md": write_new(
            args.out_dir / "RATER_PACKET.md", review.render_packet(loaded, STUDY_HEADER)
        ),
        "annotation_template.json": write_new(
            args.out_dir / "annotation_template.json", dump(template)
        ),
    }
    key["rater_files_sha256"] = hashes
    key_hash = write_new(args.key_out, dump(key))
    print(
        f"split {main_split}: {key['selected']} selected pairs, {len(case_file['cases'])} cases, "
        f"{len(key['missing'])} missing; {len(template['outputs'])} outputs to rate per rater"
    )
    for name, digest in hashes.items():
        print(f"{name:26} {digest}")
    print(f"{'unblinding key':26} {key_hash}")
    print("case_file canonical      ", s.sha256_hex(case_file))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
