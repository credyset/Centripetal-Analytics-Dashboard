"""Propose undated Seen-marker corrections for explicitly reviewed message blocks.

No message body or private telephone number is published. An undated LinkedIn
Seen marker describes that message; it supplies no receipt date, video play,
reply, qualified prospect or commercial outcome.
"""
from pathlib import Path
from datetime import datetime, timezone
import copy
import hashlib
import json
import re

from normalize_native_refresh_2026_10_28 import (AX, blocks_for, guarded_excerpt,
    selected_block, recipient_matches, make_event)
from normalize_native_gaps_2026_10_24 import DATE, AUTHOR, TIME
from apply_refresh_2026_10_23 import event_key

ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT / 'data/private/refresh_2026_10_28/native'
OUTPUT = ROOT / 'data/private/published_gap_audit_2026_10_29/sheets'
SEEN = re.compile(r'^Seen by (.+?) at ([0-9]{1,2}:[0-9]{2}\s*[AP]M)\.$')
# Only these six explicit selections were manually reviewed for this audit.
# Other visible thread markers are not borrowed by a newly selected message.
CASES = ['adamfreed','apaluma','dankatzman','samira-daswani','seckin-secilmis','yihhanma']
NEGATIVE_CASES = ['grant-siders-0860354b','rkhardalian']


def receipt_blocks(raw, meta):
    """Track actual image controls using the same message boundaries as the parser."""
    ordinary, _ = blocks_for(raw, meta)
    excerpt, _ = guarded_excerpt(raw, meta)
    day = author = None
    started = False
    current = None
    result = []

    def finish():
        nonlocal current
        if current:
            current['privateContent'] = '\n'.join(current.pop('parts'))
            current['contentFingerprint'] = hashlib.sha256(current['privateContent'].encode()).hexdigest()
            result.append(current)
            current = None

    for line_number, line in enumerate(excerpt.splitlines(), 1):
        match = AX.match(line)
        if not match:
            continue
        kind, value = match.groups()
        if kind == 'content list':
            started = True
            continue
        if not started:
            continue
        if kind == 'text' and value.startswith('entry area '):
            break
        if kind == 'text':
            dm = DATE.match(value)
            if dm or value in {'TODAY','YESTERDAY'}:
                finish()
                day = dm['label'] if dm else value
                value = value[dm.end():].strip() if dm else ''
            am = AUTHOR.match(value)
            if am:
                finish(); author = am[1]; continue
            tm = TIME.match(value)
            if tm:
                finish()
                assert day and author
                current = {'displayedDateLabel':day,'sender':author,'displayedTime':tm[1], 'parts':[], 'seenMarkers':[]}
                continue
            if current and value:
                current['parts'].append(value)
        elif kind == 'link':
            if value.startswith('View Charles’ profile Charles Solomon'):
                author = 'Charles Solomon'
            elif value.startswith('View ') and ' profile ' in value:
                author = value.split(' profile ',1)[1].split(', Value:',1)[0]
            elif current and not value.startswith(('Charles Solomon',meta['contact'])):
                current['parts'].append(value)
        elif kind == 'image' and value.startswith('Seen by '):
            assert current and current['parts'], 'Seen marker has no preceding authored message body'
            shown = SEEN.fullmatch(value)
            assert shown, 'Unreviewed Seen-label structure'
            current['seenMarkers'].append({'privateDisplayedLabel':value,'recipient':shown[1],
                'displayedTimeWithoutDate':shown[2], 'sourceExcerptLine':line_number})
    finish()
    compare = lambda block: tuple(block[k] for k in ('displayedDateLabel','sender','displayedTime','contentFingerprint'))
    assert [compare(b) for b in result] == [compare(b) for b in ordinary], 'Receipt scanner diverged from exact authored message boundaries'
    return result


def selected_receipt(raw, meta, selection):
    blocks = receipt_blocks(raw,meta)
    block = selected_block(blocks,selection,meta)
    assert selection['direction']=='outbound' and block['sender']=='Charles Solomon', 'Only verified outbound selected blocks are eligible'
    assert len(block['seenMarkers']) == 1, 'The selected message needs one own Seen marker; another message marker cannot be borrowed'
    marker = block['seenMarkers'][0]
    assert recipient_matches(marker['recipient'],meta['contact']), 'Seen recipient differs from this verified message recipient'
    return block, marker


def build(snapshot, validated_at, native=NATIVE):
    video = snapshot['video']
    prior = video['messageDateReview']['platformObservedEvents']
    rows = {r['id']:r for r in video['rows']}
    changes, public_records, private_provenance = [], [], []
    for case in CASES:
        meta = json.loads((native/(case+'_meta.json')).read_text())
        assert len(meta['selections']) == 1, 'Receipt case needs one explicit reviewed message selection'
        selection = meta['selections'][0]
        raw = (native/(case+'.txt')).read_text()
        block, marker = selected_receipt(raw,meta,selection)
        selected_event = make_event(meta,selection,block,rows[meta['profile']],video)
        existing = [e for e in prior if event_key(e)==event_key(selected_event)]
        assert len(existing)==1, 'Seen correction has no unique existing observed message'
        existing = existing[0]
        assert existing['observedAt']==meta['observedAt'] and existing['contentFingerprint']==block['contentFingerprint'], 'Original observation/capture identity changed'
        assert existing.get('platformReadReceiptObserved') is False and existing.get('readReceiptDate') is None
        fields = {'platformReadReceiptObserved':True, 'readReceiptDate':None,
            'readReceiptBasis':'An undated native LinkedIn Seen marker for the verified recipient occurs inside this exact selected authored/date/time message block. It establishes no receipt date, video play or reply.',
            'readReceiptSourceObservedAt':meta['observedAt'], 'readReceiptValidatedAt':validated_at,
            'readReceiptAppliesTo':'linkedin_message_only', 'loomVideoViewedEstablished':False}
        changes.append({'observationId':existing['observationId'], 'eventKey':event_key(existing),
            'profileId':existing['profileId'], 'date':existing['date'],
            'originalObservedAt':existing['observedAt'], 'contentFingerprint':existing['contentFingerprint'], 'fields':fields})
        public_records.append({'profileId':existing['profileId'],'company':existing['company'],'contact':existing['contact'],
            'messageDate':existing['date'],'messageKind':existing.get('messageKind'), 'messageObservationId':existing['observationId'],
            'sourceObservedAt':meta['observedAt'], 'validatedAt':validated_at, 'seenMarkerObserved':True,
            'readReceiptDate':None, 'receiptDateEstablished':False, 'videoViewedEstablished':False,
            'exactMessageBlockMatched':True, 'newReplyOrCommercialOutcomeAdded':False})
        private_provenance.append({'profileId':existing['profileId'], 'sourceCase':case,
            'sourceSha256':hashlib.sha256(raw.encode()).hexdigest(), 'displayedDateLabel':selection['dateLabel'],
            'displayedMessageTime':selection['time'], **marker})
    negatives = []
    for case in NEGATIVE_CASES:
        meta = json.loads((native/(case+'_meta.json')).read_text()); raw = (native/(case+'.txt')).read_text()
        blocks = receipt_blocks(raw,meta)
        selected = selected_block(blocks,meta['selections'][0],meta)
        assert not selected['seenMarkers'] and any(b['seenMarkers'] for b in blocks), 'Negative-case scope changed; review explicitly'
        negatives.append({'profileId':meta['profile'], 'selectedDate':meta['selections'][0]['date'],
            'selectedMessageHasOwnSeenMarker':False, 'earlierMessageMarkerNotBorrowed':True, 'sourceObservedAt':meta['observedAt']})
    assert len(changes)==6 and sum(r['messageKind']=='video' for r in public_records)==1
    review = {'snapshotAt':validated_at,'reviewedAt':validated_at,'scope':'Six explicitly reviewed selected message blocks with own undated Seen markers; two old-message negative controls. Not a complete message-read census.',
        'appliesToVideoInventorySnapshotAt':video['snapshotAt'], 'records':public_records,
        'negativeControls':negatives, 'observedMarkerCorrections':6, 'videoMessages':1, 'textFollowUpMessages':5,
        'newSourceDataCollected':False,'originalCaptureClocksPreserved':True,'readReceiptDatesAdded':0,
        'videoPlayEventsAdded':0,'nativeMessageEventsAdded':0,'replyEventsAdded':0,'commercialOutcomesAdded':0}
    return {'reviewedAt':validated_at,'changes':changes}, review, private_provenance


def main():
    snapshot = json.loads((ROOT/'data/shared-dashboard.json').read_text())
    validated = datetime.now(timezone.utc).isoformat()
    changes, review, provenance = build(snapshot,validated)
    field_audit = json.loads((OUTPUT/'videoSourceFieldAuditReview_patch.json').read_text())
    field_audit['nativeSeenMarkerReview'] = review
    for name,value in [('nativeSeenMarkerCorrections_patch.json',changes),('nativeSeenMarkerReview_patch.json',review),
        ('videoSourceFieldAuditReview_with_receipts_patch.json',field_audit),('native_seen_provenance_private.json',provenance)]:
        (OUTPUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'validatedAt':validated,'existingEventFlagsCorrected':len(changes['changes']),
        'newEvents':0,'readReceiptDatesAdded':0,'videoPlaysInferred':0,'negativeControlsPassed':len(review['negativeControls'])}))


if __name__=='__main__':
    main()
