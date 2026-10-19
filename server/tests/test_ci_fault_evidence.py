"""Fault evidence scoring only; synthetic cases are not provider acceptance."""

import unittest

from scripts.ci.youmi_behavior_faults import observed_fault_checks


class FaultEvidenceTests(unittest.TestCase):
    def report(self, outputs):
        return {'fault_outputs': [{'mode': 'truncated_json', 'output': value} for value in outputs],
                'fault_errors': [{'mode': 'read_timeout', 'error_chain': ['APITimeoutError', 'ReadTimeout']} for _ in range(2)]}

    def test_empty_output_and_valid_json_cannot_satisfy_malformed_gate(self):
        for outputs in [('', ''), (' ', '\n'), ('{}', '{}'), ('{"a":', '{}'), ('{"a":', '')]:
            with self.subTest(outputs=outputs):
                checks = observed_fault_checks(self.report(outputs))
                self.assertFalse(checks['two_nonempty_malformed_json_outputs'])
                self.assertTrue(checks['two_real_sdk_timeouts'])

    def test_two_observed_malformed_outputs_and_sdk_timeouts_are_required(self):
        self.assertTrue(all(observed_fault_checks(self.report(['{"a":', '['])).values()))
        for outputs in [[], ['['], ['[', '[', '[']]:
            self.assertFalse(observed_fault_checks(self.report(outputs))['two_nonempty_malformed_json_outputs'])
        report = self.report(['[', '['])
        report['fault_errors'][1]['error_chain'] = ['APIStatusError']
        self.assertFalse(observed_fault_checks(report)['two_real_sdk_timeouts'])
        self.assertFalse(any(observed_fault_checks({}).values()))
