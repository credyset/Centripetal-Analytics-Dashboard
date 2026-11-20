"""Verify employment-source identities cannot reappear through later imports."""
from copy import deepcopy
from pathlib import Path
import json

from publication_redactions import apply_publication_redactions,validate_publication_redactions,rules
from prepare_shared_snapshot import curate_snapshot

ROOT=Path(__file__).resolve().parents[1]
rule=rules()['01M5CWDYQKG89SJR4KZ07H7DQ3']
source_record={'id':rule['sourceId'],'title':'Excluded personal title','indexedAt':'2026-10-22T17:30:00Z',
    'durationMinutes':25.18,'classification':'recruiting_interview','classificationBasis':'Private employment assessment',
    'participantNames':['Employment candidate'],'originalTitle':'Excluded personal title',
    'recordingUrl':'https://example.invalid/private-recording',
    'metadata':{'title':'Excluded personal title','candidateName':'Employment candidate'},
    'speakerNames':['Employment candidate'],'jobAssessment':'Private hiring discussion'}
prospect={'id':'other-source','title':'Approved prospect conversation','contact':'Approved prospect'}
fixture={'nested':{'records':[deepcopy(source_record),deepcopy(prospect)]}}
original=deepcopy(fixture)
minimized=apply_publication_redactions(deepcopy(fixture))
assert fixture==original, 'Minimization must operate on a curated copy'
record=minimized['nested']['records'][0]
assert record['id']==source_record['id'] and record['indexedAt']==source_record['indexedAt']
assert record['durationMinutes']==source_record['durationMinutes']
assert record['title']==rule['safeTitle'] and set(record)<=set(rule['allowedFields'])
assert minimized['nested']['records'][1]==prospect, 'Non-target prospect data changed'
validate_publication_redactions(minimized)
for mutation in ['title','extra_context','missing_policy']:
    bad=deepcopy(minimized)
    target=bad['nested']['records'][0]
    if mutation=='title':target['title']='Restored personal title'
    elif mutation=='extra_context':target['candidateName']='Restored identity'
    else:target.pop('publicationPolicy')
    try:validate_publication_redactions(bad)
    except AssertionError:pass
    else:raise AssertionError('Unsafe employment mutation passed: '+mutation)

# Exercise the actual final curation hook, including nested metadata from a
# future source merger rather than only trusting a redaction marker in input.
source=json.loads((ROOT/'data/shared-dashboard.json').read_text())
source.setdefault('meetings',{}).setdefault('fireflies',{})['publicationHookTest']={'records':[deepcopy(source_record)]}
before=deepcopy(source)
public=curate_snapshot(source)
assert source==before, 'Curation modified raw input'
curated=public['meetings']['fireflies']['publicationHookTest']['records'][0]
assert curated['title']==rule['safeTitle'] and 'metadata' not in curated
assert curated['publicationPolicy']['candidateIdentityWithheld'] is True
assert public['outcomes']==source['outcomes'], 'Employment minimization altered commercial decisions'
assert public['time']['summary']['ownerEstimateRange']==source['time']['summary']['ownerEstimateRange']
validate_publication_redactions(public)
print('Publication redaction: opaque-source-ID minimization, nested metadata removal, unchanged business data and fail-closed validation passed.')

# Classification policy applies to unknown future calendar IDs too, while
# preserving schedule inventory, approved buyer context and CRM identity data.
excluded_event={
    'id':'privacy-calendar-fixture','name':'30 Minute Meeting',
    'status':'active','createdAt':'2026-11-13T20:25:21Z',
    'startAt':'2026-11-17T18:30:00Z','endAt':'2026-11-17T19:00:00Z',
    'bookingChainId':'privacy-calendar-fixture','bookingChainComplete':True,
    'matchedCrmDealIds':[22],'heldVerified':False,'heldStatus':'unverified',
    'commercialClassification':'excluded_career_or_relationship_booking',
    'purposeEvidence':'The invitee entered CFO in the market.',
    'newPrivateBlob':{'intake':'Unrelated personal context'},
}
buyer_event={'id':'buyer-calendar-fixture','name':'Buyer meeting','status':'active',
    'startAt':'2026-11-18T18:00:00Z','bookingChainId':'buyer-calendar-fixture',
    'commercialClassification':'prospect_booking','purposeEvidence':'Buyer needs financial planning.'}
excluded_intake={'eventId':excluded_event['id'],'inviteeName':'Withheld Invitee',
    'company':None,'stage':'CFO in the market','financialNeeds':None}
buyer_intake={'eventId':buyer_event['id'],'inviteeName':'Approved Buyer',
    'company':'BuyerCo','stage':'Series A','financialNeeds':['Financial planning']}
excluded_case={'company':'Withheld Invitee','category':'career_or_relationship_booking',
    'evidence':'Unrelated personal booking context'}
buyer_case={'company':'BuyerCo','category':'held_prospect_call_source_confirmed',
    'evidence':'Reviewed buyer dialogue'}
calendar_fixture={
    'crm':{'deals':[{'id':22,'title':'Withheld Invitee','person':'Withheld Invitee'}]},
    'meetings':{
        'events':[deepcopy(excluded_event),deepcopy(buyer_event)],
        'summary':{'eventCount':2,'bookingChainCount':2,'heldBuyerCount':0},
        'notes':['One booking entered CFO in the market.','Withheld Invitee supplied personal context.','Approved buyer note'],
        'businessContextReview':{'scope':'Two intake records','records':[deepcopy(excluded_intake),deepcopy(buyer_intake)],
            'notes':['Withheld Invitee entered unrelated information.','Intake is self-reported.']},
        'commercialSourceReview':{'cases':[deepcopy(excluded_case),deepcopy(buyer_case)],
            'retainedPriorReviews':[{'cases':[deepcopy(excluded_case),deepcopy(buyer_case)]}]},
    },
    'sources':[{'id':'meetings','coverage':{'complete':True},'note':'One career/relationship booking.'},
        {'id':'calendly_business_context','coverage':'Two intake records'}],
}
original_calendar=deepcopy(calendar_fixture)
safe_calendar=apply_publication_redactions(deepcopy(calendar_fixture))
assert calendar_fixture==original_calendar
assert apply_publication_redactions(deepcopy(safe_calendar))==safe_calendar, 'Classification minimization is not idempotent'
validate_publication_redactions(safe_calendar)
calendar=safe_calendar['meetings']
neutral=calendar['events'][0]
for key in ('id','status','createdAt','startAt','endAt','bookingChainId','bookingChainComplete','matchedCrmDealIds','heldVerified','heldStatus'):
    assert neutral[key]==excluded_event[key], 'Calendar lifecycle field changed: '+key
assert neutral['commercialClassification']=='excluded_nonbuyer_booking'
assert neutral['purposeEvidence']=='Excluded non-buyer booking; attendance unverified'
assert 'newPrivateBlob' not in neutral
assert calendar['events'][1]==buyer_event and calendar['summary']==original_calendar['meetings']['summary']
assert safe_calendar['crm']==original_calendar['crm'], 'Approved identity records changed'
assert calendar['businessContextReview']['records']==[buyer_intake]
assert calendar['businessContextReview']['publishedRecordCount']==1
assert calendar['businessContextReview']['publishedBookingChainCount']==1
assert safe_calendar['sources'][1]['coverage']==calendar['businessContextReview']['scope']
assert calendar['notes']==['Approved buyer note']
assert calendar['businessContextReview']['notes']==['Intake is self-reported.']
assert calendar['commercialSourceReview']['cases']==[buyer_case]
assert calendar['commercialSourceReview']['retainedPriorReviews'][0]['cases']==[buyer_case]
for mutate in (
    lambda d:d['meetings']['events'][0].update(name='Restored unrelated personal title'),
    lambda d:d['meetings']['events'][0].update(commercialClassification='excluded_career_or_relationship_booking'),
    lambda d:d['meetings']['events'][0].update(purposeEvidence='Restored CFO in the market'),
    lambda d:d['meetings']['events'][0].update(newPrivateBlob={'personalAssessment':'Restored new payload'}),
    lambda d:d['meetings']['businessContextReview']['records'].append(deepcopy(excluded_intake)),
    lambda d:d['meetings']['businessContextReview']['records'].append({'eventId':excluded_event['id'],'inviteeName':'Withheld Invitee','stage':'New personal answer'}),
    lambda d:d['meetings']['commercialSourceReview']['cases'].append(deepcopy(excluded_case)),
    lambda d:d['meetings']['notes'].append('Withheld Invitee supplied personal context.'),
):
    unsafe=deepcopy(safe_calendar);mutate(unsafe)
    try:validate_publication_redactions(unsafe)
    except AssertionError:pass
    else:raise AssertionError('Unsafe non-buyer context passed validation')
    assert apply_publication_redactions(unsafe)==safe_calendar, 'Late source payload was not durably minimized'

# The real final curation hook must also sanitize the calendar branch.
source['meetings'].update(deepcopy(calendar_fixture['meetings']))
source['crm']['deals'].extend(deepcopy(calendar_fixture['crm']['deals']))
source['sources']=[s for s in source['sources'] if s['id'] not in ('meetings','calendly_business_context')]+deepcopy(calendar_fixture['sources'])
before_calendar_hook=deepcopy(source)
public_calendar=curate_snapshot(source)
assert source==before_calendar_hook
assert public_calendar['meetings']['events']==safe_calendar['meetings']['events']
assert public_calendar['crm']==source['crm']
assert public_calendar['outcomes']==source['outcomes']
validate_publication_redactions(public_calendar)
print('Non-buyer booking privacy: neutral calendar proof, intake/case/note removal, truthful published scope, late-import rejection and unchanged buyer data/counters passed.')

# The verified HR cohort is protected by opaque source identity even if a later
# metadata import loses its reviewed classification. Generic classification
# protects future verified HR records that do not yet have an explicit rule.
known_rules=rules()
for source_id,known_rule in known_rules.items():
    late={'id':source_id,'title':'Restored personal interview title','classification':'unclassified',
        'indexedAt':'2026-10-12T12:00:00Z','durationMinutes':23.5,
        'purposeReferences':[{'speakerLabel':'Private participant','sentenceIndex':4}],
        'charlesSpeakerEvidence':'Private employment dialogue',
        'recordingUrl':'https://example.invalid/private-recording',
        'metadata':{'hiringAssessment':'Private assessment'}}
    safe=apply_publication_redactions({'futureImport':{'records':[deepcopy(late)]}})
    minimal=safe['futureImport']['records'][0]
    assert minimal['title']==known_rule['safeTitle'] and minimal['classification']==known_rule['safeClassification']
    assert set(minimal)<=set(known_rule['allowedFields'])
    assert minimal['id']==source_id and minimal['durationMinutes']==23.5
    validate_publication_redactions(safe)
    try:validate_publication_redactions({'futureImport':{'records':[late]}})
    except AssertionError:pass
    else:raise AssertionError('Known HR source ID restored unclassified private metadata')

future_hr={'id':'future-hr-source','title':'Private employment call','classification':'hiring_reference_check',
    'classificationBasis':'Private compensation and candidate assessment','reviewedDialogue':True,
    'purposeReviewStatus':'dialogue_reviewed_purpose_classified',
    'indexedAt':'2026-11-20T12:00:00Z','durationMinutes':17.5,'sentenceCount':120,
    'purposeReferences':[{'speakerLabel':'Private participant'}],
    'recordingUrl':'https://example.invalid/private-recording','dateBasis':'Private source prose',
    'newMetadata':{'interviewAssessment':'Unrelated HR details'}}
future_safe=apply_publication_redactions({'nested':[deepcopy(future_hr)]})
future_record=future_safe['nested'][0]
assert future_record['classification']=='excluded_employment_context'
assert future_record['title']=='Excluded employment context'
assert future_record['durationMinutes']==17.5 and future_record['sentenceCount']==120
assert future_record['purposeReviewStatus']=='dialogue_reviewed_purpose_classified'
assert not set(future_record)&{'purposeReferences','recordingUrl','newMetadata','dateBasis'}
assert apply_publication_redactions(deepcopy(future_safe))==future_safe
validate_publication_redactions(future_safe)
unsafe_review_status=deepcopy(future_safe)
unsafe_review_status['nested'][0]['purposeReviewStatus']='Restored private assessment prose'
try:validate_publication_redactions(unsafe_review_status)
except AssertionError:pass
else:raise AssertionError('Freeform HR review status passed publication validation')
assert 'purposeReviewStatus' not in apply_publication_redactions(unsafe_review_status)['nested'][0]
try:validate_publication_redactions({'nested':[future_hr]})
except AssertionError:pass
else:raise AssertionError('Future classified HR source retained private metadata')

actual=json.loads((ROOT/'data/shared-dashboard.json').read_text())
actual_before=deepcopy(actual)
actual_safe=apply_publication_redactions(deepcopy(actual))
assert actual==actual_before, 'Privacy curation changed input source evidence'
validate_publication_redactions(actual_safe)
assert apply_publication_redactions(deepcopy(actual_safe))==actual_safe

def records_by_policy(value):
    found=[]
    if isinstance(value,dict):
        if value.get('id') in known_rules:found.append(value)
        for item in value.values():found.extend(records_by_policy(item))
    elif isinstance(value,list):
        for item in value:found.extend(records_by_policy(item))
    return found

before_cohort=records_by_policy(actual['meetings']['fireflies'])
after_cohort=records_by_policy(actual_safe['meetings']['fireflies'])
assert len(before_cohort)==len(after_cohort) and {r['id'] for r in after_cohort}==set(known_rules), 'Actual verified HR cohort coverage changed'
for before,after in zip(before_cohort,after_cohort):
    assert before['id']==after['id']
    for key in ('indexedAt','occurredAt','durationMinutes','sentenceCount','speakerCount','sourceEvidenceSha256','purposeReviewStatus'):
        if key in before:assert before[key]==after[key], 'HR audit metadata changed: '+key
    assert set(after)<=set(known_rules[after['id']]['allowedFields'])
    assert not set(after)&{'purposeReferences','charlesSpeakerEvidence','speakerNames','recordingUrl','metadata'}
for key in ('summary','coverage'):
    assert actual_safe['meetings']['fireflies'][key]==actual['meetings']['fireflies'][key]
assert actual_safe['crm']==actual['crm'] and actual_safe['time']==actual['time']
assert actual_safe['outcomes']==actual['outcomes']
# Recompute the app's actual generic-booking eligibility, rather than relying on
# stored summary counters. All included/excluded IDs and lifecycle grains agree.
def eligibility(events):
    return {e['id'] for e in events if e.get('commercialClassification')!='excluded_interview_type'}
assert eligibility(actual['meetings']['events'])==eligibility(actual_safe['meetings']['events'])
lifecycle=('id','status','createdAt','updatedAt','startAt','endAt','canceledAt','bookingChainId','bookingCreatedAt','bookingChainComplete','isCurrentBooking','rescheduled','rescheduledFromEventId','rescheduledToEventId')
assert [{k:e.get(k) for k in lifecycle} for e in actual['meetings']['events']]==[{k:e.get(k) for k in lifecycle} for e in actual_safe['meetings']['events']]
assert actual_safe['meetings']['summary']==actual['meetings']['summary']
protected=set(known_rules)
before_buyers=[r for r in actual['meetings']['fireflies']['records'] if r.get('id') not in protected]
after_buyers=[r for r in actual_safe['meetings']['fireflies']['records'] if r.get('id') not in protected]
assert before_buyers==after_buyers, 'Publication privacy changed unrelated business recordings'
print('Verified HR cohort privacy: 10 opaque IDs, recursive known/future record rules, late-import rejection, preserved buyer records/audio selection and exact calendar eligibility/lifecycle sets passed.')
