"""Capability selection is explicit, never inferred from a method's existence."""

import json
import sys
from types import ModuleType
import unittest
from unittest.mock import patch

from server.companion.extraction import LLMMemoryExtractor
from server.companion.proposal import provider_capabilities


class PlainProvider:
    def response_no_stream(self, instruction, payload):
        self.instruction, self.payload = instruction, json.loads(payload)
        return '{"memories":[]}'

    def response_with_functions(self, *args, **kwargs):
        raise AssertionError('Inherited text fallback must not be treated as native tools')


class ProviderContractTests(unittest.TestCase):
    def test_inherited_fallback_and_unknown_override_use_one_plain_json_request(self):
        class Inherited(PlainProvider):
            pass
        class Unknown(PlainProvider):
            def response_with_functions(self, *args, **kwargs):
                raise AssertionError('Unknown override is not a reviewed native contract')
        for cls in (PlainProvider, Inherited, Unknown):
            with self.subTest(provider=cls.__name__):
                provider = cls()
                caps = provider_capabilities(provider)
                self.assertFalse(caps['native_tools'])
                self.assertFalse(caps['function_selection'])
                self.assertFalse(caps['strict_schema'])
                self.assertTrue(caps['plain_json'])
                self.assertEqual(LLMMemoryExtractor(lambda: provider)(['我常用青瓷杯喝茶'], []), '{"memories":[]}')
                self.assertIn('Return JSON only', provider.instruction)
                self.assertNotIn('Use the mia_memory_proposal function', provider.instruction)
                self.assertEqual(provider.payload['user_excerpts'], ['我常用青瓷杯喝茶'])

    def test_only_reviewed_native_implementation_is_selected_not_subclass_override(self):
        module = ModuleType('core.providers.llm.openai.openai')
        class Reviewed(PlainProvider):
            def response_with_functions(self, *args, **kwargs):
                yield '', None
        Reviewed.__module__ = module.__name__
        module.LLMProvider = Reviewed
        class Inherited(Reviewed):
            pass
        class Override(Reviewed):
            def response_with_functions(self, *args, **kwargs):
                yield '', None
        with patch.dict(sys.modules, {module.__name__: module}):
            self.assertTrue(provider_capabilities(Reviewed())['native_tools'])
            self.assertTrue(provider_capabilities(Inherited())['native_tools'])
            self.assertFalse(provider_capabilities(Override())['native_tools'])
            self.assertFalse(provider_capabilities(Reviewed())['function_selection'])
            self.assertFalse(provider_capabilities(Reviewed())['strict_schema'])
            replaced = Reviewed()
            replaced.response_with_functions = lambda *args: iter([])
            self.assertFalse(provider_capabilities(replaced)['native_tools'])
