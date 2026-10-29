"""Normalize explicitly reviewed native LinkedIn blocks without publishing bodies.

Each case has <slug>.txt and <slug>_meta.json under the private native directory.
Metadata: profile, contact, company, account='Charles Solomon', observedAt,
profileIdentityVerified=true, selections=[{dateLabel,time,direction,date,kind,
asset?}]. Compose-history captures additionally require sourceLayout and
recipientControlVerified=true. Selections are human/agent-reviewed anchors,
never a classifier's guesses. Source days have unknown timezone, no UTC instant.
"""
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import argparse
import copy
import hashlib
import json
import re

from apply_refresh_2026_10_23 import event_key, merge_message_review, assert_curated
from normalize_native_gaps_2026_10_24 import clean_name, parse_blocks, current_join

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / 'data/private/refresh_2026_10_28'
AX = re.compile(r'^\s*(?:\d+\s+)?(text|link|image|content list|button|heading|container)\s*(.*)$')
LOOM = re.compile(r'(?:https?://)?(?:www\.)?loom\.com/share/([0-9a-f]{32})(?:\b|/|\?)', re.I)
WEEKDAYS = {'MONDAY','TUESDAY','WEDNESDAY','THURSDAY','FRIDAY','SATURDAY','SUNDAY'}
KINDS = {'video','video_follow_up','follow_up','general_text','general_reply','reply','video_reference'}


def load(path):
    return json.loads(Path(path).read_text())


def shown_time(value):
    return re.sub(r'\s+', '', value).upper()


def recipient_matches(actual, expected):
    """Match whole name tokens, allowing verified middle names/credentials."""
    actual = actual.split(', Value:', 1)[0].split(',', 1)[0]
    actual_tokens = re.findall(r'\w+', actual.casefold())
    expected_tokens = re.findall(r'\w+', expected.casefold())
    if not actual_tokens or not expected_tokens:
        return False
    # A root-verified profile supplies identity; this second guard requires its
    # first/last names in order, rather than unsafe substring matching.
    if actual_tokens[0] != expected_tokens[0] or actual_tokens[-1] != expected_tokens[-1]:
        return False
    positions = iter(actual_tokens)
    return all(any(token == candidate for candidate in positions) for token in expected_tokens)


def guarded_excerpt(raw, meta):
    assert meta.get('account') == 'Charles Solomon', 'Wrong sender account'
    assert meta.get('profileIdentityVerified') is True, 'Actual profile URL has not been verified'
    contact = meta['contact']
    lines = raw.splitlines()
    markers = []
    prefix = 'Open the options list in your conversation with '
    for i, line in enumerate(lines):
        match = AX.match(line)
        if match and match[1] == 'button' and match[2].startswith(prefix):
            parties = match[2][len(prefix):].split(' and ')
            if len(parties) == 2 and any(clean_name(p) == 'charlessolomon' for p in parties):
                recipient = next((p for p in parties if clean_name(p) != 'charlessolomon'), '')
                if recipient_matches(recipient, contact):
                    markers.append(i)
    if markers:
        assert len(markers) == 1, 'Ambiguous target conversation marker'
        start = markers[0]
        guard = 'real_options_participants_and_verified_profile'
    else:
        assert meta.get('sourceLayout') == 'existing_history_in_compose_view', 'No verified target conversation marker'
        assert meta.get('recipientControlVerified') is True, 'Compose recipient control is unverified'
        removals = []
        for i, line in enumerate(lines):
            match = AX.match(line)
            if match and match[1] == 'button' and match[2].startswith('Remove '):
                removals.append((i, match[2][7:]))
        assert len(removals) == 1 and recipient_matches(removals[0][1], contact), 'Wrong or multiple compose recipients'
        assert any(re.search(r'\bheading New message(?:,|$)', line) for line in lines[:removals[0][0]+1]), 'Not an existing-history compose capture'
        assert 'Enter message recipients' in raw, 'Missing real recipient control'
        start = removals[0][0]
        guard = 'real_single_recipient_compose_control_and_verified_profile'
    # Stop at this recipient's composer; unrelated later overlays cannot supply
    # missing dates, senders, assets or reply evidence.
    stop = next((i + 1 for i in range(start, len(lines)) if re.search(r'\btext entry area ', lines[i])), len(lines))
    excerpt = '\n'.join(lines[start:stop])
    assert 'content list' in excerpt, 'No captured historical message list'
    assert not any(prefix in line for line in lines[start+1:stop]), 'Another recipient enters the bounded excerpt'
    return excerpt, guard


def reference_day(meta):
    observed = datetime.fromisoformat(meta['observedAt'].replace('Z', '+00:00'))
    assert observed.tzinfo is not None, 'Observation clock lacks timezone'
    mountain_day = observed.astimezone(ZoneInfo('America/Denver')).date()
    reference = date.fromisoformat(meta.get('sourceReferenceDate', mountain_day.isoformat()))
    if reference != mountain_day:
        assert meta.get('sourceReferenceDateBasis') and abs((reference - mountain_day).days) <= 1, 'Unjustified displayed-calendar reference day'
    return reference


def resolve_selection_day(label, resolved, meta):
    actual = date.fromisoformat(resolved)
    reference = reference_day(meta)
    assert actual <= reference, 'A displayed message cannot occur after the observed source calendar day'
    if label in WEEKDAYS:
        assert actual.strftime('%A').upper() == label and 0 <= (reference - actual).days < 7, 'Weekday is outside the observation week'
        return 'relative_weekday_with_known_observation_day', 'high'
    if label in {'TODAY', 'YESTERDAY'}:
        assert actual == reference - timedelta(days=label == 'YESTERDAY'), 'Relative day contradicts the source reference day'
        return 'relative_day_with_known_observation_day', 'high'
    expected = actual.strftime('%b').upper() + ' ' + str(actual.day)
    if label == expected + ', ' + str(actual.year):
        return 'explicit_displayed_year', 'high'
    assert label == expected and actual.year == reference.year, 'Omitted-year label must use the explicitly disclosed current-year convention'
    return 'observed_current_year_label_convention', 'moderate'


def blocks_for(raw, meta):
    excerpt, guard = guarded_excerpt(raw, meta)
    relative_labels = {}
    lines = excerpt.splitlines()
    for i, line in enumerate(lines):
        match = AX.match(line)
        if match and match[1] == 'text' and match[2] in {'TODAY', 'YESTERDAY'}:
            relative = reference_day(meta) - timedelta(days=match[2] == 'YESTERDAY')
            absolute = relative.strftime('%b').upper() + ' ' + str(relative.day) + ', ' + str(relative.year)
            relative_labels[absolute] = match[2]
            lines[i] = line[:match.start(2)] + absolute
    blocks = parse_blocks('\n'.join(lines), meta['contact'], recipient_identity_verified=True)
    for block in blocks:
        block['displayedDateLabel'] = relative_labels.get(block['displayedDateLabel'], block['displayedDateLabel'])
    return blocks, guard


def selected_block(blocks, selection, meta):
    direction = selection['direction']
    assert direction in {'inbound','outbound'}
    matches = [b for b in blocks if b['displayedDateLabel'] == selection['dateLabel']
        and shown_time(b['displayedTime']) == shown_time(selection['time'])
        and ((b['sender'] == 'Charles Solomon') if direction == 'outbound' else recipient_matches(b['sender'], meta['contact']))]
    if selection.get('asset'):
        assert re.fullmatch(r'[0-9a-f]{32}', selection['asset'])
        matches = [b for b in matches if selection['asset'] in {m.lower() for m in LOOM.findall(b['privateContent'])}]
    assert len(matches) == 1, f'Expected one exact authored/date/time/asset block, got {len(matches)} for {meta["profile"]} {selection["dateLabel"]} {selection["time"]}'
    return matches[0]


def make_event(meta, selection, block, row, video):
    kind = selection['kind']
    assert kind in KINDS, 'Unsupported explicit message kind'
    outbound = selection['direction'] == 'outbound'
    assets = {m.lower() for m in LOOM.findall(block['privateContent'])}
    asset = selection.get('asset')
    if kind == 'video':
        assert outbound and asset in assets, 'A video send needs the exact asset in its own authored block'
    else:
        assert not asset and not assets, 'An exact asset needs its own reviewed video classification'
    if kind == 'video_follow_up':
        assert outbound and re.search(r'\bvideo\b', block['privateContent'], re.I), 'Video follow-up lacks an explicit video reference'
    if kind == 'follow_up':
        kind = 'general_text'
    if kind in {'general_reply','reply'}:
        assert not outbound, 'Reply must be authored by this recipient'
    if kind in {'general_text','video_reference'}:
        assert outbound
    if kind == 'video_reference':
        assert re.search(r'\bvideo\b', block['privateContent'], re.I)
        assert selection.get('observedShortLink') in block['privateContent'] and selection.get('observedShortLink'), 'Reference link must be explicitly reviewed in this block'
    year_basis, year_confidence = resolve_selection_day(selection['dateLabel'], selection['date'], meta)
    observed_day = datetime.fromisoformat(meta['observedAt'].replace('Z', '+00:00')).astimezone(ZoneInfo('America/Denver')).date().isoformat()
    fingerprint = block['contentFingerprint']
    dedup = '|'.join((meta['profile'], selection['direction'], selection['date'], asset or block['displayedTime'] + ':' + fingerprint))
    deal = int(row['dealId']) if str(row.get('dealId') or '').isdigit() else None
    event = {'observationId': 'linkedin-ui:' + observed_day + ':' + meta['profile'] + ':' + selection['direction'] + ':' + hashlib.sha256(dedup.encode()).hexdigest()[:24],
        'dedupKey': dedup, 'sourceMessageId': None, 'sourceConversationId': None,
        'profileId': meta['profile'], 'company': row['company'], 'contact': row['contact'], 'sourceRow': row['sourceRow'],
        'sourceInventorySnapshotAt': video['snapshotAt'], 'crmDealId': deal, 'sourceSheetDealId': deal,
        'sourceKind': 'native_linkedin_existing_conversation', 'sourceEvidenceBasis': 'native_direct',
        'date': selection['date'], 'datePrecision': 'day', 'occurredAt': None, 'sourceTimezone': None,
        'displayedDateLabel': selection['dateLabel'], 'displayedTime': block['displayedTime'], 'contentFingerprint': fingerprint,
        'observedAsOfDate': observed_day, 'dateYearBasis': year_basis, 'dateYearConfidence': year_confidence,
        'dateBasis': 'Displayed source-calendar day anchored to this exact authored message block; ' + year_basis.replace('_',' ') + '; message timezone is unknown.',
        'channel': 'linkedin_message', 'direction': selection['direction'], 'sender': block['sender'], 'messageKind': kind,
        'videoIncluded': True if kind == 'video' else None if kind == 'video_reference' else False,
        'assetId': asset, 'assetLink': 'https://www.loom.com/share/' + asset if asset else None,
        'evidenceLink': row['linkedin'], 'observedAt': meta['observedAt'], 'profileIdentityVerified': True,
        'senderVerifiedWithinMessageBlock': True, 'dateTimeAssetAnchoredWithinSameMessageBlock': bool(asset),
        'evidenceBasis': 'Verified recipient profile and real conversation control; the selected native block establishes its sender, displayed date/time and any exact video asset. Worksheet statuses and CRM notes do not establish message delivery.',
        'replyToVideoAttributionEstablished': False, 'platformReadReceiptObserved': False, 'readReceiptDate': None}
    if kind == 'video_reference':
        event.update(videoReferenceObserved=True, observedShortLink=selection['observedShortLink'], shortLinkDestinationVerified=False)
    # This collector intentionally leaves inbound video attribution unresolved.
    # A separate reviewed attribution collector must establish the exact anchor.
    assert not selection.get('replyToVideoAttributionEstablished'), 'Video reply attribution requires a separate explicit anchor review'
    return event


def same_observation(a, b):
    if event_key(a) == event_key(b):
        return True
    if any(a.get(k) != b.get(k) for k in ('profileId','direction','date','assetId')):
        return False
    return bool(a.get('displayedTime') and b.get('displayedTime') and shown_time(a['displayedTime']) == shown_time(b['displayedTime'])
        and (not a.get('contentFingerprint') or a.get('contentFingerprint') == b.get('contentFingerprint')))


def build(before, video=None, subset=None, private=PRIVATE, cases=None, require_all=False):
    video = video or before['video']
    subset = subset or before['waalaxy'].get('sheetSubset')
    prior = before['video']['messageDateReview']
    native_dir = private / 'native'
    metas = sorted(native_dir.glob('*_meta.json'))
    if cases:
        metas = [p for p in metas if p.name[:-10] in cases]
        assert len(metas) == len(set(cases)), 'Requested capture case is missing'
    # Captures can be repeated under a cleaner filename. The most recent actual
    # capture for one profile supersedes the earlier raw capture; it does not
    # constitute a second checked profile or a second message.
    by_capture_profile = {}
    superseded = []
    for path in metas:
        meta = load(path)
        existing = by_capture_profile.get(meta['profile'])
        same_clock = existing is not None and load(existing)['observedAt'] == meta['observedAt']
        if same_clock:
            prior_meta = load(existing)
            prior_raw = existing.with_name(existing.name.replace('_meta.json', '.txt'))
            current_raw = path.with_name(path.name.replace('_meta.json', '.txt'))
            assert prior_meta == meta and prior_raw.read_bytes() == current_raw.read_bytes(), 'Conflicting same-clock duplicate captures'
        prefer_profile_filename = same_clock and path.name == meta['profile'] + '_meta.json'
        if existing is None or load(existing)['observedAt'] < meta['observedAt'] or prefer_profile_filename:
            if existing:
                superseded.append(existing.name[:-10])
            by_capture_profile[meta['profile']] = path
        else:
            superseded.append(path.name[:-10])
    metas = sorted(by_capture_profile.values())
    by_profile = {}
    for row in video['rows']:
        by_profile.setdefault(row['id'], []).append(row)
    new_events, records, checks, provenance, pending = [], [], [], [], []
    prior_events = prior.get('platformObservedEvents', [])
    prior_records = {r['profileId']: r for r in prior.get('records', [])}
    baseline_clocks = {event_key(e): e.get('observedAt') for e in prior_events}
    for path in metas:
        raw_path = path.with_name(path.name.replace('_meta.json', '.txt'))
        meta = load(path)
        if not raw_path.exists() or not raw_path.stat().st_size or not meta.get('selections'):
            pending.append({'case': path.name[:-10], 'reason': 'raw capture or explicit selections incomplete'})
            continue
        assert meta['profile'] in by_profile, 'Capture profile is outside the current inventory'
        rows = by_profile[meta['profile']]
        row = rows[0]
        raw = raw_path.read_text()
        blocks, guard = blocks_for(raw, meta)
        selected = [make_event(meta, sel, selected_block(blocks, sel, meta), row, video) for sel in meta['selections']]
        assert len(selected) == len({event_key(e) for e in selected}), 'Repeated explicit selection in one case'
        added, reobserved = [], []
        for event in selected:
            old = next((e for e in prior_events if same_observation(e, event)), None)
            if old:
                reobserved.append(old.get('observationId') or event_key(old))
            else:
                assert not any(same_observation(e, event) for e in new_events), 'The same message was selected in two captures'
                new_events.append(event)
                added.append(event)
        video_events = [e for e in added if e['messageKind'] == 'video']
        follow_events = [e for e in selected if e['messageKind'] == 'video_follow_up']
        inbound = [e for e in selected if e['direction'] == 'inbound']
        original_record = prior_records.get(meta['profile'], {})
        record = {'profileId': meta['profile'], 'sourceRow': original_record.get('sourceRow', row['sourceRow']),
            'sourceRows': original_record.get('sourceRows', [r['sourceRow'] for r in rows]),
            'company': row['company'], 'contact': row['contact'], 'linkedin': row['linkedin'], 'nativeDirectReviewCollectedAt': meta['observedAt']}
        if video_events:
            latest_video = max(video_events, key=lambda e: e['date'])
            record.update(platformSendDate=latest_video['date'], platformVideoAttributionEstablished=True,
                platformCheckStatus='matched_native_direct', nativeAssetId=latest_video['assetId'], platformEvidenceCollectedAt=meta['observedAt'])
        if follow_events:
            latest_follow = max(e['date'] for e in follow_events)
            if latest_follow >= (original_record.get('platformFollowUpDate') or ''):
                record.update(platformFollowUpDate=latest_follow, platformFollowUpEvidenceCollectedAt=meta['observedAt'])
        if inbound:
            latest_inbound = max(e['date'] for e in inbound)
            if latest_inbound >= (original_record.get('platformReplyDate') or ''):
                record.update(platformReplyDate=latest_inbound, platformGeneralReplyEvidenceCollectedAt=meta['observedAt'])
                # This collector does not establish video reply attribution. A
                # newer general reply cannot inherit an older reply's flag.
                old_attributed_same_day = any(e.get('profileId') == meta['profile'] and e.get('date') == latest_inbound
                    and e.get('replyToVideoAttributionEstablished') is True for e in prior_events)
                if not old_attributed_same_day:
                    record['platformReplyVideoAttributionEstablished'] = False
        records.append(record)
        check = {'profileId': meta['profile'], 'sourceRow': row['sourceRow'], 'sourceRows': [r['sourceRow'] for r in rows],
            'observedAt': meta['observedAt'], 'evidenceLink': row['linkedin'], 'sourceEvidenceBasis': 'native_direct',
            'profileIdentityVerified': True, 'senderAccount': 'Charles Solomon', 'coverageCompleteForThread': False,
            'crmAssetMatchRequiredForNativeProof': False, 'recipientIdentityGuard': guard,
            'status': 'matched_native_direct' if video_events else 'text_follow_up_observed' if follow_events else 'bounded_message_observed',
            'assetObserved': any(e['videoIncluded'] is True for e in selected),
            'observationIds': [e['observationId'] for e in added], 'reobservedObservationIds': reobserved,
            'newVideoSendEvents': len(video_events), 'videoFollowUpDates': sorted({e['date'] for e in follow_events}),
            'replyObservation': 'Only explicitly selected incoming blocks are counted; this bounded excerpt does not establish complete reply coverage.'}
        checks.append(check)
        provenance.append({'profileId': meta['profile'], 'sourceFile': str(raw_path.relative_to(ROOT) if raw_path.is_relative_to(ROOT) else raw_path.relative_to(private)),
            'sha256': hashlib.sha256(raw_path.read_bytes()).hexdigest(), 'observedAt': meta['observedAt'],
            'parsedMessageBlocks': len(blocks), 'selectionCount': len(selected), 'recipientIdentityGuard': guard,
            'selectedContentFingerprints': [e['contentFingerprint'] for e in selected]})
    assert not require_all or not pending, f'Incomplete native captures: {pending}'
    assert checks, 'No complete, explicitly reviewed native captures'
    assert len(checks) == len({c['profileId'] for c in checks}), 'Two active captures for the same profile'
    latest = max(c['observedAt'] for c in checks)
    partial = {'snapshotAt': latest, 'reviewedAt': latest, 'scope': {'videoSnapshotAt': video['snapshotAt'],
        'focusedNativeReviewedAt': latest, 'focusedNativeProfilesReviewed': [c['profileId'] for c in checks],
        'coverageCompleteForAllVideoDmMessages': False}, 'records': records, 'platformObservedEvents': new_events}
    review = current_join(merge_message_review(prior, partial, video, subset,
        (subset or {}).get('snapshotAt') or before['waalaxy'].get('sheetSubsetCollectedAt')), video)
    signature = hashlib.sha256(json.dumps(provenance, sort_keys=True).encode()).hexdigest()
    old_focused = copy.deepcopy(prior.get('focusedNativeReviews') or {})
    retained = copy.deepcopy(old_focused.pop('retainedPriorReviews', []))
    if old_focused and old_focused.get('captureBatchSignature') != signature:
        old_focused['historicalOnly'] = True
        if old_focused not in retained:
            retained.append(old_focused)
    review['focusedNativeReviews'] = {'snapshotAt': latest, 'reviewedAt': latest,
        'scope': 'Targeted existing native threads with explicit message-block selections; not an account-wide or complete thread census.',
        'profileChecks': checks, 'profilesChecked': len(checks), 'sourceTimezone': None,
        'captureBatchSignature': signature, 'retainedPriorReviews': retained,
        'notes': ['Original event observation clocks remain unchanged when the same message is seen again.',
            'Current-year month/day labels omit a displayed year; those observations explicitly carry moderate year confidence.',
            'Weekday labels use the known observation calendar day; no exact send timestamp or read-receipt date is inferred.',
            'Historical native cohorts retain their original collection clocks, profiles and period scopes.']}
    current_clocks = {event_key(e): e.get('observedAt') for e in review['platformObservedEvents']}
    assert all(current_clocks.get(key) == value for key, value in baseline_clocks.items()), 'A retained message was deleted or re-dated'
    review['summary'].update(newVerifiedVideoSendEventsAdded=sum(e['videoIncluded'] is True for e in new_events),
        newVerifiedVideoReplyEventsAdded=0,
        newHistoricalSeptemberVideoSendsAdded=sum(e['videoIncluded'] is True and e['date'].startswith('2026-09') for e in new_events),
        newOctoberObservedVideoSendsAdded=sum(e['videoIncluded'] is True and e['date'].startswith('2026-10') for e in new_events),
        newObservedVideoFollowUpEventsAdded=sum(e['messageKind'] == 'video_follow_up' for e in new_events))
    note = 'October 28/29 native refresh adds only explicitly selected authored/date/time blocks. Follow-up texts are separate events, source worksheet follow-up dates remain separate reports, and prior message proof retains its original clocks.'
    if note not in review['notes']:
        review['notes'].append(note)
    assert_curated(review)
    report = {'snapshotAt': latest, 'profilesChecked': len(checks), 'priorEventsRetained': len(prior_events),
        'newEvents': len(new_events), 'newVideoSendEvents': sum(e['videoIncluded'] is True for e in new_events),
        'newVideoFollowUpEvents': sum(e['messageKind'] == 'video_follow_up' for e in new_events),
        'reobservedPriorEvents': sum(len(c['reobservedObservationIds']) for c in checks),
        'totalRetainedEvents': len(review['platformObservedEvents']), 'pendingCases': pending, 'supersededCaptureCases': superseded,
        'totalObservedVideoSends': review['summary']['retainedObservedVideoSendEvents'],
        'octoberObservedVideoSends': sum(e.get('direction') == 'outbound' and e.get('videoIncluded') is True and e['date'].startswith('2026-10') for e in review['platformObservedEvents'])}
    return {'replacementMode': 'complete_review_bundle', 'completeReviewBundle': True, 'review': review}, provenance, report


def close_source_gaps(gap, video, native_review, report):
    """Close native uncertainties without changing separate source/CRM findings."""
    result = copy.deepcopy(gap)
    previous = copy.deepcopy(gap)
    retained = previous.pop('retainedPriorReviews', [])
    previous['historicalOnly'] = True
    previous['retentionBasis'] = 'Source-field review before the later direct native message checks; original source clocks and findings retained.'
    if previous not in retained:
        retained.append(previous)
    result['retainedPriorReviews'] = retained
    result['sourceInventoryCollectedAt'] = video['snapshotAt']
    result['sourceFieldReviewSnapshotAt'] = gap['snapshotAt']
    result['snapshotAt'] = result['reviewedAt'] = report['snapshotAt']
    current_profile_checks = {c['profileId']: c for c in native_review['focusedNativeReviews']['profileChecks']}
    sends = [e for e in native_review['platformObservedEvents'] if e.get('videoIncluded') is True and e.get('direction') == 'outbound']
    closed = []
    for record in result['records']:
        asset = record.get('recordingAssetId')
        matching = [e for e in sends if e['profileId'] == record['profileId'] and e['assetId'] == asset]
        if not asset or not matching:
            continue
        proof = max(matching, key=lambda e: e['date'])
        record['status'] = 'Exact native video send verified on ' + proof['date'] + '; source fields and CRM notes remain separate'
        record['nativeSendEvidence'] = {k: proof[k] for k in ('observationId','profileId','date','displayedDateLabel','displayedTime','assetId','assetLink','observedAt','evidenceLink','datePrecision','sourceTimezone')}
        record['nativeSendEvidence'].update(sourceEvidenceBasis='native_direct', sourceInventorySnapshotAt=video['snapshotAt'],
            crmAssetNotePresenceRequired=False, commercialOutcomeInferred=False)
        record['findings'].append('Later independent native message review confirms this exact authored video asset on ' + proof['date'] + '. The displayed source day has unknown timezone and is not an exact sending timestamp.')
        closed.append(record['profileId'])
    follows = [e for e in native_review['platformObservedEvents'] if e['profileId'] in current_profile_checks
        and e.get('messageKind') == 'video_follow_up' and e.get('date') == '2026-10-26']
    reports = []
    for event in follows:
        rows = [r for r in video['rows'] if r['id'] == event['profileId'] and r.get('reportedFollowUpSentDate') == event['date']]
        reports.append({'profileId': event['profileId'], 'date': event['date'], 'nativeObservedAt': event['observedAt'],
            'nativeObservationId': event['observationId'], 'sourceRows': [r['sourceRow'] for r in rows],
            'sourceInventoryCollectedAt': video['snapshotAt'], 'sourceReportMatchesNativeDay': bool(rows)})
    result['nativeClosureReview'] = {'snapshotAt': report['snapshotAt'], 'reviewedAt': report['snapshotAt'],
        'scope': 'Six priority source-field/date gaps and 19 targeted October 26 video follow-up messages; not an account-wide message census.',
        'priorityProfilesWithExactNativeVideoProof': closed, 'nativeFollowUps': reports,
        'currentNativeProfilesChecked': report['profilesChecked'], 'newNativeVideoSendEvents': report['newVideoSendEvents'],
        'newNativeFollowUpEvents': report['newVideoFollowUpEvents'], 'accountWideSendOrReplyCoverageComplete': False,
        'crmNoteOrIdentityGapsClosedByNativeEvidence': False, 'commercialDecisionsChanged': False, 'ownerHoursChanged': False}
    result['summary'].update(prioritySourceGapsWithLaterExactNativeVideoProof=len(closed),
        newNativeVideoSendEventsObserved=report['newVideoSendEvents'], newNativeFollowUpEventsObserved=report['newVideoFollowUpEvents'],
        sourceFollowUpReportsWithExactNativeDayProof=sum(r['sourceReportMatchesNativeDay'] for r in reports))
    result['notes'].append('Later native observations close the six priority sending uncertainties and corroborate 19 October 26 follow-up texts. CRM absent-note or identity gaps remain separate; no commercial acceptance, held meeting, opportunity or win is inferred.')
    assert_curated(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=ROOT / 'data/shared-dashboard.json')
    parser.add_argument('--video', type=Path, default=PRIVATE / 'sheets/video_inventory_patch.json')
    parser.add_argument('--subset', type=Path, default=PRIVATE / 'sheets/waalaxy_sheet_subset_patch.json')
    parser.add_argument('--private-dir', type=Path, default=PRIVATE)
    parser.add_argument('--case', action='append')
    parser.add_argument('--require-all', action='store_true')
    parser.add_argument('--gap', type=Path, help='Optional current Sheets gap patch to enrich with separate native closure evidence')
    args = parser.parse_args()
    bundle, provenance, report = build(load(args.input), load(args.video), load(args.subset), args.private_dir, args.case, args.require_all)
    output = args.private_dir / 'native'
    for name, value in [('native_message_review_patch.json', bundle), ('normalization_provenance_private.json', provenance), ('normalization_summary.json', report)]:
        (output / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    if args.gap:
        gap = close_source_gaps(load(args.gap), load(args.video), bundle['review'], report)
        (output / 'gap_resolution_review_with_native_patch.json').write_text(json.dumps(gap, ensure_ascii=False, indent=2) + '\n')
    manifest = {'snapshotAt': report['snapshotAt'], 'patches': {'videoMessageDateReview': 'native_message_review_patch.json'},
        'independentChildren': ([{'path': ['video','gapResolutionReview'], 'file': 'gap_resolution_review_with_native_patch.json'}] if args.gap else []),
        'notes': ['Complete reviewed native bundle preserves previous event clocks; source raw bodies and phones remain private.']}
    (output / 'integration_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
