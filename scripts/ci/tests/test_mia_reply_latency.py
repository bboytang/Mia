from datetime import datetime, timedelta, timezone
import importlib.util
import json
import os
from pathlib import Path
import sys
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from server.companion.authorization import AuthenticatedScope
from server.companion.context import ContextBuilder, ContextLimits


spec = importlib.util.spec_from_file_location('mia_reply_latency',
    Path(__file__).resolve().parents[1] / 'mia_reply_latency.py')
latency = importlib.util.module_from_spec(spec)
spec.loader.exec_module(latency)


class EmptyMemoryBaselineTests(unittest.TestCase):
    def test_sdk_observer_first_content_is_relative_to_case_not_sdk(self):
        spec = importlib.util.spec_from_file_location('mia_tts_timing',
            Path(__file__).resolve().parents[1] / 'mia_tts_timing.py')
        timing = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(timing)
        response = SimpleNamespace(__iter__=None, close=Mock())
        class Response:
            def __iter__(self):
                yield SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=None))])
                yield SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content='中文'))])
            close = response.close
        create = Mock(return_value=Response())
        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        old = Mock()
        old.with_options.return_value = client
        provider = SimpleNamespace(client=old)
        configuration = {'model_name': latency.MODEL, 'api_key': 'synthetic',
            'base_url': 'https://synthetic.invalid', 'type': 'openai'}
        modules = {'httpx': SimpleNamespace(Client=Mock()), 'mia_tts_timing': timing,
            'mia_model_comparison': SimpleNamespace(safe_provider_error=Mock()),
            'mia_companion.model_requests': SimpleNamespace(model_requests=SimpleNamespace(snapshot=lambda: {}))}
        environment = {'MIA_TEST_LLM_API_KEY': 'synthetic', 'MIA_TEST_LLM_BASE_URL': configuration['base_url']}
        with patch.dict(sys.modules, modules), patch.dict(os.environ, environment):
            latency.observe_provider(configuration, 'reply', {'provider_requests': 0, 'provider_request_cap': 1},
                threading.RLock(), lambda report: None, lambda *args: provider)
            sample = provider._p23_sample = {'started': 100.0}
            messages = [{'role': 'system', 'content': 'core'},
                {'role': 'user', 'content': '{"mia_context":{"facts":[]}}'}]
            with patch.object(latency.time, 'perf_counter', side_effect=[100.25, 100.9]):
                stream = provider.client.chat.completions.create(model=latency.MODEL,
                    messages=messages, max_tokens=4096, stream=True)
                self.assertEqual(len(list(stream)), 2)
                stream.close()
        self.assertAlmostEqual(sample['sdk_start_ms'], 250)
        self.assertAlmostEqual(sample['sdk_first_content_ms'], 900)
        create.assert_called_once()
        response.close.assert_called_once()

    def test_shutdown_mode_has_only_two_original_extraction_attempts(self):
        self.assertEqual(latency.REQUEST_CAPS['worker-shutdown'], 2)

    def test_original_prompt_budget_and_question_survive_without_index_access(self):
        scope = AuthenticatedScope('user:1:agent:a', 1, 1, 'a', 'mia', 'device', 'client', 0, 1,
            datetime.now(timezone.utc) + timedelta(days=1), frozenset({'memory:read'}))
        builder = ContextBuilder(object())  # No store/retrieve/authorization methods available.
        limits = ContextLimits(latency.MODEL, 16384, 4096, 'Synthetic unit envelope')
        query, role = '我去湖边散步应该准备什么？', '测试角色数据'
        baseline = latency.empty_memory_request(builder, scope, limits, query, role, 'baseline')
        inputs = builder._prepare(query, [], [], role, [], None)
        inputs.update(facts=[{'id': 'one', 'category': 'fact', 'content': '散步带水壶',
            'content_version': 1, 'evidence_version': 1}], traits=[], memory_status='available',
            events=[], emotion_trend={'status': 'not_relevant'}, session_id='memory')
        reference = builder._assemble(scope, 'unit-memory', limits, None, inputs).request()
        self.assertEqual(baseline['messages'][0], reference['messages'][0])
        self.assertEqual(baseline['messages'][-1], {'role': 'user', 'content': query})
        self.assertEqual(baseline['max_tokens'], reference['max_tokens'])
        data = json.loads(baseline['messages'][1]['content'])['mia_context']
        self.assertEqual(data['facts'], [])
        self.assertEqual(data['events'], [])
        self.assertEqual(data['role_data'], role)
        self.assertEqual(len(json.loads(reference['messages'][1]['content'])['mia_context']['facts']), 1)


if __name__ == '__main__':
    unittest.main()
