from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import unittest

from server.companion.authorization import AuthenticatedScope
from server.companion.context import ContextBuilder, ContextLimits


spec = importlib.util.spec_from_file_location('mia_reply_latency',
    Path(__file__).resolve().parents[1] / 'mia_reply_latency.py')
latency = importlib.util.module_from_spec(spec)
spec.loader.exec_module(latency)


class EmptyMemoryBaselineTests(unittest.TestCase):
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
