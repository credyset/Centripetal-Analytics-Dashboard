"""Apply the independently reviewed October 22 CRM, correspondence and sync evidence.

Private inputs remain ignored. This operation writes only the local dashboard
snapshots and respects the owner's publication hold.
"""
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
import copy
import json
from prepare_shared_snapshot import curate_snapshot, preserve_newer_shared_sources

ROOT = Path(__file__).resolve().parents[1]
LATEST = ROOT/'data/private/refresh_2026_10_22_latest'
AUDIT = ROOT/'data/private/completion_audit_2026_10_22'
ZAP = ROOT/'data/private/zapier_live_review_2026_10_22'


def read(path):
    return json.loads(path.read_text())


def main():
    previous = read(ROOT/'data/shared-dashboard.json')
    if previous.get('meta', {}).get('reportingAsOfDate', '') > '2026-10-22':
        raise RuntimeError('This dated review must not regress a later reporting snapshot.')
    incoming = copy.deepcopy(previous)
    incoming['crm'] = read(LATEST/'crm_mcp_patch.json')
    incoming['referrals'] = read(LATEST/'referrals_mcp_patch.json')
    data = preserve_newer_shared_sources(incoming, previous)
    crm_at = read(LATEST/'source_and_cutoff_proposal.json')['snapshotAt']
    prepared_at = datetime.now(timezone.utc).isoformat()
    zap_manifest = read(ZAP/'review_manifest.json')
    now = zap_manifest['reviewedAt']
    data['meta'].update(generatedAt=prepared_at, asOfDate='2026-10-22',
        reportingAsOfDate='2026-10-22', defaultReportingThrough='2026-10-22',
        defaultCompleteReportingThrough='2026-10-21', currentDayPartial=True,
        revision='October 22 latest CRM, commercial reconciliation and verified automation review; local only')
    for source in data['sources']:
        if source['id'] in ('crm', 'referrals'):
            source['asOf'] = crm_at
            source['coverage'] = copy.deepcopy(data[source['id']]['coverage'])
            source['note'] = ('Full accessible non-deleted CRM pagination completed October 22 05:51 MDT. '
                '769 deals /924 activities; referral inventory derived from the same source. '
                'October 22 is partial. Record changes and source won status do not establish commercial outcomes.')

    # A correspondence reply describes the relationship; it is separate from
    # an actual introduction, the existing dated follow-up and owner decisions.
    jonathan = read(AUDIT/'sheets/jonathan_reply_context_patch_2026_10_22.json')
    data['referrals']['contextReview'] = {
        'snapshotAt': jonathan['sourceCollectedAt'], 'reviewedAt': jonathan['preparedAt'],
        'records': [{key: event[key] for key in ('occurredAt','direction','referralContact',
            'dealId','summary','sourceMailMessageId','sourceThreadId','bodyEvidenceScope')}
            for event in jonathan['events']],
        'relationshipContext': jonathan['latestRelationshipContext'],
        'note': 'Jonathan reports an incumbent provider and possible general chat; Charles welcomes that chat. '
            'No completed introduction, booking, held call, active paid opportunity or formal lost outcome is established. '
            'Deal793 remains open / Intro Promised. October 21 follow-up44104 is retained once.',
        'coverageComplete': False,
    }

    reconciliation = read(AUDIT/'commercial/woodrow_venus_conflict_review.json')
    review = data['crm']['commercialContextReview']
    review.update(snapshotAt=reconciliation['reviewedAt'], reviewedAt=reconciliation['reviewedAt'])
    review['records'] = [r for r in review['records'] if r.get('dealId') != 805] + [{
        'dealId':805, 'organization':'Venus AI Consulting',
        'firstContextDocumentedAt':'2026-10-10','latestContextDocumentedAt':'2026-10-20',
        'companyContext':'Duplicate Leads 791 / Sales 805 represent one company. Last explicit owner disposition: unqualified October 16.',
        'scopeFitBasis':'Charles manually moved 805 to Negotiating Contract on October 20 at 14:50:30 UTC. '
            'This is a verified stage change; an original explicit acceptance and buyer-agreed next step remain unverified. '
            'It does not automatically supersede the owner qualification decision.',
        'headlineCountingDisposition':'No additional qualification, accepted opportunity or first-client win.',
        'requiredNextEvidence':'Latest explicit qualification decision, original acceptance date/agreed next step and exact held day (October 15–16 remains unresolved).',
        'sourceRefs':[],
        'sourceStageChangeId':6243,
    }]
    review['reconciliationNote'] = ('The supplied external verification summary was compared with primary dialogue and correspondence. '
        'Woodrow is vendor/product feedback; an invitation does not establish Charles attendance. '
        'Venus stage movement is retained separately from owner qualification/acceptance.')
    ff = data['meetings']['fireflies']
    woodrow_ids = {r['recordingId'] for r in reconciliation['woodrowReview']['primaryEvidence']}
    for row in ff['records']:
        if row['id'] in woodrow_ids:
            row.update(classification='vendor_product_evaluation_feedback',
                classificationBasis='Peter and Juliana discuss testing and improving Woodrow software. '
                    'Centripetal is evaluating the vendor product; a Woodrow purchase of CFO services is not established. '
                    'Charles is an invitee; actual participation remains unverified. Overlapping recordings remain duplicate candidates.',
                lastPurposeReviewedAt=reconciliation['reviewedAt'])

    # Existing dated status rows already include all twelve October 21 marks.
    dated = read(AUDIT/'sheets/dated_sent_status_review_2026_10_22.json')
    data['video']['datedStatusReview'] = {
        'snapshotAt':dated['preparedAt'], 'reviewedAt':dated['preparedAt'],
        'sourceDate':'2026-10-21', 'uniqueProfilesMarkedSent':12,
        'recordingLinksPresent':10,'recordingFieldContentPresent':12,
        'nonUrlRecordingNotes':2,'explicitSheetCrmDealIdsPresent':0,
        'sourceStatusLabel':'Sent 10/21/26', 'alreadyIncludedInDatedActions':True,
        'actualSenderAccountId':None,'actualSentAt':None,'deliveryVerified':False,
        'note':'Twelve distinct profiles have a date-only self-reported Sent label; ten have valid Loom URLs and two have non-URL LinkedIn DM notes. '
            'These are already retained; do not add twelve new events. No message link, delivery receipt or actual sender is established.'}
    freshness = read(AUDIT/'sheets/final_sheet_freshness_check_2026_10_22.json')
    data['video']['metadataFreshnessCheck'] = {
        'snapshotAt':freshness['checkedAt'], 'reviewedAt':freshness['checkedAt'],
        **{key:freshness[key] for key in ('currentModifiedAt','currentRevisionId',
            'unchangedSinceRetainedValues','fullValuesReread','retainedValuesCollectedAt',
            'valuesFreshnessLabel','metadataFreshnessIsNotNewValueCollection',
            'newValuePatchRequired','provenanceLimits')},
    }
    for card in data['sources']:
        if card['id']=='video':
            card['checkedAt']=freshness['checkedAt']
    meeting_check=read(AUDIT/'freshness_delta/freshness_review.json')
    data['meetings']['metadataFreshnessCheck']={
        'snapshotAt':meeting_check['checkedThrough'],'reviewedAt':meeting_check['checkedThrough'],
        'fireflies':{'latestAccessibleIds':100,'octoberIndexedIds':76,
            'newIds':0,'changedMetadataIds':0,'bodyVersionAvailable':False,
            'scope':'Latest100 metadata IDs; no body-only change detection or new dialogue retrieval.'},
        'calendly':{'activeEvents':3,'canceledEvents':0,'eventsAndInviteesUnchanged':True,
            'scope':meeting_check['calendly']['scope'],
            'futureEventStart':'2026-10-22T16:00:00Z'},
        'note':'Rechecked October 22 at 06:11 MDT: same latest 100 Fireflies IDs and metadata, '
            'including 76 October IDs; same 3 active Calendly events and invitees. '
            'A future October 22 booking is not held. Metadata cannot detect body-only transcript processing changes; '
            'these sources are not a complete actual-call roster. Original evidence dates remain unchanged.'}
    for card in data['sources']:
        if card['id'] in ('meetings','fireflies'):
            card['checkedAt']=meeting_check['checkedThrough']

    raw = read(ZAP/'weekly_history_rows.json')
    by_id = {}
    for row in raw:
        if row['id'] in by_id:
            assert row == by_id[row['id']], 'Conflicting repeated run IDs require review'
        by_id[row['id']] = row
    displayed, unique = Counter(r['status'] for r in raw), Counter(r['status'] for r in by_id.values())
    assert len(raw)==841 and len(by_id)==808
    assert unique == {'Successful':15,'Filtered':90,'On hold Too much data':703}
    counts = lambda counter: {'successful':counter['Successful'],'filtered':counter['Filtered'], 'held':counter['On hold Too much data']}
    history = {
        'coverage':{'start':'2026-10-19','end':'2026-10-22','currentDayPartial':True},
        'pagesReviewed':85,'displayedEntries':len(raw),'uniqueRunIds':len(by_id),
        'duplicateEntries':len(raw)-len(by_id),'uniqueStatusCounts':counts(unique),
        'displayedStatusCounts':counts(displayed),'heldDates':['2026-10-20'],
        'coverageComplete':False,'retainedPagesExhausted':True,'atomicSnapshot':False,
        'verifiedHeldRun':{'id':'0086536b-24cf-a814-e98c-9b9f27f09d94',
            'startedAt':'2026-10-20T20:56:26Z','sheetRow':1154,'company':'Cypher AI',
            'errorCode':'TooManyItems','failedStep':1,'filterAttempted':False,'crmStepsAttempted':False},
        'note':'All 85 displayed history pages for this Zap and October 19–22 were retained. '
            '841 entries represent 808 unique run IDs; 33 repeated held IDs have identical status/time. '
            '703 unique held IDs (736 displayed entries) are dated October 20. '
            'This is a non-atomic retained execution-history census, not unique recipients or delivered outreach. '
            'No replay, test, configuration or connection changes were performed.'}
    automation = {
        'snapshotAt':now,'reviewedAt':now,'zapId':383834891,'enabled':True,
        'sourceCaptureSavedThrough':zap_manifest['sourceCaptureSavedThrough'],
        'publishedVersion':'v2','hasDraft':True,
        'source':{'spreadsheetName':'centripetal_top20_video_sniper_prospects_aug2026',
            'worksheetName':'centripetal_top20_video_sniper_prospects_aug2026',
            'triggerColumn':'COL$Q','filter':'Status (CS Column) contains Sent'},
        'latestVerifiedRun':{'id':'0086536b-859f-acb6-d819-13415762c354',
            'startedAt':'2026-10-21T16:31:40Z','completedAt':None,'writebackAt':'2026-10-21T16:31:50Z',
            'status':'success','sheetRow':1116,'company':'BioInsights','contact':'Travis Bond',
            'profile':'travisbond','reportedSentDate':'2026-10-21',
            'crmOrganizationId':1294,'crmPersonId':2843,'crmDealId':846,'crmPipelineId':2,
            'crmStage':'Video DM Outreach','sheetSyncFlag':True,'crmIdsWrittenBack':False},
        'historyReview':history,
        'note':'Existing logged-in Zapier session used; no Google account selection or new sign-in was needed. '
            'The pre-existing draft was neither edited nor published.',
        'limits':['Successful sync establishes worksheet-to-CRM execution, not actual LinkedIn delivery, actual sender or video inclusion.',
            'The held sample stopped at the Google Sheets trigger because it returned too many items; filter and CRM creation were not attempted.',
            'Published trigger configuration names COL$Q, while retained writeback output displays the Sent status at COL$P and Loom at COL$Q. '
            'This header/position discrepancy requires a configuration audit before changes or replay; no causal defect is asserted.',
            'The reviewed writeback sets Synced to Pipedrive true but leaves explicit deal_id/org_id inputs empty. '
            'This confirms one run mapping, not all historical CRM identity joins.',
            'Waalaxy sender identity and last successful upstream account sync are separate and remain unverified.']}
    data['video']['automationReview'] = automation
    workflow = data['waalaxy']['workflowReview']
    workflow.pop('lastSuccessfulSheetToCrmSyncAt', None)
    workflow.update(snapshotAt=now,reviewedAt=now,sheetToCrmExecutionVerified=True,
        lastVerifiedSuccessfulSheetToCrmRunAt='2026-10-21T16:31:40Z',
        lastVerifiedSheetWritebackStepAt='2026-10-21T16:31:50Z',
        syncExecutionIndependentlyVerified=False,
        note='Zapier independently verifies Video DM worksheet-to-CRM execution, including a later successful run and October 20 holds. '
            'This does not verify the upstream Waalaxy-to-Sheets account or last sync. '
            'All 19 visible workflows in the legacy Waalaxy folder are enabled; 17 display None in 60 days, '
            'recruitment last ran September 9 and Jess FounderLodge September 23. '
            'These bounded folder labels do not establish current Charles reply activity.')
    workflow['zapierFolderReview'] = {'reviewedAt':now,'visibleWorkflows':19,'enabledWorkflows':19,
        'displayedNoneIn60Days':17,'otherDisplayedLastRuns':[
            {'zapId':332913745,'scope':'Recruitment','date':'2026-09-09'},
            {'zapId':368102315,'scope':'Jess FounderLodge','date':'2026-09-23'}],
        'currentCharlesUpstreamSyncEstablished':False}

    # Extend the requested review period, not the collection date of audio or
    # the amount of Christian's separately specified non-meeting allowance.
    data['time']['period'].update(end='2026-10-22', currentDayPartial=True)
    data['time']['reviewedAsOf']='2026-10-22'
    time_note='October 22 review extends the requested period through today. Retained recording/file evidence keeps its original collection dates; no additional Christian hours or new attendance is inferred.'
    if time_note not in data['time']['notes']: data['time']['notes'].append(time_note)

    cards = {
        'commercial_context':{'name':'Commercial relationship reconciliation','asOf':reconciliation['reviewedAt'],
            'note':'Primary Woodrow dialogue supports vendor feedback; Venus stage change remains separate from explicit owner commercial decisions. Earlier five-record context is retained.'},
        'referral_context':{'name':'Referral correspondence context','asOf':jonathan['sourceCollectedAt'],
            'note':'Two October 22 Jonathan/Charles email snippets with explicit UTC dates. Context only; no completed introduction or formal lost outcome.'},
        'zapier_execution':{'name':'Video DM Zapier execution review','asOf':now,
            'note':'Published ON, v2; 85 retained weekly history pages, 808 unique run IDs, 15 successful /90 filtered /703 held. One success and one held run inspected. No delivered-message inference.'},
        'source_freshness':{'name':'Final Sheet, Calendly and recording freshness checks','asOf':freshness['checkedAt'],
            'note':'October 22 06:11 MDT: Sheet revision1253 and modification time unchanged; same 100 recording IDs/metadata and 3 active calendar events/invitees. Original values/dialogue dates retained. No additional outcomes inferred.'}}
    for ident, values in cards.items():
        card=next((s for s in data['sources'] if s['id']==ident),None)
        if card is None:
            card={'id':ident};data['sources'].append(card)
        card.update(values,status='Current independent review; local only')
    data=curate_snapshot(preserve_newer_shared_sources(data, previous))
    assert data['meta']['publicationStatus']=='local_only' and data['meta']['public'] is False
    assert len(data['crm']['deals'])==769 and len(data['video']['rows'])==428
    assert len(data['meetings']['fireflies']['records'])==len(previous['meetings']['fireflies']['records'])
    encoded=json.dumps(data,ensure_ascii=False,indent=2)+'\n'
    for name in ('dashboard.json','shared-dashboard.json'):
        (ROOT/'data'/name).write_text(encoded)
    print('Applied local October 22 CRM, reconciliation, referral context and verified workflow evidence.')


if __name__=='__main__':
    main()
