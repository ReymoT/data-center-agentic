"""Small synthetic ZIP fixtures only; no policies or scientific reproduction."""

import hashlib
import io
import json
import subprocess
import zipfile
from pathlib import Path

import pytest

from scripts import verify_rule06_handoff_archive as v


def packet(files, *, missing_manifest=False, bad_digest=False):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as z:
        for name, raw in files.items():
            z.writestr(name, raw)
        if not missing_manifest:
            manifest = {n: hashlib.sha256(b).hexdigest() for n, b in files.items()}
            if bad_digest:
                manifest[next(iter(manifest))] = "bad"
            z.writestr("SHA256_MANIFEST.json", json.dumps(manifest))
    raw = stream.getvalue()
    return raw, hashlib.sha256(raw).hexdigest()


def test_hidden_markers_checked_without_extraction(tmp_path):
    raw, sha = packet(
        {"trace/.completed/decision-00.json": b"{}", "trace/.intents/decision-00.json": b"{}"}
    )
    assert v.checked_zip(raw, sha, markers={".completed": 1, ".intents": 1}) == (2, {})
    assert not list(tmp_path.iterdir())


def test_manifest_consistent_but_missing_hidden_marker_refused():
    raw, sha = packet({"trace/.completed/decision-00.json": b"{}"})
    with pytest.raises(ValueError, match=".intents"):
        v.checked_zip(raw, sha, markers={".completed": 1, ".intents": 1})


@pytest.mark.parametrize("name", ["../escape", "/absolute", "C:/drive", "a\\backslash", "a/./file"])
def test_unsafe_paths_refused(name):
    raw, sha = packet({name: b"no extraction"})
    # Windows ZIP writing can normalize backslashes before our reader sees them;
    # the original manifest name then fails exact-inventory validation instead.
    with pytest.raises(ValueError, match="unsafe|manifest"):
        v.checked_zip(raw, sha)


@pytest.mark.parametrize("mode", ["wrong_archive", "wrong_member", "no_manifest", "oversized"])
def test_corruption_and_bounds_refused(monkeypatch, mode):
    raw, sha = packet(
        {"file": b"fixture"},
        missing_manifest=mode == "no_manifest",
        bad_digest=mode == "wrong_member",
    )
    if mode == "wrong_archive":
        sha = "wrong"
    if mode == "oversized":
        monkeypatch.setattr(v, "MAX_BYTES", 1)
    with pytest.raises((ValueError, KeyError)):
        v.checked_zip(raw, sha)


def test_unlisted_zip_member_refused():
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as z:
        z.writestr("file", b"fixture")
        z.writestr("SHA256_MANIFEST.json", "{}")
    raw = stream.getvalue()
    with pytest.raises(ValueError, match="exact manifest"):
        v.checked_zip(raw, hashlib.sha256(raw).hexdigest())


def test_cli_refuses_missing_file_and_does_not_execute(tmp_path, capsys):
    assert v.main(["--package", str(tmp_path / "absent.zip")]) == 1
    assert "refused" in capsys.readouterr().err


def test_duplicate_manifest_keys_refused():
    with pytest.raises(ValueError, match="duplicate"):
        v.strict_json(b'{"same":"one","same":"two"}')


def test_symlink_member_refused_without_creating_a_link():
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as z:
        link = zipfile.ZipInfo("link")
        link.create_system = 3
        link.external_attr = 0o120777 << 16
        z.writestr(link, b"target")
        z.writestr(
            "SHA256_MANIFEST.json", json.dumps({"link": hashlib.sha256(b"target").hexdigest()})
        )
    raw = stream.getvalue()
    with pytest.raises(ValueError, match="unsafe"):
        v.checked_zip(raw, hashlib.sha256(raw).hexdigest())


def test_duplicate_zip_names_refused():
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as z:
        z.writestr("same", b"one")
        with pytest.warns(UserWarning):
            z.writestr("same", b"two")
    raw = stream.getvalue()
    with pytest.raises(ValueError, match="duplicate"):
        v.checked_zip(raw, hashlib.sha256(raw).hexdigest())


def test_private_packages_ignored_but_public_evidence_remains_trackable():
    root = Path(__file__).parents[2]
    private = [
        "RULE06_VED_REPRODUCTION_PACKAGE_2026-11-26/START_HERE.txt",
        "RULE06_VED_REPRODUCTION_PACKAGE_2026-11-26.zip",
        "RULE04_NISHA_NEW_RECEIVING_2026-11-26/continuation/run/example.json",
        "RULE04_NISHA_NEW_RECEIVING_2026-11-26.zip",
    ]
    result = subprocess.run(
        ["git", "check-ignore", "--no-index", "--stdin", "-z"],
        cwd=root,
        input=("\0".join(private) + "\0").encode(),
        capture_output=True,
        check=True,
    )
    assert result.stdout.decode().split("\0")[:-1] == private
    result = subprocess.run(
        [
            "git",
            "check-ignore",
            "--no-index",
            "docs/evidence/rule04-dev-nov23/development.cases.json",
        ],
        cwd=root,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1 and not result.stdout
