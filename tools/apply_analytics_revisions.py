"""Apply scoped, evidence-backed corrections without replacing unrelated feeds."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import argparse
import csv
import hashlib
import json
from prepare_shared_snapshot import curate_snapshot

ROOT = Path(__file__).resolve().parents[1]

def apply(invitations_csv=None, referrals_json=None, fireflies_json=None):
    target = ROOT/'data/shared-dashboard.json'
    d = json.loads(target.read_text())
    before = json.dumps(d, sort_keys=True)
    now = datetime.now(timezone.utc).isoformat()
    audit = []
    if invitations_csv:
        p = Path(invitations_csv)
        with p.open(encoding='utf-8-sig', newline='') as f:
            rows = [{'date':datetime.strptime(r['Date'], '%a %b %d %Y').date().isoformat(),
                     'invitationsSent':int(r['Sent']), 'invitationsAccepted':int(r['Accepted'])}
                    for r in csv.DictReader(f)]
        assert rows and len(rows)==len({r['date'] for r in rows})
        assert all(r['invitationsSent']>=0 and r['invitationsAccepted']>=0 for r in rows)
        rows.sort(key=lambda r:r['date'])
        start, end = rows[0]['date'], rows[-1]['date']
        complete_days = (datetime.fromisoformat(end)-datetime.fromisoformat(start)).days+1 == len(rows)
        w = d['waalaxy']
        w.setdefault('historicalCoverage', {'start':'2024-12-13','end':'2026-06-26'})
        w.setdefault('historicalSnapshotAt', '2026-07-06')
        by_day = {r['date']:r.copy() for r in w.get('daily',[])}
        for r in rows: by_day.setdefault(r['date'], {'date':r['date']}).update(r)
        w['daily'] = [by_day[k] for k in sorted(by_day)]
        # The export's final date was collected while that date was partial.
        w['invitationCoverage'] = {'start':start,'end':end,'complete':complete_days,
            'sourceDays':len(rows),'zeroActivityDatesConfirmed':True,'currentDayPartial':True,
            'completeDaysThrough':(datetime.fromisoformat(end)-timedelta(days=1)).date().isoformat(),'sourceTimezone':None,
            'sourceDateBasis':'Source export calendar days; timezone not supplied',
            'accountEvidence':'Attributed to Charles by the prior contributor; this aggregate CSV has no account identifier.',
            'sourceFilename':p.name,'sourceSha256':hashlib.sha256(p.read_bytes()).hexdigest()}
        w['invitationSummary'] = {'sent':sum(r['invitationsSent'] for r in rows),
            'accepted':sum(r['invitationsAccepted'] for r in rows),
            'cohortAcceptanceRate':None,'basis':'Actions occurring in the same source window, not a matched invitation cohort.'}
        w['notes'] = [n for n in w.get('notes',[]) if '28% accept rate' not in n]
        note = f'Invitation import contains {len(rows)} source days, including explicit zeros, from {start} through {end}. The final source day is partial; timezone and account ID are absent from the export. Acceptances may concern earlier invitations, so no cohort acceptance rate is asserted.'
        if note not in w['notes']:w['notes'].append(note)
        audit.append('Waalaxy invitation dates and explicit zero days reconciled to retained CSV; historical person flags unchanged.')
    if referrals_json:
        ref = json.loads(Path(referrals_json).read_text())
        assert ref.get('records') and ref.get('snapshotAt')
        d['referrals'] = ref
        audit.append('Referral snapshot replaced by fully paginated, explicitly pipeline-filtered source reconciliation.')
    if fireflies_json:
        ledger = json.loads(Path(fireflies_json).read_text())
        assert 'records' in ledger and ledger.get('snapshotAt')
        ledger.pop('sourceEvidence', None)  # Private fingerprints remain in retained review input.
        m = d['meetings']
        m['fireflies'] = ledger
        # Discard imported domain-only classifications as commercial outcome totals.
        for k in ('firefliesRecordings','firefliesBdCalls','firefliesClientCalls','firefliesInternalCalls'):
            m['summary'].pop(k, None)
        m['summary']['firefliesReviewedRecordings'] = len(ledger['records'])
        m['notes'] = [n for n in m.get('notes',[]) if '19 recordings classified' not in n and 'Attendance is verified by recording presence' not in n]
        note = 'A separately dated Fireflies evidence ledger is displayed below the calendar. Purpose, recording existence, participant attendance, qualification and source attribution are separate claims. No calendar or commercial held-call KPI is filled from an unlinked recording.'
        if note not in m['notes']:m['notes'].append(note)
        audit.append('Fireflies purpose and identity evidence exposed separately from unverified commercial meeting KPIs.')
    for src in d['sources']:
        if src['id']=='waalaxy' and d['waalaxy'].get('invitationCoverage'):
            src.update(status='Partial current invitation export',method='Retained Charles-attributed daily invitation CSV plus historical prospect flags',
                note='September 15–October 15 invitation actions are available, including zero days; final day partial and timezone unspecified. Messages, replies and historical person flags have separate coverage.')
        if src['id']=='referrals' and referrals_json:
            ref=d['referrals'];s=ref['summary']
            src.update(asOf=ref['snapshotAt'],status='Current referral snapshot',
                method='Fully paginated read-only Pipedrive inventory; explicit client-side pipeline filtering',
                coverage=f"{s['totalPipelineDeals']} source records; {s['activeReferralDeals']} active non-test relationship records",
                note='Current positions, not dated referral requests or qualified outcomes. Independently refreshed from the older all-account CRM snapshot; exclusion partitions are shown in Referrals.')
    if fireflies_json:
        d['sources']=[s for s in d['sources'] if s['id']!='fireflies']
        ledger=d['meetings']['fireflies']
        d['sources'].append({'id':'fireflies','name':'Fireflies · recording evidence','status':'Current reviewed recording evidence',
            'asOf':ledger['snapshotAt'],'coverage':f"{len(ledger['records'])} previously supplied recording IDs reviewed; separate bounded scan of 100 indexed records",
            'method':'Read-only recording metadata and limited purpose/identity reconciliation',
            'note':'Supporting evidence, not another acquisition vector. Index dates are not verified meeting dates; classifications and unresolved joins remain visible.'})
    public=curate_snapshot(d)
    # Replaying identical inputs must not duplicate events, notes or revision records.
    if json.dumps(public,sort_keys=True)!=before:
        public['meta']['generatedAt']=now
        public['meta']['asOfDate']=datetime.fromisoformat(now).astimezone(ZoneInfo('America/Denver')).date().isoformat()
        public['meta']['analyticsRevisedAt']=now
        public['meta']['lastRevisionNote']='Supported analytics corrections; individual source collection dates retained.'
        target.write_text(json.dumps(public,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'updated':json.dumps(public,sort_keys=True)!=before,'changes':audit}))

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--invitations-csv',type=Path)
    p.add_argument('--referrals-json',type=Path)
    p.add_argument('--fireflies-json',type=Path)
    a=p.parse_args()
    if not any(vars(a).values()):p.error('Supply one or more explicit source inputs; unrelated feeds are retained.')
    apply(a.invitations_csv,a.referrals_json,a.fireflies_json)

if __name__=='__main__':main()
