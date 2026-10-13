"""Monitor LLM backend — the shared OpenRouter client plus the monitor default.

The client, protocol, exceptions, and pricing/context tables now live in
:mod:`src.openrouter` (shared with the attack designer). This module re-exports
them so existing ``from long_context_monitoring.monitor.llm import ...`` imports keep working, and
adds the monitor-specific default model.
"""
from __future__ import annotations

from long_context_monitoring.openrouter import (  # noqa: F401 - re-exported for back-compat
    DEFAULT_CONTEXT_TOKENS,
    DEFAULT_PRICE_PER_MTOK,
    MODEL_CONTEXT_TOKENS,
    MODEL_PRICES,
    OPENROUTER_BACKEND,
    OPENROUTER_URL,
    LLMClient,
    LLMError,
    LLMResponse,
    OpenRouterClient,
    default_provider_order,
    default_provider_quantizations,
    estimate_cost_usd,
    model_context_tokens,
)

# DeepSeek V4 Flash 0731 on OpenRouter — the house monitor. Its DeepInfra
# fp8 endpoint is pinned by default (MODEL_DEFAULT_PROVIDER /
# MODEL_DEFAULT_QUANTIZATIONS in src/openrouter.py) so repeated runs land on one
# serving stack without extra flags. This is the monitor CLI's default only; the
# shared client still takes an explicit model per call.
DEFAULT_MODEL = "deepseek/deepseek-v4-flash-0731"
DEFAULT_REASONING_EFFORT = "high"

__all__ = [
    "DEFAULT_CONTEXT_TOKENS",
    "DEFAULT_MODEL",
    "DEFAULT_REASONING_EFFORT",
    "DEFAULT_PRICE_PER_MTOK",
    "MODEL_CONTEXT_TOKENS",
    "MODEL_PRICES",
    "OPENROUTER_BACKEND",
    "OPENROUTER_URL",
    "LLMClient",
    "LLMError",
    "LLMResponse",
    "OpenRouterClient",
    "default_provider_order",
    "default_provider_quantizations",
    "estimate_cost_usd",
    "model_context_tokens",
]
