"""Public-fixture checks for dated effort, independent proof and safe writes.

No ignored collection file, network connection or canonical write is required.
"""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import os
import unittest

from apply_refresh_2026_10_28 import (ROOT, apply_child_reviews,
    assert_native_retained, combine_source_cards, integrate, native_child_overrides,
    replace_group, sync_video_review_cards)
from prepare_meeting_refresh_2026_10_28 import owner_decision, OWNER_INCREMENT_ID


class OctoberRefreshTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = json.loads((ROOT / 'data/shared-dashboard.json').read_text())
        cls.decision = owner_decision(json.loads((ROOT / 'EFFORT_ESTIMATE.json').read_text()))

    def test_dated_owner_increment_is_idempotent_and_never_changes_outcomes(self):
        before = deepcopy(self.before)
        first = integrate(before, {}, {}, {}, self.decision,
            generated_at='2026-10-29T06:30:00Z')
        second = integrate(first, {}, {}, {}, self.decision,
            generated_at='2026-10-29T06:30:00Z')
        self.assertEqual(first, second)
        self.assertEqual(self.before, before, 'The integration input was mutated')
        self.assertEqual(first['outcomes'], before['outcomes'])
        summary = first['time']['summary']
        self.assertEqual((summary['nonMeetingEstimateHoursLow'], summary['nonMeetingEstimateHoursHigh']), (21.75, 23.0))
        self.assertIsNone(summary['combinedWorkedHours'])
        evidence = [row for stream in first['time']['workstreams'] for row in stream.get('evidence', [])
            if row.get('id') == OWNER_INCREMENT_ID]
        self.assertEqual(len(evidence), 1)
        self.assertEqual(first['time']['meetings'], before['time']['meetings'])

    def test_current_policy_can_be_replayed_without_temporarily_writing_it(self):
        # Model the post-publication canonical decision entirely in memory.
        from prepare_shared_snapshot import curate_snapshot
        updated = curate_snapshot(self.before, effort_decision=self.decision)
        original = json.loads((ROOT / 'EFFORT_ESTIMATE.json').read_text())
        from apply_effort_estimate import apply_effort_estimate as apply_original
        def approved_current_policy(effort, decision=None):
            return apply_original(effort, decision=self.decision if decision is None else decision)
        with patch('prepare_shared_snapshot.apply_effort_estimate', approved_current_policy):
            value = integrate(updated, {}, {}, {}, self.decision)
        self.assertEqual(value['time']['summary']['nonMeetingEstimateHoursLow'], 21.75)
        self.assertEqual(json.loads((ROOT / 'EFFORT_ESTIMATE.json').read_text()), original)

    def test_stale_or_reassigned_sheet_review_is_rejected(self):
        for change in ({'appliesToSnapshotAt': '1999-01-01T00:00:00Z'},
                       {'records': [{'sourceRow': -1, 'profileId': 'wrong-profile'}]}):
            review = {'snapshotAt': '2026-10-29T06:30:00Z', 'reviewedAt': '2026-10-29T06:31:00Z',
                'appliesToSnapshotAt': self.before['video']['snapshotAt'], 'records': []}
            review.update(change)
            with self.subTest(change=change), self.assertRaises(AssertionError):
                apply_child_reviews(deepcopy(self.before), self.before,
                    {'video.sourceFreshnessReview': review})

    def test_inventory_cannot_relabel_native_proof_as_newly_observed(self):
        changed = deepcopy(self.before)
        changed['video']['messageDateReview']['platformObservedEvents'][0]['observedAt'] = '2026-10-29T06:30:00Z'
        with self.assertRaisesRegex(AssertionError, 're-date'):
            assert_native_retained(self.before, changed)

    def test_conflicting_cards_cannot_silently_share_a_clock(self):
        card = {'id': 'review', 'asOf': '2026-10-29T06:00:00Z', 'status': 'one'}
        self.assertEqual(combine_source_cards([[card], [deepcopy(card)]]), [card])
        with self.assertRaisesRegex(AssertionError, 'Conflicting'):
            combine_source_cards([[card], [dict(card, status='contradictory')]])

    def test_native_closure_overlay_requires_the_matching_explicit_bundle(self):
        with TemporaryDirectory() as directory:
            folder = Path(directory)
            bundle = folder / 'native.json'
            bundle.write_text(json.dumps({'review': {'snapshotAt': '2026-10-29T06:00:00Z'}}))
            child = folder / 'closure.json'
            child.write_text(json.dumps({'snapshotAt': '2026-10-29T06:00:00Z', 'current': True}))
            manifest = folder / 'manifest.json'
            manifest.write_text(json.dumps({'patches': {'videoMessageDateReview': 'native.json'},
                'independentChildren': [{'path': ['video', 'gapResolutionReview'], 'file': 'closure.json'}]}))
            original = {'video.gapResolutionReview': {'snapshotAt': '2026-10-29T05:00:00Z'}}
            result = native_child_overrides(original, bundle, manifest)
            self.assertTrue(result['video.gapResolutionReview']['current'])
            self.assertNotIn('current', original['video.gapResolutionReview'])
            different = folder / 'other-native.json'
            different.write_text('{}')
            with self.assertRaisesRegex(AssertionError, 'different message bundle'):
                native_child_overrides(original, different, manifest)
            child.write_text(json.dumps({'snapshotAt': '2026-10-29T04:00:00Z'}))
            with self.assertRaisesRegex(AssertionError, 'older'):
                native_child_overrides(original, bundle, manifest)

    def test_review_cards_use_current_child_counts_and_independent_clocks(self):
        snapshot = {'sources': [], 'video': {'snapshotAt': '2026-10-29T05:00:00Z',
            'messageDateReview': {'snapshotAt': '2026-10-29T06:00:00Z',
                'reviewedAt': '2026-10-29T06:00:00Z',
                'platformObservedEvents': [
                    {'direction': 'outbound', 'videoIncluded': True, 'date': '2026-10-27'},
                    {'direction': 'outbound', 'videoIncluded': True, 'date': '2026-09-23'}],
                'focusedNativeReviews': {'profilesChecked': 5},
                'summary': {'newObservedVideoFollowUpEventsAdded': 3}},
            'sourceFreshnessReview': {'snapshotAt': '2026-10-29T05:01:00Z',
                'inventoryChanged': True, 'changedPhysicalRows': 9,
                'changedMainPhysicalRows': 7, 'changedAcceptedPhysicalRows': 2},
            'gapResolutionReview': {'snapshotAt': '2026-10-29T06:00:00Z',
                'nativeClosureReview': {'priorityProfilesWithExactNativeVideoProof': ['one'],
                    'nativeFollowUps': [{'profileId': 'one'}]}}}}
        sync_video_review_cards(snapshot)
        cards = {row['id']: row for row in snapshot['sources']}
        message = cards['video_message_dates']
        self.assertIn('2 separately observed messages; 2 exact-asset video sends', message['coverage'])
        self.assertIn('5 profiles and 3 newly observed', message['coverage'])
        self.assertEqual(message['asOf'], '2026-10-29T06:00:00Z')
        freshness = cards['video_source_freshness']
        self.assertIn('9 changed physical rows (7 main; 2 accepted)', freshness['coverage'])
        self.assertNotIn('unchanged', freshness['status'])
        self.assertEqual(freshness['asOf'], '2026-10-29T05:01:00Z')
        self.assertIn('1 priority source sending gaps', cards['video_gap_resolution']['coverage'])

    def test_raw_transcript_material_cannot_enter_shared_data(self):
        invalid = deepcopy(self.before)
        invalid['meetings']['sentences'] = [{'text': 'Private raw dialogue'}]
        with self.assertRaisesRegex(AssertionError, 'Raw content'):
            integrate(invalid, {}, {}, {}, self.decision)

    def test_group_write_rolls_back_a_partial_replacement(self):
        with TemporaryDirectory() as directory:
            targets = [Path(directory) / name for name in ('decision', 'dashboard', 'shared')]
            for index, target in enumerate(targets):
                target.write_bytes(f'original{index}'.encode())
            originals = {p: p.read_bytes() for p in targets}
            replacements = {p: b'new reviewed value' for p in targets}
            calls = 0
            def fail_second(source, target):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError('Synthetic controlled replacement failure')
                os.replace(source, target)
            with self.assertRaisesRegex(OSError, 'Synthetic'):
                replace_group(replacements, replace=fail_second)
            self.assertEqual({p: p.read_bytes() for p in targets}, originals)
            self.assertEqual(set(Path(directory).iterdir()), set(targets))
            replace_group(replacements)
            self.assertEqual({p: p.read_bytes() for p in targets}, replacements)


if __name__ == '__main__':
    unittest.main(verbosity=2)
