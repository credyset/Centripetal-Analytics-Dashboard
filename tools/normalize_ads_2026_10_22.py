"""Normalize the retained October22 Ad Set and Ad daily exports, locally only.

The required analyze-linkedin-ads calculation aid is retained separately for
each grain. This script never adds ad-set and creative totals together, never
calls LinkedIn, and never writes the shared snapshot or publishes source data.
"""
from __future__ import annotations
from collections import defaultdict
from datetime import datetime,timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import argparse,copy,csv,hashlib,io,json,re

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'data/private/refresh_2026_10_22/ads'
FIELDS={'Total Spent':'spend','Impressions':'impressions','Clicks':'clicks',
        'Lead Forms Opened':'opens','Leads':'leads','Video Views':'videoViews',
        'Video Views at 25%':'video25','Video Views at 50%':'video50',
        'Video Views at 75%':'video75','Video Completions':'videoCompletions',
        'Appointments Booked':'platformAppointmentsReported',
        'Qualified Leads':'platformQualifiedLeadsReported',
        'Conversions':'platformConversions','Post-Click Conversions':'postClickConversions',
        'View-Through Conversions':'viewThroughConversions',
        'Reactions':'reactions','Comments':'comments','Shares':'shares',
        'Follows':'follows','Total Social Actions':'socialActions',
        'Total Engagements':'engagements','Clicks to Landing Page':'landingPageClicks',
        'Clicks to LinkedIn Page':'linkedInPageClicks',
        'Member Follows':'memberFollows','Clicks to Member Profile':'memberProfileClicks'}
EXPECTED={'spend':3592.31,'impressions':25055,'clicks':106,'opens':62,'leads':4,
          'videoViews':10804,'videoCompletions':419}

def read(path):return json.loads(path.read_text())
def write(path,obj):path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def number(value):return float(str(value or '0').replace(',',''))
def day(value):return datetime.strptime(value,'%m/%d/%Y').date().isoformat()
def parse(path):
    b=path.read_bytes();text=b.decode('utf-16' if b[:2] in (b'\xff\xfe',b'\xfe\xff') else 'utf-8-sig')
    meta={}
    for label,key in [('Report Start','start'),('Report End','end'),('Date Generated','generated')]:
        match=re.search(rf'"{label}: ([^"]+)"',text);assert match,label
        meta[key]=datetime.strptime(match[1],'%B %d, %Y, %I:%M %p').replace(tzinfo=ZoneInfo('UTC')).isoformat()
    rows=list(csv.DictReader(io.StringIO(text[text.index('Start Date (in UTC)\t'):]),delimiter='\t'))
    assert all(r['Currency']=='USD' and 'Centripetal' in r['Account Name'] for r in rows)
    assert meta['start'].startswith('2026-09-04') and meta['end'].startswith('2026-10-22')
    assert all(meta['start'][:10]<=day(r['Start Date (in UTC)'])<=meta['end'][:10] for r in rows)
    return rows,meta
def sums(rows):
    out={dest:round(sum(number(r.get(src)) for r in rows),2) for src,dest in FIELDS.items()}
    for key,value in out.items():
        if key!='spend':assert value.is_integer(),key;out[key]=int(value)
    return out
def daily(rows):
    groups=defaultdict(list)
    for r in rows:groups[day(r['Start Date (in UTC)'])].append(r)
    return [{'date':d,**sums(group)} for d,group in sorted(groups.items())]
def provenance(path):return {'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}

def build(adsets,creatives,baseline,output):
    rows,meta=parse(adsets);ads,admeta=parse(creatives)
    assert meta['start']==admeta['start'] and meta['end']==admeta['end']
    assert len({(r['Ad Set ID'],day(r['Start Date (in UTC)'])) for r in rows})==len(rows)
    assert len({(r['Ad ID'],day(r['Start Date (in UTC)'])) for r in ads})==len(ads)
    total=sums(rows);assert total==sums(ads),'Cross-grain totals do not reconcile'
    assert daily(rows)==daily(ads),'Daily cross-grain totals do not reconcile'
    assert all(total[k]==v for k,v in EXPECTED.items()),'Source control totals differ'
    # Owner decisions may advance independently of delivery. Keep the newest
    # owner evidence while retaining the first pre-refresh comparison snapshot.
    incoming=read(baseline)['ads']
    comparison_baseline=RAW/'baseline_ads_before_refresh.json'
    if not comparison_baseline.exists():write(comparison_baseline,incoming)
    old=read(comparison_baseline);result=copy.deepcopy(incoming)
    mapping={r['id']:r for r in result['campaigns']}
    assert set(mapping)=={r['Ad Set ID'] for r in rows}
    assert {r['Ad Set ID'] for r in ads}==set(mapping)
    for ident,record in mapping.items():
        group=[r for r in rows if r['Ad Set ID']==ident]
        latest=max(group,key=lambda r:day(r['Start Date (in UTC)']))
        record.update(**sums(group),daily=daily(group),name=latest['Ad Set Name'],
                      objective=latest['Ad Set Objective'],statusAsOfExport=latest['Ad Set Status'],
                      parentCampaignId=latest['Campaign ID'])
    result['creatives']=[]
    for ident in sorted({r['Ad ID'] for r in ads}):
        group=[r for r in ads if r['Ad ID']==ident];latest=max(group,key=lambda r:day(r['Start Date (in UTC)']))
        result['creatives'].append({'id':ident,'name':latest['Ad Name'],
            'adSetId':latest['Ad Set ID'],'campaignCode':mapping[latest['Ad Set ID']]['code'],
            'parentCampaignId':latest['Campaign ID'],'objective':latest['Ad Set Objective'],
            'statusAsOfExport':latest['Ad Status'],**sums(group),'daily':daily(group)})
    days=daily(rows);generated=max(meta['generated'],admeta['generated']);localday=datetime.fromisoformat(generated).astimezone(ZoneInfo('America/Denver')).date().isoformat()
    actual_end=days[-1]['date'];report_end=meta['end'][:10]
    last_complete=(datetime.fromisoformat(generated)-timedelta(days=1)).date().isoformat()
    result.update(status='available',snapshotAt=generated,collectedAt=generated,
        preparedAt=localday,reportGeneratedAt=generated,refreshMode='manual_authenticated_export',
        coverage={'start':days[0]['date'],'end':actual_end,'sourceTimezone':'UTC',
                  'finalDayPartial':actual_end>last_complete,'completeDaysThrough':min(actual_end,last_complete),
                  'reportRequestedStart':meta['start'][:10],'reportRequestedEnd':report_end,
                  'requestedFinalDayPartial':report_end>last_complete,'sourceMayRestate':True,
                  'missingRequestedDates':[report_end] if actual_end<report_end else []},
        dateBasis='Explicit UTC daily export rows; no Mountain rebucketing and no missing dates filled with zero',daily=days,
        reportWindow={'start':meta['start'],'end':meta['end'],'sourceTimezone':'UTC',
                      'adSetGeneratedAt':meta['generated'],'creativeGeneratedAt':admeta['generated']})
    result['totals']={'spend':total['spend'],'impressions':total['impressions'],
        'clicks':total['clicks'],'formOpens':total['opens'],'rawLeads':total['leads'],
        'qualifiedLeads':incoming['totals']['qualifiedLeads'],'videoViews':total['videoViews'],
        'videoCompletions':total['videoCompletions']}
    result['platformTotals']=total
    if result.get('browserReview'):
        result['browserReviewSupersededByExport']=result.pop('browserReview')
    assert result['leads']==incoming['leads'],'Owner decisions or booking evidence changed'
    assert len(result['leads'])==total['leads']==4
    result['notes']=[
        'Fresh authenticated Ad Set and Ad performance exports from account 515259390; generated October22 at 06:18 and 06:19 UTC. Their requested source window is September4–October22 UTC.',
        f'Actual exported daily records cover September4–{actual_end} UTC (48 distinct days). There is no October22 daily row; this partial requested date is unavailable, not a fabricated zero. The retained daily rows end before generation, and platform attribution may later restate.',
        'Ad Set and creative totals reconcile independently and are not added together. Five delivering A–E ad sets and six ads occur in these files; three distinct parent campaign IDs occur in the delivered rows.',
        'Two additional zero-delivery ad sets were observed in the authenticated filtered UI but do not appear in these exports. They are not assigned synthetic day rows or A–E codes.',
        'A–E are ad-set variants retained for audit continuity. E is configured for Website visits despite its video-views name; compare performance within objective.',
        'Four aggregate platform submissions remain reported. Individual lead-detail exports were not refreshed, so retained identities, qualification decisions and booking/held evidence remain separately dated. Equal aggregate lead counts do not independently reverify every submission identity.',
        'Owner qualification remains one qualified/warm paid lead (NuVee). The platform Qualified Leads field reports zero under its own definition and is retained separately; it does not override owner qualification.',
        'The one platform-reported appointment is not independently verified attendance, acceptance or a client win. CRM/owner/recording outcomes remain separate.',
        'Company-page organic/sponsored analytics overlap paid distribution and must not be added to these ad totals.'
    ]
    prior=old['totals']
    result['review']={'checkedAt':localday,'sourceAsOf':generated,'accountId':'515259390',
        'rawAdSetRows':len(rows),'rawCreativeRows':len(ads),'dailyBuckets':len(days),
        'uniqueAdSets':len(mapping),'uniqueAds':len(result['creatives']),
        'parentCampaignIds':sorted({r['Campaign ID'] for r in rows}),
        'latestCompleteUTCDate':min(actual_end,last_complete),'currentMountainDateIncomplete':True,
        'leadDetailAccess':{**copy.deepcopy(old.get('review',{}).get('leadDetailAccess',{})),
                           'notRefreshedInThisCollection':True},
        'priorCoverageEnd':old['coverage']['end'],
        'changeSincePriorSnapshot':{k:round(result['totals'][k]-prior[k],2) for k in ['spend','impressions','clicks','formOpens','rawLeads','videoViews','videoCompletions']},
        'checks':{'adsetCreativeTotalsAgree':True,'dailyAdsetCreativeTotalsAgree':True,
                  'dailyKeysUnique':True,'browserControlTotalsAgree':True,'ownerDispositionsPreserved':True},
        'sourceScope':{'exportedAdSetIds':sorted(mapping),'uiOnlyZeroDeliveryAdSetIds':['409641733','445365453'],
                       'uiOnlyZeroDeliveryNames':None,'uiOnlySourceBasis':'Root authenticated browser observation; no export rows',
                       'accountWideCompleteCampaignCoverage':False,
                       'note':'Source files reflect the selected campaign/ad-set scope; zero-delivery UI records are outside delivered export rows.'}}
    result['sources']=[provenance(adsets),provenance(creatives)]
    output.parent.mkdir(parents=True,exist_ok=True);write(output,result)
    write(RAW/'normalization_review.json',{'generatedAt':generated,'adSetMeta':meta,'creativeMeta':admeta,
        'totals':result['totals'],'platformTotals':total,'actualDailyCoverage':result['coverage'],
        'rawRows':{'adsets':len(rows),'creatives':len(ads)},'checks':result['review']['checks'],
        'changes':result['review']['changeSincePriorSnapshot']})
    print(json.dumps({'output':str(output),'totals':result['totals'],'dailyCoverage':result['coverage'],
                      'adsets':len(mapping),'creatives':len(result['creatives']),'checks':result['review']['checks']}))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--adsets',type=Path,default=RAW/'adsets_daily_utf16.tsv')
    p.add_argument('--creatives',type=Path,default=RAW/'creatives_daily_utf16.tsv')
    p.add_argument('--baseline',type=Path,default=ROOT/'data/shared-dashboard.json')
    p.add_argument('--output',type=Path,default=RAW/'ads_patch.json')
    a=p.parse_args();build(a.adsets,a.creatives,a.baseline,a.output)
