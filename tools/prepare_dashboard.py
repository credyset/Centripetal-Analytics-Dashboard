"""Assemble the local concept from normalized, traceable source snapshots."""
from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import json

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / 'data'
def read(name):
    return json.loads((DATA / (name+'.json')).read_text())
now = datetime.now(timezone.utc)
ads, crm, video, waalaxy, content = (read(k) for k in ('ads','crm','video','waalaxy','content'))
meetings = read('meetings') if (DATA / 'meetings.json').exists() else None
if meetings:
    # Calendar identity matches corroborate bookings, without changing the
    # separately owner-confirmed qualification or implying attendance.
    for proof in meetings.get('verifiedLinks', []):
        if proof.get('inviteeMatch') != 'exact_name_and_email':
            continue
        matches = [lead for lead in ads['leads']
                   if lead['company'].strip().casefold() == proof['company'].strip().casefold()]
        assert len(matches) <= 1, 'Resolve repeated company submissions by person before linking'
        for lead in matches:
            lead.update(meetingBooked=True, meetingHeld=None,
                        bookingCorroboration={**proof, 'verifiedAt': meetings['snapshotAt'], 'source': 'Calendly'})
referrals = read('empty')['referrals']  # Placeholder until referral import semantics are agreed.
result = {
    'meta': {
        'generatedAt': now.isoformat(), 'asOfDate': now.astimezone(ZoneInfo('America/Denver')).date().isoformat(),
        'timezone': 'America/Denver', 'scope': 'Charles Solomon and Centripetal Advisors',
        'concept': True, 'autoRefreshEnabled': False,
        'weekStartsOn': 'Monday',
        'note': 'Local concept using actual dated snapshots. Automatic collection and private deployment are not enabled.',
    },
    'ads': ads, 'crm': crm, 'video': video, 'waalaxy': waalaxy, 'content': content, 'referrals': referrals, 'meetings': meetings,
    'sources': [
        {'id':'ads','name':'LinkedIn Ads','status':ads.get('status','Dated export'), 'asOf':ads.get('collectedAt',ads.get('snapshotAt')),
         'coverage':ads.get('coverage'), 'method':'Reconciled Campaign Manager exports',
         'note':'Daily source buckets retain LinkedIn UTC dates. Lead quality reflects October 13 owner confirmation; later delivery data does not requalify leads.'},
        {'id':'crm','name':'Pipedrive','status':'Current snapshot','asOf':crm['snapshotAt'],
         'coverage':'All accessible non-deleted deals and activities, paginated across all owners',
         'method':'Read-only API collection',
         'note':'Paginated deal/activity inventory plus scoped structured history review. Test records excluded from business KPIs. CRM done/scheduled flags do not independently verify meetings or commercial advancement.'},
        {'id':'video','name':'Video DMs','status':'Current snapshot','asOf':video['snapshotAt'],
         'coverage':f"{video['summary']['sourceRows']} source prospect rows; status inventory", 'method':'Read-only Google Sheets collection',
         'note':f"Snapshot status counts are not period sends. Loom presence is not proof of delivery. {video['summary']['rowsMissingProfile']} profile gaps and {video['summary']['duplicates']} duplicate profiles require review."},
        {'id':'waalaxy','name':'Waalaxy · Charles','status':'Historical export','asOf':waalaxy.get('snapshotAt'),
         'coverage':waalaxy.get('coverage'), 'method':'Verified Charles prospect export',
         'note':'Historical person flags, not period message totals. Latest access check still found an unrelated Waalaxy account; its figures were excluded.',
         'checkedAt':waalaxy.get('accessReview',{}).get('checkedAt')},
        {'id':'content','name':'LinkedIn content','status':'Historical export','asOf':content.get('snapshotAt'),
         'coverage':content.get('coverage'), 'method':'Charles personal analytics and company-page exports',
         'note':'Private Charles daily analytics end September 10, 2026; company private baseline is 2025. Current public followers and a visible post sample are separately dated in Content. Private organic/boosted analytics remain inaccessible for these accounts.',
         'checkedAt':content.get('accessReview',{}).get('checkedAt')},
        {'id':'referrals','name':'Referrals','status':'Data needed','asOf':None,
         'coverage':'No referral dataset supplied','method':'Awaiting owner-supplied spreadsheet or export',
         'note':'Dedicated placeholder; no referral activity, introductions or outcomes inferred from CRM stage inventory.'},
    ],
}
if meetings:
    result['sources'].append({'id':'meetings','name':'Calendly · Charles','status':meetings.get('status','Current snapshot'),
        'asOf':meetings.get('snapshotAt'),'coverage':meetings.get('coverage'),
        'method':'Read-only calendar event and lifecycle collection',
        'note':'Shared booking evidence, not another acquisition vector. Calendar status does not verify commercial qualification or attendance.'})
assert abs(sum(r['spend'] for r in ads['daily'])-ads['totals']['spend'])<0.02
assert len(crm['deals'])==len({r['id'] for r in crm['deals']})
assert len(crm['activities'])==len({r['id'] for r in crm['activities']})
assert video['summary']['sourceRows']==len(video['rows'])
out = DATA / 'dashboard.json'
out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
print(json.dumps({'output':str(out),'bytes':out.stat().st_size,'generatedAt':now.isoformat(),
                  'sources':len(result['sources']),'ads_days':len(ads['daily']),
                  'crm_deals':len(crm['deals']),'crm_activities':len(crm['activities']),
                  'video_rows':len(video['rows'])},indent=2))
