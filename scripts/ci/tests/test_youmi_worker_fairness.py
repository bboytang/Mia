import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from server.companion.extraction import normalize, source_supported


spec = importlib.util.spec_from_file_location('youmi_worker_fairness',
    Path(__file__).resolve().parents[1] / 'youmi_worker_fairness.py')
fairness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fairness)


class FairnessEvidenceTests(unittest.TestCase):
    def terminal_jobs(self):
        return [{'warm': number < 6, 'state': 'committed', 'submit_to_observed_terminal_seconds': number + 1}
            for number in range(36)]

    def test_invalid_proposal_does_not_become_a_normal_success_latency_sample(self):
        jobs = self.terminal_jobs()
        jobs[-1]['state'] = 'failed'
        result = fairness.task_verdict(jobs)
        self.assertFalse(result['normal_task_acceptance_passed'])
        self.assertIsNone(result['normal_task_latency'])
        self.assertEqual(result['terminal_task_latency']['count'], 30)
        self.assertEqual(result['successful_task_latency_exploratory']['count'], 29)
        self.assertEqual(result['terminal_task_outcomes'], {'committed': 29, 'failed': 1})

    def test_failed_warmup_and_slow_valid_jobs_still_fail_original_contract(self):
        jobs = self.terminal_jobs()
        self.assertTrue(fairness.task_verdict(jobs)['normal_task_acceptance_passed'])
        jobs[0]['state'] = 'failed'
        result = fairness.task_verdict(jobs)
        self.assertEqual(result['normal_task_latency']['count'], 30)
        self.assertFalse(result['normal_task_acceptance_passed'])
        jobs[0]['state'] = 'committed'
        for job in jobs:
            job['submit_to_observed_terminal_seconds'] = 121
        self.assertFalse(fairness.task_verdict(jobs)['normal_task_acceptance_passed'])

    def test_all_failed_tasks_have_only_terminal_latency(self):
        jobs = self.terminal_jobs()
        for job in jobs:
            job['state'] = 'failed'
        result = fairness.task_verdict(jobs)
        self.assertFalse(result['normal_task_acceptance_passed'])
        self.assertIsNone(result['normal_task_latency'])
        self.assertIsNone(result['successful_task_latency_exploratory'])
        self.assertEqual(result['terminal_task_outcomes'], {'failed': 30})

    def samples(self, order):
        jobs = [{'admission': {'id': owner + str(slot)}, 'owner': owner, 'admitted_at_ms': 1}
            for owner in ('a', 'b', 'c') for slot in (0, 1)]
        calls = [{'job_id': key, 'owner': key[0], 'started_at_ms': i + 2, 'finished_at_ms': i + 2.5}
            for i, key in enumerate(order)]
        return jobs, calls

    def test_greedy_scope_order_and_late_admission_do_not_count_as_fair_backlog(self):
        jobs, calls = self.samples(['a0', 'a1', 'b0', 'b1', 'c0', 'c1'])
        self.assertFalse(fairness.round_evidence(jobs, calls)['scope_first_cycle_fair'])
        jobs, calls = self.samples(['a0', 'b0', 'c0', 'a1', 'b1', 'c1'])
        self.assertTrue(fairness.round_evidence(jobs, calls)['scope_first_cycle_fair'])
        jobs[-1]['admitted_at_ms'] = 3
        self.assertFalse(fairness.round_evidence(jobs, calls)['all_admitted_before_first_native_finished'])

    def test_missing_or_foreign_native_entry_cannot_prove_scope_service(self):
        jobs, calls = self.samples(['a0', 'b0', 'c0', 'a1', 'b1', 'c1'])
        with self.assertRaises(AssertionError):
            fairness.round_evidence(jobs, calls[:-1])
        calls[0]['owner'] = 'foreign'
        with self.assertRaises(AssertionError):
            fairness.round_evidence(jobs, calls)

    def test_fixture_has_one_warm_five_measured_short_dense_sources_without_empty_shortcuts(self):
        fixture = json.loads(fairness.FIXTURE.read_text())
        self.assertEqual(len(fixture['rounds']), 6)
        values = []
        for row in fixture['rounds']:
            self.assertLessEqual(len(row['short']), 40)
            self.assertTrue(160 <= len(row['dense']) <= 260)
            for profile in ('short', 'dense'):
                source = row[profile]
                self.assertTrue(source_supported(source, None))
                self.assertTrue(source_supported(source, normalize(source)))
                values.append(source)
        self.assertEqual(len(set(values)), 12)


class CompleteFailedBatchTests(unittest.IsolatedAsyncioTestCase):
    async def test_rejected_warmup_preserves_six_rounds_and_fails_acceptance(self):
        child = {'native_extractions': [], 'worker_fairness_contract_passed': False}
        jobs = []

        class Socket:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def send(self, value):
                self.request = json.loads(value)

            async def recv(self):
                number = self.request['round']
                own = [x for x in jobs if x['round'] == number and x['owner'] == self.owner]
                if self.request['type'] == 'submit_fair':
                    key = f'{number}-{self.owner}-{self.request["profile"]}'
                    job = {'admission': {'id': key}, 'round': number, 'warm': number == 0,
                        'owner': self.owner, 'profile': self.request['profile'], 'admitted_at_ms': 1,
                        'state': 'failed' if number == 0 else 'committed',
                        'submit_to_observed_terminal_seconds': 2}
                    jobs.append(job)
                    child['native_extractions'].append({'job_id': key, 'owner': self.owner,
                        'started_at_ms': number * 10 + (0 if job['profile'] == 'short' else 3)
                            + ('a', 'b', 'c').index(self.owner) + 2,
                        'finished_at_ms': number * 10 + 9})
                    own = [job]
                return json.dumps({'type': 'p23_fair', 'jobs': own})

        def connect(url, *, ssl, additional_headers):
            socket = Socket()
            socket.owner = additional_headers['device-id']
            return socket

        auth = SimpleNamespace(generate_token=lambda *args: 'synthetic')
        peers = [{'device_id': x, 'client_id': x, 'private_credential': 'synthetic'} for x in ('a', 'b', 'c')]
        with tempfile.TemporaryDirectory() as directory:
            report = {}
            environment = {'MIA_P23_MODE': 'worker-fairness', 'MIA_P23_PEERS': json.dumps(peers),
                'MIA_SCOPE_CA': 'synthetic', 'MIA_P23_REPORT_DIR': directory}
            modules = {'core.auth': SimpleNamespace(AuthManager=lambda *args: auth),
                'websockets.asyncio.client': SimpleNamespace(connect=connect)}
            # Persist the synthetic child evidence after each parent observation.
            def persist(value):
                path = Path(directory) / 'app-child/app-results.json'
                path.parent.mkdir(exist_ok=True)
                path.write_text(json.dumps(child))
            with patch.dict(os.environ, environment), patch.dict(sys.modules, modules), \
                    patch.object(fairness.ssl, 'create_default_context'):
                await fairness.drive({'worker_port': 1}, report, persist)
        self.assertEqual(len(report['fair_jobs']), 36)
        self.assertEqual(len(report['fair_rounds']), 6)
        self.assertTrue(report['fairness_batch_complete'])
        self.assertTrue(report['scope_fairness_sampling_passed'])
        self.assertFalse(report['worker_contract_passed'])
        self.assertFalse(report['normal_task_acceptance_passed'])


if __name__ == '__main__':
    unittest.main()
