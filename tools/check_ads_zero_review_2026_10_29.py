"""Public fixtures for explicit aggregate-column, ID and UTC control validation."""
from copy import deepcopy
from pathlib import Path
from urllib.parse import urlencode
import json
import unittest

from prepare_ads_zero_review_2026_10_29 import verify_zero_review
from prepare_shared_snapshot import preserve_newer_shared_sources


class AdsZeroEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.ids = ['409641733', '445365453', '880330273', '880742753',
            '888447843', '891464353', '891475603']
        self.ads = {'lifecycleReview': {'accountId': '515259390'},
            'review': {'sourceScope': {'exportedAdSetIds': self.ids[2:],
                'uiOnlyZeroDeliveryAdSetIds': self.ids[:2]}}}
        self.meta = {'observedAt': '2026-10-29T06:38:16.046Z', 'accountId': '515259390',
            'sourceTimezone': 'UTC', 'start': '2026-10-22', 'end': '2026-10-29',
            'finalDayPartial': True, 'viewFilterCleared': True,
            'unfilteredAdSetCount': 7, 'parentCampaignCount': 18,
            'adSetIds': self.ids, 'aggregateMetricsObserved':
                {'spend': 0, 'impressions': 0, 'clicks': 0, 'rawLeads': 0}}
        headers = ['Ad set name', 'Off/On', 'Status', 'Key results', 'Campaign',
            'Spent', 'Cost per result', 'Impressions', 'Clicks', 'Average CTR',
            'Bid', 'Average CPM', 'Average CPC', 'Conversions', 'Cost per conversion',
            'Leads', 'Cost per lead', 'Event registrations', 'Leads (Work email)',
            'Cost per lead (Work email)']
        values = ['7 ad sets', '-', '-', '-', '-', '$0.00', '-', '0', '0',
            '-', '-', '-', '-', '0', '-', '0', '-', '0', '0', '-']
        query = urlencode({'campaignIds': json.dumps(self.ids), 'dateRange':
            json.dumps({'startDate': '10/22/2026', 'endDate': '10/29/2026'})})
        self.ax = '\n'.join(['Hi Charles', '/accounts/515259390/campaigns?',
            'tab (selected) Ad sets 7 total', 'Columns: Performance',
            'checkbox Status Completed, Value: 0', 'Campaigns 18 total',
            'There are 7 results shown in the table. There are 7 results total.',
            'button Page 1', 'Show 15 per page',
            'Value: linkedin.com/campaignmanager/accounts/515259390/performance-chart?' + query,
            '\t1 row',
            *[f'\t\t{100+i*2} column header\n\t\t\t{101+i*2} text {label}' for i, label in enumerate(headers)],
            '\t2 row', '\t\t200 column header row selection', '\t\t\t201 checkbox Select all rows',
            *[f'\t\t{300+i*2} column header\n\t\t\t{301+i*2} text {value}' for i, value in enumerate(values)],
            '\t3 row', *[f'text ID: {ident} · Sponsored Content\nbutton Completed' for ident in self.ids]])
        self.controls = 'Start date, Value: 10/22/2026\nEnd date, Value: 10/29/2026\ntext Time in UTC'

    def test_explicit_aggregate_zeros_have_only_four_verified_metrics(self):
        child = verify_zero_review(self.ax, self.controls, self.meta, self.ads)
        self.assertEqual(child['metrics'], self.meta['aggregateMetricsObserved'])
        self.assertEqual(child['snapshotAt'], self.meta['observedAt'])
        self.assertEqual(child['coverage']['completeDaysThrough'], '2026-10-28')
        self.assertTrue(child['coverage']['finalDayPartial'])
        self.assertEqual(child['sourceDailyRowsAdded'], 0)
        self.assertTrue(child['scope']['allVisibleCurrentAdSetsVerified'])

    def test_an_aggregate_dash_cannot_be_replaced_by_a_meta_zero(self):
        with self.assertRaisesRegex(AssertionError, 'aggregate zero columns'):
            verify_zero_review(self.ax.replace('text $0.00', 'text -'), self.controls, self.meta, self.ads)

    def test_metric_label_scope_or_utc_mismatch_is_rejected(self):
        for ax, controls in [(self.ax.replace('text Leads\n', 'text Qualified leads\n'), self.controls),
                             (self.ax.replace('ID: 880330273', 'ID: 999999999'), self.controls),
                             (self.ax, self.controls.replace('Time in UTC', 'Time in Mountain')),
                             (self.ax.replace('Status Completed, Value: 0', 'Status Completed, Value: 1'), self.controls)]:
            with self.subTest(ax=ax[:20], controls=controls), self.assertRaises(AssertionError):
                verify_zero_review(ax, controls, self.meta, self.ads)

    def test_current_day_cannot_be_labeled_complete(self):
        invalid = deepcopy(self.meta)
        invalid['finalDayPartial'] = False
        with self.assertRaises(AssertionError):
            verify_zero_review(self.ax, self.controls, invalid, self.ads)

    def test_newer_export_cannot_erase_the_independently_dated_ui_review(self):
        baseline = json.loads((Path(__file__).resolve().parents[1]/'data/shared-dashboard.json').read_text())
        child = verify_zero_review(self.ax, self.controls, self.meta, self.ads)
        baseline['ads']['zeroDeliveryReview'] = child
        baseline['sources'] = [c for c in baseline['sources'] if c['id'] != 'ads_zero_delivery']
        baseline['sources'].append({'id':'ads_zero_delivery','asOf':child['snapshotAt'],'status':'Current UI aggregate'})
        newer = deepcopy(baseline)
        newer['ads']['snapshotAt'] = '2030-01-01T00:00:00Z'
        newer['ads'].pop('zeroDeliveryReview')
        newer['sources'] = [c for c in newer['sources'] if c['id'] != 'ads_zero_delivery']
        for source, previous in ((newer, baseline), (baseline, newer)):
            retained = preserve_newer_shared_sources(source, previous)
            self.assertEqual(retained['ads']['snapshotAt'], newer['ads']['snapshotAt'])
            self.assertEqual(retained['ads']['zeroDeliveryReview'], child)
            self.assertEqual(next(c for c in retained['sources'] if c['id']=='ads_zero_delivery')['asOf'], child['snapshotAt'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
