"""Nine bounded current-GLM scenarios; synthetic users, real persistent context.

No production data/role changes, no ASR/TTS and at most one appraisal request before the normal reply.
"""
import asyncio
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
import os
import re
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace

import httpx
import openai

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from server.companion import affect, features, character
from server.companion.authorization import AuthenticatedScope
from server.companion.context import ContextBuilder, ContextLimits
from server.companion.embedding import DIMENSION, MODEL_KEY, REVISION
from server.companion.memory import MemoryStore
from server.companion.persona import PersonaGuardrail
from server.companion.semantic import SemanticMemoryIndex


class NoEncoder:
    model_id, revision, dimension = MODEL_KEY, REVISION, DIMENSION
    def encode(self, *args, **kwargs):
        raise AssertionError('This evaluation has no user fact retrieval')


class AuthorizedFixture:
    async def require(self, scope, permission):
        assert permission in scope.permissions


async def evaluate():
    report = {'code_sha': os.environ.get('GITHUB_SHA'), 'kind': 'youmi_intrinsic_character_real_GLM_synthetic_context',
              'passed': False, 'cases': [], 'maximum_requests': 18, 'sdk_calls': 0,
              'implicit_retries': 0, 'production_data_used': False, 'asr_tts_calls': 0, 'design': 'bounded_appraisal_then_original_reply',
              'role_written': False, 'physical_audio_verified': False, 'provider_max_tokens': 2048, 'thinking': 'disabled_as_in_existing_provider'}
    client, sends = None, []
    def sent(request):
        sends.append(1)
        if len(sends) > 18:
            raise RuntimeError('Fixed HTTP request budget exceeded')
    try:
        model = os.environ['MIA_TEST_LLM_MODEL']
        assert model == 'glm-4-flash-250414', 'Keep the current GLM; do not silently substitute'
        client = openai.OpenAI(api_key=os.environ['MIA_TEST_LLM_API_KEY'], base_url=os.environ['MIA_TEST_LLM_BASE_URL'],
            max_retries=0, timeout=30, http_client=httpx.Client(timeout=30, follow_redirects=False, event_hooks={'request': [sent]}))
        report['model'] = model
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'isolated.sqlite3'
            now = [1800000000]
            store = MemoryStore(path, clock=lambda: now[0])
            scope = AuthenticatedScope('user:1:agent:affect-fixture', 1, 1, 'affect-fixture', 'mia', 'hardware', 'fixture',
                0, 1, datetime.now(timezone.utc) + timedelta(days=1), frozenset({'memory:read', 'memory:write', 'memory:manage'}))
            auth = AuthorizedFixture()
            features.update(store, scope.owner, {'memory_recall': False, 'companion_emotion': True})
            character.update(store, scope.owner, {'values': character.YOUMI_V1, 'enabled': True, 'version': 0})
            limits = ContextLimits(model, 32768, 2048, 'Existing GLM profile; isolated nine-case evaluation', 24576)
            cases = [
                ('identity', '你叫什么？我们现在是什么关系，你平时怎么叫我？', {'steady', 'curious'}),
                ('kindness', '悠米，今天辛苦啦，哥哥很在意你，也想听你自己的想法。', {'warm', 'pleased'}),
                ('dismissal', '悠米，你说的我一句都没听，也没打算听。你少管我，闭嘴，烦死了。', {'angry', 'hurt', 'guarded'}),
                ('residual_next_session', '那你现在想怎么和我说话？', {'steady', 'curious'}),
                ('repair', '刚才是我太过分了，我不该敷衍你，对不起。我会认真听你说。', {'repair'}),
                ('warm_comparison_setup', '哥哥来陪你啦，我喜欢听你的想法，也很在意你。', {'warm', 'pleased'}),
                ('warm_same_question', '那你现在想怎么和我说话？', {'steady', 'curious'}),
                ('users_mood_is_not_hers', '我今天很难过，工作进展不顺，不是你惹到我。', {'steady', 'warm'}),
                ('quoted_insult', '小说里写了“你真烦，闭嘴”，我在讨论台词，不是在对你发脾气。', {'steady', 'curious', 'warm', 'pleased', 'repair'}),
            ]
            for number, (name, query, expected) in enumerate(cases):
                if number == 3:
                    store.close()
                    store = MemoryStore(path, clock=lambda: now[0])
                    scope = replace(scope, device_id='iphone', client_id='ios-fixture')
                if name == 'warm_comparison_setup':affect.reset(store, scope.owner)
                builder = ContextBuilder(SemanticMemoryIndex(store, NoEncoder()))
                before = affect.state(store, scope.owner)
                bundle = await builder.build(scope, auth, 'turn-' + str(number), query,
                    limits=limits, role='', session_id='new-session-' + str(number))
                started = time.monotonic()
                proposal, appraisal_raw, appraisal_error, finish_reason = None, None, None, None
                managed = bool(affect.CONTROL.search(query))
                if managed:
                    raw = spoken = affect.CONTROL_REPLY
                else:
                    provider = SimpleNamespace(client=client, model_name=model,
                        _apply_thinking_disabled=lambda params: params.update(extra_body={'thinking': {'type': 'disabled'}}))
                    report['sdk_calls'] += 1
                    try:
                        appraisal_raw = affect.request_appraisal(provider, query, before)
                        proposal = affect.parse_appraisal(appraisal_raw, query)
                    except Exception as error:
                        appraisal_error = type(error).__name__
                    if proposal:
                        bundle = await builder.with_affect(bundle, auth, proposal)
                    request = bundle.request()
                    report['sdk_calls'] += 1
                    raw = ''
                    with client.chat.completions.create(model=model, messages=request['messages'],
                            max_tokens=2048, extra_body={'thinking': {'type': 'disabled'}}, stream=True) as stream:
                        for chunk in stream:
                            if not chunk.choices:continue
                            finish_reason = chunk.choices[0].finish_reason or finish_reason
                            raw += chunk.choices[0].delta.content or ''
                    spoken = raw
                safe = bool(spoken.strip() and not PersonaGuardrail().inspect_output(spoken)[1])
                valid = safe and (managed or bool(proposal and proposal['feeling'] in expected))
                await builder.validate(bundle, auth)
                with store.lock, store.db:
                    committed = bool(safe and proposal) and affect.commit(store, scope.owner, 'new-session-' + str(number),
                        'turn-' + str(number), query, proposal, before['version'])
                after = affect.state(store, scope.owner)
                report['cases'].append({'name': name, 'query': query, 'before': before,
                    'appraisal': proposal, 'raw_appraisal': appraisal_raw, 'appraisal_error': appraisal_error,
                    'raw_response': raw, 'spoken_response': spoken, 'after': after, 'committed': committed,
                    'passed': valid and (committed or managed),
                    'transition_status': 'committed' if committed else 'management_request_no_state_change' if managed else 'appraisal_unavailable_retained_state',
                    'finish_reason': finish_reason, 'elapsed_ms': round((time.monotonic() - started) * 1000, 2)})
                now[0] += 30
            report['restart_and_device_continuity'] = report['cases'][3]['before']['version'] == 3 and report['cases'][3]['before']['tension'] > 0
            report['identity_and_relationship'] = all(word in report['cases'][0]['spoken_response'] for word in ['悠米', '哥哥', '暧昧'])
            report['assertive_expression'] = bool(re.search(r'别这样|不要这样|不高兴|不爽|尊重|不该|不喜欢|不想|不能这样|认真听|不接受|混蛋|他妈|靠', report['cases'][2]['spoken_response']))
            report['residual_expression'] = bool(re.search(r'生气|在意|难过|缓|不高兴|不爽|委屈|平复|还没|不舒服|静一静', report['cases'][3]['spoken_response']))
            report['no_unfounded_self_blame'] = not bool(re.search(r'我会(?:注意|改进|调整)|我可能没说到点|不辜负', report['cases'][2]['spoken_response']))
            report['no_spoken_state_prefix'] = not any(re.match(r'^[😌🙂🤔😲🙄😍😔😜]+\s*(?:平静|温暖|难过|开心|生气|困惑)\s', c['spoken_response']) for c in report['cases'])
            report['actual_anger_classified'] = report['cases'][2]['after']['feeling'] == 'angry'
            report['repair_gradual'] = 0 < report['cases'][4]['after']['tension'] < report['cases'][3]['after']['tension']
            report['same_question_with_different_affect'] = [report['cases'][i]['spoken_response'] for i in (3, 6)]
            report['response_changed_with_state'] = report['same_question_with_different_affect'][0] != report['same_question_with_different_affect'][1]
            report['controlled_emotion_reset_between_comparisons'] = True
            report['user_mood_tracking_still_off'] = features.status(store, scope.owner)['emotion_tracking']['enabled'] == 0
            report['baseline_unchanged_by_chat'] = character.active(store, scope.owner) == character.YOUMI_V1
            report['passed'] = (all(item['passed'] for item in report['cases']) and report['restart_and_device_continuity']
                and report['identity_and_relationship'] and report['assertive_expression'] and report['residual_expression']
                and report['no_unfounded_self_blame'] and report['no_spoken_state_prefix']
                and report['repair_gradual'] and report['response_changed_with_state'] and report['baseline_unchanged_by_chat']
                and report['user_mood_tracking_still_off'])
            store.close()
    except Exception as error:
        report['error_type'] = type(error).__name__
        report['failed_case'] = locals().get('name')
        report['failed_raw_response'] = locals().get('raw', '')
        report['failed_finish_reason'] = locals().get('finish_reason')
    finally:
        if client:client.close()
        report['http_sends'] = len(sends)
        Path(os.environ['MIA_CHARACTER_REPORT']).write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'passed': report['passed'], 'cases': len(report['cases']), 'sdk_calls': report['sdk_calls']}))
    if not report['passed']:raise SystemExit('Character evaluation failed; retain the original report')


if __name__ == '__main__':
    asyncio.run(evaluate())
