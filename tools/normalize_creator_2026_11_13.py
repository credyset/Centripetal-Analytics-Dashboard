"""Normalize the verified November 13 Charles XLSX, Creator UI, and Profile Views independently."""
from copy import deepcopy
from datetime import datetime, timedelta, date
from itertools import accumulate
from pathlib import Path
import hashlib
import json
import re

import openpyxl

ROOT=Path(__file__).resolve().parents[1]
DIR=ROOT/'data/private/refresh_2026_11_13/linkedin'


def write(name,obj):
    p=DIR/name
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
    p.chmod(0o600)


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def n(v):
    assert v is not None and str(v).strip()!=''
    x=int(str(v).replace(',',''))
    assert x>=0
    return x


def day(v):
    return datetime.strptime(v,'%m/%d/%Y').date().isoformat()


def build():
    file=DIR/'creator.xlsx'; ui_file=DIR/'browser_observations.json'
    raw=json.loads(ui_file.read_text());ui=raw['creator']; p=raw['profile']
    baseline=DIR/'baseline_previous_creator.json'
    if not baseline.exists():
        write(baseline.name,json.loads((ROOT/'data/shared-dashboard.json').read_text())['content']['creatorAnalytics'])
    previous=json.loads(baseline.read_text())
    assert ui['account']=='Charles Solomon' and ui['profile'].rstrip('/')=='https://www.linkedin.com/in/solomoncharles'
    assert ui['preset']=='90 days' and ui['sourceTimezone']=='UTC'
    book=openpyxl.load_workbook(file,read_only=True,data_only=True)
    sheet=lambda name:list(book[name].values)
    discovery=dict(sheet('DISCOVERY'))
    start,end=map(day,discovery['Overall Performance'].split(' - '))
    assert (start,end)==(ui['start'],ui['end'])==('2026-08-16','2026-11-13')
    exp=sheet('ENGAGEMENT'); assert tuple(exp[0])==('Date','Impressions','Engagements')
    daily=[{'date':day(x[0]),'impressions':n(x[1]),'engagements':n(x[2])} for x in exp[1:]]
    dates=[(date.fromisoformat(start)+timedelta(days=i)).isoformat() for i in range(90)]
    assert [x['date'] for x in daily]==dates and dates[-1]==end
    assert list(accumulate(r['impressions'] for r in daily))==ui['cumulative']
    assert ui['cumulative'][-1]==ui['impressions']==n(discovery['Impressions'])
    assert ui['membersReached']==n(discovery['Members reached'])
    fixed=['impressions','membersReached','socialEngagements','reactions','comments','reposts','saves','sendsOnLinkedIn','linkEngagements','premiumCustomButtonEngagements','visitsToLinksInAllPosts','inNetworkPercent','outOfNetworkPercent']
    summary={k:ui[k] for k in fixed}
    summary['exportEngagements']=sum(r['engagements'] for r in daily)
    assert sum(ui[k] for k in ['reactions','comments','reposts','saves','sendsOnLinkedIn'])==ui['socialEngagements']
    assert ui['premiumCustomButtonEngagements']+ui['visitsToLinksInAllPosts']==ui['linkEngagements']
    ranked={}; counts={}
    def post_id(url):
        typ,raw_id=re.search(r'(ugcPost|share)-(\d+)',url).groups()
        return f'{typ}:{raw_id}'
    for offset,metric in [(0,'engagements'),(4,'impressions')]:
        count=0
        for r in sheet('TOP POSTS')[3:]:
            if not r[offset]:continue
            url=r[offset]; key=post_id(url); published=day(r[offset+1]);count+=1
            post=ranked.setdefault(key,{'postId':key,'url':url,'publishedAt':published,'account':'Charles Solomon',
                'impressions':None,'engagements':None,'impressionRank':None,'engagementRank':None})
            assert post['publishedAt']==published
            post[metric]=n(r[offset+2]);post['impressionRank' if offset==4 else 'engagementRank']=count
        counts[metric]=count
    assert max(counts.values())<=50
    top=[]
    titles=['AppWork acquisition of Paraspot AI','Venture capital and AI startups','Pulley closure and cap-table migration']
    for rank,(identity,activity,impressions,engagements) in enumerate(ui['top'],1):
        post=ranked[identity];assert post['impressions']==impressions and post['impressionRank']==rank
        assert post['engagements'] in [None,engagements]
        top.append({'postId':identity,'activityId':activity,'title':titles[rank-1],
            'titleBasis':'Short topic label using prior verified identity and/or current source URL slug.',
            'url':f'https://www.linkedin.com/feed/update/urn:li:{identity}/',
            'analyticsUrl':f'https://www.linkedin.com/analytics/post-summary/urn:li:activity:{activity}/',
            'impressions':impressions,'engagements':engagements,'publishedAt':post['publishedAt'],'rank':rank,
            'sourceSnapshotAt':ui['observedAt'],'measurementWindow':{'start':start,'end':end,'sourceTimezone':'UTC'},
            'metricBasis':'Authenticated visible top-post row matched to stable workbook post identity.'})
    recent=[]
    for row in sheet('MOST RECENT POSTS')[1:]:
        if not row[0]:continue
        url,published,typ,impressions,inside,outside,reach,views,follow,viewers,react,comments,reposts,saves,sends,custom=row
        recent.append({'postId':post_id(url),'url':url,'publishedAt':day(published),'postType':typ,'impressions':n(impressions),
            'inNetworkLabel':inside,'outOfNetworkLabel':outside,'membersReached':n(reach),'views':n(views) if views else None,
            'followersGained':n(follow),'profileViewers':n(viewers),'reactions':n(react),'comments':n(comments),'reposts':n(reposts),
            'saves':n(saves),'sends':n(sends),'customButtonEngagements':n(custom),
            'basis':'Most Recent Posts source sample, not an exhaustive period publishing or performance census.'})
    followers=sheet('FOLLOWERS'); assert day(followers[0][0].split(' on ',1)[1])==end
    follower_daily=[{'date':day(x[0]),'newFollowers':n(x[1])} for x in followers[3:]]
    assert [x['date'] for x in follower_daily]==dates
    stamp=ui['observedAt']; source_hash=sha(ui_file)
    current=deepcopy(previous)
    coverage={**previous['coverage'],'start':start,'end':end,'sourceTimezone':'UTC','sourcePreset':'90 days',
        'finalDayPartial':True,'completeDaysThrough':'2026-11-12','observedMountainDate':'2026-11-13','sourceMayRestate':True}
    notes=['All 90 workbook daily impression rows reconcile to the independently observed cumulative chart.',
        'Daily Engagements is the workbook field; social-only and link breakdowns remain independently scoped fixed UI aggregates.',
        'The final November 13 UTC source day is partial. These daily values remain UTC buckets; they are not reallocated to Mountain days.',
        'Ranked posts and the Most Recent Posts sample are not complete publishing censuses. LinkedIn publication date is distinct from measurement date.',
        'New followers are additions, not net growth. Window-level unique reach is not daily additive.']
    export={'snapshotAt':stamp,'collectedAt':stamp,'coverage':coverage,'source':'Authenticated Charles creator workbook',
        'engagementDefinition':'Original worksheet field Engagements; daily social-only component split is unavailable.',
        'daily':daily,'summary':{'impressions':summary['impressions'],'membersReached':summary['membersReached'],'engagements':summary['exportEngagements']},
        'postCoverage':{'completePublishingHistory':False,'rankingCapPerMetric':50,'engagementRankedRows':counts['engagements'],'impressionRankedRows':counts['impressions'],
            'uniqueRankedPosts':len(ranked),'measurementWindow':{'start':start,'end':end,'sourceTimezone':'UTC'},
            'note':'Capped rankings joined by post ID; publication dates do not establish reporting windows. Missing metrics are null.'},
        'rankedPosts':sorted(ranked.values(),key=lambda x:x['impressionRank'] or 1000),'mostRecentPosts':recent,
        'followers':{'snapshotOn':end,'total':n(followers[0][1]),'daily':follower_daily,'newFollowersInWindow':sum(x['newFollowers'] for x in follower_daily),
            'definition':'Source new followers; unfollows and opening inventory are unavailable.'},
        'demographics':{k:[{'category':r[0],'value':r[1],'percentageLabel':r[2]} for r in sheet(f'{k.upper()} DEMOGRAPHICS')[1:]] for k in ['audience','content']},'notes':notes}
    export['demographics']['note']='Rounded and suppressed source percentage labels remain text.'
    archive=deepcopy(previous.get('historicalTopPostReviews',[]))
    if not any(x['sourceSnapshotAt']==previous['snapshotAt'] for x in archive):
        archive.append({'sourceSnapshotAt':previous['snapshotAt'],'measurementWindow':{k:previous['coverage'][k] for k in ['start','end','sourceTimezone']},
            'records':previous['topPosts'],'note':'Historical source snapshot; excluded from current top-post metrics.'})
    old={r['date']:r for r in previous['exportAnalytics']['daily']};new={r['date']:r for r in daily}; overlap=sorted(old.keys()&new.keys())
    added=sorted(new.keys()-old.keys());dropped=sorted(old.keys()-new.keys())
    sum_rows=lambda records,ids,field:sum(records[d][field] for d in ids)
    compare={'priorWindow':previous['coverage'],'currentWindow':{'start':start,'end':end,'sourceTimezone':'UTC'},
        'commonWindow':{'start':overlap[0],'end':overlap[-1],'days':len(overlap),'priorImpressions':sum_rows(old,overlap,'impressions'),
            'currentImpressions':sum_rows(new,overlap,'impressions'),'impressionRestatementDifference':sum_rows(new,overlap,'impressions')-sum_rows(old,overlap,'impressions'),
            'priorExportEngagements':sum_rows(old,overlap,'engagements'),'currentExportEngagements':sum_rows(new,overlap,'engagements'),
            'exportEngagementRestatementDifference':sum_rows(new,overlap,'engagements')-sum_rows(old,overlap,'engagements')},
        'newlyCoveredDates':added,'newlyCoveredImpressions':sum_rows(new,added,'impressions'),'droppedDates':dropped,'droppedImpressions':sum_rows(old,dropped,'impressions'),
        'rollingTotalDifference':summary['impressions']-previous['summary']['impressions'],'isPureGrowthSincePriorCollection':False,
        'note':'Difference between rolling source windows, separated into added dates, dropped dates, and restatements of overlapping days.'}
    assert compare['rollingTotalDifference']==compare['newlyCoveredImpressions']-compare['droppedImpressions']+compare['commonWindow']['impressionRestatementDifference']
    current.update(snapshotAt=stamp,collectedAt=stamp,checkedAt='2026-11-13',coverage=coverage,summary=summary,
        comparison={**previous['comparison'],'percentChange':ui['priorPercent'],'label':f"{ui['priorPercent']}% versus prior 90 days (platform display)"},
        chart={**previous['chart'],'points':[{'date':d,'cumulativeImpressions':v} for d,v in zip(dates,ui['cumulative'])]},
        daily=[{**x,'engagements':None,'exportEngagements':x['engagements'],'account':'Charles Solomon','sourceId':'charles_creator_export',
            'sourceTimezone':'UTC','currentDayPartial':x['date']==end,'derivation':'Direct reconciled workbook UTC day.'} for x in daily],
        exportAnalytics=export,topPosts=top,historicalTopPostReviews=archive,comparisonToPreviousSource=compare,notes=notes,
        method='Authenticated Charles creator workbook, reconciled to independent visible cumulative UI chart and fixed aggregates',
        evidence={'sourceFileSha256':sha(file),'uiFileSha256':source_hash,'observationTimeBasis':'Captured authenticated browser observation; collection timestamps are not source event timestamps.'})
    profile=deepcopy(previous['profileAnalytics']); recent_p=p['recent']
    assert len(p['chart'])==13 and p['viewers']==1671 and len(recent_p['chart'])==7 and recent_p['viewers']==272
    profile.update(snapshotAt=p['observedAt'],collectedAt=p['observedAt'],profileViewers=p['viewers'],
        evidence={'primaryContentVerified':True,'readOnly':True,'sourceSha256':source_hash,'collectionTimeBasis':'Independent authenticated Profile Viewers observation.'})
    profile['chartMetadata'].update(displayedBucketCount=len(p['chart']),firstDisplayedBucket=p['chartStart'],lastDisplayedBucket=p['chartEnd'],lastDisplayedBucketViewers=p['chart'][-1])
    profile['recentPreset']={'snapshotAt':recent_p['observedAt'],'sourcePreset':recent_p['sourcePreset'],'profileViewers':recent_p['viewers'],
        'displayedChartStart':recent_p['chartStart'],'displayedChartEnd':recent_p['chartEnd'],'sourceTimezone':None,
        'finalDisplayedDayPartial':True,'exactAggregateTimeBoundariesEstablished':False,
        'chart':[{'date':(date.fromisoformat(recent_p['chartStart'])+timedelta(days=i)).isoformat(),'displayedProfileViewers':v} for i,v in enumerate(recent_p['chart'])],
        'displayedChartPointSum':sum(recent_p['chart']),'chartPointSumReconcilesToAggregate':sum(recent_p['chart'])==recent_p['viewers'],
        'note':'The independently displayed Past 7 days aggregate is 272. Its seven displayed chart points total 296 and are not used to derive or replace the aggregate. Chart labels show November 7–13 including the partial final source day. This is not the dashboard November 6–12 selection; source timezone and exact aggregate boundaries are unavailable.'}
    profile['notes']=[*profile['notes'],'Separately retained Past 7 days aggregate: 272 on November 7–13 displayed labels, including the partial final day; do not substitute for the dashboard period.']
    current['profileAnalytics']=profile
    def selected(s,e):
        ds=[d for d in dates if s<=d<=e]; follows={x['date']:x for x in follower_daily}
        return {'start':s,'end':e,'retainedDays':len(ds),'impressions':sum_rows(new,ds,'impressions'),'exportEngagements':sum_rows(new,ds,'engagements'),
            'newFollowers':sum_rows(follows,ds,'newFollowers'),'finalDayPartial':e==end,'sourceTimezone':'UTC'}
    validation={'identityVerified':True,'workbookDailyRows':len(daily),'workbookImpressionsReconciled':True,'uiCumulativePointCount':len(ui['cumulative']),
        'uiCumulativeDifferences':[],'uiImpressions':ui['impressions'],'exportImpressions':summary['impressions'],'uiReach':ui['membersReached'],
        'exportReach':summary['membersReached'],'allSourceCountsReconciled':True,'exportEngagements':summary['exportEngagements'],
        'socialEngagements':ui['socialEngagements'],'rankedPosts':len(ranked),'freshTopPosts':len(top),'mostRecentPostSample':len(recent),
        'followers':export['followers']['total'],'newFollowers':export['followers']['newFollowersInWindow'],'week':selected('2026-11-06','2026-11-12'),
        'partialDay':selected(end,end),'month':selected('2026-11-01',end),'rollingWindowComparison':compare,
        'restatedDaily':[{'date':d,'prior':old[d],'current':new[d]} for d in overlap if old[d]!=new[d]],
        'profile90d':p['viewers'],'profilePast7Days':recent_p['viewers'],'profileSourceClock':p['observedAt']}
    write('creator_latest_patch.json',{'creatorAnalytics':current,'validation':validation})
    write('profile_analytics_patch.json',profile)
    print(json.dumps({k:validation[k] for k in ['week','partialDay','month','followers','profile90d','profilePast7Days','exportImpressions','exportReach','exportEngagements','socialEngagements','rankedPosts']}))


if __name__=='__main__':
    build()
