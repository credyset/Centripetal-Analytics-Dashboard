"""Apply reviewed completion-audit supplements locally; no source access.

Independent source timestamps and the October21 reporting cutoff are retained.
Raw evidence remains private. Replays preserve newer collaborator sources.
"""
from pathlib import Path
from datetime import datetime,timezone
import copy,json
from prepare_shared_snapshot import curate_snapshot,preserve_newer_shared_sources

ROOT=Path(__file__).resolve().parents[1]
PRIVATE=ROOT/'data/private/completion_audit_2026_10_22'


def build():
    baseline=PRIVATE/'dashboard_before_completion.json'
    if not baseline.exists():baseline.write_bytes((ROOT/'data/shared-dashboard.json').read_bytes())
    data=json.loads(baseline.read_text())
    creator=json.loads((PRIVATE/'creator/creator_export_patch.json').read_text())['creatorAnalytics']
    content=data['content']
    content['creatorPreviousSnapshot']={k:copy.deepcopy(content['creatorAnalytics'].get(k)) for k in ('snapshotAt','coverage','summary')}
    content['creatorAnalytics']=creator
    content['snapshotAt']=creator['snapshotAt']
    content['status']='current_creator_workbook_with_independent_company_source'
    content['accessReview'].update(checkedAt='2026-10-22',charlesCreatorCheckedAt='2026-10-22',
        reason='Charles signed-in creator workbook and UI collected October22, with daily impressions independently reconciled. Daily source-export Engagements, ranked post publication dates and follower additions are now available. Company daily metrics keep their separate collection and source-delay boundaries.',
        currentCharlesPrivateCoverage=copy.deepcopy(creator['coverage']))
    rows={(r['account'],r['date']):copy.deepcopy(r) for r in content.get('daily',[])}
    for r in creator['exportAnalytics']['daily']:
        rows[('Charles Solomon',r['date'])]={**r,'account':'Charles Solomon',
            'sourceId':'charles_creator_export','sourceTimezone':'UTC',
            'currentDayPartial':r['date']==creator['coverage']['end'],
            'engagementsSource':'Authenticated Charles creator XLSX',
            'engagementsSourceTimezone':'UTC',
            'engagementsMetric':'Source-export Engagements; broader than the separately recorded social-only total',
            'derivation':'Direct XLSX daily worksheet rows; impressions independently reconciled to cumulative UI'}
    content['daily']=sorted(rows.values(),key=lambda r:(r['date'],r['account']))
    content['review']={'kind':'signed_in_creator_workbook','snapshotAt':creator['snapshotAt'],
        'identityVerified':True,'sourceWindow':copy.deepcopy(creator['coverage']),
        'scope':'Charles personal creator workbook and corroborating UI; company source remains independently dated'}
    content['notes']=[n for n in content.get('notes',[]) if not n.startswith('Current signed-in Charles creator daily impressions')]
    content['notes']+=[
        'Current creator workbook supplies 90 UTC daily rows through October22 partial, including source-export Engagements. Its 555 Engagements remain distinct from the independently observed 545 social engagements and 10 link engagements. No daily social/link allocation is inferred.',
        'The current creator ranked register has 49 unique posts across two separately capped rankings. Publication dates are supplied; performance remains the full July25–October22 source window. It is not a complete publishing census or a lifetime performance register.',
        'The current follower worksheet reports 11,557 total followers on October22 and dated New followers additions. Additions do not establish net follower growth; unfollows and the opening inventory are not supplied. Earlier public follower observations retain their original dates.'
    ]
    source=next(s for s in data['sources'] if s['id']=='content')
    source.update(status='Current Charles creator workbook and corroborating UI; separate company source',
        asOf=creator['snapshotAt'],checkedAt='2026-10-22',
        coverage='Charles July25–October22 UTC, October22 partial; company daily September4–October20 UTC remains independently dated',
        method='Charles native Chrome creator XLSX download and retained signed-in UI; each of 90 impression rows reconciles',
        note='58,754 impressions, 32,110 members reached, 545 social engagements and 10 separate link engagements. Daily workbook Engagements sum to 555 and keep their broader source label. The 49 ranked posts have publication dates but are not a publishing census. The 11,557 follower snapshot and daily additions are separate from net growth. Company organic/sponsored metrics and paid overlap retain their independent source card.')
    sources={s['id']:s for s in data['sources']}
    commercial=json.loads((PRIVATE/'commercial/commercial_patch.json').read_text())
    archive=copy.deepcopy(commercial['archivedDealReview'])
    archive.pop('sourceFiles',None)
    archive['snapshotAt']=archive['collectedAt']
    archive['method']='Authenticated read-only query of the dedicated archived-deals endpoint'
    data['crm']['archiveReview']=archive
    data['crm']['coverage']['archiveCoverage'].update(
        archivedRecordsReturned=archive['archivedDealCount'],
        dedicatedArchiveQueryVerified=True,
        archivedQueryCollectedAt=archive['collectedAt'],
        note='The original non-archived snapshot returned 769 records. A separately dated October22 dedicated archive query returned zero accessible archived non-deleted deals, with pagination exhausted. These independent collection dates are not an atomic combined census; the archived-record zero is not a client-win result.')
    sources['crm_archived']={
        'id':'crm_archived','name':'Pipedrive · archived deal check',
        'status':'Current authenticated archived-deal query',
        'asOf':archive['collectedAt'],'checkedAt':'2026-10-22',
        'coverage':archive['scope'],'method':archive['method'],
        'note':'Zero accessible archived deals returned across owners and pipelines; one exhausted page. The full non-archived CRM snapshot retains its October21 collection date. No actual first-client win total is inferred.'}
    sources['crm']['note']+=' '+commercial['sourceCardNoteDelta']['crm']
    ff=data['meetings']['fireflies']
    by_id={r['id']:r for r in ff['records']}
    for ident,review in commercial['recordingClassificationUpdates'].items():
        if ident not in by_id:
            raw=json.loads((PRIVATE/f'commercial/fireflies_{ident}.json').read_text())
            transcript=json.loads(next(x['text'] for x in raw['result']['content'] if x['type']=='text'))['transcript']
            assert transcript['id']==ident
            record={'id':ident,'title':transcript['title'],
                'indexedAt':review['indexedAt'],'occurredAt':None,
                'durationMinutes':round(transcript['duration'],2),
                'evidenceStatus':'dialogue_purpose_reviewed_without_verified_prospect_join',
                'crmDealIds':[],'bookingChainIds':[],
                'joinStatus':'no_verified_crm_or_calendar_join',
                'heldStatus':'unverified_for_booked_call','qualifiedStatus':'unverified',
                'audioDurationIsAttendance':False}
            ff['records'].append(record)
            by_id[ident]=record
        record=by_id[ident]
        # New purpose evidence does not manufacture an occurrence date or join.
        record.update(classification=review['classification'],classificationBasis=review['shortBasis'],
            lastPurposeReviewedAt=review['reviewedAt'],purposeSourceCollectedAt=review['sourceCollectedAt'],
            purposeReferences=[{k:v for k,v in ref.items() if k!='file'} for ref in review['sourceReferences']],
            confirmedProspectMeetingAdded=False)
    ff['additionalPurposeReview']={
        'snapshotAt':commercial['reviewedAt'],'reviewedAt':commercial['reviewedAt'],
        'selectedRecordingsReviewed':len(commercial['recordingClassificationUpdates']),
        'recordingIds':list(commercial['recordingClassificationUpdates']),
        'nonProspectPurposesEstablished':12,'insufficientDialogueRecords':1,
        'outcomeAdditions':copy.deepcopy(commercial['outcomeChanges']),
        'note':commercial['sourceCardNoteDelta']['fireflies']}
    ff['notes'].append(commercial['sourceCardNoteDelta']['fireflies'])
    sources['fireflies_purpose']={
        'id':'fireflies_purpose','name':'Fireflies · additional purpose review',
        'status':'Current selected-dialogue purpose review','asOf':commercial['reviewedAt'],
        'checkedAt':'2026-10-22','coverage':'Thirteen additional selected October-indexed recordings; incomplete account-wide held-call coverage',
        'method':'Authenticated recording-dialogue reads; retained sentence and speaker references',
        'note':commercial['sourceCardNoteDelta']['fireflies']}
    full=json.loads((PRIVATE/'commercial/october_76_proposed_patch.json').read_text())
    for ident,review in full['recordingClassificationUpdates'].items():
        if ident not in by_id:
            record={'id':ident,'title':review['title'],'indexedAt':review['indexedAt'],
                'occurredAt':review.get('occurredAt'),'durationMinutes':round(review['durationMinutes'],2),
                'evidenceStatus':'bounded_source_response_reviewed','crmDealIds':[],'bookingChainIds':[],
                'joinStatus':'no_verified_crm_or_calendar_join','heldStatus':'unverified_for_booked_call',
                'qualifiedStatus':'unverified','audioDurationIsAttendance':False}
            ff['records'].append(record);by_id[ident]=record
        record=by_id[ident]
        if record.get('heldStatus')=='source_corroborated':
            record.setdefault('corroborationReviewedAt',full['reviewedAt'])
        record.update(classification=review['classification'],classificationBasis=review['shortBasis'],
            lastPurposeReviewedAt=review['reviewedAt'],purposeSourceCollectedAt=review['sourceCollectedAt'],
            purposeReviewStatus=review['reviewStatus'],sentenceCount=review['sentenceCount'],
            charlesSpeakerEvidence=copy.deepcopy(review['charlesParticipation']),
            purposeReferences=copy.deepcopy(review['sourceReferences']),
            duplicateCandidateIds=copy.deepcopy(review['duplicateCandidateIds']))
    ff['octoberPurposeReview']={'snapshotAt':full['reviewedAt'],'reviewedAt':full['reviewedAt'],
        'metadataInventorySnapshotAt':full['retainedMetadataSnapshotAt'],
        **copy.deepcopy(full['fullReviewSummary']),
        'recordingIds':list(full['recordingClassificationUpdates']),
        'notes':copy.deepcopy(full['notes'])}
    sources['fireflies_october_review']={
        'id':'fireflies_october_review','name':'Fireflies · retained October inventory review',
        'status':'Current complete response review of the bounded October inventory',
        'asOf':full['reviewedAt'],'checkedAt':'2026-10-22',
        'coverage':'All 76 October-indexed records within the retained 100-record metadata inventory; not all actual meetings',
        'method':'All retained October source IDs requested; dialogue and speaker evidence assessed separately from metadata',
        'note':'76 successful responses: 65 purposes classified, five insufficient dialogues and six responses with no dialogue. Nine metadata duplicate-candidate groups are retained separately from a previously verified audio duplicate. No additional eligible prospect call or dated first-client win was established. Complete actual call coverage remains unknown.'}
    ff['notes'].append(sources['fireflies_october_review']['note'])
    ff['coverage']['limits']=[
        'No qualified opportunity or new client win is inferred from source counts or conditional transcript statements.'
        if note.startswith('NoHot/Qualified') else
        'Raw transcript bodies, participant emails, recording links and client financial details remain private; only minimal reviewed fields enter the dashboard.'
        if note.startswith('Rawbodies,') else note
        for note in ff['coverage'].get('limits',[])]
    sheets=json.loads((PRIVATE/'sheets/completion_audit_patch.json').read_text())
    reviewed=sheets['reviewedAt']
    data['video']['sourceVerification']={
        'snapshotAt':reviewed,'reviewedAt':reviewed,
        'sourceModifiedAt':sheets['sheetSource']['sourceModifiedAt'],
        'sourceValuesCollectedAt':sheets['sheetSource']['reusedFullSnapshotCollectedAt'],
        'sourceValuesReread':False,'crmJoin':copy.deepcopy(sheets['crmJoin']),
        'revisionEvidence':copy.deepcopy(sheets['revisionEvidence']),
        'verifiedVideoDmSends':None,'verifiedReplyEvents':None,
        'note':'Source metadata, revision history and stable joins were reviewed independently; no later worksheet value change was established. File-level status entry dates do not establish actual send time, channel or video inclusion.'}
    data['video']['notes'] += [
        'Stable CRM join review: 81 of 82 explicit Sheet deal IDs exist in the current CRM snapshot; one points to deleted Chromie deal322 and is not silently remapped. All 58 populated organization IDs match.',
        'Of the 81 matched rows, 80 are CRM-owned by Christian and one by Charles. Automation ownership does not identify the actual outreach sender.',
        'The latest retained revision comparison bounds one Cypher AI blank-to-DMd status entry to October21. It does not verify actual delivery, a video send or a reply. The Other Note edits do not establish Charles-qualified companies.'
    ]
    data['waalaxy']['workflowReview']={
        'snapshotAt':reviewed,'reviewedAt':reviewed,
        'handoffDate':sheets['syncProvenance']['handoffDate'],
        'documentedDefaultCrmOwner':'Christian W.',
        'syncExecutionIndependentlyVerified':False,'sourceSenderAccountId':None,'lastSuccessfulUpstreamSyncAt':None,
        'configurationDifferencesNeedReadback':True,
        'legacyAirtable':copy.deepcopy(sheets['airtableEvidence']),
        'note':'The dated handoff documents a Sheet-to-CRM status workflow, not message delivery. Current configuration and run execution remain unverified. Historical Airtable records do not supply current October Charles reply or referral events.'}
    data['waalaxy']['notes'].append('Legacy Airtable checked October22: no October-created/modified CRM captures, newest capture belongs to Jess, and the latest Charles weekly record is July20. Monthly labels entered by March2026 do not establish October2026 performance. None is merged into the verified current Charles Home aggregate.')
    data['referrals']['legacyCaptureReview']={
        'snapshotAt':reviewed,'reviewedAt':reviewed,
        **copy.deepcopy(sheets['airtableEvidence']['referralCandidates'])}
    data['referrals'].setdefault('notes',[]).append('The legacy Airtable referral-field query returned 48 records, including one test; 47 non-test rows have no actual introduction dates or verified referral direction. They remain excluded from current referral event and outcome totals.')
    data['time']['workEvidence']={'snapshotAt':reviewed,**copy.deepcopy(sheets['christianWorkEvidence'])}
    data['time']['notes'].append('Drive revision metadata attributes 14 retained October file revisions on nine Mountain dates to Christian. This supports activity dates only; it does not establish human work duration, billing or additional hours. The owner allowance remains 14.5–15.75 hours.')
    data['time']['notes'].append('A speaker-label cross-check across all 76 retained October Fireflies responses found six Christian-attributed recordings, all already represented in the existing six source audio events. It adds no new recording-duration proxy or human hours; the existing verified duplicate remains excluded.')
    sources['source_audit']={
        'id':'source_audit','name':'Worksheet · CRM joins and workflow provenance review',
        'status':'Current source-quality review; source inventories retain separate dates',
        'asOf':reviewed,'checkedAt':'2026-10-22',
        'coverage':'Independent revision, CRM-join and legacy capture review; not verified send, reply, referral or human-hour events',
        'method':'Read-only Sheet metadata/revisions/cell notes; explicit CRM IDs; dated handoff and connected Airtable records',
        'note':'81 of 82 Sheet deal IDs reconcile; one references deleted deal322. All 58 populated organization IDs agree. CRM owner alone is unsafe for sender attribution. Legacy Airtable adds no current October Charles events. Fourteen Christian-attributed revision records support nine activity dates, without adding hours. Actual delivery and upstream sync execution remain unverified.'}
    data['sources']=list(sources.values())
    data['meta'].update(generatedAt=datetime.now(timezone.utc).isoformat(),asOfDate='2026-10-22',localReviewOn='2026-10-22',
        revision='October22 completion audit: creator workbook, archive/sync evidence and metric-scope corrections; local only')
    data=preserve_newer_shared_sources(data,json.loads((ROOT/'data/shared-dashboard.json').read_text()))
    result=curate_snapshot(data)
    text=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    for name in ('shared-dashboard.json','dashboard.json'):(ROOT/'data'/name).write_text(text)
    print(json.dumps({'localOnly':not result['meta']['public'],'creatorImpressions':result['content']['creatorAnalytics']['summary']['impressions'],
        'creatorSocialEngagements':result['content']['creatorAnalytics']['summary']['socialEngagements'],
        'creatorExportEngagements':result['content']['creatorAnalytics']['summary']['exportEngagements'],
        'reportingThrough':result['meta']['reportingAsOfDate']}))


if __name__=='__main__':build()
