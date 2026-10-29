"""Frozen run configuration, episode bundles, stable IDs and atomic files.

An episode bundle is the private runner input for one episode: the F02
``PrivateEpisode``, its slot-0 UTC time and the forecasts issued at each slot. It is
evaluator-side data; only the simulator and controller see it, never a policy.
"""

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from dc_sustainability import schemas as s
from dc_sustainability.experiments import registry

CONFIG_VERSION = "e02-run-config-v1"


def lf_sha256(path: Path) -> str:
    """SHA256 over LF line endings, so a CRLF checkout gives the committed hash."""
    return hashlib.sha256(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def publish(path: Path, text: str) -> None:
    """Write fully, then publish exclusively; an existing file is never replaced."""
    path = Path(path)
    temp = path.parent / f".{uuid4().hex}.tmp"
    try:
        with temp.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temp, path)
    finally:
        temp.unlink(missing_ok=True)


@dataclass(frozen=True)
class EpisodeBundle:
    episode: s.PrivateEpisode
    slot0_utc: datetime
    forecasts_by_slot: dict[int, tuple[s.CarbonForecast, ...]]


def bundle_to_json(bundle: EpisodeBundle) -> str:
    data = {
        "episode": bundle.episode.to_jsonable(),
        "slot0_utc": bundle.slot0_utc.isoformat(),
        "forecasts_by_slot": {
            str(slot): [f.to_jsonable() for f in facts]
            for slot, facts in sorted(bundle.forecasts_by_slot.items())
        },
    }
    return json.dumps(data, sort_keys=True, indent=1) + "\n"


def load_bundle(path: Path) -> EpisodeBundle:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if set(data) != {"episode", "slot0_utc", "forecasts_by_slot"}:
        raise ValueError(f"{path}: an episode bundle has episode, slot0_utc, forecasts_by_slot")
    slot0 = datetime.fromisoformat(data["slot0_utc"])
    if slot0.utcoffset() != timezone.utc.utcoffset(None):
        raise ValueError(f"{path}: slot0_utc must be an explicit UTC time")
    forecasts = {}
    for slot, facts in data["forecasts_by_slot"].items():
        if not slot.isdigit() or not 0 <= int(slot) < 30:
            raise ValueError(f"{path}: forecast slot {slot!r} is outside 0..29")
        forecasts[int(slot)] = tuple(s.CarbonForecast.from_jsonable(f) for f in facts)
    return EpisodeBundle(s.PrivateEpisode.from_jsonable(data["episode"]), slot0, forecasts)


@dataclass(frozen=True)
class RunConfig:
    name: str
    systems: tuple[str, ...]
    episodes: tuple[tuple[str, str, str], ...]  # (episode ID, bundle path, bundle LF SHA256)
    model_trials: tuple[int, ...] = (0, 1, 2)
    code_revision: str = "unrecorded"
    lock_sha256: str | None = None

    def __post_init__(self):
        if not self.name.strip():
            raise ValueError("a run needs a name")
        if not self.systems or len(set(self.systems)) != len(self.systems):
            raise ValueError("systems must be listed once each")
        for system in self.systems:
            registry.spec(system)  # unknown names fail here; availability fails at run time
        ids = [e[0] for e in self.episodes]
        if not ids or len(set(ids)) != len(ids):
            raise ValueError("episodes must be listed once each")
        if not self.model_trials or len(set(self.model_trials)) != len(self.model_trials):
            raise ValueError("model trials must be distinct")

    def identity(self) -> dict:
        """What the run is: everything that changes results, not where files live."""
        return {
            "config_version": CONFIG_VERSION,
            "name": self.name,
            "systems": list(self.systems),
            "episodes": [{"episode_id": e, "bundle_sha256": h} for e, _, h in self.episodes],
            "model_trials": list(self.model_trials),
            "code_revision": self.code_revision,
            "lock_sha256": self.lock_sha256,
        }

    @property
    def config_hash(self) -> str:
        return s.sha256_hex(self.identity())

    @property
    def run_id(self) -> str:
        return f"RUN-{self.config_hash[:12]}"


def config_from_file(path: Path, *, code_revision: str, lock_sha256: str | None) -> RunConfig:
    """Read a run config file; bundle paths are relative to the config file."""
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    if not set(data) <= {"name", "systems", "episodes", "model_trials"}:
        raise ValueError("config keys are name, systems, episodes and model_trials")
    episodes = []
    for rel in data["episodes"]:
        bundle_path = (path.parent / rel).resolve()
        bundle = load_bundle(bundle_path)
        episodes.append((bundle.episode.episode_id, str(bundle_path), lf_sha256(bundle_path)))
    return RunConfig(
        name=data["name"],
        systems=tuple(data["systems"]),
        episodes=tuple(episodes),
        model_trials=tuple(data.get("model_trials", (0, 1, 2))),
        code_revision=code_revision,
        lock_sha256=lock_sha256,
    )


def decision_id(config: RunConfig, system: str, episode_id: str, trial: int | None, slot: int):
    trial_part = "" if trial is None else f".t{trial}"
    return (
        f"DEC-{config.config_hash[:10]}.{registry.spec(system).short}."
        f"{episode_id}{trial_part}.s{slot:02d}"
    )
