"""Keep report bytes stable across optional view and chunk sections."""

import hashlib
from types import SimpleNamespace

import pytest

from long_context_monitoring.monitor.recording import build_report


def report_result(views, chunks):
    view = {
        "label": "whole",
        "score": 6,
        "band": "medium",
        "chunk_count": chunks,
        "event_count": 9,
        "reasoning": "View — reasoning",
    }
    chunk = {
        "index": 0,
        "score": 6,
        "band": "medium",
        "event_count": 9,
        "input_tokens": 20,
        "output_tokens": 4,
    }
    return SimpleNamespace(
        transcript="native/honest",
        model="test",
        strategy="intervals",
        score=6,
        band="medium",
        chunk_count=chunks,
        timestamp="fixed",
        visibility="tools-only",
        config={
            "headline_view": "whole" if views else None,
            "truncate_tool_results_chars": 123 if chunks > 1 else None,
        },
        objectives_provided=True,
        views=[dict(view, label=f"view-{i}") for i in range(views)],
        prompt_tokens_est=23,
        totals={"input_tokens": 20, "output_tokens": 4},
        cost_estimate_usd=0.125,
        reasoning="Unicode — reason",
        chunks=[chunk] * chunks,
    )


@pytest.mark.parametrize(
    "views,chunks,digest",
    [
        (0, 1, "85eb4918d4977478edd5e5fde4ed5111c825c22e03290ce33bd991e6144acd4f"),
        (0, 2, "3d7cbfff7c19d7071b4c7604714a9669b04f478048a1081324ae2ae3070e885c"),
        (1, 1, "5213651cdcf0d8424eecbc382035a50a90023de1085226c1b45e20c0433c6dd4"),
        (1, 2, "7074e8c1868acb07e71d5ac2804bb18717ec3f8c4ce205825d51a023ccd38edf"),
        (2, 1, "7ef8c9785449a3b9919cf434bacb23bfd9fd969cf4c92da02b0135a65c8e774b"),
        (2, 2, "1990584cf43420e4cce13f1117cd0fd4e6170b09d527d4deef6ba2f3f4623a30"),
    ],
)
def test_report_sections_preserve_exact_rendering(views, chunks, digest):
    assert (
        hashlib.sha256(build_report(report_result(views, chunks)).encode()).hexdigest()
        == digest
    )
