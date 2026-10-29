"""Normalize the complete October 28 read-only workbook refresh into private patches.

Worksheet dates and person-history attributes remain source reports. This script
does not write the shared dashboard, publish, or mutate the source workbook.
"""
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from urllib.parse import unquote
import hashlib
import json
import re

from recording_evidence import recording_evidence_fields
from refresh_sheet_2026_10_21 import people, population

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / 'data/private/refresh_2026_10_28/sheets'
SHEET_ID = '1_Vq5-hM3POad1V14rZjX6gfaUojUnnTvxjjSv1zDJ8M'


def load(name):
    return json.loads((PRIVATE / name).read_text())


def write(name, obj):
    (PRIVATE / name).write_text(json.dumps(obj, indent=2, ensure_ascii=False) + '\n')


def profile(value):
    match = re.search(r'linkedin\.com/in/([^/?#]+)', unquote(str(value or '')), re.I)
    return match.group(1).lower().rstrip('/') if match else None


def valid_date(value):
    if not value:
        return None
    value = str(value).strip()
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        return None


def record_rows(raw):
    return [(i, dict(zip(raw[0], row))) for i, row in enumerate(raw[1:], 2)]


def person_identity(row):
    return (row['company'].strip().casefold(), row['contact'].strip().casefold())


def source(name):
    path = PRIVATE / name
    return {'path': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def build():
    manifest = load('collection_manifest.json')
    stamp = manifest['collectedAt'].replace(' UTC', 'Z').replace(' ', 'T')
    baseline_path = PRIVATE.parent / 'baseline_shared.json'
    previous = json.loads(baseline_path.read_text() if baseline_path.exists() else (ROOT / 'data/shared-dashboard.json').read_text())
    main = load('main_values.json')['values']
    accepted = load('accepted_values.json')['values']
    metadata = load('drive_spreadsheet_metadata.json')['result']['value']['structuredContent']
    metadata_after = load('post_read_0.json')['result']['value']
    initial_file = load('drive_file_metadata.json')['result']['value']['structuredContent']
    final_file = load('post_read_1.json')['result']['value']['structuredContent']
    assert initial_file['modified_time'] == final_file['modified_time'], 'Source changed while collecting; reread values'
    collection_completed = load('post_read_1.json')['collectedAt'].replace(' UTC', 'Z').replace(' ', 'T')
    assert json.loads(metadata_after['content'][0]['text']) == json.loads(load('metadata.json')['result']['content'][0]['text'])
    assert metadata['properties']['timeZone'] == 'America/Los_Angeles'
    assert len(main) == metadata['sheets'][0]['properties']['gridProperties']['rowCount'] == 5000
    assert len(main[0]) == 29 and len(accepted[0]) == 44
    current_raw, rows, dated = {}, [], []
    groups = defaultdict(list)
    for line, item in record_rows(main):
        company, contact = str(item.get('org') or '').strip(), str(item.get('contact') or '').strip()
        if not company or not contact or (company == 'org' and contact == 'contact'):
            continue
        key = profile(item.get('li'))
        status = str(item.get('Status (CS Column)') or '').strip()
        video_date = valid_date(item.get('Video Sent Date'))
        follow_date = valid_date(item.get('Follow-up Sent Date'))
        asset_match = re.search(r'/share/([a-fA-F0-9]{32})', str(item.get('Loom Link') or ''))
        row = {
            'id': key or hashlib.sha256((company + '|' + contact).lower().encode()).hexdigest()[:16],
            'sourceRow': line, 'company': company, 'contact': contact,
            'linkedin': 'https://www.linkedin.com/in/' + key + '/' if key else '',
            'status': status or 'Blank', **recording_evidence_fields(item.get('Loom Link')),
            'recordingAssetId': asset_match.group(1).lower() if asset_match else None,
            'hasResponseStatus': bool(str(item.get('Response Status') or '').strip()),
            'responseStatus': str(item.get('Response Status') or '').strip() or None,
            'connected': str(item.get('Connected?') or '').strip() == 'Connected',
            'connectedAt': valid_date(item.get('Connected At')),
            'connectionLabel': str(item.get('Connected?') or '').strip(),
            'action': item.get('DM Action') or '', 'followUp': item.get('Follow-up Action') or '',
            'dealId': item.get('deal_id') or None,
            # Keep the historical field's exact Sent/Done definition. Source
            # taxonomy changed; the newer explicit Video Sent status is separate.
            'explicitSendStatus': status.lower() in {'sent', 'done'},
            'reportedVideoSentStatus': status.lower() == 'video sent',
            'datedSendStatus': bool(video_date),
            'reportedVideoSentDate': video_date, 'reportedFollowUpSentDate': follow_date,
            'sourceDateBasis': 'Literal date-only worksheet fields; owner-reported activity, not native-platform or delivery proof.',
            'syncedToPipedriveFlag': str(item.get('Synced to Pipedrive') or '').strip().lower() in {'true', 'yes'},
        }
        rows.append(row)
        current_raw[line] = item
        if key:
            groups[key].append(row)
        for when, kind, field in [(video_date, 'Send status', 'Video Sent Date'), (follow_date, 'Follow-up status', 'Follow-up Sent Date')]:
            if when:
                dated.append({'date': when, 'contactId': row['id'], 'sourceRow': line,
                    'type': kind, 'channel': 'unspecified', 'sourceField': field,
                    'contentType': 'video' if field == 'Video Sent Date' else 'unspecified',
                    'datePrecision': 'day', 'sourceTimezone': None,
                    'basis': 'Self-reported literal worksheet date; channel/content and delivery are not independently verified.'})
    actions = Counter(r['action'] for r in rows)
    duplicates = [{'profile': key, 'rows': [r['sourceRow'] for r in rs],
        'actions': sorted({r['action'] for r in rs}), 'statuses': sorted({r['status'] for r in rs})}
        for key, rs in groups.items() if len(rs) > 1]
    summary = {
        'sourceRows': len(rows), 'uniqueProfiles': len(groups),
        'rowsMissingProfile': sum(not r['linkedin'] for r in rows),
        'readyRows': actions['Ready for video DM'], 'sheetCompletedRows': actions['Already sent/completed'],
        'explicitSendStatusRows': sum(r['explicitSendStatus'] for r in rows),
        'reportedVideoSentStatusRows': sum(r['reportedVideoSentStatus'] for r in rows),
        'datedSendStatusRows': sum(r['datedSendStatus'] for r in rows),
        'reportedFollowUpDateRows': sum(bool(r['reportedFollowUpSentDate']) for r in rows),
        'followUpRows': sum(r['followUp'] == 'Follow-up Needed' for r in rows),
        'manualCheckRows': sum(r['followUp'] == 'Manual Check' for r in rows),
        'reviewRows': actions['Review'], 'awaitingConnectionRows': actions['Awaiting connection'],
        'skipRows': actions['Skip'], 'duplicates': len(duplicates),
        'duplicateExtraRows': sum(len(d['rows']) - 1 for d in duplicates),
        'conflictingProfiles': sum(len(d['actions']) > 1 for d in duplicates),
        'acceptedConnectionRecords': len(accepted) - 1,
        'connectedRows': sum(r['connected'] for r in rows),
        'rowsWithDealId': sum(bool(r['dealId']) for r in rows),
        'syncedToPipedriveFlagRows': sum(r['syncedToPipedriveFlag'] for r in rows),
        'recordingLinkRows': sum(r['hasRecordingLink'] for r in rows),
        'recordingFieldNonemptyRows': sum(r['hasRecordingFieldContent'] for r in rows),
        'recordingFieldNonUrlNotes': sum(r['recordingFieldKind'] == 'non_url_note' for r in rows),
        'newRowsInPeriod': None,
    }
    old_rows = previous['video']['rows']
    old_people, new_people = defaultdict(list), defaultdict(list)
    for row in old_rows:
        old_people[person_identity(row)].append(row)
    for row in rows:
        new_people[person_identity(row)].append(row)
    repairs = {}
    for who in old_people.keys() & new_people.keys():
        if len(old_people[who]) == len(new_people[who]) == 1:
            old, new = old_people[who][0], new_people[who][0]
            if old['id'] != new['id']:
                repairs[old['id']] = new['id']
    old_rows = [dict(r, id=repairs.get(r['id'], r['id'])) for r in old_rows]
    old_by, new_by = defaultdict(list), defaultdict(list)
    for row in old_rows:
        old_by[row['id']].append(row)
    for row in rows:
        new_by[row['id']].append(row)
    comparable = {key for key in old_by.keys() & new_by.keys() if len(old_by[key]) == len(new_by[key]) == 1}
    old_ids, new_ids = Counter(r['id'] for r in old_rows), Counter(r['id'] for r in rows)
    fields = ['status', 'action', 'followUp', 'connected', 'dealId', 'syncedToPipedriveFlag', 'hasRecordingLink', 'hasResponseStatus', 'responseStatus', 'reportedVideoSentDate', 'reportedFollowUpSentDate', 'recordingAssetId']
    changes = []
    for key in sorted(comparable):
        old, new = old_by[key][0], new_by[key][0]
        changed = {field: {'before': old.get(field), 'after': new.get(field)} for field in fields if old.get(field) != new.get(field)}
        if changed:
            changes.append({'profile': key, 'oldSourceRow': old['sourceRow'], 'newSourceRow': new['sourceRow'],
                'company': new['company'], 'contact': new['contact'], 'changes': changed})
    delta = {
        'basis': 'First observed between source snapshots; status/schema/helper edits are not creation/send timestamps.',
        'fromSnapshotAt': previous['video']['snapshotAt'], 'toSnapshotAt': stamp,
        'additionalRowsObserved': sum((new_ids - old_ids).values()),
        'rowsNoLongerObserved': sum((old_ids - new_ids).values()),
        'newUniqueProfilesObserved': len(new_by.keys() - old_by.keys()),
        'profileIdentityCorrectionsObserved': len(repairs),
        'derivedActionClassificationChangesObserved': sum(old_by[k][0]['action'] != new_by[k][0]['action'] for k in comparable),
        'connectedFlagChangesObserved': sum(old_by[k][0]['connected'] != new_by[k][0]['connected'] for k in comparable),
        'explicitSentDoneStatusChangesObserved': sum(not old_by[k][0]['explicitSendStatus'] and new_by[k][0]['explicitSendStatus'] for k in comparable),
        'statusChangesObserved': sum(old_by[k][0]['status'] != new_by[k][0]['status'] for k in comparable),
        'comparableUniqueIdentityCount': len(comparable),
        'summaryChanges': {key: summary[key] - previous['video']['summary'].get(key, 0) for key in
            ['sourceRows', 'uniqueProfiles', 'readyRows', 'sheetCompletedRows', 'explicitSendStatusRows', 'datedSendStatusRows', 'connectedRows', 'reviewRows', 'awaitingConnectionRows', 'skipRows', 'recordingLinkRows']},
        'note': 'Differences in statuses, date fields, completion and follow-up helper classifications are first-observed source changes. They do not by themselves establish new messages. Native observations remain a separate historical evidence layer.'}
    connection_rows = people(record_rows(accepted), set(groups))
    subset = population(connection_rows, {r['profileId'] for r in previous['waalaxy']['sheetSubset']['rows']})
    subset.update(sourceSpreadsheetId=SHEET_ID, sourceTabId=1939678986, sourceTab='Accepted Connections (Video Prospects)',
        returnedDataRows=len(connection_rows), scope='Selected connected prospects: Video DMs and Pulley Contacts lists; not account-wide Waalaxy coverage.',
        dateBasis='Date-only first/last prospect attributes. Workbook timezone America/Los_Angeles; upstream event timezone is unreported. These are not a complete event history.',
        collectionCompleteWithinTab=True, upstreamExportCompleteForAccount=False)
    prior_connections = {r['profileId']: r for r in previous['waalaxy']['sheetSubset']['rows']}
    conn_fields = ['profileStatus', 'messageSentFlag', 'messageRepliedFlag', 'emailSentFlag', 'emailRepliedFlag', 'connectedAt', 'importDate', 'connectionRequestDate', 'firstMessageAt', 'lastMessageAt', 'lastReplyAt']
    conn_changes = [{'profile': r['profileId'], 'changes': {field: {'before': prior_connections[r['profileId']].get(field), 'after': r.get(field)} for field in conn_fields if prior_connections[r['profileId']].get(field) != r.get(field)}}
        for r in connection_rows if r['profileId'] in prior_connections]
    conn_changes = [r for r in conn_changes if r['changes']]
    helper_cells = load('date_and_helper_cells.json')['result']['structuredContent']
    formulas = [c.get('userEnteredValue', {}).get('formulaValue') for s in helper_cells['sheets'] for d in s.get('data', []) for row in d.get('rowData', []) for c in row.get('values', []) if c.get('userEnteredValue', {}).get('formulaValue')]
    assert any('videoDate' in f and 'followDate' in f for f in formulas)
    assert any('Manual Connection Override' == c.get('formattedValue') for s in helper_cells['sheets'] for d in s.get('data', []) for row in d.get('rowData', []) for c in row.get('values', []))
    date_formulas = [c for s in helper_cells['sheets'] if s['properties']['sheetId'] == 569014042 for d in s.get('data', []) if d.get('startColumn') == 19 for row in d.get('rowData', []) for c in row.get('values', []) if c.get('userEnteredValue', {}).get('formulaValue')]
    assert not date_formulas, 'Formula-derived dates require separate treatment'
    accepted_raw = [r for _, r in record_rows(accepted)]
    candidates = []
    prior_reported = {(r['contactId'], r['date']) for r in previous['video'].get('datedActions', []) if r['type'] == 'Send status'}
    for row in rows:
        if row['reportedVideoSentDate'] and (row['id'], row['reportedVideoSentDate']) not in prior_reported:
            raw = current_raw[row['sourceRow']]
            asset = re.search(r'/share/([a-fA-F0-9]{32})', str(raw.get('Loom Link') or ''))
            candidates.append({key: row[key] for key in ['id', 'sourceRow', 'company', 'contact', 'linkedin', 'dealId', 'status', 'reportedVideoSentDate', 'hasRecordingLink', 'syncedToPipedriveFlag']})
            candidates[-1].update(loomAssetId=asset.group(1).lower() if asset else None,
                basis='Newly observed worksheet-reported video date, not independently verified sending or delivery.')
    notes = [
        'All allocated worksheet rows and columns were read in bounded chunks. Only nonblank company/contact records count as prospects.',
        'Current statuses and helper classifications remain source reports; classification changes are not commercial outcomes or independently observed new sends.',
        'Video Sent Date and Follow-up Sent Date are literal owner-reported date-only fields. Timezone and exact sending instants remain unreported.',
        'Recording assets establish available content; links, statuses and CRM synchronization flags do not independently establish delivery.',
        'Native conversation observations retain their original dates and collection timestamps separately from this newer inventory.',
        'Accepted-connections first/last dates are person-history attributes, not a complete message/reply event census.',
        'Synced to Pipedrive remains a source flag. Exact CRM identity/asset matching must be verified independently.',
    ]
    video = {'snapshotAt': stamp, 'status': 'available', 'coverage': 'Complete current main and accepted-connection worksheet ranges; valid prospect inventory and owner-reported dates, separate from native send/reply proof.',
        'upstreamSyncAt': None, 'accountScope': 'User-identified Charles Video DM workflow; no sender account ID in workbook.',
        'sourceUrl': 'https://docs.google.com/spreadsheets/d/' + SHEET_ID + '/edit',
        'summary': summary, 'snapshotDelta': delta, 'rows': rows, 'datedActions': dated, 'duplicateProfiles': duplicates,
        'sourceCoverage': {'mainRange': 'A1:AC5000', 'acceptedRange': 'A1:AR1011',
            'mainReturnedRowsIncludingHeader': len(main), 'acceptedReturnedRowsIncludingHeader': len(accepted),
            'excludedNonProspectPhysicalRows': len(main) - 1 - len(rows), 'completeWithinWorkbook': True,
            'spreadsheetTimezone': 'America/Los_Angeles', 'upstreamSyncAt': None,
            'collectionMethod': 'Read-only Centripetal Google Sheets integration; full allocated bounds in 500-row chunks.'},
        'connectionDiagnostics': {'connectedFlagRows': summary['connectedRows'],
            'verifyConnectionRows': sum(r['connectionLabel'] == 'Verify connection' for r in rows),
            'reviewDuplicateRows': sum(r['connectionLabel'] == 'Review duplicate' for r in rows),
            'acceptedProfilesMatchedMain': sum(r['matchedVideoProspect'] for r in connection_rows),
            'acceptedProfilesWithoutConnectedFlag': sum(r['matchedVideoProspect'] and not any(v['connected'] for v in groups[r['profileId']]) for r in connection_rows),
            'helperRuleVerified': True,
            'helperRuleBasis': 'Current source formulas verified. Main status/action and follow-up helpers use explicit date fields, Loom assets, terminal/excluded status and accepted identity verification. Accepted verification supports an explicit manual override; all current override cells are blank.',
            'manualOverrideRows': sum(bool(str(r.get('Manual Connection Override') or '').strip()) for r in accepted_raw)},
        'notes': notes, 'provenance': [source(n) for n in ['metadata.json', 'main_values.json', 'accepted_values.json', 'date_and_helper_cells.json', 'drive_file_metadata.json']]}
    waalaxy_patch = {'snapshotAt': stamp, 'sheetSubset': subset, 'sheetSubsetCollectedAt': stamp,
        'sheetSubsetUpstreamSyncAt': None, 'sheetSubsetAccountVerification': {'senderAccountId': None, 'independentlyVerified': False,
            'basis': 'User-identified Charles workflow; workbook has no sender account ID.'}}
    report = {'snapshotAt': stamp, 'reportingLocalDate': '2026-10-28', 'videoSummary': summary, 'videoDelta': delta,
        'statusCounts': dict(Counter(r['status'] for r in rows)), 'datedStatusCounts': dict(Counter(r['date'] + ' ' + r['type'] for r in dated)),
        'waalaxySubsetMetrics': subset['metrics'], 'waalaxyPersonAttributeChanges': conn_changes,
        'newVideoDateCandidates': candidates,
        'sourceSchemaReview': {'sourceStatusTaxonomyChanged': {r['status'] for r in previous['video']['rows']} != {r['status'] for r in rows}, 'dateColumnsLiteralNotFormula': True,
            'fullMainGridRows': 5000, 'acceptedColumns': 44, 'newAcceptedHelperColumns': accepted[0][40:],
            'sourceTimezone': 'America/Los_Angeles', 'upstreamMessageTimezone': None,
            'accountSenderId': None, 'nativeMessageProofPreservationRequired': True},
        'newRows': [r for r in rows if r['id'] not in old_by], 'changedComparableRows': changes,
        'rowRemapping': [{'profile': key, 'oldSourceRow': old_by[key][0]['sourceRow'], 'newSourceRow': new_by[key][0]['sourceRow']} for key in sorted(comparable)],
        'limits': notes}
    report['collectionReview'] = {'collectionStartedAt': stamp, 'collectionCompletedAt': collection_completed,
        'sourceModifiedAtBeforeAndAfter': final_file['modified_time'], 'fileUnchangedAcrossRead': True,
        'gridDimensionsUnchangedAcrossRead': True}
    video['sourceCoverage'].update(report['collectionReview'])
    assert len(rows) == sum(actions.values()) == len({r['sourceRow'] for r in rows})
    assert len(connection_rows) == len({r['profileId'] for r in connection_rows})
    assert len(dated) == summary['datedSendStatusRows'] + summary['reportedFollowUpDateRows']
    write('video_inventory_patch.json', video)
    write('waalaxy_sheet_subset_patch.json', waalaxy_patch)
    write('sheets_review_report.json', report)
    write('new_video_native_review_candidates.json', candidates)
    recording_review = {'snapshotAt': stamp, 'reviewedAt': stamp,
        'appliesToSnapshotAt': stamp, 'source': 'Complete current worksheet recording field, literal source values.',
        'nonemptyCells': summary['recordingFieldNonemptyRows'],
        'recordingUrlCells': summary['recordingLinkRows'],
        'validLoomUrls': sum(r['recordingFieldKind'] == 'loom_url' for r in rows),
        'nonUrlNotes': summary['recordingFieldNonUrlNotes'],
        'records': [{'sourceRow': r['sourceRow'], 'profile': r['id'],
            **{key: r[key] for key in ['hasRecordingFieldContent', 'hasRecordingLink', 'recordingFieldKind', 'recordingFieldNote']}}
            for r in rows if r['hasRecordingFieldContent']],
        'basis': 'Recording field values classified with the shared URL parser; recording content does not establish sending or delivery.',
        'provenance': source('main_values.json')}
    write('recording_field_review_patch.json', recording_review)
    crm_input = []
    for r in rows:
        raw = current_raw[r['sourceRow']]
        asset = re.search(r'/share/([a-fA-F0-9]{32})', str(raw.get('Loom Link') or ''))
        if r['dealId'] or asset:
            crm_input.append({key: r[key] for key in ['id', 'sourceRow', 'company', 'contact', 'linkedin', 'dealId', 'reportedVideoSentDate', 'reportedFollowUpSentDate', 'syncedToPipedriveFlag', 'recordingFieldKind']})
            crm_input[-1]['loomAssetId'] = asset.group(1).lower() if asset else None
    write('video_crm_join_input.json', {'snapshotAt': stamp, 'records': crm_input,
        'scope': 'Current valid source rows with a Sheet deal ID and/or valid Loom asset. Raw personal notes/contact information omitted.',
        'assertion': 'Sheet sync flag and deal ID are source reports until CRM identities/assets are verified.'})
    print(json.dumps({'snapshotAt': stamp, 'summary': summary, 'delta': delta,
        'waalaxySubsetMetrics': subset['metrics'], 'waalaxyPersonAttributeChanges': len(conn_changes),
        'newVideoNativeReviewCandidates': len(candidates), 'datedStatusCounts': report['datedStatusCounts']}, indent=2))


if __name__ == '__main__':
    build()
