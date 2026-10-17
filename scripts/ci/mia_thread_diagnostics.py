"""Paired actual ORT thread experiments in fresh processes, never D08 acceptance."""

import asyncio
import hashlib
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch


def encoder_for_arm(directory, threads, encoder_class, report):
    import onnxruntime as ort

    original = ort.InferenceSession

    def session(path, options, **kwargs):
        assert options.intra_op_num_threads == 1
        options.intra_op_num_threads = threads
        value = original(path, options, **kwargs)
        actual = value.get_session_options()
        assert actual.intra_op_num_threads == threads and actual.inter_op_num_threads == 1
        report['trial_session_options'] = {'intra_op_num_threads': actual.intra_op_num_threads,
            'inter_op_num_threads': actual.inter_op_num_threads,
            'providers': value.get_providers()}
        return value

    # Scope the experiment to construction of this real session. The runtime
    # encoder, tokenizer, model, normalization and invocation remain original.
    with patch.object(ort, 'InferenceSession', session):
        return encoder_class(directory)


def check_vectors(encoder, fixture, vectors):
    values = {f'document-{i}-{profile}': vector for (i, profile), vector in vectors.items()}
    values.update({f'query-{i}': encoder.encode(query, query=True)
        for i, query in enumerate(fixture['queries'])})
    return {key: {'sha256': hashlib.sha256(value.tobytes()).hexdigest(),
        'float32_le_hex': value.astype('<f4').tobytes().hex()} for key, value in values.items()}


async def run_pairs(report, save, group_state, members):
    import numpy as np

    root = Path(os.environ['MIA_P23_REPORT_DIR'])
    report.update(cgroup_before=group_state(), members_before=members(),
        thread_order=[2, 1, 1, 2], thread_arms=[],
        trial_scope='Fresh Python processes in ABBA order; actual manager/databases stay in same parent; not acceptance')
    for number, threads in enumerate(report['thread_order']):
        directory = root / f'thread-arm-{number}-{threads}'
        directory.mkdir()
        arm = {'number': number, 'intra_op_num_threads': threads, 'directory': directory.name}
        report['thread_arms'].append(arm)
        save(report)
        environment = dict(os.environ, MIA_P23_REPORT_DIR=str(directory),
            MIA_P23_MODE='thread-arm', MIA_P23_THREADS=str(threads))
        with (directory / 'python.log').open('wb') as output:
            process = await asyncio.create_subprocess_exec(sys.executable,
                str(Path(__file__).with_name('verify_mia_shared_envelope.py')),
                env=environment, stdout=output, stderr=asyncio.subprocess.STDOUT)
            arm['pid'] = process.pid
            save(report)
            try:
                arm['returncode'] = await asyncio.wait_for(process.wait(), 180)
            finally:
                if process.returncode is None:
                    process.kill()
                    await process.wait()
        assert arm['returncode'] == 0, 'Thread arm failed; preserve its original report/log'
        result = json.loads((directory / 'shared-results.json').read_text())
        assert result['code_sha'] == report['code_sha'] and result['diagnostic_complete']
        assert result['trial_session_options']['intra_op_num_threads'] == threads
        assert result['members_before']['python']['pid'] == arm['pid']
        row = result['capacity'][0]
        assert row['integrity'] == 'ok' and row['diagnostics']['competition']['rebuild']['indexed'] == 32
        assert row['static_features']['entries'] == 20000
        arm.update(diagnostic_complete=True, rss_peak_mib=row['rss_peak_mib'],
            python_cpu_seconds=row['python_cpu_seconds'], wall_seconds=row['wall_seconds'],
            sequential_pipeline=row['diagnostics']['sequential_pipeline'],
            competition=row['diagnostics']['competition'], cgroup_after=row['cgroup_after'])
        save(report)

    results = [json.loads((root / arm['directory'] / 'shared-results.json').read_text())
        for arm in report['thread_arms']]
    baseline = results[0]
    comparisons = []
    for number, result in enumerate(results):
        vectors = result['encoder_check_vectors']
        assert vectors.keys() == baseline['encoder_check_vectors'].keys()
        maximum = max(float(np.max(np.abs(
            np.frombuffer(bytes.fromhex(value['float32_le_hex']), dtype='<f4') -
            np.frombuffer(bytes.fromhex(baseline['encoder_check_vectors'][key]['float32_le_hex']), dtype='<f4'))))
            for key, value in vectors.items())
        original = baseline['capacity'][0]['result_checks']
        current = result['capacity'][0]['result_checks']
        selected = lambda checks: [[row['id'] for row in check['retrieval']['results']] for check in checks]
        candidates = lambda checks: [[(row['id'], row['candidate_sources'])
            for row in check['retrieval']['candidates']] for check in checks]
        comparisons.append({'arm_number': number,
            'vectors_bitwise_equal': vectors == baseline['encoder_check_vectors'],
            'vector_max_abs_difference': maximum,
            'retrievals_exact_equal': current == original,
            'selected_ids_and_order_equal': selected(current) == selected(original),
            'candidate_ids_order_sources_equal': candidates(current) == candidates(original)})
    report['thread_consistency'] = comparisons
    report['all_checks_exact_equal'] = all(value['vectors_bitwise_equal']
        and value['retrievals_exact_equal'] for value in comparisons)
    events = dict(line.split() for line in group_state()['memory.events'].splitlines())
    assert events['oom'] == events['oom_kill'] == '0'
    report['diagnostic_complete'] = True
