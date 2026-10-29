"""Build current source-field reviews without redating native message proof."""
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote
from zoneinfo import ZoneInfo
import copy
import csv
import io
import json
import re
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / 'data/private/refresh_2026_10_28/sheets'


def load(name):
    return json.loads((PRIVATE / name).read_text())


def save(name, value):
    (PRIVATE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def clock(value):
    return value.replace(' UTC', 'Z').replace(' ', 'T')


def result(value):
    if 'result' in value:
        value = value['result']
    if 'status' in value:
        assert value['status'] == 'fulfilled'
        value = value['value']
    assert not value.get('isError')
    return value


def revision(name):
    wrapper = load(name)
    data = result(wrapper)['structuredContent']
    rows = list(csv.reader(io.StringIO(data['content'])))
    assert rows[0][:8] == ['rank', 'org', 'icp', 'tier', 'stage', 'contact', 'ctitle', 'li']
    assert all(len(row) == 29 for row in rows), 'Partial or mismatched historical CSV row'
    # Native CSV exports can omit a final newline. Row width, expected current
    # grid bounds and an exact cell-for-cell live comparison guard the read.
    return data, rows, clock(wrapper['collectedAt'])


def normalized(value):
    return ''.join(char for char in unicodedata.normalize('NFKC', value).casefold() if char.isalnum())


def profile(row):
    match = re.search(r'linkedin\.com/in/([^/?#]+)', unquote(row['li']), re.I)
    return match[1].lower().rstrip('/') if match else None


def valid_records(rows):
    return [dict(zip(rows[0], row)) for row in rows[1:] if row[1] and row[5] and row[1] != 'org']


def identity(row):
    return profile(row), normalized(row['org']), normalized(row['contact'])


def build():
    before = json.loads((PRIVATE.parent / 'baseline_shared.json').read_text())
    video = load('video_inventory_patch.json')
    report = load('sheets_review_report.json')
    stamp = video['snapshotAt']
    complete = video['sourceCoverage']['collectionCompletedAt']
    reviewed = datetime.now(timezone.utc).isoformat()
    previous, previous_rows, previous_read = revision('previous_revision_1380.json')
    current, current_rows, current_read = revision('current_revision_1401.json')
    live = load('main_values.json')['values']
    assert len(current_rows) == len(live) == 5000
    assert all(a == [str(v) for v in b] for a, b in zip(current_rows, live))
    prior_by_identity = {(normalized(row['org']), normalized(row['contact'])): row for row in valid_records(previous_rows)}
    current_by_identity = {(normalized(row['org']), normalized(row['contact'])): row for row in valid_records(current_rows)}
    assert prior_by_identity.keys() == current_by_identity.keys()
    source_rows = {row['id']: row for row in video['rows']}
    old_assets = {row.get('recordingAssetId') for row in before['video']['rows'] if row.get('recordingAssetId')}
    new_assets = [row for row in video['rows'] if row.get('recordingAssetId') and row['recordingAssetId'] not in old_assets]
    assert len(new_assets) == 5
    for row in new_assets:
        who = normalized(row['company']), normalized(row['contact'])
        assert not prior_by_identity[who]['Loom Link']
        assert row['recordingAssetId'] in current_by_identity[who]['Loom Link']

    records = []
    for row in new_assets:
        records.append({'profileId': row['id'], 'sourceRow': row['sourceRow'],
            'company': row['company'], 'contact': row['contact'],
            'crmDealId': int(row['dealId']) if row.get('dealId') else None,
            'status': 'Current source recording asset is present; native sending evidence is separate',
            'findings': ['The current recording field contains a valid Loom asset that was absent in the prior complete source snapshot.',
                'The exact company/contact source row had an empty recording field in revision1380 and the asset appears in revision1401. These bounds date the source-field appearance, not the recording creation or sending.',
                'The current Video Sent worksheet label is undated for this row. This source review establishes no actual LinkedIn send, reply, delivery receipt or commercial decision.'],
            'recordingAssetId': row['recordingAssetId'], 'currentRecordingFieldKind': row['recordingFieldKind'],
            'sourceReportedVideoDate': row['reportedVideoSentDate'],
            'sourceAssetAppearedAfter': previous['revisionModifiedTime'],
            'sourceAssetAppearedBy': current['revisionModifiedTime'],
            'sourceEventProofInferred': False})
    sub = source_rows['alexchantavy']
    old_sub = next(row for row in before['video']['rows'] if row['id'] == sub['id'])
    assert old_sub['reportedVideoSentDate'] == '2026-10-21' and sub['reportedVideoSentDate'] == '2026-10-26'
    records.append({'profileId': sub['id'], 'sourceRow': sub['sourceRow'], 'company': sub['company'],
        'contact': sub['contact'], 'status': 'Worksheet video date changed; native evidence remains independent',
        'findings': ['The literal Video Sent Date changed from October21 to October26. It is a changed source report, rather than evidence of two separate sends.',
            'The recording asset is unchanged. Earlier unconfirmed native proof keeps its original clock; the new source date does not establish a native send or retrospectively change prior observations.'],
        'priorSourceReportedVideoDate': old_sub['reportedVideoSentDate'],
        'sourceReportedVideoDate': sub['reportedVideoSentDate'],
        'recordingAssetId': sub['recordingAssetId'], 'sourceEventProofInferred': False})
    henry = source_rows['henry-birge-lee']
    prior_henry = next(row for row in before['video']['rows'] if row['sourceRow'] == henry['sourceRow'])
    records.append({'profileId': henry['id'], 'sourceRow': henry['sourceRow'], 'company': henry['company'],
        'contact': henry['contact'], 'status': 'Observed source profile correction; not a new prospect',
        'findings': ['The unique company/contact source row now uses a different LinkedIn URL. This is treated as a source identity correction in the snapshot comparison, with both source keys retained.',
            'The helper reports Connected, while the source action is Skip. No new outreach, automation activation, immutable profile equivalence or commercial outcome is inferred.'],
        'priorSourceProfileId': prior_henry['id'], 'currentSourceProfileId': henry['id'],
        'externalProfileEquivalenceEstablished': False, 'sourceEventProofInferred': False})

    # Independently reread both historical native CSVs and verify every one of
    # the forty identity/date joins against the new complete current inventory.
    left, left_rows, left_read = revision('historical_revision_1253.json')
    right, right_rows, right_read = revision('historical_revision_1290.json')
    a, b = valid_records(left_rows), valid_records(right_rows)
    ka, kb = Counter(map(identity, a)), Counter(map(identity, b))
    assert len(a) == 428 and len(b) == 468 and not ka - kb
    new_keys = kb - ka
    assert sum(new_keys.values()) == 40 and all(count == 1 for count in new_keys.values())
    added = [row for row in b if identity(row) in new_keys]
    assert len({profile(row) for row in added}) == 40
    for row in added:
        joined = source_rows[profile(row)]
        assert normalized(joined['company']) == normalized(row['org'])
        assert normalized(joined['contact']) == normalized(row['contact'])
    as_mountain = lambda value: datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(ZoneInfo('America/Denver')).isoformat()
    appearance = {'snapshotAt': max(left_read, right_read), 'reviewedAt': reviewed,
        'appliesToSnapshotAt': stamp, 'revisionComparisonComplete': True,
        'stableIdentityComparisonVerified': True,
        'scope': 'Fresh complete historical revision exports with all forty source identity/date joins independently revalidated against the current inventory.',
        'baselineRevisionId': left['revisionId'], 'laterRevisionId': right['revisionId'],
        'firstAppearedAfter': left['revisionModifiedTime'], 'firstAppearedBy': right['revisionModifiedTime'],
        'firstAppearedAfterMountain': as_mountain(left['revisionModifiedTime']),
        'firstAppearedByMountain': as_mountain(right['revisionModifiedTime']),
        'baselineValidSourceRows': len(a), 'laterValidSourceRows': len(b),
        'retainedPriorStableIdentities': sum(ka.values()), 'newStableSourceRecordsMinimum': 40,
        'newUniqueProfilesMinimum': 40, 'sourceRecordsRemoved': 0,
        'subsequentIdentityCorrectionsObserved': 1, 'subsequentChangedHistoricalCohortJoins': 0,
        'currentInventoryJoinCount': 40, 'exactRowAddedTimestampAvailable': False,
        'actualMessageEventsAdded': 0, 'sourceWritesPerformed': False,
        'records': [{'profileId': profile(row), 'company': row['org'], 'contact': row['contact'],
            'currentSourceRow': source_rows[profile(row)]['sourceRow'],
            'firstAppearedAfter': left['revisionModifiedTime'], 'firstAppearedBy': right['revisionModifiedTime']} for row in added],
        'notes': ['Every historical revision row has the expected29-column CSV shape, and all forty exact profile plus normalized company/contact joins were independently checked against the new inventory.',
            'The source first-appearance bounds remain October21–22. Rereading the proof does not move those appearances into the current week.',
            'The separate Henry source URL correction does not affect any of these forty identities. Current inventory changes are reported separately.',
            'These are source-record first appearances, not exact row-add times, new people, message events or CRM creations.']}
    prior = copy.deepcopy(before['video']['gapResolutionReview'])
    prior['historicalOnly'] = True
    gap = {'snapshotAt': complete, 'reviewedAt': reviewed,
        'reportingAsOfDate': '2026-10-29', 'appliesToVideoInventorySnapshotAt': stamp,
        'summary': {'description': 'Current recording/date/identity and inactive-QC source fields, separate from native sending proof and commercial outcomes.',
            'newSourceRecordingAssets': 5, 'changedSourceVideoDates': 1,
            'newSourceFollowUpDateReports': 19, 'currentQcPendingNotActivatedRows': 77,
            'currentQcApprovedNotActivatedRows': 19, 'newNativeMessagesInferred': 0,
            'commercialOutcomesChanged': False, 'ownerHoursChanged': False},
        'records': records, 'sourceAppearanceReview': appearance,
        'retainedPriorReviews': [prior],
        'notes': ['The October24 source-gap review is retained as historical proof with its original clocks. Its earlier empty InStockRx recording finding is superseded by the current source asset.',
            'Nineteen additional literal Follow-up Sent Date fields report October26. They are owner-reported source dates; no actual message events are inferred.',
            'The current source has77 QC Pending - Not Activated and19 QC Approved - Not Activated rows. Those workflow labels do not establish activation, absence of older contact history or any sending.',
            'Worksheet status/date changes and source-field first appearance are different from native-platform message proof. Retained native observations keep their original dates and observation clocks.',
            'No worksheet, CRM record, message, automation or owner decision was changed.']}
    old_main = json.loads((ROOT / 'data/private/refresh_2026_10_23/sheets/main_values.json').read_text())['values']
    old_accepted = json.loads((ROOT / 'data/private/refresh_2026_10_23/sheets/accepted_values.json').read_text())['values']
    accepted = load('accepted_values.json')['values']
    changed_main = sum(a != b for a, b in zip(live, old_main)) + abs(len(live) - len(old_main))
    changed_accepted = sum(a != b for a, b in zip(accepted, old_accepted)) + abs(len(accepted) - len(old_accepted))
    drive = result(load('drive_file_after.json'))['structuredContent']
    revisions = result(load('drive_revisions.json'))['structuredContent']
    freshness = {'snapshotAt': complete, 'reviewedAt': reviewed, 'reportingLocalDate': '2026-10-28',
        'appliesToSnapshotAt': stamp,
        'scope': 'Complete allocated main/accepted source ranges and date/helper cells; values changed since the retained prior source.',
        'sourceRanges': ["'centripetal_top20_video_sniper_prospects_aug2026'!A1:AC5000", "'Accepted Connections (Video Prospects)'!A1:AR1011"],
        'collectionCompleteWithinWorkbook': True, 'fullValuesReread': True,
        'valuesIdenticalToRetainedSource': False, 'inventoryChanged': True,
        'changedPhysicalRows': changed_main + changed_accepted,
        'changedMainPhysicalRows': changed_main, 'changedAcceptedPhysicalRows': changed_accepted,
        'priorInventorySnapshotAt': before['video']['snapshotAt'], 'newInventorySnapshotAt': stamp,
        'inventoryCollectionClockPreserved': False, 'currentCounts': video['summary'],
        'sourceModifiedAt': drive['modified_time'], 'fileUnchangedAcrossCollection': True,
        'currentRevisionId': revisions['currentRevisionId'], 'previousRevisionId': revisions['previousRevisionId'],
        'historyAccess': {'revisionMetadataAccessible': True, 'revisionMetadataRows': len(revisions['revisions']),
            'previousRevisionContentReadable': True, 'currentRevisionMatchesFullLiveRead': True,
            'previousMainRevisionRows': len(previous_rows), 'currentMainRevisionRows': len(current_rows),
            'cellEditTimestampOrEventLogProvided': False},
        'dateFieldReview': {'videoDateField': 'Video Sent Date', 'followUpDateField': 'Follow-up Sent Date',
            'dateFieldsLiteralNotFormula': True, 'datePrecision': 'day', 'exactSendingTimestampAvailable': False,
            'upstreamEventTimezone': None, 'workbookTimezone': 'America/Los_Angeles',
            'rowAddedTimestampFieldPresent': False, 'firstLastPersonFieldsAreEventCensus': False},
        'counterChangesFromThisReview': {'sourceRows': 0, 'uniqueProfiles': 0,
            'worksheetVideoDateRows': 0, 'worksheetFollowUpDateRows': 19, 'newNativeSendOrReplyProof': 0},
        'note': 'Source values changed while the valid company/contact population stayed stable. The newer source inventory has its own collection clock; historical native and commercial proof is not redated.'}
    cards = [
        {'id': 'video', 'name': 'Video DMs', 'asOf': stamp, 'status': 'Current full worksheet inventory; native proof separate',
            'coverage': '468 valid source rows /460 exact normalized profiles,71 recording URLs,22 literal video dates and63 literal follow-up dates.',
            'method': 'Read-only complete allocated main/accepted ranges in500-rowchunks; stable metadata/modified-time checks.',
            'note': 'No new valid source rows were observed. Five recording assets, nineteen follow-up date reports and one changed video date are source evidence, not actual-send proof.'},
        {'id': 'waalaxy', 'name': 'Waalaxy · selected connected-person worksheet', 'asOf': stamp,
            'status': 'Current selected worksheet; complete event history unavailable',
            'coverage': '173 connected-status source rows:151 VideoDM-list profiles and22 Pulley-list profiles. This is not account-wide activity.',
            'method': 'Complete allocated Accepted Connections tab read; exact normalized profile identities.',
            'note': 'Five additional profiles were observed, with historical connection datesOct20–25. Existing168person attributes are unchanged; message/reply flags are not current event totals or verified sender-account provenance.'},
        {'id': 'video_source_freshness', 'name': 'Video DM · full-range changed-source verification', 'asOf': complete,
            'status': 'Fresh complete source read; changed fields independently labelled',
            'coverage': 'Main A1:AC5000 and accepted A1:AR1011; source modified time stable across collection.',
            'method': 'Full source values, literal-date/helper review and complete historical/current revision comparisons.',
            'note': 'Current source values differ from the prior snapshot; its native messages and owner decisions retain their own evidence dates.'},
        {'id': 'video_gap_resolution', 'name': 'Video DM · current source-field and identity review', 'asOf': complete,
            'status': 'Current source findings; actual native sending checked separately',
            'coverage': 'Five added recording fields, one changed video date, nineteen added follow-up date reports and one source URL correction.',
            'method': 'Exact current source rows plus complete dated revision comparisons; earlier gap review retained historically.',
            'note': 'All forty historical October21–22 appearance joins were independently revalidated. Their dates are unchanged; this review adds no message or commercial-outcome events.'}]
    save('gap_resolution_review_patch.json', gap)
    save('source_appearance_review_patch.json', appearance)
    save('freshness_review_patch.json', freshness)
    save('source_cards_patch.json', cards)
    print(json.dumps({'sourceInventoryAt': stamp, 'sourceReviewAt': complete, 'changedPhysicalRows': freshness['changedPhysicalRows'],
        'currentGapRecords': len(records), 'revalidatedHistoricalFirstAppearanceJoins': 40, 'newMessageEventsInferred': 0}))


if __name__ == '__main__':
    build()
