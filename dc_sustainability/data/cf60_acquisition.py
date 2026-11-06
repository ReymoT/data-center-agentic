"""Privileged source acquisition. Never import/call from the broker or policy view."""

from dc_sustainability.data import carbon_source
from dc_sustainability.data.cf60_broker import RestrictedHistory, candidates


def acquire(source_path, *, issue, interpretation, authorization):
    """Validate the pinned full CSV, then COPY only this issue's authorized rows.

    This operation reads the full source. Real execution needs separately recorded
    row/custody authorization; a nonempty locator is evidence linkage, not approval.
    No source acquisition is performed by the synthetic receiving harness.
    """
    from dc_sustainability import schemas as s

    labels = set(candidates(issue, interpretation))
    rows, _ = carbon_source.load_source(source_path)
    return RestrictedHistory(
        ((label, value) for label, value in rows if label in labels),
        issue=issue,
        interpretation=interpretation,
        authorization=authorization,
        source=s.SourceRef(
            source_id="SRC-D01",
            path=carbon_source.SOURCE_URL,
            sha256=carbon_source.SHA256,
            commit=carbon_source.COMMIT,
            redistribution_status="unresolved",
        ),
    )
