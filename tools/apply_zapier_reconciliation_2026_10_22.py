"""Apply reviewed trigger semantics, recording-field types and CRM joins locally."""
from pathlib import Path
from datetime import datetime, timezone
import copy
import json
from prepare_shared_snapshot import curate_snapshot

ROOT=Path(__file__).resolve().parents[1]
SHEETS=ROOT/'data/private/completion_audit_2026_10_22/sheets'
ZAP=ROOT/'data/private/zapier_live_review_2026_10_22'


def read(path):
    return json.loads(path.read_text())


def main():
    data=read(ROOT/'data/shared-dashboard.json')
    if data['meta']['reportingAsOfDate']>'2026-10-22':
        raise RuntimeError('Do not apply this dated review over a later reporting snapshot.')
    fields=read(SHEETS/'video_recording_field_review_patch.json')
    crosswalk=read(SHEETS/'video_crm_crosswalk_patch.json')
    audit=read(ZAP/'held_count_audit_summary.json')
    reviewed=crosswalk['reviewedAt']
    video=data['video']
    if (video.get('crmReconciliation') or {}).get('reviewedAt','')>reviewed:
        raise RuntimeError('A later independent video reconciliation is already present.')
    assert video['snapshotAt']==fields['sourceSnapshotAt']==crosswalk['sourceSnapshotAt']
    old_ids={r['sourceRow']:r.get('dealId') for r in video['rows']}
    source_rows={r['sourceRow']:r for r in video['rows']}
    notes={r['sourceRow']:r['exactRecordingFieldNote'] for r in fields['recordingFieldReview']['nonUrlRows']}
    field_records=[]
    for record in fields['sourceRowRecordingClass']:
        if not record['recordingFieldNonempty']:
            continue
        row=source_rows[record['sourceRow']]
        assert not record['profileId'] or record['profileId']==row['id']
        field_records.append({'sourceRow':row['sourceRow'],'profile':row['id'],
            'hasRecordingFieldContent':True,'hasRecordingLink':record['hasRecordingLink'],
            'recordingFieldKind':record['recordingReferenceClass'],
            'recordingFieldNote':notes.get(row['sourceRow'])})
    assert len(field_records)==60 and sum(r['hasRecordingLink'] for r in field_records)==57
    video['recordingFieldReview']={'snapshotAt':reviewed,'reviewedAt':reviewed,
        'appliesToSnapshotAt':video['snapshotAt'],'nonemptyCells':60,
        'validLoomUrls':57,'nonUrlNotes':3,'records':field_records,
        'note':'Recording-field content was validated as URL syntax:57 Loom share URLs and 3 separate text notes. '
            'A nonempty cell alone does not establish a video asset; a URL does not establish delivery.'}
    video['datedStatusReview']={'snapshotAt':reviewed,'reviewedAt':reviewed,
        'sourceValuesCollectedAt':video['snapshotAt'],'sourceDate':'2026-10-21',
        'uniqueProfilesMarkedSent':12,'recordingLinksPresent':10,
        'recordingFieldContentPresent':12,'nonUrlRecordingNotes':2,
        'explicitSheetCrmDealIdsPresent':0,'sourceStatusLabel':'Sent 10/21/26',
        'alreadyIncludedInDatedActions':True,'actualSenderAccountId':None,
        'actualSentAt':None,'deliveryVerified':False,
        'note':'Twelve existing self-reported dated Sent rows:ten valid Loom URLs and two non-URL LinkedIn DM notes. '
            'No new send events or verified deliveries are added.'}
    video['notes']=[
        'Sheet helper completion may include nonblank recording-field content, including notes as well as URLs; it does not prove delivery.'
        if note.startswith('Sheet-classified completion includes') else
        'Synced to Pipedrive is a source flag. The independent October 21 ten-row Loom cohort has exact CRM profile/asset-note matches; the flag alone does not verify delivery.'
        if note.startswith('Synced to Pipedrive is a source flag;') else note
        for note in video.get('notes',[])]
    cohort=[r for r in crosswalk['rows'] if r['selfReportedStatus']=='Sent 10/21/26']
    assert len(cohort)==10
    crm_ids={r['id'] for r in data['crm']['deals']}
    records=[]
    for record in cohort:
        assert record['profileMatchProof']['sameCanonicalProfile']
        assert record['recordingNoteProof']['sameSourceRecordingAsset']
        assert record['matchedCrmDealId'] in crm_ids
        note_ids=record['recordingNoteProof']['noteIds']
        records.append({'sourceRow':record['sourceRow'],'company':record['company'],
            'contact':record['contact'],'profile':record['profileId'],
            'recordingFieldKind':'loom_url','crmDealId':record['matchedCrmDealId'],
            'crmPersonId':record['matchedCrmPersonId'],'crmNoteIds':note_ids,
            'status':'Profile and asset matched',
            'evidenceCollectedAt':record['evidenceCollectedAt'],
            'evidenceBasis':'Exact canonical LinkedIn profile plus the same source Loom asset in CRM note '+', '.join(map(str,note_ids))+'. Original Sheet deal ID remains blank.'})
    filter_runs={1064:('0086536b-506f-a748-ec33-54d30466fea4','2026-10-21T15:30:26Z'),
                 1068:('0086536b-bdb8-ac38-ec80-a1901a6f0484','2026-10-21T15:26:51Z')}
    for record in crosswalk['nonUrlDatedRowsBoundedSearch']:
        run_id,at=filter_runs[record['sourceRow']]
        records.append({'sourceRow':record['sourceRow'],'company':record['company'],
            'contact':record['contact'],'profile':record['profileId'],
            'recordingFieldKind':'non_url_note','crmDealId':None,
            'status':'Non-URL DM note; run filtered',
            'runId':run_id,'runAt':at,
            'evidenceBasis':'Recording field contains a LinkedIn DM note, not a video URL. '
                'The structured Sent field was blank at trigger time and filtering stopped CRM creation. '
                'No expected Loom-specific sync failure is established; bounded CRM searches found no match.'})
    video['crmReconciliation']={'snapshotAt':reviewed,'reviewedAt':reviewed,
        'appliesToSnapshotAt':video['snapshotAt'],'cohortDate':'2026-10-21',
        'crmInventorySnapshotAt':data['crm']['snapshotAt'],
        'selfReportedSentRows':12,'validVideoAssetRows':10,'messageNoteWithoutAssetRows':2,
        'videoAssetCohortCrmMatches':10,'expectedVideoCrmMissing':0,
        'records':sorted(records,key=lambda r:r['sourceRow']),
        'undatedStatusReview':{'sourceRows':29,'currentCrmRecordsEvidenced':29,
            'sourceLoomUrls':26,'sameAssetInCrmNotes':25,
            'note':'These statuses lack send dates; current record presence does not establish period outreach or delivery.'},
        'specificLinkageGaps':copy.deepcopy(crosswalk['specificGaps']),
        'notes':['Zero missing records is scoped to the ten reviewed October 21 rows with Loom URLs, not all held trigger IDs or all outreach.',
            'All 29 exact undated Sent/Done source rows also have current CRM record evidence; no dated send total is inferred.',
            'Sonata has a source Loom URL absent from the reviewed CRM notes. Chromie retains deleted Sheet ID322 while matching current record836; no formal merge intent is inferred. Leo AI lacks a CRM profile URL but has an explicit source deal ID and matching recording note.',
            'Original worksheet deal IDs and all 33 dated status markers remain unchanged. The independent crosswalk does not write back to Sheets or Pipedrive.'],
        'limits':['Asset preparation, self-reported status and CRM presence do not independently establish actual sender, sending time or delivery.']}
    automation=video['automationReview']
    automation.update(snapshotAt=reviewed,reviewedAt=reviewed)
    automation['source'].update(triggerColumnName='Loom Link',filterColumn='COL$P',
        filterColumnName='Status (CS Column)',mappingDefectEstablished=False)
    history=automation['historyReview']
    history['reconciliation']={'reviewedAt':reviewed,'interpretation':'bulk_sheet_trigger_burst',
        'businessImpactEstablished':False,'sampledHeldRuns':6,'blankPayloadSamples':4,
        'prospectPayloadsWithoutSentStatus':2,
        'heldBurst':{'startAt':'2026-10-20T20:56:26Z','endAt':'2026-10-20T20:56:28Z'},
        'heldTimestampCounts':audit['heldTimestampClusters'],
        'sampleSelection':'Targeted sample spread through retained history, not a random or complete eligibility audit.',
        'note':'703 distinct held IDs cluster into one approximately two-second Google Sheets trigger burst. '
            'Four reviewed payloads contain only row identifiers/hash data; two contain prospect data with blank Sent and Loom fields. '
            'None of these six establishes an eligible sent-video CRM write. '
            'This is consistent with bulk-trigger flood protection; the exact initiating edit and all-row eligibility remain unverified.'}
    history['note']='All 85 retained pages were reviewed:841 displayed entries represent808 distinct IDs. '
    history['note']+='The 33 repeated IDs occur across adjacent pages with identical status/time. '
    history['note']+='Tied, non-atomic pagination can repeat or omit items; these are retained observations, not a certified complete execution census. '
    history['note']+='The703 held IDs are technical history, not an evidenced business-data deficit.'
    automation['limits']=['No held entries were replayed and no workflow configuration was changed.',
        'ColumnQ is Loom Link; columnP is the downstream Status filter. Different source fields alone do not establish a mapping defect.',
        'The verified October 21 ten-record Loom cohort is present in CRM. The703 held IDs do not establish703 intended syncs, missed messages or missing records.',
        'Waalaxy upstream synchronization and actual LinkedIn sender, sending time and delivery remain separate evidence gaps.']
    workflow=data['waalaxy']['workflowReview']
    workflow.update(snapshotAt=reviewed,reviewedAt=reviewed,
        note='October 21 ten-row Loom cohort has exact CRM profile/asset-note matches. '
            'The retained October 20 held-trigger burst does not establish missing outreach records. '
            'This Sheet-to-CRM reconciliation does not establish the Charles Waalaxy upstream account or last successful upstream sync.')
    for source in data['sources']:
        if source['id']=='zapier_execution':
            source.update(asOf=reviewed,note='Historical bulk Sheet-trigger burst, separate from business activity. '
                'Six targeted held inputs did not establish eligible sent-video syncs. October 21 ten-row Loom cohort is present in CRM; no703-record deficit is inferred.')
    ident='video_crm_reconciliation'
    card=next((s for s in data['sources'] if s['id']==ident),None)
    if card is None:
        card={'id':ident};data['sources'].append(card)
    card.update(name='Video DM recording fields and CRM crosswalk',asOf=reviewed,
        status='Current independent review; local only',
        note='57 valid Loom URLs and 3 non-URL notes across 60 populated recording cells. '
            'October 21:12 Sent labels,10 Loom URLs,10 exact CRM profile/asset-note matches and 2 non-URL DM notes. All 29 undated Sent/Done rows have current record evidence. No delivery inference.')
    data['meta'].update(generatedAt=datetime.now(timezone.utc).isoformat(),
        revision='October 22 trigger-burst interpretation, recording URL correction and verified CRM cohort; local only')
    data=curate_snapshot(data)
    assert old_ids=={r['sourceRow']:r.get('dealId') for r in data['video']['rows']}
    assert sum(r.get('hasRecordingLink',False) for r in data['video']['rows'])==57
    assert len(data['video']['datedActions'])==33 and data['meta']['public'] is False
    text=json.dumps(data,ensure_ascii=False,indent=2)+'\n'
    for name in ('dashboard.json','shared-dashboard.json'):
        (ROOT/'data'/name).write_text(text)
    print('Applied local trigger interpretation, 57 actual recording URLs and 10/10 verified CRM cohort matches.')


if __name__=='__main__':
    main()
