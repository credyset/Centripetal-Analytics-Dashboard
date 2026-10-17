"""Apply a retained, signed-in Charles creator analytics observation.

Collection is through the owner-designated Chrome UI. This script normalizes
the minimal retained evidence only; it does not access browser sessions or APIs.
"""
import copy
import json
from pathlib import Path
from prepare_shared_snapshot import curate_snapshot

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'data/private/charles_creator_2026-10-16/observed_7_days.json'


def normalize(source):
    current=copy.deepcopy(source)
    assert current['account']['identityVerified']
    assert current['account']['profileUrl']=='https://www.linkedin.com/in/solomoncharles/'
    assert current['coverage']['sourceTimezone']=='UTC' and current['chart']['display']=='Cumulative'
    cumulative=0
    daily=[]
    for point in current['chart']['points']:
        value=point['cumulativeImpressions']-cumulative
        assert value>=0
        daily.append({'date':point['date'],'account':'Charles Solomon','impressions':value,
            'engagements':None,'sourceId':'charles_creator_current','sourceTimezone':'UTC',
            'currentDayPartial':point['date']==current['coverage']['end'],
            'derivation':'First difference of the source cumulative chart'})
        cumulative=point['cumulativeImpressions']
    assert cumulative==current['summary']['impressions']
    assert sum(current['summary'][k] for k in ('reactions','comments','reposts','saves','sendsOnLinkedIn'))==current['summary']['socialEngagements']
    current['daily']=daily
    return current


def build():
    creator=normalize(json.loads(SOURCE.read_text()))
    target=ROOT/'data/shared-dashboard.json'
    data=json.loads(target.read_text());content=data['content']
    content.setdefault('historicalCoverage',copy.deepcopy(content['coverage']))
    content['creatorAnalytics']=creator
    content['snapshotAt']=creator['snapshotAt']
    content['status']='current_creator_snapshot_with_historical_reference'
    rows={(r['account'],r['date']):r for r in content['daily']}
    for row in creator['daily']:rows[(row['account'],row['date'])]=row
    content['daily']=sorted(rows.values(),key=lambda r:(r['date'],r['account']))
    content['accessReview'].update(status='current_charles_creator_access',checkedAt=creator['checkedAt'],
        reason='Owner-designated Centreptal Advisors x RedySet Chrome window is signed in as Charles Solomon. Current personal creator analytics are accessible; company/private boosted breakdowns were not collected.',
        currentCharlesPrivateCoverage=creator['coverage'])
    content['accessReview'].setdefault('historicalPrivateCharlesCoverageEnd','2026-09-10')
    content['accessReview']['newestPrivateCharlesCoverageEnd']=creator['coverage']['end']
    if content.get('review',{}).get('kind')!='signed_in_charles_creator':
        content.setdefault('historicalPublicReview',copy.deepcopy(content.get('review',{})))
    content['review']={'kind':'signed_in_charles_creator','snapshotAt':creator['snapshotAt'],
        'identityVerified':True,'sourceWindow':creator['coverage'],
        'scope':'7-day personal creator view only; company/private boosted analytics not collected'}
    content['publicObservations']['notes']=[
        'These public observations came from a visitor view; their counters exclude private analytics. Charles’s separate signed-in creator snapshot is shown above.'
        if 'The current authenticated account is Christian Wutz.' in n else n
        for n in content['publicObservations'].get('notes',[])]
    content['notes']=[n for n in content['notes'] if 'Current private analytics' not in n and 'current private analytics' not in n and 'Current Charles/profile and company admin analytics were unavailable' not in n]
    content['notes']=[n.replace('Charles’s latest on-disk aggregate covers', 'Historical private exports: Charles’s aggregate covers') for n in content['notes']]
    note='Current signed-in Charles creator analytics cover October 11–17 UTC; the final UTC day is partial. Historical exports, daily impressions, fixed-window social totals and public observations retain separate scopes.'
    if note not in content['notes']:content['notes'].append(note)
    src=next(s for s in data['sources'] if s['id']=='content')
    src.update(status='Current Charles creator snapshot; historical company reference',asOf=creator['snapshotAt'],
        checkedAt=creator['checkedAt'],coverage='Charles creator October 11–17 UTC (final day partial); historical export and public observation windows remain separate',
        method='Read-only signed-in Charles Chrome creator analytics plus retained exports and public observations',
        note='Charles identity verified in the owner-designated Chrome profile. 4,635 impressions, 2,250 members reached and 82 social engagements in the fixed 7-day UTC window. Daily impressions are derived from its cumulative chart; daily engagements, wider-window private data, current company analytics and organic/sponsored separation remain incomplete.')
    output=curate_snapshot(data)
    text=json.dumps(output,ensure_ascii=False,indent=2)+'\n'
    target.write_text(text)
    (ROOT/'data/dashboard.json').write_text(text)
    print(json.dumps({'account':creator['account']['name'],'coverage':creator['coverage'],
        'impressions':creator['summary']['impressions'],'socialEngagements':creator['summary']['socialEngagements']}))


if __name__=='__main__':build()
