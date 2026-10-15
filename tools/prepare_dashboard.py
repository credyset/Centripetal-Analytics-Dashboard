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
referrals = read('empty')['referrals']  # Placeholder until referral import semantics are agreed.
result = {
    'meta': {
        'generatedAt': now.isoformat(), 'asOfDate': now.astimezone(ZoneInfo('America/Denver')).date().isoformat(),
        'timezone': 'America/Denver', 'scope': 'Charles Solomon and Centripetal Advisors',
        'concept': True, 'autoRefreshEnabled': False,
        'weekStartsOn': 'Monday',
        'note': 'Local concept using actual dated snapshots. Automatic collection and private deployment are not enabled.',
    },
    'ads': ads, 'crm': crm, 'video': video, 'waalaxy': waalaxy, 'content': content, 'referrals': referrals,
    'sources': [
        {'id':'ads','name':'LinkedIn Ads','status':'Audited snapshot', 'asOf':'2026-10-13',
         'coverage':'September 4–October 12, 2026', 'method':'Reconciled Campaign Manager exports',
         'note':'39 daily source buckets (UTC). Lead quality reflects October 13 owner confirmation. Paid daily buckets retain the platform timezone.'},
        {'id':'crm','name':'Pipedrive','status':'Current snapshot','asOf':crm['snapshotAt'],
         'coverage':'All accessible non-deleted deals and activities, paginated across all owners',
         'method':'Read-only API collection',
         'note':'No stage-history reconstruction or independently verified bookings/held calls. Test records excluded from business KPIs; all open deal values unpopulated.'},
        {'id':'video','name':'Video DMs','status':'Current snapshot','asOf':video['snapshotAt'],
         'coverage':f"{video['summary']['sourceRows']} source prospect rows; status inventory", 'method':'Read-only Google Sheets collection',
         'note':'Snapshot status counts are not period sends. Loom presence is not proof of delivery. Four profile gaps and six duplicate profiles require review.'},
        {'id':'waalaxy','name':'Waalaxy · Charles','status':'Historical export','asOf':waalaxy.get('snapshotAt'),
         'coverage':waalaxy.get('coverage'), 'method':'Verified Charles prospect export',
         'note':'Historical person flags, not period message totals. Current browser is signed in to Christian; that unrelated account was excluded.'},
        {'id':'content','name':'LinkedIn content','status':'Historical export','asOf':content.get('snapshotAt'),
         'coverage':content.get('coverage'), 'method':'Charles personal analytics and company-page exports',
         'note':'Charles daily analytics end September 10, 2026. Company-page baseline is 2025. Top-ranked posts are not a complete publishing register. Current profile/page admin access unavailable in this browser session.'},
        {'id':'referrals','name':'Referrals','status':'Data needed','asOf':None,
         'coverage':'No referral dataset supplied','method':'Awaiting owner-supplied spreadsheet or export',
         'note':'Dedicated placeholder; no referral activity, introductions or outcomes inferred from CRM stage inventory.'},
    ],
}
assert abs(sum(r['spend'] for r in ads['daily'])-3056.57)<0.02
assert len(crm['deals'])==len({r['id'] for r in crm['deals']})
assert len(crm['activities'])==len({r['id'] for r in crm['activities']})
assert video['summary']['sourceRows']==len(video['rows'])
out = DATA / 'dashboard.json'
out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
print(json.dumps({'output':str(out),'bytes':out.stat().st_size,'generatedAt':now.isoformat(),
                  'sources':len(result['sources']),'ads_days':len(ads['daily']),
                  'crm_deals':len(crm['deals']),'crm_activities':len(crm['activities']),
                  'video_rows':len(video['rows'])},indent=2))
