"""Real opt-in/stop/correction/delete gate; no clock or seven-day substitute."""

import json
import time


def context_data(answer):
    return json.loads(answer['input']['messages'][1]['content'])['mia_context']


async def drive_emotions(sample, ask, manage, start, stop, first_pid, checkpoint):
    began = int(time.time())
    proof = {'server_pids': [first_pid], 'observations': [], 'steps': [],
             'boundary': 'Actual current server dates only; real seven-calendar-day acceptance remains user self-test'}
    def record(phase, **values):
        proof.update(phase=phase, **values)
        proof['steps'].append({'phase': phase, **values})
        checkpoint(proof)
    initial = await manage('observations')
    record('default_off', actual_view=initial)
    assert not initial['consent']['enabled'] and not initial['observations']
    assert initial['trend']['status'] == 'disabled'
    await ask(sample['default_off'])
    view = await manage('observations')
    record('default_off_after_message', actual_view=view)
    assert not view['observations'], 'Default-off message persisted an observation'
    enabled = await manage('emotion_consent', enabled=True)
    record('enabled', actual_view=enabled)
    assert enabled['consent']['enabled'] and enabled['trend']['status'] == 'insufficient_observations'
    version = enabled['consent']['version']
    sessions, seen = [], set()
    for source in sample['sources']:
        answer, saved = await ask(source['text'])
        assert not saved['memories'], 'Transient mood became a durable user fact'
        sessions.append(answer['session_id'])
        view = await manage('observations')
        record('source_observed', actual_view=view, source_index=len(sessions) - 1)
        added = [row for row in view['observations'] if row['id'] not in seen]
        assert len(added) == 1, 'Actual provider supplied no single valid mood observation'
        observation = added[0]
        assert observation['source_kind'] == 'self_report' and observation['subject'] == 'user'
        assert observation['tendency'] == source['tendency']
        assert observation['source_excerpt'] in source['text']
        assert observation['session_id'] == answer['session_id'] and observation['consent_version'] == version
        assert began <= observation['observed_at'] <= int(time.time())
        seen.add(observation['id'])
        proof['observations'].append(observation)
        record('source_verified')
    assert len(seen) == 5 and len(set(sessions)) == 5
    await ask(sample['other_person_quote'])
    view = await manage('observations')
    record('other_person_quote', actual_view=view)
    assert {row['id'] for row in view['observations']} == seen
    answer, _ = await ask(sample['trend_query'])
    assert context_data(answer)['emotion_trend']['status'] == 'insufficient_observations'
    view = await manage('observations')
    record('insufficient_calendar', actual_view=view)
    assert view['trend']['status'] == 'insufficient_observations'
    group = view['trend']['groups']['self_report']
    assert group['count'] == 5 and group['sessions'] == 5 and group['calendar_span_days'] < 7
    assert not group['distribution'] and not group['evidence_ids']
    proof['actual_insufficient_trend'] = view['trend']
    target = proof['observations'][0]
    await manage('observation_update', id=target['id'], tendency='neutral')
    corrected = next(row for row in (await manage('observations'))['observations'] if row['id'] == target['id'])
    assert corrected['tendency'] == 'neutral' and corrected['version'] == target['version'] + 1
    assert corrected['correction_origin'] == 'user_management'
    assert corrected['source_excerpt'] == target['source_excerpt']
    proof['actual_management_correction'] = corrected
    record('corrected')
    disabled = await manage('emotion_consent', enabled=False)
    record('disabled', actual_view=disabled)
    assert not disabled['consent']['enabled'] and disabled['consent']['version'] > version
    assert disabled['trend']['status'] == 'disabled'
    answer, _ = await ask(sample['disabled_message'])
    assert context_data(answer)['emotion_trend']['status'] == 'disabled'
    view = await manage('observations')
    record('disabled_after_message', actual_view=view)
    assert {row['id'] for row in view['observations']} == seen
    await stop()
    second_pid = await start()
    assert second_pid != first_pid
    proof['server_pids'].append(second_pid)
    answer, _ = await ask(sample['trend_query'])
    assert context_data(answer)['emotion_trend']['status'] == 'disabled'
    after_restart = await manage('observations')
    record('disabled_after_restart', actual_view=after_restart)
    assert not after_restart['consent']['enabled'] and len(after_restart['observations']) == 5
    await manage('emotion_consent', enabled=True)
    await manage('observation_delete', id=target['id'])
    remaining = (await manage('observations'))['observations']
    record('deleted_one', remaining=remaining)
    assert {row['id'] for row in remaining} == seen - {target['id']}
    await manage('emotion_clear')
    assert not (await manage('observations'))['observations']
    await stop()
    third_pid = await start()
    assert len({first_pid, second_pid, third_pid}) == 3
    proof['server_pids'].append(third_pid)
    answer, saved = await ask(sample['trend_query'])
    final = await manage('observations')
    record('cleared_after_restart', actual_view=final)
    assert final['consent']['enabled'] and not final['observations'] and not saved['memories']
    assert context_data(answer)['emotion_trend']['status'] == 'insufficient_observations'
    proof.update(final=final, source_sessions=sessions, real_calendar_acceptance='unexecuted_user_self_test',
                 semantic_review='required; original replies retained; no claim of a seven-day trend')
    record('complete')
    return proof
