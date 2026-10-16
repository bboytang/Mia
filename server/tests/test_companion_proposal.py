"""Existing Provider tool proposals stay raw and require original source validation."""

import json
from types import SimpleNamespace
import unittest

from server.companion.extraction import EvidenceContext, LLMMemoryExtractor, validate_output
from server.companion.memory import MemoryError
from server.companion.proposal import NAME, read_stream, tool_definition


def delta(arguments='', name=None, index=0, identity=None):
    return SimpleNamespace(index=index, id=identity, function=SimpleNamespace(name=name, arguments=arguments))


class ProposalTests(unittest.TestCase):
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
        self.assertEqual(no_match['relations']['maxItems'], 0)
        self.assertEqual(context[0]['content'], '我喜欢做陶器')


if __name__ == '__main__':
    unittest.main()
