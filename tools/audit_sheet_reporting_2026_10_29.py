"""Audit source attributes and snapshot comparisons; write private proposals only.

The two comparisons use retained evidence. A new audit clock does not refresh
worksheet values, CSV generation, native messages or commercial decisions.
"""
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
import argparse
import copy
import hashlib
import json

from refresh_sheets_2026_10_28 import valid_date
from import_waalaxy_actions_2026_10_22 import parse_source, totals

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / 'data/private/published_gap_audit_2026_10_29/sheets'
SOURCE = ROOT / 'data/private/refresh_2026_10_28/sheets'


def connection_diagnostics(video, subset):
    rows_by_profile = defaultdict(list)
    for row in video['rows']:
        rows_by_profile[row['id']].append(row)
    subset_rows = subset.get('rows', [])
    assert len(subset_rows) == len({r['profileId'] for r in subset_rows}), 'Duplicate accepted profile identity'
    matches = [r for r in subset_rows if r.get('matchedVideoProspect')]
    assert all(r['profileId'] in rows_by_profile for r in matches), 'Stale accepted-to-main profile match'
    without_flag = [r for r in matches if not any(v['connected'] for v in rows_by_profile[r['profileId']])]
    diagnostics = copy.deepcopy(video.get('connectionDiagnostics') or {})
    diagnostics.update(acceptedProfilesMatchedMain=len(matches),
        acceptedProfilesWithoutConnectedFlag=len(without_flag),
        acceptedProfilesWithoutConnectedFlagMissingDate=sum(not r.get('connectedAt') for r in without_flag))
    return diagnostics


def export_overlap(export, subset, sheet_collected_at, reviewed_at):
    exports = export.get('rows', [])
    sheet = subset.get('rows', [])
    a = {r['profileId'] for r in exports}
    b = {r['profileId'] for r in sheet}
    assert len(a) == len(exports) and len(b) == len(sheet), 'Duplicate source identities must be reviewed before comparing memberships'
    assert export['metrics']['connectedProspects'] == len(a)
    assert subset['metrics']['connectedProspects'] == len(b)
    return {'sameProfiles': len(a & b), 'onlyInExports': len(a - b), 'onlyInSheet': len(b - a),
        'reviewedAt': reviewed_at, 'appliesToSheetSnapshotAt': sheet_collected_at,
        'exportParentReviewedAt': export.get('reviewedAt'),
        'exportSourceObservationThrough': export.get('sourceObservationThrough'),
        'exportUniqueProfiles': len(a), 'sheetUniqueProfiles': len(b),
        'profileMatchBasis': 'Exact normalized profile IDs in the two retained source inventories; no new aliases inferred.',
        'newSourceDataCollected': False, 'actualMessageEventsAdded': 0,
        'treatment': 'Do not sum snapshots or their daily person attributes. Membership/source freshness differs. This comparison uses the explicitly identified current Sheet inventory and retains the older CSV source dates.'}


def audit(snapshot, main_values, reviewed_at):
    video = snapshot['video']
    subset = snapshot['waalaxy']['sheetSubset']
    export = snapshot['waalaxy']['selectedExportSnapshot']
    assert len(main_values[0]) == 29 and main_values[0][22] == 'Connected At'
    rows = copy.deepcopy(video['rows'])
    accepted = {r['profileId']: r for r in subset['rows']}
    recovered = []
    serial_source_dates_verified = 0
    invalid = []
    for row in rows:
        source = dict(zip(main_values[0], main_values[row['sourceRow'] - 1]))
        assert source['org'].strip() == row['company'] and source['contact'].strip() == row['contact'], 'Wrong current source row'
        for column, field in [('Video Sent Date','reportedVideoSentDate'), ('Follow-up Sent Date','reportedFollowUpSentDate'), ('Connected At','connectedAt')]:
            literal = source.get(column)
            parsed = valid_date(literal, date_column=column, reference_day=video['snapshotAt'][:10])
            if literal and parsed is None:
                invalid.append({'profileId': row['id'], 'sourceRow': row['sourceRow'], 'sourceColumn': column})
            if column != 'Connected At':
                assert parsed == row.get(field), 'A literal video/follow-up date differs from the published source report'
                continue
            if parsed and str(literal or '').replace('.0','').isdigit():
                person = accepted.get(row['id'])
                assert person and person['connectedAt'] == parsed and row['connected'] is True, 'Serial date lacks independent exact accepted-profile corroboration'
                serial_source_dates_verified += 1
            if parsed != row.get(field):
                assert row.get(field) is None and parsed, 'Conflicting date correction needs manual review'
                person = accepted.get(row['id'])
                assert person and person['connectedAt'] == parsed and row['connected'] is True, 'Serial date lacks independent exact accepted-profile corroboration'
                row[field] = parsed
                row['connectedAtDatePrecision'] = 'day'
                row['connectedAtSourceTimezone'] = None
                row['connectedAtEvidenceBasis'] = 'Explicit Connected At worksheet date attribute; integral Sheets serial decoded with the 1899-12-30 epoch and independently matched to the same accepted-profile date. Not a dated invitation acceptance event.'
                recovered.append({'profileId': row['id'], 'sourceRow': row['sourceRow'], 'date': parsed,
                    'sourceColumn': column, 'sourceEncoding': 'integral_google_sheets_serial_string',
                    'exactAcceptedProfileDateMatch': True})
    assert not invalid, 'Unclassified explicit source date values remain'
    diagnostics = connection_diagnostics(video, subset)
    diagnostics['serialConnectionDatesDecodedAndCorroborated'] = serial_source_dates_verified
    overlap = export_overlap(export, subset, snapshot['waalaxy']['sheetSubsetCollectedAt'], reviewed_at)
    fixed_export = copy.deepcopy(export)
    previous_overlap = copy.deepcopy(fixed_export.get('overlapWithSheet') or {})
    comparable = ('sameProfiles','onlyInExports','onlyInSheet')
    if any(previous_overlap.get(k) != overlap[k] for k in comparable):
        previous_overlap.update(historicalOnly=True, originalComparisonSheetSnapshotAt=previous_overlap.get('appliesToSheetSnapshotAt'),
            originalComparisonSheetClockUnreported=not bool(previous_overlap.get('appliesToSheetSnapshotAt')),
            parentExportReviewAt=export.get('reviewedAt'),
            retentionBasis='Original stored overlap retained without inventing the missing historical Sheet comparison clock.')
        retained = fixed_export.setdefault('retainedPriorOverlapReviews', [])
        if previous_overlap not in retained:
            retained.append(previous_overlap)
    fixed_export['overlapWithSheet'] = overlap
    assert fixed_export['reviewedAt'] == export['reviewedAt'], 'An audit must not re-date the CSV source review'
    native = video['messageDateReview']['platformObservedEvents']
    sends = [e for e in native if e['direction'] == 'outbound' and e.get('videoIncluded') is True]
    follows = [e for e in native if e.get('messageKind') == 'video_follow_up']
    dated_source = [r for r in rows if r.get('reportedVideoSentDate')]
    source_exact = lambda row: any(e['profileId'] == row['id'] and e['date'] == row['reportedVideoSentDate'] and e.get('assetId') == row.get('recordingAssetId') for e in sends)
    inventory_profiles = Counter(r['id'] for r in rows if r.get('linkedin'))
    assets = Counter(r['recordingAssetId'] for r in rows if r.get('recordingAssetId'))
    report = {'reviewedAt': reviewed_at, 'sourceInventorySnapshotAt': video['snapshotAt'],
        'scope': 'Retained complete main/accepted source values, normalized current inventories and explicitly observed native messages. Audit time is not a new source collection clock.',
        'issuesResolved': {'decodedConnectionDateRows': len(recovered), 'decodedConnectionDateUniqueProfiles': len({r['profileId'] for r in recovered}),
            'missingConnectionDiagnostic': {'prior': video['connectionDiagnostics'].get('acceptedProfilesWithoutConnectedFlagMissingDate'),
                'current': diagnostics['acceptedProfilesWithoutConnectedFlagMissingDate']},
            'staleExportOverlap': {'prior': {k: previous_overlap.get(k) for k in comparable}, 'current': {k: overlap[k] for k in comparable}}},
        'sourceChecks': {'sourceRows': len(rows), 'uniqueProfiles': len(inventory_profiles),
            'rowsMissingProfile': sum(not r['linkedin'] for r in rows), 'duplicateProfiles': sum(c > 1 for c in inventory_profiles.values()),
            'duplicateExtraRows': sum(c-1 for c in inventory_profiles.values() if c>1),
            'duplicateVideoAssets': sum(c > 1 for c in assets.values()),
            'invalidExplicitDateFields': invalid, 'connectedDateRowsAfterCorrection': sum(bool(r.get('connectedAt')) for r in rows),
            'sourceResponseLabels': dict(Counter(r.get('responseStatus') or 'blank' for r in rows)),
            'sourceVideoDateRows': len(dated_source), 'sourceFollowUpDateRows': sum(bool(r.get('reportedFollowUpSentDate')) for r in rows)},
        'nativeSourceOverlap': {'verifiedVideoSendsAllDates': len(sends), 'verifiedSendUniqueProfiles': len({e['profileId'] for e in sends}),
            'verifiedSendUniqueAssets': len({e['assetId'] for e in sends}),
            'currentSourceVideoDateRowsWithSameProfileAssetAndDay': sum(source_exact(r) for r in dated_source),
            'currentSourceVideoDateRowsWithoutExactNativeVideoProof': [{'profileId': r['id'], 'sourceRow': r['sourceRow'], 'company': r['company'], 'sourceDate': r['reportedVideoSentDate']} for r in dated_source if not source_exact(r)],
            'currentSourceFollowUpDateRowsWithSameNativeProfileAndDay': sum(any(e['profileId']==r['id'] and e['date']==r.get('reportedFollowUpSentDate') for e in follows) for r in rows if r.get('reportedFollowUpSentDate')),
            'newNativeEventsAddedByThisAudit': 0, 'sourceReportsAddedToNativeCounts': False},
        'limits': ['Source connection dates are date-only historical attributes, not exact acceptance-event dates or timestamps.',
            'Worksheet response labels remain undated source classifications; Interested does not establish qualification or a held call.',
            'No duplicate source row is silently deleted. Source helper counts retain their row denominator; native events remain independently deduplicated.',
            'Missing native proof for a source report does not establish non-sending. Missing CRM note assets do not establish automation failure.',
            'Held calls, accepted opportunities and wins remain independently reviewed commercial decisions.',
            'No Zapier run count is converted into unique prospects, sent messages or delivery totals.']}
    date_corrections = {'appliesToVideoInventorySnapshotAt': video['snapshotAt'], 'reviewedAt': reviewed_at,
        'sourceValueCollectionClockPreserved': True, 'changes': [
            {'profileId': row['id'], 'sourceRow': row['sourceRow'], 'previousConnectedAt': None,
             'fields': {key: row[key] for key in ('connectedAt','connectedAtDatePrecision','connectedAtSourceTimezone','connectedAtEvidenceBasis')}}
            for row in rows if any(change['sourceRow'] == row['sourceRow'] for change in recovered)]}
    patches = {'videoRows': rows, 'videoConnectionDateCorrections': date_corrections,
        'videoConnectionDiagnostics': diagnostics, 'waalaxySelectedExportSnapshot': fixed_export,
        'videoSourceFieldAuditReview': {'snapshotAt': reviewed_at, 'reviewedAt': reviewed_at,
            'appliesToVideoInventorySnapshotAt': video['snapshotAt'], 'sourceCollectionClockPreserved': True,
            'connectionDateRowsRecovered': len(recovered), 'records': recovered,
            'scope': 'Normalization correction of already-collected explicit date attributes, independently corroborated by exact accepted-profile date joins; no new event proof.'}}
    return patches, report


def invitation_lineage(snapshot, paths):
    waalaxy = snapshot['waalaxy']
    days = {r['date']: r for r in waalaxy['daily'] if all(k in r for k in ('invitationsSent','invitationsAccepted'))}
    results = []
    for segment in waalaxy['invitationCoverage']['segments']:
        path = paths[segment['sourceFilename']]
        raw = path.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == segment['sourceSha256'], 'Invitation source hash mismatch'
        records = [r for r in parse_source(raw) if segment['start'] <= r['date'] <= segment['end']]
        assert len(records) == segment['sourceDays'] and totals(records) == {'sent': segment['sent'], 'accepted': segment['accepted']}
        assert all(all(r[k] == days[r['date']][k] for k in ('invitationsSent','invitationsAccepted')) for r in records)
        results.append({**copy.deepcopy(segment), 'sourceHashVerified': True, 'everyRetainedBucketMatchesOriginalCsv': True})
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', type=Path, default=ROOT/'data/shared-dashboard.json')
    parser.add_argument('--source-dir', type=Path, default=SOURCE)
    parser.add_argument('--output', type=Path, default=PRIVATE)
    args = parser.parse_args()
    snapshot = json.loads(args.snapshot.read_text())
    reviewed = datetime.now(timezone.utc).isoformat()
    patches, report = audit(snapshot, json.loads((args.source_dir/'main_values.json').read_text())['values'], reviewed)
    downloads = Path('/Users/christianwutz/Downloads')
    report['invitationSourceLineage'] = invitation_lineage(snapshot, {f'invitations ({n}).csv': downloads/f'invitations ({n}).csv' for n in (4,5,6)})
    args.output.mkdir(parents=True, exist_ok=True)
    for key, value in patches.items():
        (args.output/(key+'_patch.json')).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    (args.output/'audit_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'reviewedAt': reviewed, 'sourceInventoryClockPreserved': snapshot['video']['snapshotAt'], 'issuesResolved': report['issuesResolved']}))


if __name__ == '__main__':
    main()
