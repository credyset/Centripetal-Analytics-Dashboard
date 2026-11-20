"""Apply durable opaque-source-ID publication exclusions to curated snapshots."""
from pathlib import Path
import copy
import json
import re

ROOT=Path(__file__).resolve().parents[1]

def rules():
    policy=json.loads((ROOT/'PUBLICATION_REDACTIONS.json').read_text())
    assert policy['version']==1 and policy['records'], 'Publication exclusions must be explicitly configured'
    templates={rule['id']:rule for rule in policy.get('recordClassificationPolicies',[])}
    configured={}
    for entry in policy['records']:
        if entry.get('policyId'):
            assert entry['policyId'] in templates, 'Opaque source policy template is missing'
            rule={key:copy.deepcopy(value) for key,value in templates[entry['policyId']].items() if key not in ('id','classificationPatterns')}
            rule.update(entry)
        else:rule=entry
        configured[entry['sourceId']]=rule
    return configured

def classification_policies():
    return json.loads((ROOT/'PUBLICATION_REDACTIONS.json').read_text()).get('classificationPolicies',[])

def record_classification_policies():
    return json.loads((ROOT/'PUBLICATION_REDACTIONS.json').read_text()).get('recordClassificationPolicies',[])

def apply_booking_classification_policy(snapshot,policy):
    """Keep non-buyer lifecycle proof while withholding unrelated intake context."""
    meetings=snapshot.get(policy['sourceSection']) or {}
    patterns=[re.compile(pattern,re.I) for pattern in policy['privateContextPatterns']]
    unsafe_classes=set(policy['excludedClassifications'])
    safe_class=policy['safeCommercialClassification']
    marker=policy['publicationPolicy']
    events=meetings.get('events',[])
    crm_deals={row['id']:row for row in snapshot.get('crm',{}).get('deals',[])}
    context=meetings.get('businessContextReview') or {}
    excluded_ids=set()
    withheld_names=set()

    def has_private_context(value):
        return any(pattern.search(value) for pattern in patterns) if isinstance(value,str) else False

    def excluded(value):
        return any(value.get(key) in unsafe_classes for key in ('commercialClassification','classification','category')) or any(has_private_context(value.get(key)) for key in ('stage','purposeEvidence','evidence'))

    for event in events:
        if excluded(event) or event.get('id') in policy.get('sourceIds',[]) or event.get('commercialClassification')==safe_class or event.get('publicationPolicy')==marker:
            excluded_ids.add(event['id'])
    for row in context.get('records',[]):
        if row.get('eventId') in excluded_ids or excluded(row):
            if row.get('eventId'):excluded_ids.add(row['eventId'])
            for key in ('inviteeName','company'):
                if isinstance(row.get(key),str) and row[key].strip():withheld_names.add(row[key].strip())
    # The neutral event marker and its existing CRM join keep subsequent
    # imports from restoring named notes after the original intake was removed.
    # Identity records themselves remain untouched.
    for event in events:
        if event.get('id') in excluded_ids:
            for deal_id in event.get('matchedCrmDealIds',[]):
                deal=crm_deals.get(deal_id) or {}
                for key in ('person','title'):
                    if isinstance(deal.get(key),str) and deal[key].strip():withheld_names.add(deal[key].strip())

    def withheld_text(value):
        return has_private_context(value) or (isinstance(value,str) and any(re.search(r'(?<!\w)'+re.escape(name)+r'(?!\w)',value,re.I) for name in withheld_names))

    for event in events:
        if event.get('id') in excluded_ids:
            calendar_excluded=event.get('commercialClassification')=='excluded_interview_type' or event.get('id') in policy.get('sourceIds',[]) or event.get('publicationPolicy',{}).get('calendarCountsExcluded') is True
            minimal={key:copy.deepcopy(value) for key,value in event.items() if key in policy['allowedEventFields']}
            event_marker=copy.deepcopy(marker)
            event_marker['calendarCountsExcluded']=calendar_excluded
            minimal.update(name='Interview' if calendar_excluded else policy['safeEventName'],commercialClassification='excluded_interview_type' if calendar_excluded else safe_class,purposeEvidence=policy['safePurposeEvidence'],publicationPolicy=event_marker)
            event.clear();event.update(minimal)

    def prune_review(review):
        if not isinstance(review,dict):return
        if 'cases' in review:
            review['cases']=[row for row in review['cases'] if not excluded(row) and row.get('eventId') not in excluded_ids and not withheld_text(row.get('company'))]
        if 'notes' in review:review['notes']=[note for note in review['notes'] if not withheld_text(note)]
        if 'note' in review and withheld_text(review['note']):review['note']=policy['safeSourceNote']
        for prior in review.get('retainedPriorReviews',[]):prune_review(prior)

    prune_review(meetings.get('commercialSourceReview'))
    if 'notes' in meetings:meetings['notes']=[note for note in meetings['notes'] if not withheld_text(note)]
    if context and excluded_ids:
        context['records']=[row for row in context.get('records',[]) if row.get('eventId') not in excluded_ids and not excluded(row)]
        if 'notes' in context:context['notes']=[note for note in context['notes'] if not withheld_text(note)]
        by_id={event['id']:event for event in events}
        chains={by_id[row['eventId']].get('bookingChainId') or row['eventId'] for row in context['records'] if row.get('eventId') in by_id}
        context.update(publishedRecordCount=len(context['records']),publishedBookingChainCount=len(chains),publicationPolicy=copy.deepcopy(marker))
        context['scope']=f"{len(context['records'])} published Calendly business-intake records across {len(chains)} original booking chains; self-reported business intake and concise cancellation context only."
    for card in snapshot.get('sources',[]):
        if card.get('id') in ('meetings',policy['businessContextSourceId']):
            if withheld_text(card.get('note')):card['note']=policy['safeSourceNote']
            if card.get('id')==policy['businessContextSourceId'] and context and excluded_ids:card['coverage']=context['scope']
    return snapshot

def record_rule(value,configured,classification_rules=()):
    for key in ('id','recordingId','sourceId'):
        source_id=value.get(key)
        if isinstance(source_id,str) and source_id in configured:
            return configured[source_id]
    for rule in classification_rules:
        classification=value.get('classification')
        marker=value.get('publicationPolicy')
        if classification==rule['safeClassification'] or marker==rule['publicationPolicy'] or (
                isinstance(classification,str) and any(re.search(pattern,classification,re.I) for pattern in rule['classificationPatterns'])):
            return rule
    return None

def apply_publication_redactions(snapshot):
    """Minimize matched records, including arbitrary later metadata children.

    Only curated copies use this handler. It never touches the raw/private source
    files, changes source IDs/counts, or makes commercial/effort decisions.
    """
    configured=rules()
    classification_rules=record_classification_policies()
    def visit(value):
        if isinstance(value,dict):
            rule=record_rule(value,configured,classification_rules)
            if rule:
                enum_fields=rule.get('safeEnumFields',{})
                minimized={key:item for key,item in value.items() if key in rule['allowedFields'] and (key not in enum_fields or item in enum_fields[key])}
                minimized.update(title=rule['safeTitle'],classification=rule['safeClassification'],
                    classificationBasis=rule['safeClassificationBasis'],
                    publicationPolicy=copy.deepcopy(rule['publicationPolicy']))
                value.clear();value.update(minimized)
            for item in value.values():visit(item)
        elif isinstance(value,list):
            for item in value:visit(item)
    visit(snapshot)
    for policy in classification_policies():apply_booking_classification_policy(snapshot,policy)
    return snapshot

def validate_publication_redactions(snapshot):
    configured=rules()
    classification_rules=record_classification_policies()
    def visit(value):
        if isinstance(value,dict):
            rule=record_rule(value,configured,classification_rules)
            if rule:
                assert set(value)<=set(rule['allowedFields']), 'Excluded employment record restored unnecessary source fields'
                assert value.get('title')==rule['safeTitle'], 'Excluded employment record restored an identifying title'
                assert value.get('classification')==rule['safeClassification']
                assert value.get('classificationBasis')==rule['safeClassificationBasis'], 'Excluded employment record restored private assessment context'
                assert value.get('publicationPolicy')==rule['publicationPolicy'], 'Excluded employment record lost its publication policy'
                for key,allowed_values in rule.get('safeEnumFields',{}).items():
                    if key in value:assert value[key] in allowed_values, 'Audit review status restored unsafe freeform context'
            for item in value.values():visit(item)
        elif isinstance(value,list):
            for item in value:visit(item)
    visit(snapshot)
    expected=copy.deepcopy(snapshot)
    for policy in classification_policies():apply_booking_classification_policy(expected,policy)
    assert expected==snapshot, 'Non-buyer booking restored unrelated personal context or unsafe intake metadata'
    return True
