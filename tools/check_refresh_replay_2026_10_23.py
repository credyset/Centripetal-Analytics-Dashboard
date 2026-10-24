"""Regressions for partial source refreshes and independently dated evidence.

Uses retained private collection fixtures when present. In a public checkout it
builds the same replay situations from the curated shared snapshot; no ignored
private file, network connection, source write, or publication is required.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import copy
import json
import unittest

from apply_refresh_2026_10_23 import apply_patches, event_key, merge_message_review

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / 'data/private/refresh_2026_10_23'


def load(path):
    return json.loads(path.read_text())


def fixture():
    baseline_path = PRIVATE / 'baseline_shared.json'
    baseline = load(baseline_path if baseline_path.exists() else ROOT / 'data/shared-dashboard.json')
    fresh_path = PRIVATE / 'sheets/video_inventory_patch.json'
    fresh = copy.deepcopy(load(fresh_path) if fresh_path.exists() else baseline['video'])
    # A synthetic later import must remain later than any real fixture after
    # the dashboard is updated, rather than relying on a hard-coded date.
    clocks = [datetime.now(timezone.utc)]
    for value in (baseline['video'].get('snapshotAt'), fresh.get('snapshotAt'),
                  baseline['video'].get('messageDateReview', {}).get('snapshotAt'),
                  baseline['video'].get('messageDateReview', {}).get('reviewedAt')):
        if value:
            stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
            clocks.append(stamp.replace(tzinfo=timezone.utc) if stamp.tzinfo is None else stamp)
    future = (max(clocks) + timedelta(days=1)).isoformat().replace('+00:00', 'Z')
    fresh['snapshotAt'] = future
    # Export-only inventory is deliberately missing the old row-scoped joins.
    # Reorder rows as well as changing the collection clock: the same numeric
    # row must not silently keep an earlier contact's identity proof.
    row_numbers = {row['sourceRow']: row['sourceRow'] + 10000 for row in fresh['rows']}
    for row in fresh['rows']:
        row['sourceRow'] = row_numbers[row['sourceRow']]
    for row in fresh.get('datedActions', []):
        if row.get('sourceRow') in row_numbers:
            row['sourceRow'] = row_numbers[row['sourceRow']]
    for key in ('crmReconciliation', 'recordingFieldReview', 'messageDateReview'):
        fresh.pop(key, None)
    return baseline, fresh, future


class RefreshReplayTests(unittest.TestCase):
    def setUp(self):
        self.baseline, self.fresh, self.future = fixture()
        self.before = copy.deepcopy(self.baseline)
        self.prior = copy.deepcopy(self.baseline['video']['messageDateReview'])
        self.reporting_day = max('2026-10-23', self.baseline['meta'].get('reportingAsOfDate', ''))

    def apply_inventory_only(self):
        return apply_patches(self.baseline, {'videoInventory': self.fresh},
                             reporting_as_of=self.reporting_day)

    def partial_review(self, **changes):
        value = {'snapshotAt': self.future, 'reviewedAt': self.future,
                 'records': [], 'platformObservedEvents': [],
                 'separateEmailContext': [], 'explicitReplyReports': [],
                 'nativePlatformCoverage': {}}
        value.update(changes)
        return value

    def merge(self, incoming):
        return merge_message_review(self.prior, incoming, self.fresh,
                                    self.baseline['waalaxy'].get('sheetSubset'),
                                    self.baseline['waalaxy'].get('sheetSubsetCollectedAt'))

    def test_inventory_refresh_archives_old_row_scoped_reviews(self):
        result = self.apply_inventory_only()
        video = result['video']
        archived = video.get('historicalRowScopedReviews', [])
        self.assertTrue(archived, 'Old review evidence must remain accessible in a historical archive.')
        for kind in ('crmReconciliation', 'recordingFieldReview'):
            prior = self.baseline['video'].get(kind)
            self.assertIsNotNone(prior, f'The regression fixture needs an earlier {kind}.')
            active = video.get(kind)
            self.assertTrue(not active or active.get('appliesToSnapshotAt') == video['snapshotAt'],
                            f'{kind} must not remain active against a different inventory.')
            matches = [entry for entry in archived
                       if entry.get('reviewKind') == kind and entry.get('historicalOnly') is True
                       and entry.get('review') == prior]
            self.assertTrue(matches, f'Archive must preserve the complete original {kind}, including its clock and rows.')
        self.assertEqual(self.baseline, self.before, 'Integration must not mutate its baseline input.')

    def test_inventory_refresh_keeps_email_context_and_native_proof_separate(self):
        result = self.apply_inventory_only()['video']['messageDateReview']
        self.assertEqual(result.get('separateEmailContext'), self.prior.get('separateEmailContext'))
        old_events = {event_key(event): event for event in self.prior.get('platformObservedEvents', [])}
        current = {event_key(event): event for event in result.get('platformObservedEvents', [])}
        self.assertTrue(set(old_events) <= set(current))
        self.assertEqual(len(current), len(old_events), 'A worksheet refresh cannot add native observations.')
        for key, event in old_events.items():
            for field in ('date', 'occurredAt', 'observedAt', 'sourceRow', 'assetId',
                          'loomAssetId', 'direction', 'videoIncluded'):
                self.assertEqual(current[key].get(field), event.get(field),
                                 f'Inventory refresh must not re-date or reassign historical native evidence: {field}.')

    def test_partial_native_review_preserves_independent_families(self):
        result = self.merge(self.partial_review())
        for family in ('separateEmailContext', 'explicitReplyReports', 'nativePlatformCoverage'):
            self.assertTrue(self.prior.get(family), f'The regression fixture needs retained {family}.')
            self.assertEqual(result.get(family), self.prior[family],
                             f'Empty fields in an incremental native review cannot erase {family}.')
        old_events = {event_key(event) for event in self.prior['platformObservedEvents']}
        new_events = {event_key(event) for event in result['platformObservedEvents']}
        self.assertEqual(new_events, old_events, 'Rechecking an empty native increment must not duplicate or erase events.')
        self.assertTrue({row['profileId'] for row in self.prior['records']} <=
                        {row['profileId'] for row in result['records']})

    def test_partial_record_update_keeps_omitted_evidence(self):
        prior_record = self.prior['records'][0]
        prior_record['retainedEvidenceMarker'] = 'Earlier independently dated CRM context'
        ident = prior_record['profileId']
        incoming = self.partial_review(records=[{'profileId': ident,
                                                'platformCheckStatus': 'matched',
                                                'lastPlatformCheckedAt': self.future}])
        result = self.merge(incoming)
        record = next(row for row in result['records'] if row['profileId'] == ident)
        self.assertEqual(record['platformCheckStatus'], 'matched')
        self.assertEqual(record['lastPlatformCheckedAt'], self.future)
        for field in ('company', 'contact', 'linkedin', 'reportedReplyDate',
                      'reportedReplyNoteId', 'retainedEvidenceMarker'):
            if field in prior_record:
                self.assertEqual(record.get(field), prior_record[field],
                                 f'A partial contact update cannot discard earlier {field}.')

    def test_replaying_inventory_does_not_duplicate_archived_proof(self):
        first = self.apply_inventory_only()
        second = apply_patches(first, {'videoInventory': self.fresh},
                               reporting_as_of=self.reporting_day)
        self.assertEqual(second['video'].get('historicalRowScopedReviews'),
                         first['video'].get('historicalRowScopedReviews'))

    def test_partial_native_review_cannot_mix_different_cohort_scopes(self):
        variants = [{'cohort': 'Different independently reviewed cohort'},
                    {'profileChecks': [{'profileId': 'new-test-cohort-profile',
                                        'status': 'checked_unconfirmed'}]}]
        for coverage in variants:
            with self.subTest(coverage_keys=sorted(coverage)):
                with self.assertRaises((AssertionError, ValueError)):
                    self.merge(self.partial_review(nativePlatformCoverage=coverage))

    def test_complete_review_wrapper_accepts_explicit_new_cohort(self):
        review = copy.deepcopy(self.prior)
        review.update(snapshotAt=self.future, reviewedAt=self.future)
        review['nativePlatformCoverage']['cohort'] = 'Explicit complete replacement cohort'
        incoming = {'replacementMode': 'complete_review_bundle',
                    'completeReviewBundle': True, 'review': review}
        result = self.merge(incoming)
        self.assertEqual(result['nativePlatformCoverage']['cohort'],
                         'Explicit complete replacement cohort')
        self.assertEqual(result['separateEmailContext'], review['separateEmailContext'])
        self.assertEqual({event_key(event) for event in result['platformObservedEvents']},
                         {event_key(event) for event in self.prior['platformObservedEvents']})

    def test_incomplete_complete_review_wrapper_is_rejected(self):
        required = {'snapshotAt', 'reviewedAt', 'scope', 'summary', 'records',
                    'platformObservedEvents', 'separateEmailContext',
                    'explicitReplyReports', 'nativePlatformCoverage', 'notes'}
        complete = copy.deepcopy(self.prior)
        complete.update(snapshotAt=self.future, reviewedAt=self.future)
        self.assertTrue(required <= set(complete), 'Fixture must contain every complete-review family.')
        for missing in required:
            with self.subTest(missing_family=missing):
                review = copy.deepcopy(complete)
                review.pop(missing)
                incoming = {'replacementMode': 'complete_review_bundle',
                            'completeReviewBundle': True, 'review': review}
                with self.assertRaises((AssertionError, ValueError)):
                    self.merge(incoming)


if __name__ == '__main__':
    unittest.main(verbosity=2)
