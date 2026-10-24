"""Curate bounded native-conversation observations with message-block anchoring.

Raw bodies remain private. Dates are displayed source days, never exact instants.
The requested asset must occur inside its own dated, authored message block.
"""
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import argparse
import copy
import hashlib
import json
import re

from apply_refresh_2026_10_23 import merge_message_review, event_key

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / 'data/private/gap_resolution_2026_10_24'
DATE = re.compile(r'^(?P<label>(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\s+\d{1,2}(?:,\s*\d{4})?|MONDAY|TUESDAY|WEDNESDAY|THURSDAY|FRIDAY|SATURDAY|SUNDAY)(?:\s|$)')
AUTHOR = re.compile(r'^(.*?) sent the following messages? at ([0-9]{1,2}:[0-9]{2}\s*[AP]M)$')
TIME = re.compile(r'^•\s*([0-9]{1,2}:[0-9]{2}\s*[AP]M)$')


def load(path):
    return json.loads(path.read_text())


def clean_name(value):
    return ''.join(c for c in value.casefold() if c.isalnum())


def parse_blocks(raw, contact):
    """Extract date/sender/time/body only within the captured conversation list."""
    assert 'Open the options list in your conversation with Charles Solomon and ' in raw
    assert clean_name(contact) in clean_name(raw), 'Wrong recipient excerpt'
    rows = raw.splitlines()
    started = False
    day = author = None
    current, blocks = None, []

    def finish():
        nonlocal current
        if current:
            current['privateContent'] = '\n'.join(current.pop('parts'))
            current['contentFingerprint'] = hashlib.sha256(current['privateContent'].encode()).hexdigest()
            blocks.append(current)
            current = None

    for line in rows:
        match = re.match(r'^\s*(?:\d+\s+)?(text|link|image|content list|button|heading|container)\s*(.*)$', line)
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
            if dm:
                finish()
                day = dm['label']
                value = value[dm.end():].strip()
            am = AUTHOR.match(value)
            if am:
                finish()
                author = am[1]
                continue
            tm = TIME.match(value)
            if tm:
                finish()
                assert day and author, 'Message time lacks a preceding date/sender'
                current = {'displayedDateLabel': day, 'sender': author, 'displayedTime': tm[1], 'parts': []}
                continue
            if current and value:
                current['parts'].append(value)
        elif kind == 'link':
            if value.startswith('View Charles’ profile Charles Solomon'):
                author = 'Charles Solomon'
            elif value.startswith('View ') and ' profile ' in value:
                # Recipient links confirm the next sender without copying their
                # entire link label into the preceding message's content.
                who = value.split(' profile ', 1)[1].split(', Value:', 1)[0]
                author = who
            elif current:
                # Keep the private link destination as well as its visible
                # label: a native preview may expose the exact Loom only in
                # Value, even when the message text is a shortened URL.
                if not value.startswith(('Charles Solomon', contact)):
                    current['parts'].append(value)
    finish()
    return blocks


def choose_block(blocks, label, shown_time, direction, contact, asset=None):
    candidates = [b for b in blocks if b['displayedDateLabel'] == label and b['displayedTime'] == shown_time
        and ((b['sender'] == 'Charles Solomon') == (direction == 'outbound'))]
    if direction == 'inbound':
        candidates = [b for b in candidates if clean_name(contact) in clean_name(b['sender'])]
    if asset:
        candidates = [b for b in candidates if re.search(r'(?:https?://)?(?:www\.)?loom\.com/share/' + re.escape(asset) + r'(?:\b|/|\?)', b['privateContent'])]
    assert len(candidates) == 1, f'Expected one authored dated message block, got {len(candidates)}: {label} {shown_time} {direction}'
    return candidates[0]


def resolve_day(label, resolved, observed_at):
    parsed = date.fromisoformat(resolved)
    observed = datetime.fromisoformat(observed_at.replace('Z', '+00:00')).astimezone(ZoneInfo('America/Denver')).date()
    assert parsed <= observed
    if label in {'MONDAY','TUESDAY','WEDNESDAY','THURSDAY','FRIDAY','SATURDAY','SUNDAY'}:
        assert parsed.strftime('%A').upper() == label and 0 <= (observed - parsed).days < 7
    else:
        expected = parsed.strftime('%b').upper() + ' ' + str(parsed.day)
        assert label == expected or label == expected + ', ' + str(parsed.year)
    return resolved


def current_join(review, video):
    by_profile = {}
    for row in video['rows']:
        by_profile.setdefault(row['id'], []).append(row)
    for event in review.get('platformObservedEvents', []):
        if event.get('sourceEvidenceBasis') != 'native_direct':
            continue
        rows = by_profile.get(event['profileId'], [])
        event['currentSourceRows'] = [r['sourceRow'] for r in rows]
        event['currentAssetSourceRows'] = [r['sourceRow'] for r in rows if event.get('assetId') and r.get('recordingAssetId') == event['assetId']]
        event['currentInventorySnapshotAt'] = video['snapshotAt']
        event['currentInventoryMatchBasis'] = 'Exact current worksheet profile; native message proof is independent of worksheet asset fields and CRM note contents.'
    return review


def build(before, private=PRIVATE):
    video = before['video']
    prior = video['messageDateReview']
    proof = private / 'native'
    cases = [
        ('caddi', 'alejandro-castellano', 'Alejandro Castellano'),
        ('eve', 'nadav-cornberg', 'Nadav Cornberg'),
        ('sonata', 'saganschultz', 'Sagan Schultz'),
        ('navigara', 'jirka-bachel', 'Jiri Bachel'),
        ('dark_watch', 'noeljthomas', 'Noel Thomas'),
        ('subimage', 'alexchantavy', 'Alex Chantavy'),
        ('saile', 'marcsayoub', 'Marc Ayoub'),
        ('sohar', 'ashishmandavia', 'Ashish Mandavia'),
    ]
    events, records, checks, provenance = [], [], [], []
    by_profile = {r['id']: r for r in video['rows']}
    for slug, profile, contact in cases:
        meta = load(proof / (slug + '_meta.json'))
        raw_path = proof / (slug + '.txt')
        raw = raw_path.read_text()
        assert meta['profile'] == profile and meta.get('account', 'Charles Solomon') == 'Charles Solomon'
        row = by_profile[profile]
        sheet_deal_id = int(row['dealId']) if str(row.get('dealId') or '').isdigit() else None
        blocks = parse_blocks(raw, contact)
        observed = meta['observedAt']
        observed_day = datetime.fromisoformat(observed.replace('Z', '+00:00')).astimezone(ZoneInfo('America/Denver')).date().isoformat()
        record = {'profileId': profile, 'sourceRow': row['sourceRow'], 'sourceRows': [row['sourceRow']],
            'company': row['company'], 'contact': row['contact'], 'linkedin': row['linkedin'],
            'platformEvidenceCollectedAt': observed, 'nativeDirectReviewCollectedAt': observed}
        check = {'profileId': profile, 'sourceRow': row['sourceRow'], 'observedAt': observed,
            'evidenceLink': row['linkedin'], 'sourceEvidenceBasis': 'native_direct',
            'profileIdentityVerified': True, 'senderAccount': 'Charles Solomon',
            'coverageCompleteForThread': False, 'crmAssetMatchRequiredForNativeProof': False}

        def add(label, shown_time, direction, resolved, kind, asset=None, video_included=False, **extra):
            block = choose_block(blocks, label, shown_time, direction, contact, asset)
            resolve_day(label, resolved, observed)
            if kind == 'video_reference':
                assert 'video' in block['privateContent'].casefold() and meta['observedVideoLink'] in block['privateContent']
            fingerprint = block['contentFingerprint']
            dedup = '|'.join((profile, direction, resolved, asset or shown_time + ':' + fingerprint))
            year_basis = ('observed_current_year_label_convention' if slug in ('caddi','sonata','saile') else
                'same_thread_explicit_prior_year_anchor' if slug == 'eve' else 'relative_weekday_with_observation_day')
            basis = meta.get('dateBasis') or meta.get('dateYearBasis') or ('Displayed Wednesday anchored to the October 24 observation; source timezone is unknown.' if label == 'WEDNESDAY' else meta.get('basis'))
            event = {'observationId': 'linkedin-ui:' + observed_day + ':' + profile + ':' + direction + ':' + hashlib.sha256(dedup.encode()).hexdigest()[:24],
                'dedupKey': dedup, 'sourceMessageId': None, 'sourceConversationId': None,
                'profileId': profile, 'company': row['company'], 'contact': row['contact'],
                'sourceRow': row['sourceRow'], 'sourceInventorySnapshotAt': video['snapshotAt'],
                'crmDealId': sheet_deal_id, 'sourceSheetDealId': sheet_deal_id, 'sourceKind': 'native_linkedin_existing_conversation',
                'sourceEvidenceBasis': 'native_direct', 'date': resolved,
                'datePrecision': 'day', 'occurredAt': None, 'sourceTimezone': None,
                'displayedDateLabel': label, 'displayedTime': shown_time,
                'contentFingerprint': fingerprint, 'observedAsOfDate': observed_day,
                'dateBasis': basis, 'dateYearBasis': year_basis,
                'dateYearConfidence': 'moderate' if slug in ('caddi','sonata','saile') else 'high',
                'channel': 'linkedin_message', 'direction': direction, 'sender': block['sender'],
                'messageKind': kind, 'videoIncluded': video_included, 'assetId': asset,
                'assetLink': 'https://www.loom.com/share/' + asset if asset else None,
                'evidenceLink': row['linkedin'], 'observedAt': observed,
                'profileIdentityVerified': True, 'senderVerifiedWithinMessageBlock': True,
                'dateTimeAssetAnchoredWithinSameMessageBlock': bool(asset),
                'evidenceBasis': 'Exact recipient profile and displayed sender/date/time verified within this specific native message block. CRM note contents and worksheet statuses do not establish or invalidate the observed message.',
                'replyToVideoAttributionEstablished': False,
                'platformReadReceiptObserved': False, 'readReceiptDate': None}
            event.update(extra)
            events.append(event)
            return event

        if slug == 'caddi':
            asset = meta['expectedAssetId']
            add(meta['displayedSendDay'], meta['displayedSendTime'], 'outbound', meta['sendDate'], 'video', asset, True)
            add(meta['displayedFollowUpDay'], meta['displayedFollowUpTime'], 'outbound', meta['followUpDate'], 'video_follow_up')
            add(meta['displayedReplyDay'], meta['displayedReplyTime'], 'inbound', meta['replyDate'], 'reply',
                replyToVideoAttributionEstablished=True, replyToVideoAssetId=asset,
                attributionBasis='Direct response to Charles explicit same-day video follow-up', replyMeaning='declined')
            record.update(platformSendDate=meta['sendDate'], platformReplyDate=meta['replyDate'],
                platformReplyVideoAttributionEstablished=True, platformVideoAttributionEstablished=True,
                platformCheckStatus='matched_native_direct', nativeAssetId=asset)
            check.update(status='matched_native_direct', assetId=asset, platformSendDate=meta['sendDate'], platformReplyDate=meta['replyDate'],
                replyToVideoAttributionEstablished=True, replyMeaning='declined', assetObserved=True)
        elif slug in ('eve', 'saile'):
            asset = meta['assetId']
            add(meta['displayedSendDay'], meta['displayedSendTime'], 'outbound', meta['sendDate'], 'video', asset, True)
            add(meta['displayedFollowUpDay'], meta['displayedFollowUpTime'], 'outbound', meta['followUpDate'], 'video_follow_up')
            record.update(platformSendDate=meta['sendDate'], platformVideoAttributionEstablished=True,
                platformCheckStatus='matched_native_direct', nativeAssetId=asset,
                nativeAssetDoesNotPopulateSourceRecordingField=True)
            check.update(status='matched_native_direct', assetId=asset, platformSendDate=meta['sendDate'], assetObserved=True,
                replyObservation='No incoming reply visible in this bounded excerpt; no claim of complete thread coverage.')
        elif slug == 'sonata':
            add(meta['displayedSendDay'], meta['displayedSendTime'], 'outbound', meta['videoReferenceMessageDate'], 'video_reference',
                video_included=None, videoReferenceObserved=True, observedShortLink=meta['observedVideoLink'], shortLinkDestinationVerified=False)
            add(meta['displayedFollowUpDay'], meta['displayedFollowUpTime'], 'outbound', meta['followUpDate'], 'video_follow_up')
            record.update(platformVideoReferenceDate=meta['videoReferenceMessageDate'], platformFollowUpDate=meta['followUpDate'],
                platformCheckStatus='video_reference_asset_unconfirmed', platformVideoAttributionEstablished=False,
                expectedSourceAssetId=meta['expectedAssetId'], shortLinkDestinationVerified=False)
            check.update(status='video_reference_asset_unconfirmed', assetObserved=False, expectedAssetId=meta['expectedAssetId'],
                platformVideoReferenceDate=meta['videoReferenceMessageDate'], platformFollowUpDate=meta['followUpDate'])
        elif slug == 'navigara':
            add(meta['displayedDay'], meta['outboundTime'], 'outbound', meta['date'], 'general_text')
            add(meta['displayedDay'], meta['inboundTime'], 'inbound', meta['date'], 'general_reply')
            add(meta['displayedDay'], '9:35 AM', 'outbound', meta['date'], 'general_text')
            record.update(platformReplyDate=meta['date'], platformReplyVideoAttributionEstablished=False,
                platformCheckStatus='general_text_observed', platformVideoAttributionEstablished=False,
                nativeLatestSequenceContainsVideoAsset=False)
            check.update(status='general_text_observed', assetObserved=False, platformReplyDate=meta['date'],
                replyToVideoAttributionEstablished=False, replyMeaning='willing_to_connect_not_a_held_meeting')
        elif slug == 'dark_watch':
            add(meta['displayedDay'], meta['displayedSendTime'], 'outbound', meta['date'], 'general_text')
            record.update(platformCheckStatus='general_text_observed', platformVideoAttributionEstablished=False,
                nativeLatestSequenceContainsVideoAsset=False)
            check.update(status='general_text_observed', assetObserved=False,
                replyObservation='No October reply visible; older April reply is outside this reviewed sequence.')
        elif slug == 'sohar':
            add(meta['displayedFollowUpDay'], meta['displayedFollowUpTime'], 'outbound', meta['followUpDate'], 'general_text')
            record.update(platformFollowUpDate=meta['followUpDate'], platformCheckStatus='general_text_observed',
                platformVideoAttributionEstablished=False, nativeLatestSequenceContainsVideoAsset=False)
            check.update(status='general_text_observed', assetObserved=False, platformFollowUpDate=meta['followUpDate'],
                replyObservation='No incoming reply visible in the current-period sequence; older 2025 replies are separate.')
        else:
            assert meta['expectedAssetId'] not in raw, 'Expected asset is now present; revise the explicit check'
            record.update(platformCheckStatus='checked_unconfirmed', platformVideoAttributionEstablished=False)
            check.update(status='checked_unconfirmed', assetObserved=False, expectedAssetId=meta['expectedAssetId'],
                basis='Matching asset was not established in the bounded excerpt; no non-send or deletion is inferred.')
        records.append(record)
        checks.append(check)
        provenance.append({'profileId': profile, 'sourceFile': str(raw_path.relative_to(ROOT)),
            'sha256': hashlib.sha256(raw_path.read_bytes()).hexdigest(), 'observedAt': observed,
            'parsedMessageBlocks': len(blocks)})
    latest = max(c['observedAt'] for c in checks)
    focused = {'snapshotAt': latest, 'reviewedAt': latest, 'scope': 'Eight targeted native thread checks; not a complete account or thread message census.',
        'profileChecks': checks, 'profilesChecked': len(checks), 'newHistoricalSeptemberVideoSends': 3,
        'newHistoricalSeptemberAttributedReplies': 1, 'sourceTimezone': None,
        'notes': ['Legacy 19-profile October asset cohort retains its original scope and collection clock.',
            'Current-year omitted year labels for Caddi/Sonata/Saile use the observed authenticated account convention; year confidence is moderate. Eve has an explicit prior-year chronology in the same thread.',
            'Native messages are independently verified; a missing CRM note or blank worksheet asset does not negate the observed message.',
            'No source edits, held calls, qualification or opportunity decisions are established by these checks.']}
    partial = {'snapshotAt': latest, 'reviewedAt': latest,
        'scope': {'videoSnapshotAt': video['snapshotAt'], 'focusedNativeReviewedAt': latest,
            'focusedNativeProfilesReviewed': [r['profileId'] for r in checks], 'coverageCompleteForAllVideoDmMessages': False},
        'records': records, 'platformObservedEvents': events, 'focusedNativeReviews': focused}
    review = current_join(merge_message_review(prior, partial, video, before['waalaxy'].get('sheetSubset'), before['waalaxy'].get('sheetSubsetCollectedAt')), video)
    review['summary'].update(newVerifiedVideoSendEventsAdded=3, newVerifiedVideoReplyEventsAdded=1,
        newHistoricalSeptemberVideoSendsAdded=3, newOctoberObservedVideoSendsAdded=0,
        retainedObservedVideoReplyEvents=sum(e.get('direction') == 'inbound' and e.get('replyToVideoAttributionEstablished') is True for e in review['platformObservedEvents']))
    review['notes'].append('October 24 targeted checks add three historical September video sends and one attributed September declined reply. October verified video sends remain 18; source literal date/status reports are unchanged. Navigara/Dark Watch latest October messages are general text, and Sonata is a video reference with an unverified short-link destination.')
    assert len(events) == 14 and sum(bool(e.get('videoIncluded')) for e in events) == 3
    assert len({event_key(e) for e in events}) == len(events), 'Same-day text observations collided'
    assert {event_key(e) for e in prior['platformObservedEvents']} <= {event_key(e) for e in review['platformObservedEvents']}
    assert sum(e.get('direction') == 'outbound' and bool(e.get('videoIncluded')) and e['date'].startswith('2026-10') for e in review['platformObservedEvents']) == 18
    return {'replacementMode': 'complete_review_bundle', 'completeReviewBundle': True, 'review': review}, provenance


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=ROOT / 'data/shared-dashboard.json')
    parser.add_argument('--private-dir', type=Path, default=PRIVATE)
    args = parser.parse_args()
    bundle, provenance = build(load(args.input), args.private_dir)
    for name, value in [('native_message_review_patch.json', bundle), ('normalization_provenance_private.json', provenance)]:
        (args.private_dir / 'native' / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    review = bundle['review']
    print(json.dumps({'events': len(review['platformObservedEvents']), 'observedVideoSends': review['summary']['retainedObservedVideoSendEvents'],
        'attributedVideoReplies': review['summary']['retainedObservedVideoReplyEvents'], 'OctoberObservedVideoSends': 18}))


if __name__ == '__main__':
    main()
