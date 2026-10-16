"""Observed real provider failures; no manufactured model text or success rows."""

import asyncio
import json
import time


def observed_fault_checks(report):
    """Keep empty output, malformed JSON and real SDK timeout distinct."""
    truncated = [row for row in report.get('fault_outputs', []) if row['mode'] == 'truncated_json']
    malformed = []
    for row in truncated:
        output = row['output']
        if not isinstance(output, str) or not output.strip():
            malformed.append(False)
            continue
        try:
            json.loads(output)
        except json.JSONDecodeError:
            malformed.append(True)
        else:
            malformed.append(False)
    timeouts = [row for row in report.get('fault_errors', []) if row['mode'] == 'read_timeout']
    return {
        'two_nonempty_malformed_json_outputs': len(malformed) == 2 and all(malformed),
        'two_real_sdk_timeouts': len(timeouts) == 2 and all(
            any('Timeout' in name for name in row['error_chain']) for row in timeouts),
    }


async def drive_faults(endpoint, tls, headers, root, sample, ask, manage, start, stop, first_pid):
    from websockets.asyncio.client import connect

    proofs = []
    for mode, key in [('truncated_json', 'truncated_source'), ('read_timeout', 'timeout_source')]:
        async with connect(endpoint, ssl=tls, additional_headers=headers, open_timeout=10) as socket:
            assert json.loads(await socket.recv())['type'] == 'hello'
            await socket.send(json.dumps({'type': 'test_chat', 'query': sample[key], 'fault_kind': mode}))
            answer = None
            while True:
                value = json.loads(await asyncio.wait_for(socket.recv(), timeout=65))
                assert value['type'] not in {'test_error', 'mia_authorization'}
                if value['type'] == 'test_reply':
                    answer = value
                    assert value['job_state_at_reply'] in {'pending', 'extracting', 'retry_wait'}
                if value['type'] == 'test_failed':
                    assert answer and value['state'] == 'failed' and value['attempts'] == 2
                    assert value['job_id'] == answer['admission_status']['id'] and not value['memories']
                    proofs.append({'mode': mode, 'job_id': value['job_id'], 'attempts': value['attempts'],
                        'terminal_error_category': value['error_category'],
                        'job_state_at_foreground_reply': answer['job_state_at_reply'],
                        'source_session': answer['session_id']})
                    break
    report = json.loads((root / 'results.json').read_text())
    checks = observed_fault_checks(report)
    # An undemonstrated truncation fault must fail the final gate, but must not
    # prevent independent recovery/restart checks from producing real evidence.
    assert (await manage('list'))['memories'] == []
    source, saved = await ask(sample['source'])
    assert saved['job_state'] == 'committed' and len(saved['memories']) == 1
    fact = saved['memories'][0]
    assert fact['content'] == sample['source'] and fact['confirmed'] and fact['source']
    started = time.monotonic()
    await stop()
    shutdown = time.monotonic() - started
    assert shutdown <= 20, 'Idle isolated service shutdown exceeded original twenty-second bound'
    second_pid = await start()
    assert second_pid != first_pid
    answer, saved = await ask(sample['query'])
    assert answer['session_id'] != source['session_id']
    assert answer['diagnostics']['selected_fact_ids'] == [fact['id']]
    assert sample['answer_term'] in answer['raw'] and sample['answer_term'] in answer['tts_text']
    assert len(saved['memories']) == 1 and saved['memories'][0]['id'] == fact['id']
    report = json.loads((root / 'results.json').read_text())
    duplicates = report['duplicate_submissions']
    assert len(duplicates) == 4 and all(row['status'] == 'duplicate' and row['same_id'] for row in duplicates)
    return {'faults': proofs, 'duplicate_submissions': duplicates, 'normal_source_id': fact['id'],
        'checks': checks, 'passed': all(checks.values()),
        'server_pids': [first_pid, second_pid], 'idle_shutdown_seconds': shutdown,
        'scope': 'Real selected model and SDK, extraction-only fault envelope; ordinary restart and idle shutdown, not in-flight/full-server/P23 shutdown acceptance',
        'semantic_review': 'all actual raw foreground answers require review'}
