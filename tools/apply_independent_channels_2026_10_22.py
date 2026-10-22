"""Apply reviewed invitation, creator, message-date and concluded-Ads evidence."""
from pathlib import Path
from datetime import datetime, timezone
import copy
import json
from import_waalaxy_actions_2026_10_22 import apply_invitation_patch
from prepare_shared_snapshot import curate_snapshot, preserve_newer_shared_sources

ROOT=Path(__file__).resolve().parents[1]


def load(relative):return json.loads((ROOT/relative).read_text())


def apply_patches(before):
    assert before['meta'].get('reportingAsOfDate','')<='2026-10-22', 'Use a newer review for a newer reporting period.'
    result=copy.deepcopy(before)
    invitation=load('data/private/waalaxy_actions_refresh_2026_10_22/invitation_patch.json')
    creator=load('data/private/independent_refresh_2026_10_22/creator/creator_latest_patch.json')
    messages=load('data/private/video_dm_event_review_2026_10_22/video_message_dates_patch.json')
    lifecycle=load('data/private/independent_refresh_2026_10_22/ads/lifecycle_patch.json')
    availability=load('data/private/independent_refresh_2026_10_22/company_availability_patch.json')
    assert creator['validation']['allSourceCountsReconciled']
    result['waalaxy']=apply_invitation_patch(result['waalaxy'],invitation)
    current=result['content'].get('creatorAnalytics') or {}
    assert current.get('snapshotAt','')<=creator['creatorAnalytics']['snapshotAt'], 'Newer creator evidence is already present.'
    result['content']['creatorAnalytics']=copy.deepcopy(creator['creatorAnalytics'])
    result['content']['companyAvailabilityReview']=copy.deepcopy(availability)
    result['video']['messageDateReview']=copy.deepcopy(messages)
    result['ads']['lifecycleReview']=copy.deepcopy(lifecycle)
    cards={row['id']:row for row in result['sources']}
    cards['waalaxy_invitations']=copy.deepcopy(invitation['sourceCard'])
    cards['content'].update(asOf=creator['creatorAnalytics']['collectedAt'],checkedAt='2026-10-22',
        status='Current Charles creator workbook and matching UI; separately dated company evidence',
        note='Fresh Charles workbook and matching UI collected October 22. All 90 daily impression rows reconcile. Ranked posts remain a capped subset; the current UTC day is partial. Company metrics retain their independent collection date and coverage.')
    cards['video_message_dates']={'id':'video_message_dates','name':'Video DM · message-date evidence review',
        'asOf':messages.get('reviewedAt') or messages['snapshotAt'],'checkedAt':'2026-10-22',
        'status':'Current bounded CRM and message-date review',
        'coverage':f"{messages.get('nativePlatformCoverage',{}).get('cohortProfilesChecked',0)} October 21 video-asset profiles checked in Charles’s conversations; targeted CRM and exact-profile historical attributes. Account-wide event coverage incomplete.",
        'method':'Read-only CRM notes, activities and associated mail; retained source dates and separately identified conversation observations',
        'note':'Observed video messages corroborate existing worksheet reports and are not added again. Message dates retain their evidence basis. CRM note creation dates are not sends, historical emails are not Video DMs, and latest LinkedIn replies do not establish video attribution. Commercial outcomes are unchanged.'}
    cards['ads_lifecycle']={'id':'ads_lifecycle','name':'LinkedIn Ads · conclusion check',
        'asOf':lifecycle['reviewedAt'],'checkedAt':'2026-10-22','status':'Current authenticated completed-status review',
        'coverage':'September 4–October 22 UTC account-view selection; underlying retained daily export ends October 21.',
        'method':'Charles signed-in Campaign Manager reload and matching reporting-date selection',
        'note':lifecycle['note']}
    cards['content_company_availability']={'id':'content_company_availability','name':'LinkedIn company content · date availability',
        'asOf':availability['reviewedAt'],'checkedAt':'2026-10-22','status':'Latest available source date reverified',
        'coverage':'Metadata and matching aggregate check only; retained daily company export still ends October 20 UTC.',
        'method':'Authenticated company-page analytics date picker and matching displayed totals',
        'note':availability['note']}
    result['sources']=list(cards.values())
    result=curate_snapshot(preserve_newer_shared_sources(result,before))
    for key in ('crm','meetings','outcomes','time','referrals'):
        assert result[key]==before[key],f'Unexpected commercial or effort change:{key}'
    for key in ('rows','datedActions','crmReconciliation'):
        assert result['video'][key]==before['video'][key],f'Original Video DM evidence changed:{key}'
    for key in ('daily','totals','leads','campaigns','creatives'):
        assert result['ads'][key]==before['ads'][key],f'Original paid evidence changed:{key}'
    assert result['content']['companyAnalytics']==before['content']['companyAnalytics']
    return result


def main():
    path=ROOT/'data/shared-dashboard.json';before=json.loads(path.read_text())
    data=apply_patches(before)
    data['meta'].update(generatedAt=datetime.now(timezone.utc).isoformat(),
        revision='October 22 owner invitation CSV, latest Charles creator workbook, message-date review and concluded-Ads verification',
        lastRevisionNote='Independent channel updates; commercial outcomes and owner effort estimate unchanged.')
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    local=ROOT/'data/dashboard.json'
    if local.exists():local.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'creatorImpressions':data['content']['creatorAnalytics']['summary']['impressions'],
        'invitationDays':data['waalaxy']['invitationCoverage']['sourceDays'],
        'messageDateProfiles':len(data['video']['messageDateReview']['records']),
        'platformObservations':len(data['video']['messageDateReview'].get('platformObservedEvents',[])),
        'completedAdSets':data['ads']['lifecycleReview']['completedAdSets'],
        'commercialOutcomesUnchanged':True,'effortEstimateUnchanged':True}))


if __name__=='__main__':main()
