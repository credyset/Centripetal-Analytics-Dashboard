"""Retain the verified Campaign Manager aggregate without inventing daily data.

Observed read-only through Charles's native Chrome and independently through
the accessible Chrome extension account. The configured daily CSV download
stalled and no new file was found. Observation time is known to the date only.
"""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
PRIVATE=ROOT/'data/private/refresh_2026_10_21'
baseline=json.loads((PRIVATE/'dashboard_before_refresh.json').read_text())['ads']
observations={'A':(433.35,2309,9,4,0),'B':(158.96,693,3,2,0),
              'C':(1000,6431,34,31,3),'D':(1000,5188,26,25,1),'E':(1000,10434,34,0,0)}
rows=[]
for c in baseline['campaigns']:
    spend,impressions,clicks,opens,leads=observations[c['code']]
    rows.append({**{k:c[k] for k in ('id','code','name','objective')},
        'spend':spend,'impressions':impressions,'clicks':clicks,'opens':opens,'leads':leads})
review={'accountId':'515259390','checkedAt':'2026-10-21','collectedAt':'2026-10-21',
    'observationTimePrecision':'date_only','coverage':{'start':'2026-09-04','end':'2026-10-22',
        'sourceTimezone':'UTC','finalDayPartial':True},
    'scope':'All seven ad sets in the observed account reporting view; five have delivery and two older Megadata ad sets have no delivery in this source window',
    'totals':{'spend':3592.31,'impressions':25055,'clicks':106,'rawLeads':4,'formOpens':62,
        'platformConversions':5,'platformAppointments':1,'qualifiedLeads':None,'heldProspectCalls':None},
    'adSets':rows,'zeroDeliveryOlderAdSets':2,
    'method':'Read-only native Charles Chrome aggregate, independently corroborated through the accessible Campaign Manager extension view',
    'dailyExportAvailable':False,'warnings':[
        'The fixed September 4–October 22 UTC source window includes a partial final UTC day. These totals are not this week or October-only performance.',
        'Five delivering ad sets reconcile to the observed totals; two older Megadata ad sets have no delivery in this window. Ad-set IDs/names are matched to the retained export.',
        'Daily Ad Set Performance / All columns / broken out by day was configured, but the export download stalled and no new file was found. The retained daily export still ends October 16 UTC; later daily buckets remain unknown.',
        'The four source-reported lead submissions do not establish their current identities, qualification or attendance. The existing owner-reviewed lead register retains its separate provenance.',
        'Five platform conversions and one platform appointment are platform tracking events, not independently verified held meetings, accepted opportunities, signed agreements or new clients.'
    ]}
for field,sourcefield in [('spend','spend'),('impressions','impressions'),('clicks','clicks'),('formOpens','opens'),('rawLeads','leads')]:
    assert abs(sum(r[sourcefield] for r in rows)-review['totals'][field])<0.001
(PRIVATE/'ads_browser_patch.json').write_text(json.dumps(review,indent=2)+'\n')
print('Ads browser aggregate: seven-ad-set scope and five delivering ad-set totals reconciled; daily source unchanged.')
