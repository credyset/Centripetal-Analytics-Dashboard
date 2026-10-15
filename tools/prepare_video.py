"""Prepare a labelled Video DM snapshot; never infer delivery from a Loom link."""
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter, defaultdict
from urllib.parse import unquote
import hashlib, json, re

BASE = Path(__file__).resolve().parent.parent
raw = json.loads((BASE / 'data/private/video_sheet.json').read_text())['values']
connection_raw = json.loads((BASE / 'data/private/video_connections.json').read_text())['values']
manifest_path = BASE / 'data/private/video_manifest.json'
manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
now = manifest.get('snapshotAt') or datetime.now(timezone.utc).isoformat()
header = raw[0]
rows = []
groups = defaultdict(list)
dated = []
for line, values in enumerate(raw[1:], 2):
    r = dict(zip(header, values))
    company, contact = str(r.get('org', '')).strip(), str(r.get('contact', '')).strip()
    if not company or not contact or (company == 'org' and contact == 'contact'):
        continue
    url = str(r.get('li', '')).strip()
    match = re.search(r'linkedin\.com/in/([^/?#]+)', unquote(url), re.I)
    key = match.group(1).lower().rstrip('/') if match else ''
    status = str(r.get('Status (CS Column)', '')).strip()
    item = {
        'id': key or hashlib.sha256((company+'|'+contact).lower().encode()).hexdigest()[:16],
        'sourceRow': line, 'company': company, 'contact': contact,
        'linkedin': 'https://www.linkedin.com/in/'+key+'/' if key else '',
        'status': status, 'loom': str(r.get('Loom Link', '')).strip(),
        'reply': str(r.get('Response Status', '')).strip(),
        'connected': str(r.get('Connected?', '')).lower() in ('true','yes','connected'),
        'connectedAt': r.get('Connected At', ''), 'action': r.get('DM Action', ''),
        'followUp': r.get('Follow-up Action', ''), 'dealId': r.get('deal_id', ''),
        'explicitSendStatus': status.lower() in ('sent','done'),
    }
    rows.append(item)
    if key: groups[key].append(item)
    dated_match = re.search(r'(\d{1,2})/(\d{1,2})/(\d{2,4})', status)
    if dated_match:
        month, day, year = map(int, dated_match.groups()); year += 2000 if year < 100 else 0
        try: date = datetime(year, month, day).date().isoformat()
        except ValueError: continue
        action = 'Follow-up status' if re.match(r'f/?u|follow',status,re.I) else 'Send status'
        dated.append({'date': date, 'contactId': item['id'], 'type': action, 'sourceRow': line})

actions = Counter(r['action'] for r in rows)
duplicates = [{'profile': k, 'rows': [r['sourceRow'] for r in rs],
               'actions': sorted(set(r['action'] for r in rs))}
              for k, rs in groups.items() if len(rs) > 1]
conflicts = [d for d in duplicates if len(d['actions']) > 1]
conn_header = connection_raw[0]
connections = [dict(zip(conn_header,r)) for r in connection_raw[1:] if r]
history = []
for path in (BASE / 'data/history').glob('video_*.json'):
    previous = json.loads(path.read_text())
    if previous.get('snapshotAt', '') < now:
        history.append(previous)
previous = max(history, key=lambda r: r['snapshotAt']) if history else None
delta = None
if previous:
    # A separately confirmed URL/name repair changes the profile-based identity key.
    # Reconcile only the explicitly identified source rows; it is not prospect acquisition.
    old_rows_by_source = {r['sourceRow']: r for r in previous['rows']}
    new_rows_by_source = {r['sourceRow']: r for r in rows}
    repair_rows = set(manifest.get('knownSourceCorrections', {}).get('sourceRows', []))
    identity_repairs = {rownum for rownum in repair_rows
                        if rownum in old_rows_by_source and rownum in new_rows_by_source
                        and old_rows_by_source[rownum]['id'] != new_rows_by_source[rownum]['id']
                        and old_rows_by_source[rownum]['company'] == new_rows_by_source[rownum]['company']}
    normalized_old_rows = [dict(r, id=new_rows_by_source[r['sourceRow']]['id'])
                           if r['sourceRow'] in identity_repairs else r for r in previous['rows']]
    old_ids, new_ids = Counter(r['id'] for r in normalized_old_rows), Counter(r['id'] for r in rows)
    old_by = defaultdict(list)
    new_by = defaultdict(list)
    for r in normalized_old_rows: old_by[r['id']].append(r)
    for r in rows: new_by[r['id']].append(r)
    comparable = {key for key in old_by.keys() & new_by.keys()
                  if len(old_by[key]) == len(new_by[key]) == 1}
    delta = {
        'basis': 'first-observed snapshot difference',
        'fromSnapshotAt': previous['snapshotAt'], 'toSnapshotAt': now,
        'newProfileIdsObserved': len(new_ids.keys() - old_ids.keys()),
        'removedProfileIdsObserved': len(old_ids.keys() - new_ids.keys()),
        'identityCorrectionsObserved': len(identity_repairs),
        'additionalRowsObserved': sum((new_ids - old_ids).values()),
        'rowsNoLongerObserved': sum((old_ids - new_ids).values()),
        'explicitSentDoneStatusChangesObserved': sum(
            not old_by[key][0]['explicitSendStatus'] and new_by[key][0]['explicitSendStatus']
            for key in comparable),
        'statusChangesObserved': sum(old_by[key][0]['status'] != new_by[key][0]['status'] for key in comparable),
        'derivedActionClassificationChangesObserved': sum(old_by[key][0]['action'] != new_by[key][0]['action'] for key in comparable),
        'comparableUniqueIdentityCount': len(comparable),
        'note': 'First observed between retained snapshots; not actual row creation or sending dates. Confirmed profile URL/name repairs are reconciled as identity corrections, not new prospects or removed rows. Duplicate identities are excluded from status-change counts. Derived helper action changes are separate from Charles status changes.',
    }
result = {
    'snapshotAt': now, 'status': 'available',
    'coverage': 'Current status snapshot; row-added and video-sent dates are not consistently recorded',
    'sourceUrl': 'https://docs.google.com/spreadsheets/d/1_Vq5-hM3POad1V14rZjX6gfaUojUnnTvxjjSv1zDJ8M/edit',
    'rows': rows, 'datedActions': dated,
    'snapshotDelta': delta,
    'sourceCoverage': {'method': manifest.get('method', 'retained source snapshot'),
                       'complete': manifest.get('complete'),
                       'ranges': manifest.get('ranges', [])},
    'summary': {
        'sourceRows': len(rows), 'uniqueProfiles': len(groups),
        'rowsMissingProfile': sum(not r['linkedin'] for r in rows),
        'readyRows': actions['Ready for video DM'],
        'sheetCompletedRows': actions['Already sent/completed'],
        'explicitSendStatusRows': sum(r['explicitSendStatus'] for r in rows),
        'followUpRows': sum(r['followUp']=='Follow-up Needed' for r in rows),
        'manualCheckRows': sum(r['followUp']=='Manual Check' for r in rows),
        'reviewRows': actions['Review'], 'awaitingConnectionRows': actions['Awaiting connection'],
        'skipRows': actions['Skip'], 'duplicates': len(duplicates),
        'duplicateExtraRows': sum(len(d['rows'])-1 for d in duplicates),
        'conflictingProfiles': len(conflicts),
        'acceptedConnectionRecords': len(connections),
        'connectedRows': sum(r['connected'] for r in rows),
        'rowsWithDealId': sum(bool(r['dealId']) for r in rows),
        'newRowsInPeriod': None,
    },
    'duplicateProfiles': duplicates,
    'notes': [
        'Status totals count source rows. Unique profiles deduplicate valid normalized LinkedIn URLs; rows without a valid profile remain unresolved.',
        'Spreadsheet sent/completed includes a Loom link or exact Sent/Done status. A Loom link alone does not establish delivery.',
        'Explicit Sent/Done is a self-reported status, not independently verified delivery. Undated sends cannot be assigned to the selected period.',
        'Follow-up categories overlap the main status categories; do not add them to the prospect total.',
        'Historical row-added/sent dates remain unavailable; compare first-observed changes between retained snapshots. Profile URL/name corrections are not new prospects or sends.',
        'Connection dates and automation message dates are not Video DM send dates. The status snapshot is unaffected by the date filter.',
    ],
}
assert len(rows)==sum(actions.values())
assert len({r['sourceRow'] for r in rows})==len(rows)
(BASE/'data/video.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result['summary'],indent=2))
