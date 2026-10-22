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

def curate_snapshot(source):
    public = copy.deepcopy(source)
    apply_owner_confirmations(public)
    apply_outcome_confirmations(public)
    if public.get('time'):
        apply_effort_estimate(public['time'])
    pending=public.get('meta',{}).get('publicationStatus')=='pending_owner_approval'
    public['meta'].update(public=not pending, publicDataPolicy=('Local review snapshot; refreshed private source supplements await publication approval.' if pending else 'Owner-approved detailed snapshot including prospect identities and available business record links.'))
    public['meta']['note'] = ('Local review snapshot; refreshed private source supplements have not been published. ' if pending else 'Published snapshot; ') + 'Source coverage varies. Automatic refresh is not enabled.'
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
                            'Message/reply events and campaign breakdowns remain unavailable; historical person flags retain older coverage.'
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
    # A partial browser review never replaces the full historical CRM/Ads source.
    for key in ('crm','ads','referrals'):
        old_review=(previous.get(key) or {}).get('browserReview') or {}
        incoming=(result.get(key) or {}).get('browserReview') or {}
        if old_review.get('collectedAt','')>incoming.get('collectedAt',''):
            result.setdefault(key,{})['browserReview']=copy.deepcopy(old_review)
            retained.add(key)
            if key in ('crm','ads'):retained.add(key+'_browser')
    # Recording review is an independently dated supplement to calendar data.
    prior_ff=(previous.get('meetings') or {}).get('fireflies')
    current_ff=(result.get('meetings') or {}).get('fireflies')
    if prior_ff and (not current_ff or stamp(prior_ff)>stamp(current_ff)):
        result.setdefault('meetings',{})['fireflies']=copy.deepcopy(prior_ff)
        retained.add('fireflies')
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
    if old_meta.get('publicationStatus')=='pending_owner_approval' and not publication_approved:
        incoming_meta['publicationStatus']='pending_owner_approval'
    return result

def write_shared(source):
    target = ROOT / 'data/shared-dashboard.json'
    previous=json.loads(target.read_text()) if target.exists() else {}
    snapshot = curate_snapshot(preserve_newer_shared_sources(source, previous))
    target.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2)+'\n')
    return target

if __name__ == '__main__':
    source = json.loads((ROOT/'data/dashboard.json').read_text())
    print(write_shared(source))
