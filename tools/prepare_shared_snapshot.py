"""Write the approved, curated reporting snapshot shared through GitHub."""
from pathlib import Path
import copy
import json
import re
from datetime import datetime, timezone
from apply_owner_confirmations import apply_owner_confirmations
from apply_effort_estimate import apply_effort_estimate
from apply_outcome_confirmations import apply_outcome_confirmations
from recording_evidence import apply_video_evidence_reviews
from publication_redactions import apply_publication_redactions

ROOT = Path(__file__).resolve().parents[1]

def publication_policy():
    path = ROOT / 'PUBLICATION_POLICY.json'
    return json.loads(path.read_text()) if path.exists() else {}

def apply_publication_policy(snapshot):
    """An import or prior public snapshot cannot override an owner local hold."""
    policy = publication_policy()
    if policy.get('mode') == 'local_only':
        snapshot.setdefault('meta', {}).update(
            publicationStatus='local_only',
            publicationPolicyConfirmedOn=policy.get('confirmedOn'),
            publicationPolicyBasis=policy.get('basis'),
            public=False)
    return snapshot

def sync_inventory_source_cards(snapshot):
    """Keep CRM/referral collection metadata tied to the selected inventory."""
    for card in snapshot.get('sources', []):
        ident = card.get('id')
        if ident not in ('crm', 'referrals'):
            continue
        section = snapshot.get(ident) or {}
        if section.get('snapshotAt'):
            card['asOf'] = section['snapshotAt']
        if section.get('coverage') is not None:
            card['coverage'] = copy.deepcopy(section['coverage'])
    return snapshot

def curate_snapshot(source, effort_decision=None):
    public = copy.deepcopy(source)
    apply_owner_confirmations(public)
    apply_outcome_confirmations(public)
    if public.get('video'):
        apply_video_evidence_reviews(public['video'])
    if public.get('time'):
        apply_effort_estimate(public['time'], decision=effort_decision)
    sync_inventory_source_cards(public)
    apply_publication_policy(public)
    state=public.get('meta',{}).get('publicationStatus')
    local_only=state=='local_only'
    pending=state=='pending_owner_approval'
    public.setdefault('meta',{}).update(public=not (local_only or pending), publicDataPolicy=('Owner-directed local-only snapshot; GitHub and GitHub Pages remain unchanged. Future publication requires a new explicit owner instruction and policy change.' if local_only else 'Local review snapshot; refreshed private source supplements await publication approval.' if pending else 'Owner-approved detailed snapshot including prospect identities and available business record links.'))
    public['meta']['note'] = ('Local-only snapshot by owner instruction; refreshed source supplements have not been published. ' if local_only else 'Local review snapshot; refreshed private source supplements have not been published. ' if pending else 'Published snapshot; ') + 'Source coverage varies. Automatic refresh is not enabled.'
    if public['meta']['public']:
        for card in public.get('sources',[]):
            if isinstance(card.get('status'),str):
                card['status']=card['status'].replace('; local only','')
    for name in ('ads', 'waalaxy', 'content'):
        public.get(name, {}).pop('sources', None)
    def scrub(value):
        if isinstance(value, dict):
            return {key: scrub(item) for key, item in value.items()
                    if key not in ('provenance', 'sourceUrl', 'sourcePath')}
        if isinstance(value, list):
            return [scrub(item) for item in value]
        if isinstance(value, str):
            return re.sub(r'/Users/[^\s]+', '[local source]', value)
        return value
    public = scrub(public)
    meetings=public.get('meetings') or {}
    if 'records' in (meetings.get('fireflies') or {}):
        for key in ('firefliesRecordings','firefliesBdCalls','firefliesClientCalls','firefliesInternalCalls'):
            meetings.get('summary',{}).pop(key,None)
        meetings['notes']=[n for n in meetings.get('notes',[]) if '19 recordings classified' not in n and 'Attendance is verified by recording presence' not in n]
    for item in public.get('sources', []):
        if item['id'] == 'waalaxy':
            tooltip_source = public.get('waalaxy',{}).get('invitationImportReview',{}).get('sourceType') == 'authenticated_home_chart_tooltips'
            home_note = ('See the separately dated, verified Charles Home account aggregate alongside the authenticated chart tooltips and earlier CSV buckets.' if tooltip_source else
                         'See the separately dated, verified Charles Home account aggregate; it does not refresh this daily invitation CSV or selected-person subset.')
            item['note'] = ('Invitation source-date buckets are available, including source-reported zero days. Accepted buckets can be revised retrospectively; exact acceptance-event dates and matched invitation cohorts are unverified. '
                            'The final source day is partial and the source timezone is unspecified. '
                            + ('A separately dated selected connected-prospect subset is available through Sheets; sender account and upstream sync time are unverified. ' if public.get('waalaxy',{}).get('sheetSubset') else '') +
                            'Dated message/reply events and campaign breakdowns remain unavailable; historical person flags retain older coverage. '
                            + (home_note if public.get('waalaxy',{}).get('accountAnalytics') else '')
                            if public.get('waalaxy',{}).get('invitationCoverage') else
                            'Historical Charles-only person flags, not period message totals. Current campaign analytics remain unavailable.')
    return apply_publication_redactions(public)

def stamp(section):
    value = (section.get('snapshotAt') or section.get('collectedAt')) if isinstance(section,dict) else None
    if not value:return datetime.min.replace(tzinfo=timezone.utc)
    dt = datetime.fromisoformat(value.replace('Z','+00:00'))
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt

def review_stamp(section):
    """A child review follows its own evidence clock, never its parent clock."""
    return stamp({'snapshotAt':next((section.get(key) for key in
        ('lastReviewedAt','reviewedAt','snapshotAt','collectedAt') if section.get(key)),None)})

def merge_review_rows(source, previous, child, identity):
    """Retain omitted source decisions and supersede only by explicit review."""
    selected={}
    for container in (previous,source):
        seen=set()
        for row in (container.get('meetings') or {}).get(child,[]):
            ident=row.get(identity)
            assert ident and ident not in seen, f'Duplicate or absent {child} identity'
            seen.add(ident)
            assert review_stamp(row)>stamp(None), f'{child} needs an independent review clock'
            prior=selected.get(ident)
            if prior and review_stamp(row)==review_stamp(prior):
                assert row==prior, f'Conflicting {child} records share a review clock'
            if prior is None or review_stamp(row)>review_stamp(prior):selected[ident]=copy.deepcopy(row)
    return list(selected.values())

def merge_invitation_restatements(source, previous):
    """Keep independently dated bucket versions when the invitation parent changes."""
    selected = {}
    for container in (source, previous):
        review = (container.get('waalaxy') or {}).get('invitationImportReview') or {}
        records = review.get('separatelyObservedRestatements', [])
        assert isinstance(records, list), 'Invitation restatements must be a record list'
        for row in records:
            assert isinstance(row, dict), 'Invitation restatement must be a record'
            day = row.get('date')
            assert isinstance(day, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}', day), 'Invitation restatement requires a source date'
            assert datetime.fromisoformat(day).date().isoformat() == day, 'Invalid invitation restatement source date'
            clocks = {}
            for field in ('laterTooltipObservedAt', 'retainedCsvCollectedAt'):
                value = row.get(field)
                assert isinstance(value, str) and re.search(r'(?:Z|[+-]\d{2}:\d{2})$', value), 'Invitation restatement requires independent collection clocks'
                clock = datetime.fromisoformat(value.replace('Z', '+00:00'))
                assert clock.utcoffset() is not None, 'Invitation restatement clock requires a timezone offset'
                clocks[field] = clock
            assert clocks['laterTooltipObservedAt'] >= clocks['retainedCsvCollectedAt'], 'Invitation restatement predates the retained CSV'
            for field in ('retainedCsv', 'laterAuthenticatedTooltip'):
                values = row.get(field)
                assert isinstance(values, dict) and set(values) == {'invitationsSent', 'invitationsAccepted'}, 'Invitation restatement requires both source counts'
                assert all(type(value) is int and value >= 0 for value in values.values()), 'Invitation restatement counts must be nonnegative integers'
            assert row.get('appliedToRetainedSeries') is False, 'Separate invitation restatements do not replace retained date buckets'
            assert isinstance(row.get('basis'), str) and row['basis'].strip(), 'Invitation restatement needs its source interpretation'
            identity = (day, clocks['laterTooltipObservedAt'])
            if identity in selected:
                assert row == selected[identity], 'Conflicting invitation restatements share a source date and observation clock'
            else:
                selected[identity] = copy.deepcopy(row)
    return [selected[key] for key in sorted(selected)]

def preserve_newer_shared_sources(source, previous, publication_approved=False):
    """Older local inputs must not erase newer collaborator source revisions."""
    result=copy.deepcopy(source)
    retained=set()
    for key in ('ads','crm','video','waalaxy','content','referrals','meetings','time'):
        current, old = result.get(key) or {}, previous.get(key) or {}
        if stamp(old)>stamp(current) or (key=='time' and old.get('reviewedAsOf','')>current.get('reviewedAsOf','') and stamp(old)>=stamp(current)) or (key=='waalaxy' and old.get('invitationCoverage') and not current.get('invitationCoverage') and stamp(old)>=stamp(current)):
            result[key]=copy.deepcopy(old)
            retained.add(key)
    # Independent selected-person sources must survive an account-wide refresh.
    # Their collection dates do not establish when the upstream account synced.
    old_w=previous.get('waalaxy') or {}
    new_w=result.setdefault('waalaxy',{})
    # Daily invitation imports have an independent collection clock. Choose
    # that family from the original inputs, even if a whole-container choice
    # above selected the other person's/account snapshot. Keep other measures
    # on each day and never re-date the parent inventory or Sheet source.
    invitation_card=None
    invitation_candidates=[]
    for container in (source,previous):
        section=container.get('waalaxy') or {}
        collected=(section.get('invitationCollectedAt') or
                   (section.get('invitationCoverage') or {}).get('collectedAt') or
                   (section.get('invitationImportReview') or {}).get('snapshotAt'))
        if collected and section.get('invitationCoverage'):
            invitation_candidates.append((stamp({'collectedAt':collected}),section,container))
    if invitation_candidates:
        _,chosen,chosen_container=max(invitation_candidates,key=lambda item:item[0])
        by_day={}
        for row in new_w.get('daily',[]):
            other={key:copy.deepcopy(value) for key,value in row.items()
                   if key not in ('invitationsSent','invitationsAccepted')}
            if len(other)>1:by_day[row['date']]=other
        for row in chosen.get('daily',[]):
            fields={key:copy.deepcopy(row[key]) for key in ('invitationsSent','invitationsAccepted') if key in row}
            if fields:by_day.setdefault(row['date'],{'date':row['date']}).update(fields)
        new_w['daily']=[by_day[key] for key in sorted(by_day)]
        for key in ('invitationCollectedAt','invitationCoverage','invitationSummary','invitationImportReview'):
            if key in chosen:new_w[key]=copy.deepcopy(chosen[key])
        prefixes=('Invitation import contains','Latest owner-supplied invitation CSV:')
        new_w['notes']=[note for note in new_w.get('notes',[]) if not str(note).startswith(prefixes)]
        new_w['notes'].extend(copy.deepcopy(note) for note in chosen.get('notes',[])
                             if str(note).startswith(prefixes) and note not in new_w['notes'])
        invitation_card=next((copy.deepcopy(card) for card in chosen_container.get('sources',[])
                              if card['id']=='waalaxy_invitations'),None)
        if not invitation_card:
            invitation_card={'id':'waalaxy_invitations','name':'Waalaxy · daily invitation source buckets',
                'asOf':chosen.get('invitationCollectedAt') or chosen['invitationCoverage'].get('collectedAt') or chosen.get('invitationImportReview',{}).get('snapshotAt'),
                'coverage':copy.deepcopy(chosen['invitationCoverage']),
                'status':'Current independently dated invitation export',
                'method':'Retained invitation CSV date buckets',
                'note':'Invitation date buckets retain their own collection date. Source timezone, exact acceptance-event dates and matched invitation cohorts are unverified; message/reply actions have separate coverage.'}
    # An invitation-family winner can omit earlier independently observed
    # versions. Merge from both original inputs, preserving every source clock;
    # these observations never modify daily rows or become new acceptance events.
    restatements = merge_invitation_restatements(source, previous)
    if restatements:
        new_w.setdefault('invitationImportReview', {})['separatelyObservedRestatements'] = restatements
    if old_w.get('sheetSubset') and old_w.get('sheetSubsetCollectedAt','')>new_w.get('sheetSubsetCollectedAt',''):
        for key in ('sheetSubset','sheetSubsetCollectedAt','sheetSubsetAccountVerification','sheetSubsetUpstreamSyncAt'):
            if key in old_w:new_w[key]=copy.deepcopy(old_w[key])
    old_export=old_w.get('selectedExportSnapshot') or {}
    new_export=new_w.get('selectedExportSnapshot') or {}
    if old_export.get('reviewedAt','')>new_export.get('reviewedAt',''):
        new_w['selectedExportSnapshot']=copy.deepcopy(old_export)
    # Account/page supplements have independent collection dates. A newer
    # creator or person export must not silently drop them or refresh their age.
    for parent,child,source_id in (('content','creatorAnalytics','content'),
                                    ('content','companyAnalytics','content_company'),
                                    ('content','companyAvailabilityReview','content_company_availability'),
                                    ('waalaxy','accountAnalytics','waalaxy_account'),
                                    ('crm','archiveReview','crm_archived'),
                                    ('video','sourceVerification','source_audit'),
                                    ('video','automationReview','zapier_execution'),
                                    ('video','recordingFieldReview','video_crm_reconciliation'),
                                    ('video','crmReconciliation','video_crm_reconciliation'),
                                    ('video','messageDateReview','video_message_dates'),
                                    ('crm','incrementalReview','crm_incremental'),
                                    ('crm','mailboxReview','crm_inbox_context'),
                                    ('video','gapResolutionReview','video_gap_resolution'),
                                    ('video','sourceFreshnessReview','video_source_freshness'),
                                    ('ads','lifecycleReview','ads_lifecycle'),
                                    ('ads','zeroDeliveryReview','ads_zero_delivery'),
                                    ('video','datedStatusReview','source_audit'),
                                    ('video','metadataFreshnessCheck','source_freshness'),
                                    ('meetings','metadataFreshnessCheck','source_freshness'),
                                    ('waalaxy','workflowReview','source_audit'),
                                    ('crm','commercialContextReview','commercial_context'),
                                    ('waalaxy','replyContextReview','commercial_context'),
                                    ('referrals','eventReview','referral_events'),
                                    ('referrals','contextReview','referral_context'),
                                    ('referrals','legacyCaptureReview','source_audit'),
                                    ('time','workEvidence','source_audit'),
                                    ('time','meetings','time')):
        prior=(previous.get(parent) or {}).get(child)
        incoming=(result.get(parent) or {}).get(child)
        if prior and (not incoming or stamp(prior)>stamp(incoming)):
            result.setdefault(parent,{})[child]=copy.deepcopy(prior)
            retained.add(source_id)
        elif prior and parent in retained:
            retained.add(source_id)
    # A partial browser review never replaces the full historical CRM/Ads source.
    for key in ('crm','ads','referrals'):
        old_review=(previous.get(key) or {}).get('browserReview') or {}
        incoming=(result.get(key) or {}).get('browserReview') or {}
        if old_review.get('collectedAt','')>incoming.get('collectedAt',''):
            result.setdefault(key,{})['browserReview']=copy.deepcopy(old_review)
            retained.add(key)
            if key in ('crm','ads'):retained.add(key+'_browser')
    for key in ('crm','ads'):
        if key in retained and result.get(key,{}).get('browserReview'):
            retained.add(key+'_browser')
    # Recording review is an independently dated supplement to calendar data.
    prior_ff=(previous.get('meetings') or {}).get('fireflies')
    current_ff=(result.get('meetings') or {}).get('fireflies')
    if prior_ff and (not current_ff or stamp(prior_ff)>stamp(current_ff)):
        result.setdefault('meetings',{})['fireflies']=copy.deepcopy(prior_ff)
        retained.add('fireflies')
    elif prior_ff and 'meetings' in retained:
        # Replacing the entire calendar container also retained its recording
        # review. Keep the separate Fireflies source-card timestamp in sync.
        retained.add('fireflies')
    # A later metadata-only recording import must not erase reviewed dialogue
    # purposes. Occurrence dates and joins still follow their separate evidence.
    new_ff=(result.get('meetings') or {}).get('fireflies') or {}
    for review_key,source_id in (('additionalPurposeReview','fireflies_purpose'),
                                ('octoberPurposeReview','fireflies_october_review'),
                                ('incrementalPurposeReview','fireflies_incremental_review'),
                                ('newDuplicateEvidence','fireflies_incremental_review')):
        prior_review=(prior_ff or {}).get(review_key)
        if prior_review and stamp(prior_review)>stamp(new_ff.get(review_key)):
            new_ff[review_key]=copy.deepcopy(prior_review)
            retained.add(source_id)
        elif prior_review and 'fireflies' in retained:
            retained.add(source_id)
    prior_records={r['id']:r for r in (prior_ff or {}).get('records',[])}
    for record in new_ff.get('records',[]):
        old_record=prior_records.get(record['id']) or {}
        if old_record.get('lastPurposeReviewedAt','')>record.get('lastPurposeReviewedAt',''):
            for key in ('classification','classificationBasis','lastPurposeReviewedAt',
                        'purposeSourceCollectedAt','purposeReferences','confirmedProspectMeetingAdded',
                        'purposeReviewStatus','sentenceCount','charlesSpeakerEvidence','duplicateCandidateIds'):
                if key in old_record:record[key]=copy.deepcopy(old_record[key])
            retained.add('fireflies_purpose')
            if old_record.get('purposeReviewStatus'):retained.add('fireflies_october_review')
        # Metadata timestamps cannot retract an independently corroborated
        # occurrence date or join. A later explicit corroboration review can.
        old_corroboration=old_record.get('corroborationReviewedAt') or old_record.get('evidenceCollectedAt','')
        incoming_corroboration=record.get('corroborationReviewedAt') or (
            record.get('evidenceCollectedAt','') if record.get('heldStatus')=='source_corroborated' else '')
        if old_record.get('heldStatus')=='source_corroborated' and old_corroboration>incoming_corroboration:
            for key in ('company','occurredAt','occurrenceDatePrecision','heldStatus','evidenceStatus',
                        'joinStatus','crmDealIds','bookingChainIds','qualifiedStatus',
                        'charlesSpeakerConfirmed','evidenceCollectedAt','corroborationReviewedAt',
                        'audioDurationIsAttendance'):
                if key in old_record:record[key]=copy.deepcopy(old_record[key])
    # A metadata-only import can omit previously reviewed recordings because
    # its date window or pagination differs. Retain their independently dated
    # purpose evidence without claiming they were returned by that new import.
    incoming_record_ids={r['id'] for r in new_ff.get('records',[])}
    for ident,old_record in prior_records.items():
        if old_record.get('lastPurposeReviewedAt') and ident not in incoming_record_ids:
            record=copy.deepcopy(old_record)
            record['retainedForPurposeEvidenceOnly']=True
            record['metadataPresenceStatus']='Not returned by the latest metadata import; independently dated dialogue review retained'
            new_ff.setdefault('records',[]).append(record)
            retained.add('fireflies_purpose')
            if old_record.get('purposeReviewStatus'):retained.add('fireflies_october_review')
    # Public observations can be refreshed while private content exports retain
    # their historical date. Preserve those independent collection dates too.
    for nested in ('publicObservations','accessReview'):
        old=(previous.get('content') or {}).get(nested) or {}
        incoming=(result.get('content') or {}).get(nested) or {}
        if old.get('checkedAt','')>incoming.get('checkedAt',''):
            result.setdefault('content',{})[nested]=copy.deepcopy(old)
            retained.add('content')
    # Profile discovery has its own UI collection clock, independent of the
    # creator workbook. Select from the original inputs so a parent-container
    # choice cannot erase a newer nested profile review in either direction.
    profile_candidates=[]
    for container in (source,previous):
        profile=((container.get('content') or {}).get('creatorAnalytics') or {}).get('profileAnalytics')
        if profile:profile_candidates.append((stamp(profile),profile,container))
    profile_card=None
    if profile_candidates:
        _,profile,chosen_container=max(profile_candidates,key=lambda item:item[0])
        result.setdefault('content',{}).setdefault('creatorAnalytics',{})['profileAnalytics']=copy.deepcopy(profile)
        profile_card=next((copy.deepcopy(s) for s in chosen_container.get('sources',[])
                           if s['id']=='content_profile'),None)
    # Focused reviews have independent clocks, even when another import wins
    # their whole parent inventory. Select from both original inputs before a
    # parent-container choice can discard a newer child. Nested revision/date
    # analyses keep their own historical scope; display guards must still join
    # them to a compatible current inventory before using row-based claims.
    focused_cards={}
    # Calendar preparation does not retract independently reviewed dialogue,
    # commercial state or an original occurrence decision. Merge by source
    # identity; a later explicit review can supersede the same identity.
    commercial_rows=[]
    for child,identity in (('sourceVerifiedHeldCalls','conversationId'),
                           ('sourceObservedOpportunities','opportunityId'),
                           ('sourceObservedOpportunityStateReviews','opportunityId')):
        merged=merge_review_rows(source,previous,child,identity)
        if merged:
            result.setdefault('meetings',{})[child]=merged
            commercial_rows.extend(merged)
    if commercial_rows:
        reviewed=max(review_stamp(row) for row in commercial_rows).isoformat()
        focused_cards['commercial_source_evidence']={
            'id':'commercial_source_evidence','name':'Commercial source decisions · retained independent evidence',
            'asOf':reviewed,'status':'Individually dated source confirmations; incomplete total coverage',
            'method':'Stable conversation/opportunity identity and each row’s own review clock',
            'note':'Calendar inventory dates do not refresh or retract reviewed calls, opportunity documentation or closure evidence. Original acceptance and complete commercial totals remain separately unverified.'}
    independent_paths={('meetings','businessContextReview'),('time','novemberRecordingReview'),('video','connectionInventoryReview'),
                       ('content','creatorAnalytics','exportAnalytics')}
    focused_paths=[(('crm','incrementalReview'),'crm_incremental'),
                   (('ads','zeroDeliveryReview'),'ads_zero_delivery'),
                   (('crm','mailboxReview'),'crm_inbox_context'),
                   (('video','gapResolutionReview'),'video_gap_resolution'),
                   (('video','sourceFreshnessReview'),'video_source_freshness'),
                   (('video','connectionInventoryReview'),'video_connection_inventory'),
                   (('video','gapResolutionReview','sourceAppearanceReview'),None),
                   (('video','gapResolutionReview','identityDateReview'),None),
                   (('meetings','businessContextReview'),'calendly_business_context'),
                   (('time','novemberRecordingReview'),'time_november'),
                   (('content','creatorAnalytics','exportAnalytics'),'content_creator_export')]
    for path,source_id in focused_paths:
        candidates=[]
        for container in (source,previous):
            value=container
            for part in path:
                value=(value or {}).get(part) if isinstance(value,dict) else None
            if value:candidates.append((review_stamp(value) if path in independent_paths else stamp(value),value,container))
        if not candidates:continue
        if path in independent_paths and len(candidates)>1 and candidates[0][0]==candidates[1][0]:
            assert candidates[0][1]==candidates[1][1], f'Conflicting {path} reviews share a collection clock'
        _,chosen,chosen_container=max(candidates,key=lambda item:item[0])
        target=result
        for part in path[:-1]:target=target.setdefault(part,{})
        target[path[-1]]=copy.deepcopy(chosen)
        if source_id:
            chosen_card=next((copy.deepcopy(s) for s in chosen_container.get('sources',[]) if s['id']==source_id),None)
            if source_id=='content_creator_export':
                chosen_card={'id':source_id,'name':'LinkedIn · Charles creator workbook',
                    'asOf':chosen.get('snapshotAt') or chosen.get('collectedAt'),
                    'coverage':copy.deepcopy(chosen.get('coverage')),
                    'status':'Independently dated creator workbook',
                    'method':'Authenticated creator workbook; retained independently of creator UI and profile-view collections',
                    'note':'Workbook source dates and partial-day coverage are unchanged by a newer parent/UI collection.'}
            if chosen_card:focused_cards[source_id]=chosen_card
    by_id={s['id']:s for s in result.get('sources',[])}
    for src in previous.get('sources',[]):
        if src['id'] in retained or (src['id']=='fireflies' and src['id'] not in by_id):
            by_id[src['id']]=copy.deepcopy(src)
    if invitation_card:by_id['waalaxy_invitations']=invitation_card
    if profile_card:by_id['content_profile']=profile_card
    by_id.update(focused_cards)
    result['sources']=list(by_id.values())
    sync_inventory_source_cards(result)
    if 'crm' in retained and not result.get('meta',{}).get('reportingAsOfDate'):
        result.setdefault('meta',{})['defaultReportingThrough']=result['crm'].get('coverage',{}).get('reportingThrough')
    # Review freshness is distinct from source freshness. Re-importing an older
    # export must not erase the newer reporting scope or a publication hold.
    old_meta=previous.get('meta') or {}
    incoming_meta=result.setdefault('meta',{})
    if old_meta.get('reportingAsOfDate','')>incoming_meta.get('reportingAsOfDate',''):
        for key in ('generatedAt','asOfDate','reportingAsOfDate','defaultReportingThrough',
                    'defaultCompleteReportingThrough','defaultDatePreset','currentDayPartial','revision'):
            if key in old_meta:incoming_meta[key]=copy.deepcopy(old_meta[key])
    if not publication_approved:
        holds={'pending_owner_approval':1,'local_only':2}
        old_hold=old_meta.get('publicationStatus')
        if holds.get(old_hold,0)>holds.get(incoming_meta.get('publicationStatus'),0):
            incoming_meta['publicationStatus']=old_hold
    return apply_publication_policy(result)

def write_shared(source):
    target = ROOT / 'data/shared-dashboard.json'
    previous=json.loads(target.read_text()) if target.exists() else {}
    snapshot = curate_snapshot(preserve_newer_shared_sources(source, previous))
    target.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2)+'\n')
    return target

if __name__ == '__main__':
    source = json.loads((ROOT/'data/dashboard.json').read_text())
    print(write_shared(source))
