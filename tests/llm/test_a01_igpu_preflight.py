"""Offline tests for the A01 Arc/Vulkan metadata-only launcher."""

import pytest

from scripts.a01_igpu_preflight import (
    EXPECTED_RUNTIME_SHA256,
    METADATA_ENDPOINTS,
    _local_url,
    parse_arc_compute,
)

ARC_LINE = (
    'time=x level=INFO msg="inference compute" id=0 library=Vulkan compute=0.0 '
    'name=Vulkan0 description="Intel(R) Arc(TM) 140V GPU (16GB)" driver=0.0 '
    'type=iGPU total="18.0 GiB" available="17.2 GiB"'
)


def test_http_allowlist_has_metadata_only_and_cannot_construct_inference_url():
    assert EXPECTED_RUNTIME_SHA256 == (
        "ec9f3325f134597c7188b735dcc4e79a9eca4bf53f6b958ddf22aa04bf5ce57a"
    )
    assert METADATA_ENDPOINTS == {"/api/version", "/api/tags", "/api/show", "/api/ps"}
    for forbidden in ("/api/chat", "/api/generate", "/api/embed", "/api/pull"):
        with pytest.raises(ValueError, match="not permitted"):
            _local_url(11437, forbidden)


def test_arc_compute_parser_requires_exact_candidate_and_preserves_raw_reported_fields():
    parsed = parse_arc_compute(ARC_LINE)
    assert parsed == {
        "library": "Vulkan",
        "name": "Vulkan0",
        "description": "Intel(R) Arc(TM) 140V GPU (16GB)",
        "type": "iGPU",
        "reported_total": "18.0 GiB",
        "reported_available": "17.2 GiB",
        "reported_driver": "0.0",
        "reported_compute": "0.0",
    }


@pytest.mark.parametrize(
    "text",
    [
        ARC_LINE.replace("library=Vulkan", "library=cpu"),
        ARC_LINE.replace("type=iGPU", "type=discrete"),
        ARC_LINE.replace("Intel(R) Arc(TM) 140V GPU (16GB)", "other device"),
        ARC_LINE + "\n" + ARC_LINE,
        ARC_LINE + "\ndropping integrated GPU",
        "no compute discovery",
    ],
)
def test_arc_compute_parser_blocks_cpu_drift_wrong_device_drop_or_ambiguity(text):
    with pytest.raises(ValueError):
        parse_arc_compute(text)
