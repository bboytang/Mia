"""Existing Provider tool proposals stay raw and require original source validation."""

import json
from types import SimpleNamespace
import unittest

from server.companion.extraction import EvidenceContext, LLMMemoryExtractor, decode, validate_output
from server.companion.memory import MemoryError
from server.companion.proposal import NAME, read_stream, tool_definition


def delta(arguments='', name=None, index=0, identity=None):
    return SimpleNamespace(index=index, id=identity, function=SimpleNamespace(name=name, arguments=arguments))


class ProposalTests(unittest.TestCase):
    def test_all_branches_project_source_evidence_without_serialized_metadata_or_aliases(self):
        cases = [(['我平常用木梳梳头'], '我梳头用角梳，不是木梳'),
            (['我喜欢书法'], '我常用青瓷杯喝茶'),
            (['我观云会画图', '观云时我做笔记', '我周末去山顶观云'], '我常用青瓷杯喝茶'),
            (['我喜欢书法'], '整理旧相册对我很有意义')]
        for texts, source in cases:
            for native in (False, True):
                with self.subTest(source=source, native=native):
                    context = EvidenceContext([{'id': str(i), 'category': 'fact', 'content': text,
                        'content_version': 2, 'evidence_version': 3, 'entities': '["数据库字符串"]',
                        'keywords': '["元数据"]', 'trigger_terms': '["活动"]', 'extra_private': 'do not project',
                        'evidence': [{'session_id': f's{i}', 'fingerprint': f'fp{i}', 'excerpt': text,
                            'unneeded': 'do not project'}]} for i, text in enumerate(texts)])
                    before = json.dumps(context, ensure_ascii=False)
                    captured = []
                    def capture(payload):
                        shown = json.loads(payload)['existing_memories']
                        captured.extend(shown)
                        shown[0]['evidence'][0]['excerpt'] = 'provider-local mutation'
                    class PlainProvider:
                        def response_no_stream(self, instruction, payload):
                            capture(payload)
                            return '{"memories":[]}'
                    class ToolProvider:
                        def response_with_functions(self, session, dialogue, functions):
                            capture(dialogue[1]['content'])
                            yield None, [delta('{"memories":[]}', NAME)]
                    provider = ToolProvider() if native else PlainProvider()
                    LLMMemoryExtractor(lambda: provider)([source], context)
                    self.assertEqual(json.dumps(context, ensure_ascii=False), before)
                    self.assertEqual(captured[0]['id'], context[0]['id'])
                    self.assertEqual(captured[0]['content'], context[0]['content'])
                    self.assertEqual(captured[0]['evidence'][0]['session_id'], 's0')
                    self.assertNotIn('entities', captured[0])
                    self.assertNotIn('keywords', captured[0])
                    self.assertNotIn('trigger_terms', captured[0])
                    self.assertNotIn('extra_private', captured[0])
                    self.assertNotIn('unneeded', captured[0]['evidence'][0])

    def test_trailing_format_fence_decodes_one_original_object_without_repair(self):
        source = '我常用青瓷杯喝茶'
        value = {'memories': [{'category': 'fact', 'content': source, 'source_quote': source,
            'source_index': 0, 'kind': 'explicit', 'subject': 'user', 'value': 'durable',
            'sensitive': False, 'entities': ['青瓷杯'], 'keywords': ['喝茶'], 'trigger_terms': ['喝茶']}]}
        raw = json.dumps(value, ensure_ascii=False, indent=2)
        for opening in ('', '```\n', '```json\n'):
            with self.subTest(opening=opening):
                arguments = opening + raw + '\n```'
                original = read_stream(iter([(None, [delta(arguments, NAME)])]))
                self.assertEqual(original, arguments)
                self.assertEqual(decode(original), value)
                self.assertEqual(validate_output(original, [source], [])['memories'][0]['content'], source)
        for field in ('entities', 'keywords', 'trigger_terms'):
            for invalid in (['喝茶'] * 9, '["喝茶"]', ['喝茶喝茶']):
                bad = json.loads(raw)
                bad['memories'][0][field] = invalid
                arguments = json.dumps(bad, ensure_ascii=False) + '\n```'
                self.assertEqual(decode(arguments), bad)
                with self.assertRaises(MemoryError):
                    validate_output(arguments, [source], [])

    def test_trailing_fence_does_not_allow_extra_text_multiple_objects_or_invalid_json(self):
        raw = '{"memories":[]}'
        for value in ('', '```', raw + '\n说明\n```', '说明\n' + raw + '\n```',
                raw + '\n' + raw + '\n```', raw + '```', '{"memories":\n```',
                '[{"memories":[]}]\n```', raw + '\n```\n说明'):
            with self.subTest(value=value), self.assertRaises(MemoryError):
                decode(value)

    def test_growth_schema_requires_possible_owned_shared_anchor_without_filling_output(self):
        source = '我常用青瓷杯喝茶'
        raw = json.dumps({'memories': [{'category': 'fact', 'content': source, 'source_quote': source,
            'source_index': 0, 'kind': 'explicit', 'subject': 'user', 'value': 'durable', 'sensitive': False,
            'entities': ['青瓷杯'], 'keywords': ['喝茶'], 'trigger_terms': ['喝茶']}]}, ensure_ascii=False)
        class Provider:
            calls = 0
            def response_with_functions(self, session, dialogue, functions):
                self.calls += 1
                self.schema = functions[0]['function']['parameters']
                yield None, [delta(raw, NAME)]
        for texts, expected in [(['我喜欢书法', '他送我红围巾', '周末我会散步'], False),
                                (['我观云会画图', '观云时我做笔记', '我周末去山顶观云'], True)]:
            context = EvidenceContext([{'id': str(i), 'content': text, 'category': 'fact',
                'content_version': 1, 'evidence_version': 1,
                'evidence': [{'session_id': f's{i}', 'fingerprint': f'fp{i}'}]} for i, text in enumerate(texts)])
            before = json.dumps(context)
            provider = Provider()
            result = LLMMemoryExtractor(lambda: provider)([source], context)
            self.assertEqual(result, raw)
            self.assertEqual(provider.calls, 1)
            self.assertEqual('trait' in provider.schema['properties'], expected)
            self.assertEqual(json.dumps(context), before)
            self.assertIsNone(validate_output(result, [source], context)['trait'])
            if expected:
                anchor = provider.schema['properties']['trait']['properties']['anchor']
                self.assertEqual((anchor['minLength'], anchor['maxLength']), (2, 32))
        schema = tool_definition([{'id': 'one', 'content': '我观云会画图'}], sources=['观云时我做笔记'],
                                 natural=False, growth=False, significance=False, tracking=False)
        anchor = schema['function']['parameters']['properties']['memories']['items']['properties']['relations']['items']['properties']['anchor']
        self.assertEqual((anchor['minLength'], anchor['maxLength']), (2, 32))

    def test_original_function_arguments_reach_existing_validator_unchanged_once(self):
        source = '我梳头用角梳，不是木梳'
        target = {'id': 'owned', 'content': '我平常用木梳梳头', 'category': 'fact',
                  'content_version': 2, 'evidence_version': 3}
        raw = json.dumps({'memories': [{'category': 'fact', 'content': source, 'source_index': 0,
            'source_quote': source, 'kind': 'explicit', 'subject': 'user', 'value': 'durable', 'sensitive': False,
            'entities': ['角梳'], 'keywords': ['梳头'], 'trigger_terms': ['梳头'],
            'importance_weight': None, 'importance_evidence': None, 'relations': [], 'reconciliation': {
                'form': 'natural', 'kind': 'correction', 'target_id': 'owned', 'old_quote': target['content'],
                'evidence': source, 'old_value': '木梳', 'new_value': '角梳', 'anchor': '梳头'}}], 'trait': None}, ensure_ascii=False)
        class Provider:
            calls = []
            closed = False
            def response_with_functions(self, session, dialogue, functions):
                self.calls.append((session, dialogue, functions))
                try:
                    yield None, [delta(raw[:20], NAME[:11], identity='call-real')]
                    yield None, [delta(raw[20:], NAME[11:])]
                finally:
                    self.closed = True
            def response_no_stream(self, *args):
                raise AssertionError('Second provider path must not be called')
        provider = Provider()
        result = LLMMemoryExtractor(lambda: provider)([source], [target])
        self.assertEqual(result, raw)
        self.assertTrue(provider.closed)
        self.assertEqual(len(provider.calls), 1)
        payload = json.loads(provider.calls[0][1][1]['content'])
        self.assertEqual(payload['user_excerpts'], [source])
        schema = provider.calls[0][2][0]['function']['parameters']
        self.assertEqual(schema['properties']['memories']['items']['properties']['source_quote']['enum'], [source])
        self.assertEqual(validate_output(result, [source], [target])['memories'][0]['replaces_id'], 'owned')
        self.assertEqual(target['content_version'], 2)

    def test_plain_json_fallback_does_not_start_a_second_request(self):
        self.assertEqual(read_stream(iter([('{"memories":', None), ('[],"trait":null}', None)])),
                         '{"memories":[],"trait":null}')

    def test_lone_formatting_fence_keeps_original_tool_arguments(self):
        source = '周六上午我通常在书桌边整理纸质邮票册'
        raw = json.dumps({'memories': [{'category': 'fact', 'content': source,
            'source_quote': source, 'source_index': 0, 'kind': 'explicit', 'subject': 'user',
            'value': 'durable', 'sensitive': False, 'entities': ['纸质邮票册'],
            'keywords': ['整理'], 'trigger_terms': ['书桌边']}]}, ensure_ascii=False)
        # The captured Provider response has a bare fence plus one unique call.
        result = read_stream(iter([('```', [delta(raw, NAME, identity='call-real')]), ('', None)]))
        self.assertEqual(result, raw)
        self.assertEqual(validate_output(result, [source], [])['memories'][0]['content'], source)
        invalid = json.loads(raw)
        invalid['memories'][0]['entities'] = ['不存在的线索']
        invalid = json.dumps(invalid, ensure_ascii=False)
        with self.assertRaises(MemoryError):
            validate_output(read_stream(iter([('```', [delta(invalid, NAME)])])), [source], [])

    def test_oversized_clue_arrays_remain_rejected_with_specific_retry_feedback(self):
        source = '周六上午我通常在书桌边整理纸质邮票册'
        memory = {'category': 'fact', 'content': source, 'source_quote': source, 'source_index': 0,
            'kind': 'explicit', 'subject': 'user', 'value': 'durable', 'sensitive': False}
        for field in ('entities', 'keywords', 'trigger_terms'):
            with self.subTest(field=field):
                valid = json.dumps({'memories': [dict(memory, **{field: ['整理'] * 8})]}, ensure_ascii=False)
                self.assertEqual(validate_output(valid, [source], [])['memories'][0][field], ['整理'])
                raw = json.dumps({'memories': [dict(memory, **{field: ['整理'] * 9})]}, ensure_ascii=False)
                with self.assertRaisesRegex(MemoryError, field + ' has 9 extraction clues; at most 8'):
                    validate_output(raw, [source], [])

    def test_ordinary_fact_uses_same_provider_function_once_without_invented_optional_fields(self):
        source = '我常用青瓷杯喝茶'
        raw = json.dumps({'memories': [{'category': 'fact', 'content': source, 'source_quote': source,
            'source_index': 0, 'kind': 'explicit', 'subject': 'user', 'value': 'durable', 'sensitive': False,
            'entities': ['青瓷杯'], 'keywords': ['喝茶'], 'trigger_terms': ['喝茶'], 'relations': []}]}, ensure_ascii=False)
        class Provider:
            calls = 0
            def response_with_functions(self, session, dialogue, functions):
                self.calls += 1
                self.schema = functions[0]['function']['parameters']
                yield None, [delta(raw, NAME)]
            def response_no_stream(self, *args):
                raise AssertionError('No second provider request')
        provider = Provider()
        result = LLMMemoryExtractor(lambda: provider)([source], [])
        self.assertEqual(result, raw)
        self.assertEqual(provider.calls, 1)
        memory = validate_output(result, [source], [])['memories'][0]
        self.assertEqual(memory['content'], source)
        self.assertIsNone(memory['emotional_weight'])
        self.assertNotIn('trait', provider.schema['required'])
        self.assertNotIn('importance_weight', provider.schema['properties']['memories']['items']['properties'])

    def test_ambiguous_wrong_mixed_or_unbounded_proposals_are_rejected_and_closed(self):
        examples = [[(None, [delta('{}', NAME, index=1)])],
                    [(None, [delta('{}', 'unrelated_action')])],
                    [('explanation', [delta('{}', NAME)])],
                    [('```json', [delta('{}', NAME)])],
                    [('```\nexplanation', [delta('{}', NAME)])],
                    [('```{}', [delta('{}', NAME)])],
                    [('```', [delta('{}', 'unrelated_action')])],
                    [('```', [delta('{}', NAME, index=1)])],
                    [(None, [delta('x' * 32769, NAME)])],
                    [(None, [delta('{}', NAME, identity='one')]), (None, [delta('', identity='two')])]]
        for events in examples:
            with self.subTest(events=str(events)[:80]):
                closed = []
                def stream():
                    try:
                        yield from events
                    finally:
                        closed.append(True)
                with self.assertRaises(MemoryError):
                    read_stream(stream())
                self.assertEqual(closed, [True])

    def test_schema_rejects_known_bad_clue_without_inventing_replacement(self):
        context = [{'id': 'owned', 'content': '我喜欢做陶器'}]
        feedback = {'message': 'real validation failure', 'rejected_clues': {'keywords': ['bad value']}}
        tool = tool_definition(context, sources=['我喜欢做陶器'], natural=False, growth=True,
                               significance=False, tracking=False, feedback=feedback)
        schema = tool['function']['parameters']
        properties = schema['properties']['memories']['items']['properties']
        self.assertEqual(properties['keywords']['items']['not']['enum'], ['bad value'])
        self.assertNotIn('default', properties['keywords'])
        self.assertNotIn('importance_weight', properties)
        self.assertNotIn('importance_evidence', properties)
        self.assertIn('sensitive', schema['properties']['memories']['items']['required'])
        self.assertEqual(schema['properties']['trait']['properties']['evidence_ids']['items']['enum'], ['owned'])
        self.assertNotIn('observations', schema['properties'])
        self.assertEqual(feedback['rejected_clues'], {'keywords': ['bad value']})

    def test_relation_schema_excludes_only_targets_with_no_possible_literal_anchor(self):
        context = [{'id': 'shared', 'content': '我喜欢做陶器'}, {'id': 'unrelated', 'content': '周末湖边跑步'}]
        props = tool_definition(context, sources=['我经常做陶器'], natural=False, growth=False,
            significance=False, tracking=False)['function']['parameters']['properties']['memories']['items']['properties']
        self.assertEqual(props['relations']['maxItems'], 4)
        self.assertEqual(props['relations']['items']['properties']['target_id']['enum'], ['shared'])
        no_match = tool_definition([context[1]], sources=['我经常做陶器'], natural=False, growth=False,
            significance=False, tracking=False)['function']['parameters']['properties']['memories']['items']['properties']
        self.assertNotIn('relations', no_match)
        self.assertNotIn('reconciliation', no_match)
        self.assertEqual(context[0]['content'], '我喜欢做陶器')


if __name__ == '__main__':
    unittest.main()
