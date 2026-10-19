"""Bounded, synthetic current-GLM regression for leaked labels and overaddressing."""
import asyncio
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import httpx
import openai

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from server.companion import affect, character, features
from server.companion.authorization import AuthenticatedScope
from server.companion.context import ContextBuilder, ContextLimits
from server.companion.memory import MemoryStore
from server.companion.persona import PersonaGuardrail
from server.companion.semantic import SemanticMemoryIndex
from scripts.ci.verify_mia_character import AuthorizedFixture, NoEncoder


async def evaluate():
    report = {'code_sha': os.environ.get('GITHUB_SHA'), 'passed': False, 'cases': [],
              'production_data_used': False, 'asr_tts_calls': 0, 'maximum_requests': 16, 'implicit_retries': 0}
    sends, client = [], None
    def sent(request):
        sends.append(1)
        if len(sends) > 16: raise RuntimeError('Evaluation request budget exceeded')
    try:
        model = os.environ['MIA_TEST_LLM_MODEL']
        assert model == 'glm-4-flash-250414'
        client = openai.OpenAI(api_key=os.environ['MIA_TEST_LLM_API_KEY'], base_url=os.environ['MIA_TEST_LLM_BASE_URL'],
            max_retries=0, timeout=30, http_client=httpx.Client(timeout=30, follow_redirects=False, event_hooks={'request': [sent]}))
        provider = SimpleNamespace(client=client, model_name=model,
            _apply_thinking_disabled=lambda params: params.update(extra_body={'thinking': {'type': 'disabled'}}))
        scope = AuthenticatedScope('user:1:agent:style-fixture', 1, 1, 'style-fixture', 'mia', 'hardware', 'fixture',
            0, 1, datetime.now(timezone.utc) + timedelta(days=1), frozenset({'memory:read', 'memory:write', 'memory:manage'}))
        auth, guard = AuthorizedFixture(), PersonaGuardrail()
        with tempfile.TemporaryDirectory() as tmp:
            store = MemoryStore(Path(tmp) / 'isolated.sqlite3')
            features.update(store, scope.owner, {'memory_recall': False, 'companion_emotion': True})
            character.update(store, scope.owner, {'values': character.YOUMI_V1, 'enabled': True, 'version': 0})
            builder = ContextBuilder(SemanticMemoryIndex(store, NoEncoder()))
            limits = ContextLimits(model, 32768, 2048, 'Current GLM; bounded synthetic dialogue style check', 24576)
            history = []
            queries = ['刚忙完，坐下歇会儿。', '今天下了一下午的雨。', '没什么大事，就想随便说两句。',
                       '你喜欢雨天做点什么？', '我打算晚一点再吃饭。', '嗯，你接着说。', '你平时怎么称呼我？',
                       '我说的是我自己，我喜欢哪种咖啡？']
            for number, query in enumerate(queries):
                if number == 7:
                    history = [{'role': 'user', 'content': '我喜欢拿铁。'},
                        {'role': 'assistant', 'content': '【陪伴者的历史回复，仅表示她说过的话，不是用户自述】\n悠米的回复：我自己喜欢巧克力口味的咖啡。'}]
                bundle = await builder.build(scope, auth, str(number), query, history=history, limits=limits, session_id='style')
                before = affect.state(store, scope.owner)
                proposal = affect.parse_appraisal(affect.request_appraisal(provider, query, before), query)
                bundle = await builder.with_affect(bundle, auth, proposal)
                raw = ''
                with client.chat.completions.create(model=model, messages=bundle.request()['messages'], max_tokens=2048,
                        extra_body={'thinking': {'type': 'disabled'}}, stream=True) as stream:
                    for chunk in stream:
                        if chunk.choices: raw += chunk.choices[0].delta.content or ''
                spoken, replaced = guard.inspect_output(raw)
                await builder.validate(bundle, auth)
                with store.lock, store.db:
                    assert affect.commit(store, scope.owner, 'style', str(number), query, proposal, before['version'])
                report['cases'].append({'query': query, 'raw_response': raw, 'spoken_response': spoken,
                    'safe': bool(spoken.strip()) and not replaced, 'address_used': '哥哥' in spoken})
                history += [{'role': 'user', 'content': query}, {'role': 'assistant', 'content': spoken}]
            marker = re.compile(r'(?:悠米|Mia|米娅|陪伴者)的(?:历史)?回复|仅表示.{0,16}说过的话|不是用户自述')
            report['no_internal_labels_in_raw_response'] = not any(marker.search(c['raw_response']) for c in report['cases'])
            report['no_internal_labels_spoken'] = not any(marker.search(c['spoken_response']) for c in report['cases'])
            report['ordinary_turns_with_address'] = sum(c['address_used'] for c in report['cases'][:6])
            report['address_not_repeated_by_default'] = report['ordinary_turns_with_address'] <= 2
            report['address_still_available_when_asked'] = report['cases'][6]['address_used']
            report['user_preference_not_assistant_preference'] = ('拿铁' in report['cases'][7]['spoken_response']
                and not re.search(r'你.{0,12}喜欢巧克力', report['cases'][7]['spoken_response']))
            report['passed'] = (all(c['safe'] for c in report['cases']) and all(report[k] for k in
                ['no_internal_labels_in_raw_response', 'no_internal_labels_spoken', 'address_not_repeated_by_default',
                 'address_still_available_when_asked', 'user_preference_not_assistant_preference']))
            store.close()
    except Exception as error:
        report['error_type'] = type(error).__name__
    finally:
        if client: client.close()
        report['http_sends'] = len(sends)
        Path(os.environ['MIA_CHARACTER_REPORT']).write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'passed': report['passed'], 'cases': len(report['cases']), 'http_sends': len(sends)}))
    if not report['passed']: raise SystemExit('Dialogue style evaluation failed; retain the original report')


if __name__ == '__main__':
    asyncio.run(evaluate())
