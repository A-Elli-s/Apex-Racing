import copy
import importlib.util
import pathlib
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / 'scripts' / 'audit_points.py'
spec = importlib.util.spec_from_file_location('audit_points', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def sample():
    return {'series': 'IMSA', 'season': 2026, 'data': {
        'headers': ['Rank', 'Drivers', 'Daytona', 'Sebring', 'Total'],
        'rows': [['1', 'Driver A', '350', '300', '650'],
                 ['2', 'Driver B', '320', '250', '570'],
                 ['3', 'Driver C', '290', '100', '390']]}}


class AuditTests(unittest.TestCase):
    def test_audits_published_totals(self):
        doc = sample()
        changed, status = module.audit_snapshot(doc, '2026-10-23T00:00:00Z')
        self.assertTrue(changed)
        self.assertEqual(status, 'verified_against_published_total')
        self.assertEqual(doc['data']['rows'][0][-1], '650')

    def test_rejects_mismatched_published_total(self):
        doc = sample()
        doc['data']['rows'][0][-1] = '999'
        original = copy.deepcopy(doc)
        changed, status = module.audit_snapshot(doc, '2026-10-23T00:00:00Z')
        self.assertFalse(changed)
        self.assertIn('disagrees', status)
        self.assertEqual(doc, original)

    def test_rejects_missing_event_points(self):
        doc = sample()
        doc['data']['rows'][1][2] = '-'
        changed, status = module.audit_snapshot(doc, '2026-10-23T00:00:00Z')
        self.assertFalse(changed)
        self.assertIn('Missing event points', status)

    def test_reconstructs_only_with_explicit_metadata(self):
        doc = sample()
        doc['series'] = 'F2'
        doc['data']['headers'].pop()
        for row in doc['data']['rows']:
            row.pop()
        changed, _ = module.audit_snapshot(doc, '2026-10-23T00:00:00Z')
        self.assertFalse(changed)
        self.assertEqual(len(doc['data']['headers']), 4)
        doc['data'].update({'awarded_points_columns': ['Daytona', 'Sebring'],
                            'points_include_adjustments': True,
                            'source_complete_through': 'Round 2'})
        changed, status = module.audit_snapshot(doc, '2026-10-23T00:00:00Z')
        self.assertTrue(changed)
        self.assertEqual(status, 'calculated_from_awarded_event_points')
        self.assertEqual(doc['data']['rows'][0][-1], '650')

    def test_does_not_sum_finish_positions(self):
        doc = sample()
        doc['series'] = 'F3'
        doc['data']['headers'] = ['Rank', 'Drivers', 'Race 1 finish', 'Race 2 finish', 'Total']
        changed, status = module.audit_snapshot(doc, '2026-10-23T00:00:00Z')
        self.assertFalse(changed)
        self.assertIn('no declared', status)


if __name__ == '__main__':
    unittest.main()
