"""Prepare source-reported dates and a bounded CRM audit, not inferred Video DM delivery."""
from pathlib import Path
from datetime import datetime
import hashlib
import html
import json
import re

ROOT=Path(__file__).resolve().parents[1]
PRIVATE=ROOT/'data/private/video_dm_event_review_2026_10_22'


def source_body(path):
    wrapped=json.loads(path.read_text())
    result=wrapped.get('result',wrapped)
    if 'content' in result:
        assert not result.get('isError'),f'Unsuccessful source response:{path.name}'
        result=json.loads(next(c['text'] for c in result['content'] if c['type']=='text'))
    assert result.get('success') is True,f'Unsuccessful API response:{path.name}'
    return wrapped,result


def build(data):
    manifest=json.loads((PRIVATE/'collection_manifest.json').read_text())
    assert manifest['complete'] and manifest['readOnly']
    video=data['video'];waalaxy=data['waalaxy']
    people={r['profileId']:r for r in waalaxy['sheetSubset']['rows']}
    dated_sends={e['contactId']:e for e in video['datedActions'] if e['type']=='Send status'}
    # This source explicitly reports an earlier reply date. Its note-creation
    # timestamp is retained separately and is never used as the reply date.
    _,body=source_body(PRIVATE/'notes_241_0.json')
    reply_note=next(n for n in body['data'] if n['id']==972)
    plain=html.unescape(re.sub(r'<[^>]*>',' ',reply_note['content']))
    assert re.search(r'responded positively\s+4\.29\.26',plain,re.I)
    reply_profile=next(r for r in video['rows'] if r.get('dealId')==241)
    reply_report={'eventId':'pipedrive-note:972:reported-reply:2026-04-29',
        'profileId':reply_profile['id'],'company':reply_profile['company'],
        'contact':reply_profile['contact'],'crmDealId':241,'sourceNoteId':972,
        'reportedReplyDate':'2026-04-29','datePrecision':'day','occurredAt':None,
        'sourceTimezone':None,'channel':'unspecified','videoIncluded':None,
        'sourceKind':'explicit_crm_note_report','sourceNoteRecordedAt':reply_note['add_time'],
        'evidenceLink':'https://centripetaladvisors.pipedrive.com/deal/241',
        'basis':'The CRM note explicitly reports an April 29 reply. This is not a platform message receipt and does not establish video attribution, qualification, a held call or a new commercial outcome.'}
    records=[];by_profile={}
    for row in video['rows']:
        person=people.get(row['id'],{})
        send=dated_sends.get(row['id'])
        report=reply_report if row['id']==reply_report['profileId'] else None
        if not (send or person.get('firstMessageAt') or person.get('lastMessageAt') or person.get('lastReplyAt') or report):continue
        if row['id'] in by_profile:
            record=by_profile[row['id']]
            record['sourceRows'].append(row['sourceRow'])
            if row.get('dealId') and row['dealId'] not in record['sourceDealIds']:
                record['sourceDealIds'].append(row['dealId'])
            continue
        record={'profileId':row['id'],'sourceRow':row['sourceRow'],'sourceRows':[row['sourceRow']],
            'company':row['company'],'contact':row['contact'],'linkedin':row['linkedin'],
            'sheetDealId':row.get('dealId'),'sourceDealIds':[row['dealId']] if row.get('dealId') else [],
            'matchedCrmDealId':row.get('matchedCrmDealId'),
            'reportedSendDate':send['date'] if send else None,
            'reportedSendBasis':'Dated worksheet Sent status; sender, channel/content and delivery unverified' if send else None,
            'hasRecordingAssetReference':bool(row.get('hasRecordingLink')),
            'firstLinkedInMessageDate':person.get('firstMessageAt') or None,
            'latestLinkedInMessageDate':person.get('lastMessageAt') or None,
            'latestLinkedInReplyDate':person.get('lastReplyAt') or None,
            'reportedReplyDate':report['reportedReplyDate'] if report else None,
            'reportedReplyNoteId':report['sourceNoteId'] if report else None,
            'historySource':'Retained Waalaxy selected-person dates via exact canonical profile match' if person else None,
            'historyDatePrecision':'day' if person else None,'historySourceTimezone':None,
            'historySenderAccountId':None,'videoAttributionEstablished':False,
            'basis':'Dates are independently labelled source attributes, not a delivered-video event log. Latest/first person dates are not all message events and do not establish a count or a video reply.'}
        records.append(record);by_profile[row['id']]=record
    notes=[];mail=[];activities=[]
    for path in PRIVATE.glob('notes_*.json'):
        _,value=source_body(path);notes.extend(value.get('data') or [])
    for path in PRIVATE.glob('mail_*.json'):
        _,value=source_body(path);mail.extend(w['data'] for w in value.get('data') or [])
    for path in PRIVATE.glob('activities_*.json'):
        _,value=source_body(path);activities.extend(value.get('data') or [])
    target_ids=set(manifest['targetDeals'])
    related=[a for a in activities if a.get('deal_id') in target_ids]
    sent=[m for m in mail if m.get('sent_flag')==1 and not m.get('draft_flag')]
    assert len({n['id'] for n in notes})==len(notes)
    assert len({m['id'] for m in mail})==len(mail)
    assert len({a['id'] for a in activities})==len(activities)
    assert all(not re.search(r'loom\.com/share',m.get('body') or '',re.I) for m in sent)
    # This is context only. Explicit message_time supplies an actual email send
    # timestamp; neither email delivery nor video DM delivery is inferred.
    email_context=[{'eventId':f"pipedrive-mail:{m['id']}",'sourceMessageId':m['id'],
        'crmDealId':m['deal_id'],'occurredAt':m['message_time'],'sourceTimezone':'UTC',
        'channel':'email','direction':'outbound','sender':'Charles Solomon',
        'loomShareLinkPresent':False,'videoIncluded':None,'includeInVideoDmTotals':False,
        'evidenceLink':f"https://centripetaladvisors.pipedrive.com/deal/{m['deal_id']}"}
        for m in sent]
    joined=[r for r in video['rows'] if r['id'] in people]
    patch={'snapshotAt':manifest['completedAt'],'reviewedAt':manifest['completedAt'],
        'scope':{'videoSnapshotAt':video['snapshotAt'],
            'crmCollectionCompletedAt':manifest['completedAt'],
            'videoRowsSha256':hashlib.sha256(json.dumps(video['rows'],sort_keys=True).encode()).hexdigest(),
            'personHistoryCollectedAt':waalaxy.get('sheetSubsetCollectedAt'),
            'personHistoryScope':waalaxy['sheetSubset']['scope'],
            'exactProfileMatches':len({r['id'] for r in joined}),'matchedVideoRows':len(joined),
            'crmDealsReviewed':len(target_ids),
            'crmNotesReviewed':len(notes),'relatedMailRowsReviewed':len(mail),
            'allOwnerActivitiesReviewed':len(activities),'relatedActivitiesReviewed':len(related),
            'coverageCompleteForAllVideoDmMessages':False},
        'summary':{'rowsWithReportedSendDate':sum(bool(r['reportedSendDate']) for r in records),
            'profilesWithFirstLinkedInMessageDate':sum(bool(r['firstLinkedInMessageDate']) for r in records),
            'profilesWithLatestLinkedInMessageDate':sum(bool(r['latestLinkedInMessageDate']) for r in records),
            'profilesWithLatestLinkedInReplyDate':sum(bool(r['latestLinkedInReplyDate']) for r in records),
            'explicitCrmReplyDateReports':1,'relatedActualOutboundEmails':len(sent),
            'excludedEmailDrafts':sum(bool(m.get('draft_flag')) for m in mail),
            'newVerifiedVideoSendEventsAdded':0,'newVerifiedVideoReplyEventsAdded':0,
            'accountWideActualVideoSends':None,'accountWideActualVideoReplies':None},
        'records':records,'explicitReplyReports':[reply_report],
        'separateEmailContext':email_context,
        'notes':[
            'Existing worksheet Send status dates are exposed as reported dates; these are not additional sends.',
            'The ten October 21 video-asset CRM matches establish source provenance. Their note timestamps reflect synchronization; native message corroboration, when available, is recorded separately.',
            'Retained Waalaxy first/latest LinkedIn dates are person attributes with date-only precision. Actual sender identity and video inclusion are unverified.',
            'One CRM note explicitly reports an April 29 reply. Its May 1 note creation date is not the reply date; commercial outcome classifications are unchanged.',
            'Associated mail evidence is historical email, kept separate from Video DM reporting. The unsent draft is excluded.',
            'CRM task due/completion timestamps and planned sequence dates are not actual sends. No replay, outreach or source record changes were performed.'
        ]}
    # Optional private browser observations survive regeneration of the CRM
    # audit. Native UI evidence is deliberately bounded to the reviewed
    # conversations, with day-only dates and no fabricated message timestamp.
    platform_path=PRIVATE/'platform_observations.json'
    if platform_path.exists():
        platform=json.loads(platform_path.read_text())
        events=platform['platformObservedEvents']
        assert len({e['dedupKey'] for e in events})==len(events)
        assert all(e.get('occurredAt') is None and e.get('sourceTimezone') is None for e in events)
        assert all(e['datePrecision']=='day' and e['dateBasis'] for e in events)
        assert all(e['sourceKind']=='native_linkedin_existing_conversation' for e in events)
        patch['snapshotAt']=max(patch['snapshotAt'],platform['reviewedAt'])
        patch['reviewedAt']=patch['snapshotAt']
        patch['scope']['nativeConversationProfilesReviewed']=platform['profilesReviewed']
        patch['scope']['nativeConversationReviewedAt']=platform['reviewedAt']
        patch['platformObservedEvents']=events
        patch['nativePlatformCoverage']=platform['nativePlatformCoverage']
        for check in platform['nativePlatformCoverage']['profileChecks']:
            record=by_profile[check['profileId']]
            record['platformCheckStatus']=check['status']
            record['platformReplyObservation']=check['replyObservation']
        for e in events:
            record=by_profile[e['profileId']]
            if e['direction']=='outbound' and e['videoIncluded']:
                assert e['assetId'] and record['reportedSendDate']==e['date']
                record['platformSendDate']=e['date']
                record['platformSendDateBasis']=e['dateBasis']
                record['platformVideoAttributionEstablished']=True
            elif e['direction']=='inbound':
                record['platformReplyDate']=e['date']
                record['platformReplyDateBasis']=e['dateBasis']
                record['platformReplyVideoAttributionEstablished']=False
        patch['summary']['newVerifiedVideoSendEventsAdded']=sum(e['direction']=='outbound' and e['videoIncluded'] is True for e in events)
        patch['summary']['newVerifiedVideoReplyEventsAdded']=sum(e['direction']=='inbound' and e['videoIncluded'] is True for e in events)
        patch['summary']['previouslyReportedSendsCorroborated']=patch['summary']['newVerifiedVideoSendEventsAdded']
        patch['summary']['additionalSendsAboveExistingReportedStatusCount']=0
        patch['notes'].extend(platform['notes'])
    return patch


if __name__=='__main__':
    data=json.loads((ROOT/'data/shared-dashboard.json').read_text())
    patch=build(data)
    out=PRIVATE/'video_message_dates_patch.json'
    out.write_text(json.dumps(patch,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'output':str(out),'scope':patch['scope'],'summary':patch['summary']}))
