"""Normalize retained read-only Sheets evidence without replacing older baselines.

The accepted-connections tab is a selected prospect snapshot, not account-wide
Waalaxy analytics or a complete message/acceptance event stream.
"""
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import unquote
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / 'data/private/sheets_refresh_2026-10-16'


def read(path):
    return json.loads(path.read_text())


def profile(value):
    m = re.search(r'linkedin\.com/in/([^/?#]+)', unquote(str(value or '')), re.I)
    return m.group(1).lower().rstrip('/') if m else None


def source(path):
    return {'path': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def date(value):
    value = str(value or '').strip()
    return value if re.fullmatch(r'\d{4}-\d{2}-\d{2}', value) else None


def yes(value):
    return str(value or '').strip().lower() in {'true', 'yes', 'connected'}


def records(data):
    header = data['values'][0]
    return [(i, dict(zip(header, values))) for i, values in enumerate(data['values'][1:], 2)]


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
    if re.match(r'sent\s+\d', value, re.I):
        return 'Dated send status recorded'
    return 'Other recorded status'


def build():
    manifest = read(PRIVATE / 'manifest.json')
    meta = read(PRIVATE / 'metadata.json')
    main = read(PRIVATE / 'video_sheet.json')
    connection_source = read(PRIVATE / 'connections.json')
    assert len(meta['sheets']) == len(manifest['ranges']) == 2
    assert meta['sheets'][0]['columnCount'] == 29 and meta['sheets'][1]['columnCount'] == 40
    assert len(main['values']) <= meta['sheets'][0]['rowCount']
    assert len(connection_source['values']) <= meta['sheets'][1]['rowCount']
    previous = read(ROOT / 'data/video.json')
    historical_waalaxy = read(ROOT / 'data/waalaxy.json')
    shared_waalaxy = read(ROOT / 'data/shared-dashboard.json')['waalaxy']
    rows = []
    dated = []
    groups = defaultdict(list)
    for line, r in records(main):
        company, contact = str(r.get('org') or '').strip(), str(r.get('contact') or '').strip()
        if not company or not contact or (company == 'org' and contact == 'contact'):
            continue
        key = profile(r.get('li'))
        status = str(r.get('Status (CS Column)') or '').strip()
        row = {'id': key or hashlib.sha256((company+'|'+contact).lower().encode()).hexdigest()[:16],
               'sourceRow': line, 'company': company, 'contact': contact,
               'linkedin': 'https://www.linkedin.com/in/'+key+'/' if key else '',
               'status': status_category(status), 'hasRecordingLink': bool(str(r.get('Loom Link') or '').strip()),
               'hasResponseStatus': bool(str(r.get('Response Status') or '').strip()),
               'connected': yes(r.get('Connected?')), 'connectedAt': date(r.get('Connected At')),
               'action': r.get('DM Action') or '', 'followUp': r.get('Follow-up Action') or '',
               'dealId': r.get('deal_id') or None,
               'explicitSendStatus': status.lower() in {'sent', 'done'},
               'syncedToPipedriveFlag': yes(r.get('Synced to Pipedrive'))}
        rows.append(row)
        if key:
            groups[key].append(row)
        stamp = re.search(r'(\d{1,2})/(\d{1,2})/(\d{2,4})', status)
        if stamp:
            from datetime import date as realdate
            month, day, year = map(int, stamp.groups())
            year += 2000 if year < 100 else 0
            try:
                day_string = realdate(year, month, day).isoformat()
            except ValueError:
                continue
            dated.append({'date': day_string, 'contactId': row['id'], 'sourceRow': line,
                          'type': 'Follow-up status' if re.match(r'f/?u|follow', status, re.I) else 'Send status',
                          'basis': 'self-reported dated status, not independently verified delivery'})
    actions = Counter(r['action'] for r in rows)
    duplicates = [{'profile': key, 'rows': [r['sourceRow'] for r in values],
                   'actions': sorted({r['action'] for r in values})}
                  for key, values in groups.items() if len(values) > 1]
    summary = {
        'sourceRows': len(rows), 'uniqueProfiles': len(groups),
        'rowsMissingProfile': sum(not r['linkedin'] for r in rows),
        'readyRows': actions['Ready for video DM'], 'sheetCompletedRows': actions['Already sent/completed'],
        'explicitSendStatusRows': sum(r['explicitSendStatus'] for r in rows),
        'followUpRows': sum(r['followUp'] == 'Follow-up Needed' for r in rows),
        'manualCheckRows': sum(r['followUp'] == 'Manual Check' for r in rows),
        'reviewRows': actions['Review'], 'awaitingConnectionRows': actions['Awaiting connection'],
        'skipRows': actions['Skip'], 'duplicates': len(duplicates),
        'duplicateExtraRows': sum(len(d['rows'])-1 for d in duplicates),
        'conflictingProfiles': sum(len(d['actions']) > 1 for d in duplicates),
        'acceptedConnectionRecords': len(connection_source['values'])-1,
        'connectedRows': sum(r['connected'] for r in rows),
        'rowsWithDealId': sum(bool(r['dealId']) for r in rows),
        'syncedToPipedriveFlagRows': sum(r['syncedToPipedriveFlag'] for r in rows),
        'newRowsInPeriod': None,
    }
    # Reconcile unique exact company/contact identities when a profile URL was
    # corrected. Otherwise a URL edit would look like a new and removed prospect.
    def identity(r):
        return (str(r['company']).strip().casefold(), str(r['contact']).strip().casefold())
    old_people, new_people = defaultdict(list), defaultdict(list)
    for r in previous['rows']:
        old_people[identity(r)].append(r)
    for r in rows:
        new_people[identity(r)].append(r)
    repair_map = {}
    for who in old_people.keys() & new_people.keys():
        if len(old_people[who]) == len(new_people[who]) == 1:
            old, new = old_people[who][0], new_people[who][0]
            if old['id'] != new['id']:
                repair_map[old['id']] = new['id']
    normalized_old = [dict(r, id=repair_map.get(r['id'], r['id'])) for r in previous['rows']]
    old_ids = Counter(r['id'] for r in normalized_old)
    new_ids = Counter(r['id'] for r in rows)
    old_by, new_by = defaultdict(list), defaultdict(list)
    for r in normalized_old:
        old_by[r['id']].append(r)
    for r in rows:
        new_by[r['id']].append(r)
    comparable = {key for key in old_by.keys() & new_by.keys() if len(old_by[key]) == len(new_by[key]) == 1}
    delta = {'basis': 'First observed between source snapshots; not creation/send timestamps',
             'fromSnapshotAt': previous['snapshotAt'], 'toSnapshotAt': manifest['snapshotAt'],
             'additionalRowsObserved': sum((new_ids-old_ids).values()),
             'rowsNoLongerObserved': sum((old_ids-new_ids).values()),
             'profileIdentityCorrectionsObserved': len(repair_map),
             'derivedActionClassificationChangesObserved': sum(old_by[k][0]['action'] != new_by[k][0]['action'] for k in comparable),
             'connectedFlagChangesObserved': sum(old_by[k][0]['connected'] != new_by[k][0]['connected'] for k in comparable),
             'explicitSentDoneStatusChangesObserved': sum(not old_by[k][0]['explicitSendStatus'] and new_by[k][0]['explicitSendStatus'] for k in comparable),
             'comparableUniqueIdentityCount': len(comparable),
             'note': 'Unique exact company/contact matches reconcile corrected profile keys before row-change counts. Comparable status changes exclude duplicate identities; these are observed differences, not creation or sending events.',
             'summaryChanges': {k: summary[k]-previous['summary'].get(k, 0) for k in ['sourceRows', 'uniqueProfiles', 'readyRows', 'sheetCompletedRows', 'explicitSendStatusRows', 'connectedRows', 'reviewRows', 'awaitingConnectionRows']}}
    provenance = [source(PRIVATE / f) for f in ['metadata.json', 'manifest.json', 'video_sheet.json', 'connections.json']]
    connections = []
    daily = defaultdict(Counter)
    for line, r in records(connection_source):
        key = profile(r.get('linkedinUrl'))
        if not key:
            continue
        entry = {'profileId': key, 'sourceRow': line, 'list': r.get('prospectList') or None,
                 'profileStatus': r.get('profileStatus') or None,
                 'messageSentFlag': yes(r.get('messageSent')), 'messageRepliedFlag': yes(r.get('messageReplied')),
                 'emailSentFlag': yes(r.get('emailSent')), 'emailRepliedFlag': yes(r.get('emailReplied')),
                 'connectedAt': date(r.get('connectedAt')), 'importDate': date(r.get('importDate')),
                 'connectionRequestDate': date(r.get('connectionRequestDate')),
                 'firstMessageAt': date(r.get('firstMessageAt')),
                 'lastMessageAt': date(r.get('lastLinkedinMessageSentDate')),
                 'lastReplyAt': date(r.get('lastLinkedinReplyDate')),
                 'matchedVideoProspect': key in groups}
        connections.append(entry)
        for field, label in [('connectedAt', 'connectionsRecorded'), ('connectionRequestDate', 'connectionRequestsFirstRecorded'),
                             ('firstMessageAt', 'firstMessageRecipients'), ('lastMessageAt', 'lastMessageRecipients'),
                             ('lastReplyAt', 'lastReplyingProspects'), ('importDate', 'prospectsImported')]:
            if entry[field]:
                daily[entry[field]][label] += 1
    assert len(connections) == len({r['profileId'] for r in connections}), 'Review duplicate connected profiles'
    assert summary['connectedRows'] == sum(r['matchedVideoProspect'] for r in connections) + sum(len(v)-1 for k, v in groups.items() if k in {r['profileId'] for r in connections})
    prior_connections = read(ROOT / 'data/private/video_connections.json')
    prior_conn_ids = {profile(r.get('linkedinUrl')) for _, r in records(prior_connections)}
    new_conn_ids = {r['profileId'] for r in connections}
    subset_metrics = {
        'connectedProspects': len(connections), 'videoDmListProspects': sum(r['list'] == 'Video DMs' for r in connections),
        'pulleyListProspects': sum(str(r['list']).startswith('Pulley Contacts') for r in connections),
        'matchedMainUniqueProfiles': sum(r['matchedVideoProspect'] for r in connections),
        'messageRecipientFlags': sum(r['messageSentFlag'] for r in connections),
        'replyingProspectFlags': sum(r['messageRepliedFlag'] for r in connections),
        'connectedAtKnown': sum(bool(r['connectedAt']) for r in connections),
        'connectedAtMissing': sum(not r['connectedAt'] for r in connections),
        'latestConnectedAt': max((r['connectedAt'] for r in connections if r['connectedAt']), default=None),
        'latestMessageDate': max((r['lastMessageAt'] for r in connections if r['lastMessageAt']), default=None),
        'latestReplyDate': max((r['lastReplyAt'] for r in connections if r['lastReplyAt']), default=None),
        'newlyObservedConnectedProfileIds': len(new_conn_ids-prior_conn_ids),
        'currentPeriodMessageEvents': None, 'currentPeriodReplyEvents': None,
        'acceptanceRate': None, 'accountWideProspects': None,
    }
    video = {'snapshotAt': manifest['snapshotAt'], 'status': 'available',
        'coverage': 'Complete current main tab and accepted-connection tab; snapshot inventory, not added/sent events.',
        'upstreamSyncAt': None, 'accountScope': manifest['accountAttribution'],
        'sourceUrl': 'https://docs.google.com/spreadsheets/d/'+manifest['spreadsheetId']+'/edit',
        'summary': summary, 'snapshotDelta': delta, 'rows': rows, 'datedActions': dated,
        'duplicateProfiles': duplicates, 'provenance': provenance,
        'notes': ['Sheet-classified completion includes recording-link presence; a recording link does not prove delivery.',
                  'Explicit Sent/Done remains a self-reported status, not verified sending in the selected period.',
                  'Synced to Pipedrive is a source flag; successful CRM identity synchronization is not independently verified here.',
                  'Collection freshness is separate from an unreported upstream export/sync timestamp.',
                  'Prepared refresh rows omit emails, phone numbers, source notes/hooks, response text and recording-access URLs.']}
    waalaxy = {'snapshotAt': manifest['snapshotAt'], 'status': 'available_scoped_sheet_subset',
        'account': 'Charles Solomon workflow', 'upstreamSyncAt': None,
        'accountVerification': {'senderAccountId': None, 'independentlyVerified': False,
            'basis': manifest['accountAttribution'], 'scope': 'Only this accepted-connections subset; no Christian/Jess account data imported.'},
        'sheetSubset': {'sourceSpreadsheetId': manifest['spreadsheetId'], 'sourceTabId': meta['sheets'][1]['sheetId'],
            'sourceTab': meta['sheets'][1]['title'], 'returnedDataRows': len(connections),
            'scope': 'Selected connected prospects: Video DMs and Pulley Contacts lists; not account-wide Waalaxy coverage.',
            'dateBasis': 'Source date-only first/last prospect attributes; timezone not supplied. These are not a complete event history.',
            'metrics': subset_metrics, 'rows': connections,
            'dailyPeopleAttributes': [{'date': d, **counts} for d, counts in sorted(daily.items())],
            'listCounts': dict(Counter(r['list'] for r in connections)),
            'collectionCompleteWithinTab': True, 'upstreamExportCompleteForAccount': False},
        'preservedSources': {'historicalCharlesBaseline': {'snapshotAt': historical_waalaxy['snapshotAt'],
                'coverage': historical_waalaxy['coverage'], 'metrics': historical_waalaxy['metrics'],
                'provenance': source(ROOT / 'data/waalaxy.json')},
            'datedInvitations': {'coverage': shared_waalaxy.get('invitationCoverage'), 'summary': shared_waalaxy.get('invitationSummary'),
                                'treatment': 'Retained unchanged; selected connected-person rows are not an invitation-event replacement.'}},
        'provenance': provenance,
        'notes': ['No live Waalaxy account API tool is exposed. The usable new source is the Google Sheets accepted-connections tab.',
                  'All current workbook tabs and allocated cell ranges were inspected; no linked source spreadsheet, sender-account column or upstream sync timestamp was found.',
                  'Connected prospects are a selected population; do not divide this subset by account invitations to infer acceptance rate.',
                  'messageSent/messageReplied flag people, not total sends/replies. First/last dates cannot reconstruct all messages or replies.',
                  'The legacy Charles prospect baseline and newer dated invitation source retain their own coverage and timestamps.',
                  'The source has no sender-account ID. It belongs to the user-identified Charles workflow, but should not be presented as a newly authenticated Charles account-wide export.']}
    (ROOT / 'data/video_refresh.json').write_text(json.dumps(video, indent=2) + '\n')
    (ROOT / 'data/waalaxy_refresh.json').write_text(json.dumps(waalaxy, indent=2) + '\n')
    print(json.dumps({'snapshotAt': manifest['snapshotAt'], 'video': summary,
                      'delta': delta, 'waalaxySubset': subset_metrics}, indent=2))


if __name__ == '__main__':
    build()
