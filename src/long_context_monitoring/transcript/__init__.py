"""Canonical transcript layer shared across the pipeline.

Holds the JSONL -> events parser (:mod:`src.transcript.trajectory`) that the
monitor, injector, and viewer all build on. It lives here — not under the
viewer — because it is the one coupling point between the generation and
monitoring workstreams (see AGENTS.md), not a debugging-UI concern.
"""
