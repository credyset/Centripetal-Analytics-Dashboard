"""Preserve independently dated invitation versions without revising source series."""
import copy
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import unittest

from prepare_shared_snapshot import (curate_snapshot, merge_invitation_restatements,
                                     preserve_newer_shared_sources)

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / 'data/private/adversarial_followup_2026_11_20/video'
PRIMARY = ROOT / 'data/private/refresh_2026_11_13/waalaxy'
RECORD = {
    'date': '2026-10-28',
    'retainedCsv': {'invitationsSent': 73, 'invitationsAccepted': 19},
    'laterAuthenticatedTooltip': {'invitationsSent': 73, 'invitationsAccepted': 25},
    'laterTooltipObservedAt': '2026-11-13T13:41:17.625Z',
    'retainedCsvCollectedAt': '2026-10-29T05:59:13.568976+00:00',
    'appliedToRetainedSeries': False,
    'basis': 'The latest view restated six additional acceptances for this historical source-day bucket. This bounded bridge does not reimport the earlier October series; the old CSV value is preserved. Neither vintage establishes exact acceptance-event dates.',
}


def fixture(parent='2026-11-20T05:18:16Z', invitation='2026-11-20T05:20:19.937Z', records=None):
    review = {'snapshotAt': invitation, 'sourceType': 'authenticated_home_chart_tooltips'}
    if records is not None:
        review['separatelyObservedRestatements'] = copy.deepcopy(records)
    return {'meta': {}, 'sources': [], 'waalaxy': {
        'snapshotAt': parent, 'invitationCollectedAt': invitation,
        'invitationCoverage': {'start': '2026-10-28', 'end': '2026-10-28', 'collectedAt': invitation},
        'invitationImportReview': review,
        'invitationSummary': {'sent': 73, 'accepted': 19},
        'daily': [{'date': '2026-10-28', 'invitationsSent': 73, 'invitationsAccepted': 19,
                   'historicalPersonFlags': 3}], 'metrics': {'historicalPeople': 7}}}


def records(snapshot):
    return snapshot['waalaxy']['invitationImportReview']['separatelyObservedRestatements']


def numeric_values(value, path=()):
    """All original numeric measures, excluding the new source-version context."""
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            if key != 'separatelyObservedRestatements':
                result.update(numeric_values(item, path + (key,)))
        return result
    if isinstance(value, list):
        result = {}
        for index, item in enumerate(value):
            result.update(numeric_values(item, path + (index,)))
        return result
    return {path: value} if type(value) in (int, float) else {}


class InvitationRestatementTests(unittest.TestCase):
    def test_newer_invitation_and_parent_refresh_keep_older_evidence(self):
        old = fixture(records=[RECORD])
        newer = fixture(parent='2026-11-23T10:00:00Z', invitation='2026-11-23T11:00:00Z')
        newer['waalaxy']['daily'].append({'date': '2026-11-23', 'invitationsSent': 9, 'invitationsAccepted': 2})
        newer['waalaxy']['invitationCoverage']['end'] = '2026-11-23'
        newer['waalaxy']['invitationSummary'] = {'sent': 82, 'accepted': 21}
        original_old, original_newer = copy.deepcopy(old), copy.deepcopy(newer)
        for source, previous in ((newer, old), (old, newer)):
            result = preserve_newer_shared_sources(source, previous)
            self.assertEqual(records(result), [RECORD])
            self.assertEqual(result['waalaxy']['invitationImportReview']['snapshotAt'], '2026-11-23T11:00:00Z')
            self.assertEqual(result['waalaxy']['daily'], newer['waalaxy']['daily'])
            self.assertEqual(result['waalaxy']['invitationSummary'], newer['waalaxy']['invitationSummary'])
            self.assertEqual(records(result)[0]['laterTooltipObservedAt'], '2026-11-13T13:41:17.625Z')
            replay = preserve_newer_shared_sources(newer, result)
            self.assertEqual(records(replay), [RECORD])
            self.assertEqual(replay['waalaxy']['daily'], newer['waalaxy']['daily'])
        self.assertEqual(old, original_old)
        self.assertEqual(newer, original_newer)

    def test_merge_uses_original_inputs_when_parent_and_invitation_winners_differ(self):
        parent_winner = fixture(parent='2026-11-25T12:00:00Z', invitation='2026-11-20T12:00:00Z', records=[RECORD])
        invitation_winner = fixture(parent='2026-11-19T12:00:00Z', invitation='2026-11-26T12:00:00Z')
        invitation_winner['waalaxy']['invitationSummary']['basis'] = 'Winning invitation family'
        result = preserve_newer_shared_sources(invitation_winner, parent_winner)
        self.assertEqual(result['waalaxy']['snapshotAt'], parent_winner['waalaxy']['snapshotAt'])
        self.assertEqual(result['waalaxy']['invitationCollectedAt'], invitation_winner['waalaxy']['invitationCollectedAt'])
        self.assertEqual(records(result), [RECORD])
        self.assertEqual(result['waalaxy']['invitationSummary']['basis'], 'Winning invitation family')

    def test_deduplication_and_multiple_observation_versions(self):
        later = copy.deepcopy(RECORD)
        later['laterTooltipObservedAt'] = '2026-11-15T13:41:17.625Z'
        later['laterAuthenticatedTooltip']['invitationsAccepted'] = 26
        merged = merge_invitation_restatements(fixture(records=[later, RECORD]), fixture(records=[RECORD]))
        self.assertEqual(merged, [RECORD, later])
        self.assertIsNot(merged[0], RECORD)

    def test_same_key_payload_conflicts_fail_in_both_orders(self):
        conflict = copy.deepcopy(RECORD)
        conflict['laterAuthenticatedTooltip']['invitationsAccepted'] = 26
        for first, second in ((RECORD, conflict), (conflict, RECORD)):
            with self.assertRaisesRegex(AssertionError, 'Conflicting invitation restatements'):
                preserve_newer_shared_sources(fixture(records=[first]), fixture(records=[second]))
        # Equivalent UTC offsets cannot evade the same-instant conflict check.
        conflict['laterTooltipObservedAt'] = '2026-11-13T13:41:17.625+00:00'
        with self.assertRaisesRegex(AssertionError, 'Conflicting invitation restatements'):
            merge_invitation_restatements(fixture(records=[RECORD]), fixture(records=[conflict]))

    def test_source_clock_and_count_validation(self):
        for field, value in [('laterTooltipObservedAt', '2026-11-13T13:41:17.625'),
                             ('appliedToRetainedSeries', True), ('retainedCsvCollectedAt', '2026-11-14T00:00:00Z')]:
            malformed = copy.deepcopy(RECORD)
            malformed[field] = value
            with self.assertRaises(AssertionError):
                merge_invitation_restatements(fixture(records=[malformed]), {})
        malformed = copy.deepcopy(RECORD)
        malformed['laterAuthenticatedTooltip']['invitationsAccepted'] = True
        with self.assertRaisesRegex(AssertionError, 'nonnegative integers'):
            merge_invitation_restatements(fixture(records=[malformed]), {})

    @unittest.skipUnless((PRIMARY / 'waalaxy.json').exists(), 'Retained private primary sources are not available')
    def test_exact_restoration_patch_matches_local_primary_and_raw_counts(self):
        primary = json.loads((PRIMARY / 'waalaxy.json').read_text())
        original = primary['invitationImportReview']['separatelyObservedRestatements']
        self.assertEqual(original, [RECORD])
        patch = json.loads((PRIVATE / 'waalaxy_restatement_patch.json').read_text())
        self.assertEqual(patch, {'waalaxy': {'invitationImportReview': {'separatelyObservedRestatements': original}}})
        browser = json.loads((PRIMARY / 'browser_observations.json').read_text())
        self.assertEqual(browser['bridge']['observedAt'], RECORD['laterTooltipObservedAt'])
        self.assertEqual(browser['bridge']['daily'][0], {'date': '2026-10-28', 'sent': 73, 'accepted': 25})
        csv_path = ROOT / 'data/private/refresh_2026_10_28/waalaxy/source_invitations_6.csv'
        with csv_path.open(encoding='utf-8-sig', newline='') as handle:
            row = next(row for row in csv.DictReader(handle) if row['Date'] == 'Wed Oct 28 2026')
        self.assertEqual((int(row['Sent']), int(row['Accepted'])), (73, 19))
        current = json.loads((ROOT / 'data/shared-dashboard.json').read_text())
        segment = next(segment for segment in current['waalaxy']['invitationCoverage']['segments'] if segment.get('sourceFilename') == 'invitations (6).csv')
        self.assertEqual(segment['collectedAt'], RECORD['retainedCsvCollectedAt'])
        self.assertEqual(segment['sourceSha256'], hashlib.sha256(csv_path.read_bytes()).hexdigest())

    def test_actual_series_and_public_curation_unchanged(self):
        current = json.loads((ROOT / 'data/shared-dashboard.json').read_text())
        restored = copy.deepcopy(current)
        restored['waalaxy']['invitationImportReview']['separatelyObservedRestatements'] = [copy.deepcopy(RECORD)]
        candidate = curate_snapshot(preserve_newer_shared_sources(restored, current))
        self.assertEqual(records(candidate), [RECORD])
        self.assertEqual(candidate['waalaxy']['daily'], current['waalaxy']['daily'])
        self.assertEqual(numeric_values(candidate['waalaxy']), numeric_values(current['waalaxy']))
        for field in ('snapshotAt', 'invitationCollectedAt', 'invitationCoverage', 'invitationSummary', 'accountAnalytics'):
            self.assertEqual(candidate['waalaxy'][field], current['waalaxy'][field])
        self.assertEqual(current, json.loads((ROOT / 'data/shared-dashboard.json').read_text()))

    def test_invitation_ui_discloses_versions_without_changing_selected_totals(self):
        snapshot = json.loads((ROOT / 'data/shared-dashboard.json').read_text())
        snapshot['waalaxy']['invitationImportReview']['separatelyObservedRestatements'] = [copy.deepcopy(RECORD)]
        script = r"""
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const snapshot=JSON.parse(fs.readFileSync(0,'utf8'));
const app=fs.readFileSync('app.js','utf8').replace(/\ninit\(\);\s*$/,'');
const ctx=vm.createContext({Intl,Date,URL,setTimeout:()=>{},document:{querySelector:()=>null},snapshot});
vm.runInContext(app,ctx);const run=source=>vm.runInContext(source,ctx);
run("S.data=snapshot;S.start='2026-10-28';S.end='2026-10-28';");
assert.equal(run('selectedInvitations().sent'),73);assert.equal(run('selectedInvitations().accepted'),19);
const before=JSON.stringify(snapshot),html=run('waalaxy()');
assert.match(html,/Historical invitation bucket versions/);
assert.match(html,/Oct 28, 2026 source-date bucket/);
assert.match(html,/73 Sent \/ 19 Accepted/);assert.match(html,/73 Sent \/ 25 Accepted/);
assert.match(html,/collected Oct 28, 2026, 11:59 PM MDT/);
assert.match(html,/observed Nov 13, 2026, 6:41 AM MST/);
assert.match(html,/\+6 Accepted is a retrospective source-bucket restatement, not new acceptance events in the selected period/);
assert.match(html,/displayed historical CSV remains 19 Accepted/);
assert.equal(JSON.stringify(snapshot),before);
assert.equal(run('selectedInvitations().accepted'),19);
const context=run('waalaxyInvitationRestatements(snapshot.waalaxy)');
run("S.start='2026-11-12';S.end='2026-11-18';");
assert.equal(run('waalaxyInvitationRestatements(snapshot.waalaxy)'),context);
assert.equal(run('selectedInvitations().sent'),35);assert.equal(run('selectedInvitations().accepted'),11);
run("snapshot.waalaxy.invitationImportReview.snapshotAt='2026-11-25T12:00:00Z';");
assert.equal(run('waalaxyInvitationRestatements(snapshot.waalaxy)'),context);
run('delete snapshot.waalaxy.invitationImportReview.separatelyObservedRestatements;');
assert.equal(run('waalaxyInvitationRestatements(snapshot.waalaxy)'), '');
console.log('Waalaxy UI: exact dated 73/19 versus73/25, retrospective+6, unchanged selected totals and original child clock passed.');
"""
        result = subprocess.run(['node', '-e', script], cwd=ROOT, input=json.dumps(snapshot),
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main(verbosity=2)
