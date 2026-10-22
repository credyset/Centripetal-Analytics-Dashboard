"""Write the approved, curated reporting snapshot shared through GitHub."""
from pathlib import Path
import copy
import json
import re
from datetime import datetime, timezone
from apply_owner_confirmations import apply_owner_confirmations
from apply_effort_estimate import apply_effort_estimate
from apply_outcome_confirmations import apply_outcome_confirmations

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

def curate_snapshot(source):
    public = copy.deepcopy(source)
    apply_owner_confirmations(public)
    apply_outcome_confirmations(public)
    if public.get('time'):
        apply_effort_estimate(public['time'])
    apply_publication_policy(public)
    state=public.get('meta',{}).get('publicationStatus')
    local_only=state=='local_only'
    pending=state=='pending_owner_approval'
    public.setdefault('meta',{}).update(public=not (local_only or pending), publicDataPolicy=('Owner-directed local-only snapshot; GitHub and GitHub Pages remain unchanged. Future publication requires a new explicit owner instruction and policy change.' if local_only else 'Local review snapshot; refreshed private source supplements await publication approval.' if pending else 'Owner-approved detailed snapshot including prospect identities and available business record links.'))
    public['meta']['note'] = ('Local-only snapshot by owner instruction; refreshed source supplements have not been published. ' if local_only else 'Local review snapshot; refreshed private source supplements have not been published. ' if pending else 'Published snapshot; ') + 'Source coverage varies. Automatic refresh is not enabled.'
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
            item['note'] = ('Dated invitation actions are available, including source-reported zero days. '
                            'The final source day is partial and the source timezone is unspecified. '
                            + ('A separately dated selected connected-prospect subset is available through Sheets; sender account and upstream sync time are unverified. ' if public.get('waalaxy',{}).get('sheetSubset') else '') +
                            'Dated message/reply events and campaign breakdowns remain unavailable; historical person flags retain older coverage. '
                            + ('See the separately dated, verified Charles Home account aggregate; it does not refresh this daily invitation CSV or selected-person subset.' if public.get('waalaxy',{}).get('accountAnalytics') else '')
                            if public.get('waalaxy',{}).get('invitationCoverage') else
                            'Historical Charles-only person flags, not period message totals. Current campaign analytics remain unavailable.')
    return public

def stamp(section):
    value = (section.get('snapshotAt') or section.get('collectedAt')) if isinstance(section,dict) else None
    if not value:return datetime.min.replace(tzinfo=timezone.utc)
    dt = datetime.fromisoformat(value.replace('Z','+00:00'))
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt

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
    if old_w.get('sheetSubset') and old_w.get('sheetSubsetCollectedAt','')>new_w.get('sheetSubsetCollectedAt',''):
        for key in ('sheetSubset','sheetSubsetCollectedAt','sheetSubsetAccountVerification','sheetSubsetUpstreamSyncAt'):
            if key in old_w:new_w[key]=copy.deepcopy(old_w[key])
    old_export=old_w.get('selectedExportSnapshot') or {}
    new_export=new_w.get('selectedExportSnapshot') or {}
    if old_export.get('reviewedAt','')>new_export.get('reviewedAt',''):
        new_w['selectedExportSnapshot']=copy.deepcopy(old_export)
    # Account/page supplements have independent collection dates. A newer
    # creator or person export must not silently drop them or refresh their age.
    for parent,child,source_id in (('content','companyAnalytics','content_company'),
                                    ('waalaxy','accountAnalytics','waalaxy_account'),
                                    ('crm','archiveReview','crm_archived'),
                                    ('video','sourceVerification','source_audit'),
                                    ('waalaxy','workflowReview','source_audit'),
                                    ('referrals','legacyCaptureReview','source_audit'),
                                    ('time','workEvidence','source_audit')):
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
                                ('octoberPurposeReview','fireflies_october_review')):
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
    by_id={s['id']:s for s in result.get('sources',[])}
    for src in previous.get('sources',[]):
        if src['id'] in retained or (src['id']=='fireflies' and src['id'] not in by_id):
            by_id[src['id']]=copy.deepcopy(src)
    result['sources']=list(by_id.values())
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
