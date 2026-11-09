"""Reject unpinned converter sources before executing a caller-supplied probe."""

import hashlib

import pytest

from scripts import probe_a01_claim_grammar as probe


@pytest.mark.parametrize("changed", probe.CONVERTER_FILES)
def test_unpinned_source_cannot_be_reported_as_pinned(tmp_path, monkeypatch, changed):
    expected = {}
    for name in probe.CONVERTER_FILES:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"synthetic converter fixture")
        expected[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    monkeypatch.setattr(probe, "EXPECTED_CONVERTER_SHA256", expected)
    (tmp_path / changed).write_bytes(b"changed fixture")

    def forbidden(*args, **kwargs):
        raise AssertionError("probe must not execute for unpinned source")

    monkeypatch.setattr(probe, "_probe", forbidden)
    with pytest.raises(ValueError, match="converter source differs"):
        probe.assess(tmp_path / "nonexistent-probe", tmp_path)
