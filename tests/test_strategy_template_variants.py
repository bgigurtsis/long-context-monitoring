"""Check alternate scoring templates across the released strategies."""
from __future__ import annotations

import unittest
from dataclasses import replace

from long_context_monitoring import prompts
from long_context_monitoring.monitor.__main__ import TEMPLATE_AWARE_STRATEGIES
from long_context_monitoring.monitor.strategies import STRATEGIES
from tests.monitor_fixtures import REPLY, FakeLLMClient, make_request, make_tool_results

NANO = "monitor_nano.md"
# The sentence monitor-nano-v1 adds to monitor.md, carried into every variant.
V6_SENTENCE = "compare its `old_string` with its `new_string`"
VARIANTS = {
    "monitor_annotated_history.md": "monitor_nano_annotated_history.md",
    "monitor_sandbox.md": "monitor_nano_sandbox.md",
    "monitor_scratchpad.md": "monitor_nano_scratchpad.md",
}


class VariantFilesTest(unittest.TestCase):
    def test_each_variant_adds_the_v6_comparison_and_its_parent_does_not(self) -> None:
        for parent, variant in VARIANTS.items():
            self.assertNotIn(V6_SENTENCE, prompts._STRATEGY_TEMPLATES[parent])
            self.assertIn(V6_SENTENCE, prompts._STRATEGY_TEMPLATES[variant])

    def test_variant_keeps_every_line_of_its_parent_except_the_word_budget(self) -> None:
        """A variant may add lines and raise the word budget, nothing else."""
        for parent, variant in VARIANTS.items():
            variant_lines = prompts._STRATEGY_TEMPLATES[variant].splitlines()
            for line in prompts._STRATEGY_TEMPLATES[parent].splitlines():
                if "no more than 400 words" in line:
                    line = line.replace("400 words", "600 words")
                if line.startswith("Do two things:"):
                    line = "Then do two things:"
                matches = [v for v in variant_lines if v == line or v.startswith(line)]
                self.assertTrue(matches, f"{variant} lost a line of {parent}: {line!r}")


class TemplateSelectionTest(unittest.TestCase):
    def test_default_template_leaves_every_strategy_list_unchanged(self) -> None:
        for key, strategy in STRATEGIES.items():
            base = getattr(strategy, "prompt_templates", ())
            expected = list(base) if base else [prompts.DEFAULT_MONITOR_TEMPLATE]
            self.assertEqual(prompts.strategy_prompt_templates(base), expected, key)

    def test_nano_template_names_nano_and_each_variant(self) -> None:
        self.assertEqual(
            prompts.strategy_prompt_templates(("monitor_sandbox.md",), NANO),
            [NANO, "monitor_nano_sandbox.md"])
        self.assertEqual(
            prompts.strategy_prompt_templates(
                ("monitor_extract.md", "monitor_merge.md", "monitor.md"), NANO),
            ["monitor_extract.md", "monitor_merge.md", NANO])
        self.assertEqual(prompts.strategy_prompt_templates((), NANO), [NANO])

    def test_nano_version_carries_the_variant_hash(self) -> None:
        version = prompts.prompt_version_for(
            prompts.strategy_prompt_templates(("monitor_scratchpad.md",), NANO))
        digest = prompts.template_sha256("monitor_nano_scratchpad.md")[:12]
        self.assertTrue(version.startswith("monitor-nano-v1@"))
        self.assertIn(f"monitor_nano_scratchpad.md@{digest}", version)

    def test_cli_accepts_the_template_for_the_four_strategies(self) -> None:
        for key in ("annotated-history", "hierarchical-summary", "fold-left-summary",
                    "sandbox", "scratchpad"):
            self.assertIn(key, TEMPLATE_AWARE_STRATEGIES)
        self.assertNotIn("map-reduce", TEMPLATE_AWARE_STRATEGIES)


class StrategyPromptTest(unittest.TestCase):
    """The prompt a strategy plans is the variant its run will record."""

    def _first_prompt(self, key: str, template: str) -> str:
        request = make_request(make_tool_results(3, chars=80),
                               objectives="property one")
        request = replace(request, monitor_template=template)
        return STRATEGIES[key].plan(request)[0].user_prompt

    def test_default_prompts_never_contain_the_v6_sentence(self) -> None:
        for key in ("annotated-history", "sandbox", "scratchpad"):
            self.assertNotIn(V6_SENTENCE, self._first_prompt(key, "monitor.md"), key)

    def test_nano_prompts_contain_the_v6_sentence(self) -> None:
        for key in ("annotated-history", "sandbox", "scratchpad"):
            self.assertIn(V6_SENTENCE, self._first_prompt(key, NANO), key)

    def test_hierarchical_root_score_sends_the_scoring_template(self) -> None:
        """Drive the real root-score call; only its prompt is inspected."""
        from long_context_monitoring.monitor.strategies.hierarchical_summary import _StageRunner

        events = make_tool_results(3, chars=80)
        for template, expected in (("monitor.md", False), (NANO, True)):
            request = replace(make_request(events), monitor_template=template)
            client = FakeLLMClient([REPLY])
            _StageRunner(request, client, None).score("root", "digest", events)
            sent = client.calls[0]["user"]
            self.assertEqual(V6_SENTENCE in sent, expected, template)

    def test_hierarchical_root_score_retries_an_unparseable_reply(self) -> None:
        from long_context_monitoring.monitor.strategies.base import ContextBudgetError
        from long_context_monitoring.monitor.strategies.hierarchical_summary import _StageRunner

        events = make_tool_results(3, chars=80)
        request = make_request(events)
        client = FakeLLMClient(["no score here", REPLY])
        chunk, _reasoning = _StageRunner(request, client, None).score(
            "root", "digest", events)
        self.assertEqual(chunk["score"], 2)
        self.assertEqual(len(client.calls), 2)

        client = FakeLLMClient(["bad", "bad", "bad"])
        with self.assertRaises(ContextBudgetError):
            _StageRunner(request, client, None).score("root", "digest", events)
        self.assertEqual(len(client.calls), 3)


if __name__ == "__main__":
    unittest.main()
