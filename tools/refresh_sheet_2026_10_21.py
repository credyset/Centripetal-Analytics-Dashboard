"""Normalize complete read-only Sheets snapshots and separate selected CSV exports.

This writes isolated ignored patches only; it does not mutate dashboard inputs.
Workbook formatting/non-record rows, source attributes and delivery are distinct.
"""
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import unquote
import csv
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / 'data/private/refresh_2026_10_21'
SPREADSHEET = '1_Vq5-hM3POad1V14rZjX6gfaUojUnnTvxjjSv1zDJ8M'


def read(name):
    return json.loads((PRIVATE / name).read_text())


def values(name):
    return read(name)['result']['structuredContent']['values']


def records(rows):
    return [(line, dict(zip(rows[0], row))) for line, row in enumerate(rows[1:], 2)]


def profile(value):
    match = re.search(r'linkedin\.com/in/([^/?#]+)', unquote(str(value or '')), re.I)
    return match.group(1).lower().rstrip('/') if match else None


def yes(value):
    return str(value or '').strip().lower() in {'true', 'yes', 'connected'}


def iso_date(value):
    if value in (None, ''):
        return None
    if isinstance(value, (int, float)):
        # Google Sheets date serials use the 1899-12-30 epoch. These remain
        # date-only attributes; converting them does not establish an instant.
        return (date(1899, 12, 30) + timedelta(days=int(value))).isoformat()
    value = str(value).strip()
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        return date.fromisoformat(value).isoformat()
    return None


def status_category(value):
    value = str(value or '').strip()
    allowed = {'sent', 'done', 'no li response', 'not a real profile', 'target', 'not a target',
               'already responded', 'passed', 'sent li invite', 'need email to send li invite',
               'qc approved — not activated', 'qc pending — not activated', 'duplicate',
               'waiting for li response', 'target - pass'}
    if not value:
        return 'Blank'
    if value.lower() in allowed:
        return value
    if re.match(r'f/?u|follow', value, re.I):
        return 'Follow-up status recorded'
    if re.match(r'sent\s+email\s+\d', value, re.I):
        return 'Dated email send status recorded'
    if re.match(r'sent\s+\d', value, re.I):
        return 'Dated send status recorded'
    return 'Other recorded status'


def provenance(name):
    path = PRIVATE / name
    return {'path': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def people(raw, main_ids):
    result = []
    for line, item in raw:
        key = profile(item.get('linkedinUrl'))
        if not key:
            continue
        result.append({'profileId': key, 'sourceRow': line, 'list': item.get('prospectList') or None,
            'profileStatus': item.get('profileStatus') or None,
            'messageSentFlag': yes(item.get('messageSent')), 'messageRepliedFlag': yes(item.get('messageReplied')),
            'emailSentFlag': yes(item.get('emailSent')), 'emailRepliedFlag': yes(item.get('emailReplied')),
            'connectedAt': iso_date(item.get('connectedAt')), 'importDate': iso_date(item.get('importDate')),
            'connectionRequestDate': iso_date(item.get('connectionRequestDate')),
            'firstMessageAt': iso_date(item.get('firstMessageAt')),
            'lastMessageAt': iso_date(item.get('lastLinkedinMessageSentDate')),
            'lastReplyAt': iso_date(item.get('lastLinkedinReplyDate')),
            'matchedVideoProspect': key in main_ids})
    assert len(result) == len({r['profileId'] for r in result}), 'Review duplicate source identities before combining'
    return result


def population(rows, old_ids=None):
    daily = defaultdict(Counter)
    for row in rows:
        for field, label in [('connectedAt', 'connectionsRecorded'), ('connectionRequestDate', 'connectionRequestsFirstRecorded'),
                             ('firstMessageAt', 'firstMessageRecipients'), ('lastMessageAt', 'lastMessageRecipients'),
                             ('lastReplyAt', 'lastReplyingProspects'), ('importDate', 'prospectsImported')]:
            if row[field]:
                daily[row[field]][label] += 1
    metrics = {'connectedProspects': len(rows),
        'videoDmListProspects': sum(r['list'] == 'Video DMs' for r in rows),
        'pulleyListProspects': sum(str(r['list']).startswith('Pulley Contacts') for r in rows),
        'matchedMainUniqueProfiles': sum(r['matchedVideoProspect'] for r in rows),
        'messageRecipientFlags': sum(r['messageSentFlag'] for r in rows),
        'replyingProspectFlags': sum(r['messageRepliedFlag'] for r in rows),
        'connectedAtKnown': sum(bool(r['connectedAt']) for r in rows),
        'connectedAtMissing': sum(not r['connectedAt'] for r in rows),
        'latestConnectedAt': max((r['connectedAt'] for r in rows if r['connectedAt']), default=None),
        'latestMessageDate': max((r['lastMessageAt'] for r in rows if r['lastMessageAt']), default=None),
        'latestReplyDate': max((r['lastReplyAt'] for r in rows if r['lastReplyAt']), default=None),
        'currentPeriodMessageEvents': None, 'currentPeriodReplyEvents': None, 'acceptanceRate': None,
        'accountWideProspects': None}
    if old_ids is not None:
        metrics['newlyObservedConnectedProfileIds'] = len({r['profileId'] for r in rows} - old_ids)
    return {'metrics': metrics, 'rows': rows,
        'dailyPeopleAttributes': [{'date': day, **counts} for day, counts in sorted(daily.items())],
        'listCounts': dict(Counter(r['list'] for r in rows))}


def build():
    meta = read('sheets_metadata.json')['result']['structuredContent']
    main_raw = values('sheets_main_raw.json')
    connection_raw = values('sheets_connections_formatted.json')
    assert meta['properties']['timeZone'] == 'America/Los_Angeles'
    assert meta['sheets'][0]['properties']['title'] == 'centripetal_top20_video_sniper_prospects_aug2026'
    assert meta['sheets'][1]['properties']['title'] == 'Accepted Connections (Video Prospects)'
    assert len(main_raw) <= meta['sheets'][0]['properties']['gridProperties']['rowCount']
    assert len(connection_raw) <= meta['sheets'][1]['properties']['gridProperties']['rowCount']
    stamp = read('sheets_main_raw.json')['collectedAt'].replace(' UTC', 'Z').replace(' ', 'T')
    previous = read('sheets_prior_snapshot.json')
    rows, dated = [], []
    groups = defaultdict(list)
    for line, item in records(main_raw):
        company, contact = str(item.get('org') or '').strip(), str(item.get('contact') or '').strip()
        if not company or not contact or (company == 'org' and contact == 'contact'):
            continue
        key = profile(item.get('li'))
        status = str(item.get('Status (CS Column)') or '').strip()
        row = {'id': key or hashlib.sha256((company+'|'+contact).lower().encode()).hexdigest()[:16],
            'sourceRow': line, 'company': company, 'contact': contact,
            'linkedin': 'https://www.linkedin.com/in/'+key+'/' if key else '',
            'status': status_category(status), 'hasRecordingLink': bool(str(item.get('Loom Link') or '').strip()),
            'hasResponseStatus': bool(str(item.get('Response Status') or '').strip()),
            'connected': yes(item.get('Connected?')), 'connectedAt': iso_date(item.get('Connected At')),
            'connectionLabel': str(item.get('Connected?') or '').strip(),
            'action': item.get('DM Action') or '', 'followUp': item.get('Follow-up Action') or '',
            'dealId': item.get('deal_id') or None, 'explicitSendStatus': status.lower() in {'sent', 'done'},
            'datedSendStatus': bool(re.match(r'sent\s+\d', status, re.I)),
            'syncedToPipedriveFlag': yes(item.get('Synced to Pipedrive'))}
        rows.append(row)
        if key:
            groups[key].append(row)
        match = re.search(r'(\d{1,2})/(\d{1,2})/(\d{2,4})', status)
        if match:
            month, day, year = map(int, match.groups())
            year += 2000 if year < 100 else 0
            try:
                when = date(year, month, day).isoformat()
            except ValueError:
                continue
            category = ('Follow-up status' if re.match(r'f/?u|follow', status, re.I) else
                        'Email send status' if re.match(r'sent\s+email', status, re.I) else 'Send status')
            dated.append({'date': when, 'contactId': row['id'], 'sourceRow': line, 'type': category,
                'channel': 'email' if category == 'Email send status' else 'unspecified',
                'basis': 'self-reported dated status; channel/content and delivery are not independently verified'})
    actions = Counter(r['action'] for r in rows)
    duplicates = [{'profile': key, 'rows': [r['sourceRow'] for r in group], 'actions': sorted({r['action'] for r in group})}
        for key, group in groups.items() if len(group)>1]
    summary = {'sourceRows': len(rows), 'uniqueProfiles': len(groups), 'rowsMissingProfile': sum(not r['linkedin'] for r in rows),
        'readyRows': actions['Ready for video DM'], 'sheetCompletedRows': actions['Already sent/completed'],
        'explicitSendStatusRows': sum(r['explicitSendStatus'] for r in rows),
        'datedSendStatusRows': sum(r['datedSendStatus'] for r in rows),
        'followUpRows': sum(r['followUp']=='Follow-up Needed' for r in rows),
        'manualCheckRows': sum(r['followUp']=='Manual Check' for r in rows),
        'reviewRows': actions['Review'], 'awaitingConnectionRows': actions['Awaiting connection'], 'skipRows': actions['Skip'],
        'duplicates': len(duplicates), 'duplicateExtraRows': sum(len(d['rows'])-1 for d in duplicates),
        'conflictingProfiles': sum(len(d['actions'])>1 for d in duplicates),
        'acceptedConnectionRecords': len(connection_raw)-1, 'connectedRows': sum(r['connected'] for r in rows),
        'rowsWithDealId': sum(bool(r['dealId']) for r in rows),
        'syncedToPipedriveFlagRows': sum(r['syncedToPipedriveFlag'] for r in rows), 'newRowsInPeriod': None}
    # One company/contact can retain its source identity while its profile URL
    # changes. Reconcile only unique exact company/contact matches, and report
    # the observed edit separately from prospect acquisition.
    identity = lambda row: (row['company'].strip().casefold(), row['contact'].strip().casefold())
    old_people, new_people = defaultdict(list), defaultdict(list)
    for row in previous['video']['rows']:
        old_people[identity(row)].append(row)
    for row in rows:
        new_people[identity(row)].append(row)
    identity_edits = {}
    for who in old_people.keys() & new_people.keys():
        if len(old_people[who])==len(new_people[who])==1:
            old, new = old_people[who][0], new_people[who][0]
            if old['id'] != new['id']:
                identity_edits[old['id']] = new['id']
    prior_rows = [dict(row, id=identity_edits.get(row['id'],row['id'])) for row in previous['video']['rows']]
    old_by, new_by = defaultdict(list), defaultdict(list)
    for row in prior_rows:
        old_by[row['id']].append(row)
    for row in rows:
        new_by[row['id']].append(row)
    comparable = {key for key in old_by.keys() & new_by.keys() if len(old_by[key])==len(new_by[key])==1}
    delta = {'basis':'First observed between source snapshots; not creation/send timestamps',
        'fromSnapshotAt':previous['video']['snapshotAt'], 'toSnapshotAt':stamp,
        'additionalRowsObserved':sum((Counter(r['id'] for r in rows)-Counter(r['id'] for r in prior_rows)).values()),
        'rowsNoLongerObserved':sum((Counter(r['id'] for r in prior_rows)-Counter(r['id'] for r in rows)).values()),
        'profileIdentityCorrectionsObserved':len(identity_edits),
        'derivedActionClassificationChangesObserved':sum(old_by[k][0]['action'] != new_by[k][0]['action'] for k in comparable),
        'connectedFlagChangesObserved':sum(old_by[k][0]['connected'] != new_by[k][0]['connected'] for k in comparable),
        'explicitSentDoneStatusChangesObserved':sum(not old_by[k][0]['explicitSendStatus'] and new_by[k][0]['explicitSendStatus'] for k in comparable),
        'comparableUniqueIdentityCount':len(comparable),
        'summaryChanges':{key:summary[key]-previous['video']['summary'].get(key,0) for key in
            ['sourceRows','uniqueProfiles','readyRows','sheetCompletedRows','explicitSendStatusRows','connectedRows','reviewRows','awaitingConnectionRows']},
        'note':'Rows are reordered in the source. Unique exact company/contact matches reconcile observed profile URL edits before growth counts; no new/removed prospect is inferred from those edits. Duplicate identities are excluded from status comparisons. The 725 non-prospect physical rows are excluded.'}
    connections = people(records(connection_raw), set(groups))
    old_conn_ids = {r['profileId'] for r in previous['sheetSubset']['rows']}
    subset = population(connections, old_conn_ids)
    subset.update(sourceSpreadsheetId=SPREADSHEET, sourceTabId=1939678986, sourceTab='Accepted Connections (Video Prospects)',
        returnedDataRows=len(connections), scope='Selected connected prospects: Video DMs and Pulley Contacts lists; not account-wide Waalaxy coverage.',
        dateBasis='Date-only first/last prospect attributes. Workbook timezone America/Los_Angeles; upstream event timezone is unreported. These are not a complete event history.',
        collectionCompleteWithinTab=True, upstreamExportCompleteForAccount=False)
    conn_ids = {r['profileId'] for r in connections}
    without_flag=[r for r in connections if r['profileId'] in groups and not any(v['connected'] for v in groups[r['profileId']])]
    helper=read('sheets_connection_helper_formula.json')['structuredContent']['values'][0][0]
    assert 'verifiedMatches' in helper and "$U$2:$U,\"<>\"" in helper and 'Verify connection' in helper
    video = {'snapshotAt':stamp,'status':'available','coverage':'Complete current main and accepted-connection worksheet ranges; valid prospect inventory, not row-added/send events.',
        'upstreamSyncAt':None,'accountScope':'User-identified Charles Video DM workflow; no sender account ID in workbook.',
        'summary':summary,'snapshotDelta':delta,'rows':rows,'datedActions':dated,'duplicateProfiles':duplicates,
        'sourceCoverage':{'mainRange':'A1:AC1206','acceptedRange':'A1:AN1011','mainReturnedRowsIncludingHeader':len(main_raw),
            'acceptedReturnedRowsIncludingHeader':len(connection_raw),'excludedNonProspectPhysicalRows':len(main_raw)-1-len(rows),
            'completeWithinWorkbook':True,'spreadsheetTimezone':'America/Los_Angeles','upstreamSyncAt':None},
        'connectionDiagnostics':{'connectedFlagRows':summary['connectedRows'], 'verifyConnectionRows':sum(r['connectionLabel']=='Verify connection' for r in rows),
            'acceptedProfilesMatchedMain':sum(r['matchedVideoProspect'] for r in connections),
            'acceptedProfilesWithoutConnectedFlag':len(without_flag),
            'acceptedProfilesWithoutConnectedFlagMissingDate':sum(not r['connectedAt'] for r in without_flag),
            'helperRuleVerified':True,
            'helperRuleBasis':'Live V2 formula requires a unique connected-status URL match with a nonblank acceptance date. Status-only matches intentionally remain Verify connection; every currently excluded matched profile lacks the date.'},
        'notes':['Only populated company/contact records count as prospects; blank/formatting/helper rows are excluded.',
            'Sheet-classified completion includes recording-link presence; a recording link does not prove delivery.',
            'Exact Sent/Done statuses remain separate from dated send statuses. Dated status text is self-reported; it does not independently verify video content, channel or delivery.',
            'The October 19 email status is kept separate from send/follow-up status counts.',
            'The live helper intentionally requires an acceptance date as well as connected status and an exact unique URL match. All 33 accepted profiles without a main Connected flag lack that date; these are verification gaps, not demonstrated formula errors.',
            'Synced to Pipedrive is a source flag; successful identity synchronization is not independently verified.',
            'Snapshot differences are first-observed changes, not actual creation/send dates. Collection freshness is separate from unknown upstream sync.'],
        'provenance':[provenance(name) for name in ['sheets_main_raw.json','sheets_connections_raw.json','sheets_connections_formatted.json','sheets_metadata.json']]}
    export_rows = []
    export_evidence = []
    for name in ['waalaxy_video_dms_2026_10_20.csv','waalaxy_pulley_2026_10_20.csv']:
        with (PRIVATE/name).open(encoding='utf-8-sig', newline='') as handle:
            raw = list(csv.DictReader(handle))
        normalized = people(list(enumerate(raw,2)), set(groups))
        for row in normalized:
            row['sourceExport'] = name
        export_rows.extend(normalized)
        export_evidence.append({**provenance(name),'sourceRows':len(raw),
            'filesystemModifiedAt':datetime.fromtimestamp((PRIVATE/name).stat().st_mtime,timezone.utc).isoformat(),
            'exportGeneratedAt':None})
    assert len(export_rows)==len({r['profileId'] for r in export_rows}), 'Cross-export duplicate requires reconciliation'
    exports = population(export_rows)
    exports.update(status='available_selected_exports', reviewedAt=stamp,
        sourceObservationThrough=max(r['connectedAt'] for r in export_rows if r['connectedAt']),
        scope='Two locally retained selected-person CSV exports, Video DMs and Pulley lists. Separate from current accepted-connections worksheet.',
        dateBasis='Source date-only first/last attributes; upstream timezone and export generation timestamp are unreported.',
        upstreamExportCompleteForAccount=False, senderAccountId=None, provenance=export_evidence,
        overlapWithSheet={'sameProfiles':len({r['profileId'] for r in export_rows}&conn_ids),
            'onlyInExports':len({r['profileId'] for r in export_rows}-conn_ids),
            'onlyInSheet':len(conn_ids-{r['profileId'] for r in export_rows}),
            'treatment':'Do not sum snapshots or their daily person attributes. Membership/source freshness differs.'},
        notes=['These exports are selected people and first/last attributes, not complete messages/replies/invitation events.',
            'File modification time is not an authenticated upstream export or sync time.',
            'No sender/account ID is present; owner identified the Charles workflow. No account-wide claim or cohort acceptance rate is supported.'])
    patch = {'snapshotAt':stamp,'sheetSubset':subset,'sheetSubsetCollectedAt':stamp,
        'sheetSubsetUpstreamSyncAt':None,'sheetSubsetAccountVerification':{'senderAccountId':None,'independentlyVerified':False,
            'basis':'User-identified Charles workflow; workbook has no sender account ID.'}, 'selectedExportSnapshot':exports}
    (PRIVATE/'sheets_video_patch.json').write_text(json.dumps(video,indent=2)+'\n')
    (PRIVATE/'waalaxy_patch.json').write_text(json.dumps(patch,indent=2)+'\n')
    report = {'snapshotAt':stamp,'video':summary,'videoDelta':delta,'connectionDiagnostics':video['connectionDiagnostics'],
        'sheetSubset':subset['metrics'],'selectedExports':exports['metrics'],'populationOverlap':exports['overlapWithSheet'],
        'datedStatusCounts':dict(Counter((r['date']+' '+r['type']) for r in dated))}
    (PRIVATE/'sheets_review_summary.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    build()
