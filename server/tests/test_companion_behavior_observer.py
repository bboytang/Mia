"""The real-behavior observer must preserve the reviewed Provider methods."""
import ast
import json
import os
from pathlib import Path
import sys
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import httpx

from server.companion.proposal import provider_capabilities
from server.tests.test_companion_request_accounting import MODULE, SDKFixtureProvider, sse


class BehaviorObserverTests(unittest.TestCase):
    def test_sdk_observer_preserves_contract_and_raw_output(self):
        source = Path(__file__).resolve().parents[2] / 'scripts/ci/verify_mia_behavior.py'
        selected = next(n for n in ast.parse(source.read_text()).body
                        if isinstance(n, ast.FunctionDef) and n.name == 'selected_provider')
        http = []
        output = {'memories': [], 'trait': None}
        def transport(request):
            http.append(request)
            return sse(output)
        provider = SDKFixtureProvider(transport)
        options = provider.client.with_options
        def isolated_options(**kwargs):
            kwargs['http_client'].close()
            kwargs['http_client'] = httpx.Client(transport=httpx.MockTransport(transport))
            return options(**kwargs)
        provider.client.with_options = isolated_options
        report = {'requests': 0, 'request_kinds': [], 'extraction_outputs': []}
        namespace = dict(os=os, httpx=httpx, json=json, LOCK=threading.Lock(),
            SUITE='personal', REQUEST_CAP=16, save=lambda unused: None,
            create_instance=lambda *args: provider)
        helper = SimpleNamespace(configure_provider=lambda unused: None,
            safe_provider_error=lambda error: {'error_class': type(error).__name__})
        configuration = {'api_key': 'fixture-only', 'model_name': 'glm-4-flash-250414',
            'base_url': 'https://fixture.invalid/v4', 'type': 'openai'}
        with patch.dict(sys.modules, {MODULE: SimpleNamespace(LLMProvider=SDKFixtureProvider),
                                     'mia_model_comparison': helper}), patch.dict(os.environ, {
                'MIA_TEST_LLM_API_KEY': configuration['api_key'],
                'MIA_TEST_LLM_MODEL': configuration['model_name'],
                'MIA_TEST_LLM_BASE_URL': configuration['base_url']}):
            exec(compile(ast.Module(body=[selected], type_ignores=[]), str(source), 'exec'), namespace)
            try:
                actual = namespace['selected_provider'](configuration, report, 'extraction')
                self.assertTrue(provider_capabilities(actual)['native_tools'])
                self.assertIs(actual.response_with_functions.__func__, SDKFixtureProvider.response_with_functions)
                chunks = list(actual.response_with_functions('session', [{'role': 'user', 'content': 'fixture'}]))
                self.assertEqual(json.loads(''.join(text or '' for text, _ in chunks)), output)
                self.assertEqual([json.loads(value) for value in report['extraction_outputs']], [output])
                self.assertEqual(report['requests'], 1)
                self.assertEqual(len(http), 1)
                self.assertEqual(actual.client.max_retries, 0)
                self.assertFalse(actual.client._client.follow_redirects)
            finally:
                provider.client.close()
