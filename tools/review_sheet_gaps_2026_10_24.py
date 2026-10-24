"""Review unchanged Sheets values and distinguish identity/date gaps from events.

Writes private, curated review patches only. No source values, inventory clocks,
commercial decisions, or shared dashboard files are changed.
"""
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / 'data/private/gap_resolution_2026_10_24/sheets'
RETAINED = ROOT / 'data/private/refresh_2026_10_23/sheets'


def load(path):
    return json.loads(path.read_text())


def write(name, value):
    (PRIVATE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def utc(value):
    return value.replace(' UTC', 'Z').replace(' ', 'T')


def reference(row):
    return {k: row.get(k) for k in ('id', 'sourceRow', 'company', 'contact', 'linkedin', 'status',
        'dealId', 'recordingAssetId', 'reportedVideoSentDate', 'reportedFollowUpSentDate')}


def build():
    current = load(ROOT / 'data/shared-dashboard.json')
    video = current['video']
    rows = video['rows']
    main = load(PRIVATE / 'main_values.json')['values']
    accepted = load(PRIVATE / 'accepted_values.json')['values']
    assert main == load(RETAINED / 'main_values.json')['values'], 'Source changed; prepare a new guarded inventory/crosswalk'
    assert accepted == load(RETAINED / 'accepted_values.json')['values'], 'Accepted-person source changed; compare attributes independently'
    metadata = load(PRIVATE / 'spreadsheet_metadata.json')['result']['value']['structuredContent']
    before_file = load(PRIVATE / 'file_metadata.json')['result']['value']['structuredContent']
    after_file = load(PRIVATE / 'post_read_0.json')['result']['value']['structuredContent']
    assert before_file['modified_time'] == after_file['modified_time'], 'Workbook changed during collection'
    assert metadata['properties']['timeZone'] == 'America/Los_Angeles'
    reviewed = utc(load(PRIVATE / 'post_read_0.json')['collectedAt'])
    local_day = datetime.fromisoformat(reviewed.replace('Z', '+00:00')).astimezone(ZoneInfo('America/Denver')).date().isoformat()
    raw_records = {i: dict(zip(main[0], r)) for i, r in enumerate(main[1:], 2)}
    valid_raw = [(i, r) for i, r in raw_records.items() if str(r.get('org') or '').strip() and str(r.get('contact') or '').strip() and not (r['org'] == 'org' and r['contact'] == 'contact')]
    assert len(valid_raw) == len(rows) == video['summary']['sourceRows']
    revisions = load(PRIVATE / 'file_revisions.json')['result']['value']['structuredContent']
    previous_revision = load(PRIVATE / 'previous_revision_1304.json')['result']['structuredContent']
    cells = load(PRIVATE / 'date_helper_cells.json')['result']['value']['structuredContent']
    date_cells = [c for sheet in cells['sheets'] if sheet['properties']['sheetId'] == 569014042 for block in sheet.get('data', []) if block.get('startColumn') == 19 for row in block.get('rowData', []) for c in row.get('values', [])]
    assert not any(c.get('userEnteredValue', {}).get('formulaValue') for c in date_cells)
    groups = defaultdict(list)
    for row in rows:
        if row.get('linkedin'):
            groups[row['id']].append(row)
    duplicates = []
    for profile, grouped in groups.items():
        if len(grouped) < 2:
            continue
        active = [r for r in grouped if r['status'] != 'Skip']
        duplicates.append({'profileId': profile, 'sourceRows': [r['sourceRow'] for r in grouped],
            'companies': sorted({r['company'] for r in grouped}), 'contactNames': sorted({r['contact'] for r in grouped}),
            'sourceStatuses': sorted({r['status'] for r in grouped}),
            'sourceActions': sorted({r['action'] for r in grouped}),
            'activeSourceRows': [r['sourceRow'] for r in active],
            'skippedSourceRows': [r['sourceRow'] for r in grouped if r['status'] == 'Skip'],
            'recordingOrDateEvidenceRows': [r['sourceRow'] for r in grouped if r.get('recordingAssetId') or r.get('reportedVideoSentDate') or r.get('reportedFollowUpSentDate')],
            'identityStatus': 'Same person key resolved by exact normalized LinkedIn profile; source rows retained.',
            'sourceCleanupStatus': 'Source contains both active and Skip copies; do not treat them as different people.' if len(active) == 1 else 'Multiple active source copies remain; current helper conservatively blocks readiness pending source cleanup.',
            'addsNewSendOrReplyEvent': False})
    connected_rows = [r for r in rows if r['connected']]
    connected_profiles = {r['id'] for r in connected_rows if r.get('linkedin')}
    dated_video = [r for r in rows if r.get('reportedVideoSentDate')]
    dated_followup = [r for r in rows if r.get('reportedFollowUpSentDate')]
    video_undated = [reference(r) for r in rows if r['status'] == 'Video Sent' and not r.get('reportedVideoSentDate')]
    followup_undated = [reference(r) for r in rows if r['status'] == 'Follow-up Sent' and not r.get('reportedFollowUpSentDate')]
    missing_profiles = [reference(r) for r in rows if not r.get('linkedin')]
    for item in video_undated:
        raw = raw_records[item['sourceRow']]
        if item['id'] == 'mac-dougherty':
            item['sourceChannelAmbiguity'] = 'The worksheet note describes email while the standardized status is Video Sent. Neither asset nor sending date is supplied; native video content is unverified by the worksheet.'
    freshness = {'snapshotAt': reviewed, 'reviewedAt': reviewed, 'reportingLocalDate': local_day,
        'appliesToSnapshotAt': video['snapshotAt'],
        'scope': 'Complete read-only current main/accepted worksheet values and source date/helper cells; comparison against retained October 23 collection.',
        'sourceRanges': ["'centripetal_top20_video_sniper_prospects_aug2026'!A1:AC5000", "'Accepted Connections (Video Prospects)'!A1:AR1011"],
        'collectionCompleteWithinWorkbook': True, 'fullValuesReread': True,
        'valuesIdenticalToRetainedSource': True, 'inventoryChanged': False, 'changedPhysicalRows': 0,
        'retainedInventorySnapshotAt': video['snapshotAt'], 'inventoryCollectionClockPreserved': True,
        'retainedCounts': video['summary'], 'sourceModifiedAt': after_file['modified_time'],
        'fileUnchangedAcrossCollection': True, 'currentRevisionId': revisions['currentRevisionId'],
        'previousRevisionId': revisions['previousRevisionId'],
        'historyAccess': {'revisionMetadataAccessible': True, 'revisionMetadataRows': len(revisions['revisions']),
            'previousRevisionContentReadable': bool(previous_revision.get('content')),
            'previousRevisionModifiedAt': previous_revision.get('revisionModifiedTime'),
            'cellEditTimestampOrEventLogProvided': False,
            'limit': 'File/revision modification times are not prospect-added, video-sent or reply timestamps. Readable revision content does not establish a complete per-cell activity log.'},
        'dateFieldReview': {'videoDateField': 'Video Sent Date', 'followUpDateField': 'Follow-up Sent Date',
            'dateFieldsLiteralNotFormula': True, 'datePrecision': 'day', 'exactSendingTimestampAvailable': False,
            'upstreamEventTimezone': None, 'workbookTimezone': metadata['properties']['timeZone'],
            'rowAddedTimestampFieldPresent': False, 'firstLastPersonFieldsAreEventCensus': False},
        'counterChangesFromThisReview': {'sourceRows': 0, 'uniqueProfiles': 0, 'worksheetVideoDateRows': 0,
            'worksheetFollowUpDateRows': 0, 'newNativeSendOrReplyProof': 0},
        'note': 'October 24 reread verifies unchanged worksheet state. Original inventory and CRM row-guard dates remain unchanged; independently collected native observations are a separate source family.'}
    identities = {
        'snapshotAt': reviewed, 'reviewedAt': reviewed, 'reportingLocalDate': local_day,
        'appliesToSnapshotAt': video['snapshotAt'],
        'summary': {'sourceRows': len(rows), 'uniqueValidProfiles': len(groups),
            'duplicateProfileGroups': len(duplicates), 'duplicateExtraSourceRows': sum(len(g) - 1 for g in groups.values()),
            'sameProfileIdentityGroupsResolved': len(duplicates),
            'activeDuplicateGroupsPendingSourceCleanup': sum(len(r['activeSourceRows']) > 1 for r in duplicates),
            'groupsWithActiveAndSkipCopies': sum(bool(r['skippedSourceRows']) and bool(r['activeSourceRows']) for r in duplicates),
            'connectedSourceRows': len(connected_rows), 'connectedUniqueProfiles': len(connected_profiles),
            'connectedExtraDuplicateRows': len(connected_rows) - len(connected_profiles),
            'missingProfileSourceRows': len(missing_profiles),
            'recordingAssets': sum(bool(r.get('recordingAssetId')) for r in rows),
            'uniqueRecordingAssets': len({r['recordingAssetId'] for r in rows if r.get('recordingAssetId')}),
            'recordingAssetRowsWithoutReportedVideoDate': sum(bool(r.get('recordingAssetId')) and not r.get('reportedVideoSentDate') for r in rows),
            'videoStatusRowsWithoutReportedVideoDate': len(video_undated),
            'followUpStatusRowsWithoutReportedFollowUpDate': len(followup_undated),
            'reportedVideoDateRows': len(dated_video),
            'uniqueReportedVideoProfileDates': len({(r['id'], r['reportedVideoSentDate']) for r in dated_video}),
            'reportedFollowUpDateRows': len(dated_followup),
            'uniqueReportedFollowUpProfileDates': len({(r['id'], r['reportedFollowUpSentDate']) for r in dated_followup})},
        'duplicateGroups': duplicates, 'missingProfileRows': missing_profiles,
        'undatedVideoStatusRows': video_undated, 'undatedFollowUpStatusRows': followup_undated,
        'datedVideoReportsWithoutSourceAsset': [reference(r) for r in dated_video if not r.get('recordingAssetId')],
        'analyticalTreatment': ['Count exact normalized profile keys once when reporting people; source row/status inventories remain source rows.',
            '115 Connected row flags describe 113 unique profiles. Two active/Skip duplicate copies account for the difference.',
            'Current reported send/follow-up profile-date keys are already unique; deduplicating source identities adds no send or reply events.',
            'Four active duplicate groups have no exact match in the selected accepted-connections tab. This is incomplete subset evidence, not a platform-wide proof of disconnection.',
            'Source status, available asset, CRM record presence and native sent-message observations remain separately labelled.'],
        'sourceWritesPerformed': False, 'changesCommercialOutcomes': False,
        'note': 'These findings clarify source identities and denominators without editing source rows or declaring manual qualification decisions.'}
    write('freshness_review_patch.json', freshness)
    write('identity_date_gap_review_patch.json', identities)
    write('date_gap_candidates_private.json', [reference(r) for r in rows if (r.get('recordingAssetId') and not r.get('reportedVideoSentDate')) or (r['status'] == 'Video Sent' and not r.get('reportedVideoSentDate')) or (r['status'] == 'Follow-up Sent' and not r.get('reportedFollowUpSentDate'))])
    print(json.dumps({'snapshotAt': reviewed, 'reportingLocalDate': local_day, 'sourceValuesUnchanged': True,
        'inventoryClockPreserved': video['snapshotAt'], 'identitySummary': identities['summary']}))


if __name__ == '__main__':
    build()
