import importlib.util
import json
from pathlib import Path
import unittest

from server.companion.extraction import normalize, source_supported


spec = importlib.util.spec_from_file_location('mia_worker_fairness',
    Path(__file__).resolve().parents[1] / 'mia_worker_fairness.py')
fairness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fairness)


class FairnessEvidenceTests(unittest.TestCase):
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


if __name__ == '__main__':
    unittest.main()
