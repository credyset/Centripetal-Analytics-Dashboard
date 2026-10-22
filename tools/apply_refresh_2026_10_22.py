"""Apply independently dated October 22 channel detail to the local review.

No source access or publication. Preserve the October 21 CRM/calendar/creator
collection dates and reporting cutoff; newer channel sources keep their own
UTC or unspecified source-day windows. Replays start from a retained baseline.
"""
from pathlib import Path
from datetime import datetime, timezone
import copy
import json
from prepare_shared_snapshot import curate_snapshot, preserve_newer_shared_sources

ROOT=Path(__file__).resolve().parents[1]
PRIVATE=ROOT/'data/private/refresh_2026_10_22'


def read(name):
    return json.loads((PRIVATE/name).read_text())


def build():
    baseline=PRIVATE/'dashboard_before_channel_refinement.json'
    if not baseline.exists():baseline.write_bytes((ROOT/'data/shared-dashboard.json').read_bytes())
    current=json.loads(baseline.read_text())
    sources={s['id']:s for s in current['sources']}
    ads=read('ads/ads_patch.json')
    current['ads']=ads
    sources['ads'].update(asOf=ads['collectedAt'],checkedAt='2026-10-22',
        status='Current authenticated daily ad-set and creative exports',coverage=ads['coverage'],
        method='Charles signed-in native Chrome: Ad Set Performance and Ad Performance, All columns, broken out by day',
        note='116 ad-set/day and 117 ad/day rows reconcile at both daily and aggregate grains. Actual retained dates September 4–October 21 UTC; requested October 22 has no row and is unavailable, not zero. Five delivering ad sets and six creatives; two older UI ad sets have no exported delivery rows. Owner qualification and corroborated attendance remain separate from platform counters.')
    if 'ads_browser' in sources:
        sources['ads_browser'].update(status='Historical aggregate superseded by daily exports',
            note='The October 21 fixed-window browser control totals reconcile to the newer daily ad-set and creative exports. Current period reporting now uses the dated exports; this older observation is an audit cross-check.')
    company=read('company/company_patch.json')
    current['content']['companyAnalytics']=company
    content=current['content']
    content['historicalAccessReview']=copy.deepcopy(content.get('accessReview',{}))
    content['accessReview']={
        **copy.deepcopy(content.get('accessReview',{})),
        'status':'current_charles_creator_and_company_access',
        'checkedAt':'2026-10-22',
        'charlesCreatorCheckedAt':'2026-10-21',
        'companyAnalyticsCheckedAt':'2026-10-22',
        'reason':'Charles signed-in creator snapshot collected October 21; independently collected company-admin daily organic/sponsored metrics through October 20 UTC reviewed October 22. Company post-level publishing and boost attribution remain unavailable.',
        'newestPrivateCompanyCoverageEnd':company['coverage']['end'],
        'currentCompanyPrivateCoverage':copy.deepcopy(company['coverage'])}
    # Historical follower counts retain their original collection date; the
    # current company follower observation lives on its independently dated row.
    content['accessReview'].pop('publicFollowers',None)
    content['notes']=[
        ('Current company daily organic/sponsored metrics are available through October 20 UTC. Post-level boost status, publication counts and campaign/post joins remain unavailable. Sponsored activity overlaps Ads and must not be added to Ads.'
         if n.startswith('No current boosted-post analytics') else n)
        for n in content.get('notes',[])]
    sources['content'].update(
        status='Current Charles 90-day creator snapshot; company daily metrics have a separate source card',
        coverage='Charles creator July 25–October 22 UTC, final day partial; independent company coverage September 4–October 20 UTC is documented separately',
        note='58,532 impressions, 32,032 members reached and 543 social engagements in the fixed Charles 90-day window collected October 21. All 90 cumulative points reconcile. Daily personal social engagements and a complete post register remain unavailable. See the independently dated company source for current daily organic/sponsored metrics; its collection does not refresh this creator snapshot.')
    sources['content_company']={
        'id':'content_company','name':'LinkedIn · Centripetal company content',
        'status':'Current authenticated company daily metrics; two-day source delay',
        'asOf':company['collectedAt'],'checkedAt':'2026-10-22','coverage':company['coverage'],
        'method':'Charles signed-in company-admin Content export; UTC Metrics worksheet',
        'note':'47 explicit daily rows September 4–October 20 UTC, separated into organic and sponsored. The source labels a delay up to two days and rejects October 21. Sponsored counters exactly overlap Ads over the same days and must not be added to Ads. The workbook contains no post-level register; publication count, period unique reach and aggregate engagement rate remain unavailable.'}
    # A fresh company export does not refresh Charles's creator snapshot or the
    # older public post sample. Only the independently verified follower row moves.
    for profile in current['content'].get('publicObservations',{}).get('profiles',[]):
        if profile.get('name','').lower()=='centripetal advisors':
            profile['previousObservation']={k:copy.deepcopy(profile.get(k)) for k in ('followers','checkedAt')}
            profile.update(followers=899,checkedAt='2026-10-22',
                observationBasis='Authenticated Charles company-admin header, independently agreeing with the public company page')
    account=read('waalaxy/waalaxy_home_patch_2026_10_22.json')
    account.pop('proof',None)
    account['snapshotAt']=account['collectedOn']  # Day precision only.
    current['waalaxy']['accountAnalytics']=account
    waalaxy=current['waalaxy']
    waalaxy['historicalAccessReview']=copy.deepcopy(waalaxy.get('accessReview',{}))
    waalaxy['accessReview']={
        'status':'charles_fixed_window_account_verified',
        'checkedAt':'2026-10-22',
        'reason':'Charles name and exact LinkedIn profile verified in the native Charles Chrome Home view. The separate extension account identifying Christian is excluded. Current fixed-month aggregate does not refresh the older daily invitation CSV or historical person flags.',
        'newestVerifiedCharlesAccountAggregateOn':account['collectedOn'],
        'sourceWindow':copy.deepcopy(account['sourceWindow']),
        'newestDatedInvitationActivity':waalaxy.get('invitationCoverage',{}).get('end'),
        'sheetSenderAndSyncVerified':False,
        'dailyActionExportRetained':False}
    waalaxy['notes']=[
        ('Historical Charles person export is dated July 6, 2026. Current account access was unavailable during the original concept check; the separate October 22 review now verifies Charles fixed-month Home aggregates, without refreshing those person flags.'
         if n.startswith('Historical Charles export') else
         'Prospect lists are not campaign histories. A current fixed-window Charles account aggregate is available separately; dated message/reply actions, campaign-level breakdowns and positive-reply classifications remain unavailable.'
         if n.startswith('Prospect lists are not campaign histories.') else n)
        for n in waalaxy.get('notes',[])]
    sources['waalaxy_account']={
        'id':'waalaxy_account','name':'Waalaxy · verified Charles account aggregate',
        'status':'Current authenticated fixed-window account snapshot',
        'asOf':account['collectedOn'],'checkedAt':'2026-10-22',
        'coverage':'October 1–22 displayed source days; October 22 partial, source timezone unspecified',
        'method':'Native Charles Chrome Home view; account name and exact LinkedIn profile independently verified',
        'note':'430 invitation actions, 132 accepted invitations, zero platform message actions and two answered messages in the fixed current-month source window. No daily CSV was retained; these overlap older invitation/person sources and are not added to them. Zero platform message actions does not establish zero manual LinkedIn or Video DM sends. Displayed rate denominators and positive reply outcomes remain unverified.'}
    current['sources']=list(sources.values())
    current['meta'].update(generatedAt=datetime.now(timezone.utc).isoformat(),
        asOfDate='2026-10-22',localReviewOn='2026-10-22',
        revision='October 22 channel detail refinement and pre-October XCaliber acceptance evidence; owner-directed local only')
    # A replay of these retained channel patches cannot erase later independent
    # creator, CRM or other collaborator evidence.
    current=preserve_newer_shared_sources(current,json.loads((ROOT/'data/shared-dashboard.json').read_text()))
    result=curate_snapshot(current)
    payload=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    for name in ('shared-dashboard.json','dashboard.json'):(ROOT/'data'/name).write_text(payload)
    print(json.dumps({'localOnly':not result['meta']['public'],
        'reportingCutoff':result['meta']['reportingAsOfDate'],
        'adsDailyThrough':result['ads']['coverage']['end'],
        'companyDailyThrough':company['coverage']['end'],
        'companySponsoredOverlapsAds':company['summary']['sponsored']['impressions'],
        'waalaxyFixedWindowSent':account['metrics']['invitationActionsSent']}))


if __name__=='__main__':build()
