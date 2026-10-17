import os
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts.ci import mia_model_comparison as comparison


class ModelComparisonTests(unittest.TestCase):
    def test_default_retains_original_provider_policy_and_envelope(self):
        original = lambda params: params.update(original=True)
        provider = SimpleNamespace(model_name='glm-4-flash', _apply_thinking_disabled=original)
        with patch.dict(os.environ, {'MIA_TEST_MODEL_OVERRIDE': ''}):
            self.assertIsNone(comparison.configure_provider(provider))
            self.assertIs(provider._apply_thinking_disabled, original)
            self.assertEqual(comparison.selected_model('glm-4-flash'), 'glm-4-flash')
            self.assertEqual(comparison.output_tokens(), 768)
            self.assertEqual(comparison.context_window(), 8192)

    def test_each_authorized_model_uses_frozen_comparison_request_policy(self):
        for model in comparison.APPROVED_MODELS:
            if model == 'glm-4-flash-250414':
                continue
            with self.subTest(model=model), patch.dict(os.environ, {'MIA_TEST_MODEL_OVERRIDE': model}):
                provider = SimpleNamespace(model_name=model)
                envelope = comparison.configure_provider(provider)
                params = {'model': model, 'messages': [{'role': 'user', 'content': 'actual source'}],
                          'tools': [{'type': 'function'}], 'extra_body': {'existing': True}}
                provider._apply_thinking_disabled(params)
                self.assertEqual(params['model'], model)
                self.assertEqual(params['messages'], [{'role': 'user', 'content': 'actual source'}])
                self.assertEqual(params['extra_body'], {'existing': True,
                    'thinking': {'type': 'enabled'}, 'tool_stream': True})
                self.assertEqual(envelope['model'], model)
                self.assertEqual(comparison.selected_model('glm-4-flash'), model)
                self.assertEqual(comparison.output_tokens(), 4096)
                self.assertEqual(comparison.context_window(), 16384)
                plain = {'model': model}
                provider._apply_thinking_disabled(plain)
                self.assertNotIn('tool_stream', plain['extra_body'])

    def test_dated_flash_preserves_installed_provider_policy(self):
        original = lambda params: params.update(original=True)
        provider = SimpleNamespace(model_name='glm-4-flash-250414', _apply_thinking_disabled=original)
        with patch.dict(os.environ, {'MIA_TEST_MODEL_OVERRIDE': 'glm-4-flash-250414'}):
            envelope = comparison.configure_provider(provider)
            self.assertIs(provider._apply_thinking_disabled, original)
            self.assertEqual(comparison.selected_model('baseline'), 'glm-4-flash-250414')
            self.assertEqual(envelope['thinking'], 'original_provider_policy')
            self.assertEqual(comparison.output_tokens(), 4096)
            self.assertEqual(comparison.context_window(), 16384)

    def test_unapproved_or_mismatched_model_fails_without_fallback(self):
        with patch.dict(os.environ, {'MIA_TEST_MODEL_OVERRIDE': 'unapproved-model'}):
            with self.assertRaises(ValueError):
                comparison.selected_model('glm-4-flash')
        with patch.dict(os.environ, {'MIA_TEST_MODEL_OVERRIDE': 'glm-5.3-flash'}):
            with self.assertRaises(ValueError):
                comparison.configure_provider(SimpleNamespace(model_name='glm-4-flash'))

    def test_error_observation_keeps_status_and_code_without_secret_payload(self):
        error = RuntimeError('synthetic-private-secret')
        error.status_code, error.code = 403, '1211'
        error.body = {'key': 'synthetic-private-secret'}
        error.__cause__ = TimeoutError('synthetic-private-secret')
        value = comparison.safe_provider_error(error)
        self.assertEqual(value, {'error_class': 'RuntimeError', 'status_code': 403,
                                'code': '1211', 'causes': ['TimeoutError']})
        self.assertNotIn('synthetic-private-secret', json.dumps(value))
