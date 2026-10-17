"""Build the private, minimal CRM dashboard dataset from retained read-only snapshots."""
import json
import re
from pathlib import Path
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from collections import Counter, defaultdict

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / 'data' / 'private'
OUTPUT = ROOT / 'data' / 'crm.json'
TZ = ZoneInfo('America/Denver')

def load(name):
    return json.loads((PRIVATE / name).read_text())

def iso(value):
    if not value: return None
    value = str(value)
    if len(value) == 10: return value
    try:
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')
    except ValueError: return value

def localdate(value):
    if not value: return None
    try:
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(TZ).date().isoformat()
    except ValueError: return str(value)[:10]

def ref(value):
    if isinstance(value, dict):
        return value.get('name') or value.get('value') or value.get('id')
    return value

def ident(value):
    return value.get('id', value.get('value')) if isinstance(value, dict) else value

def test_label(value):
    return bool(re.search(r'(?:\btest\b|[_ ]test(?:[_ ]|$)|nurturetest$)',value or '',re.I))

def safe_subject(value):
    # Activity task titles are allowed, but embedded contact addresses are not published.
    return re.sub(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', '[email redacted]', value or '')

def redact_contact_addresses(value):
    if isinstance(value,dict): return {k:redact_contact_addresses(v) for k,v in value.items()}
    if isinstance(value,list): return [redact_contact_addresses(v) for v in value]
    return safe_subject(value) if isinstance(value,str) else value

def assess(out, manifest, raw_deals, raw_activities):
    deals=[d for d in out['deals'] if not d['isTest']]
    acts=[a for a in out['activities'] if not a['isTest']]
    today=datetime.fromisoformat(out['snapshotAt'].replace('Z','+00:00')).astimezone(TZ).date()
    day=today.isoformat(); end=(today-timedelta(days=1)).isoformat()
    stages={s['id']:s for s in out['stages']}
    def due_bucket(a):
        if a['done']: return 'done'
        if not a['dueDate']: return 'undated'
        return 'overdue' if a['dueDate']<day else 'today' if a['dueDate']==day else 'future'
    def count_scope(rows):
        return {'records':len(rows),'done':sum(a['done'] for a in rows),'undone':sum(not a['done'] for a in rows),
          'overdue':sum(due_bucket(a)=='overdue' for a in rows),'dueToday':sum(due_bucket(a)=='today' for a in rows),
          'future':sum(due_bucket(a)=='future' for a in rows),'undatedUndone':sum(due_bucket(a)=='undated' for a in rows)}
    def groups(key, rows=acts):
        return [{key:k,**count_scope([a for a in rows if a[key]==k])} for k in sorted({a[key] for a in rows},key=str)]
    def period(start, finish):
        def within(value): return start <= (localdate(value) or '') <= finish
        created=[a for a in acts if within(a['createdAt'])]
        completed=[a for a in acts if a['done'] and within(a['completedAt'])]
        due=[a for a in acts if a['dueDate'] and start<=a['dueDate']<=finish]
        updated=[a for a in acts if within(a['updatedAt'])]
        return {'start':start,'end':finish,'activitiesCreated':len(created),'activitiesMarkedDone':len(completed),
          'automationActivitiesCreated':sum(a.get('referenceType')=='automation' for a in created),
          'activitiesDue':len(due),'latestUpdatedActivities':len(updated),
          'callsCreated':sum(a['type']=='call' for a in created),'callsMarkedDone':sum(a['type']=='call' for a in completed),
          'callsDue':sum(a['type']=='call' for a in due),
          'meetingsCreated':sum(a['type']=='meeting' for a in created),'meetingsMarkedDone':sum(a['type']=='meeting' for a in completed),
          'meetingsDue':sum(a['type']=='meeting' for a in due),
          'createdByType':dict(Counter(a['type'] for a in created)),'completedByType':dict(Counter(a['type'] for a in completed)),
          'createdByOwner':dict(Counter(a['owner'] for a in created)),'completedByOwner':dict(Counter(a['owner'] for a in completed)),
          'createdActivityIds':[a['id'] for a in created],'completedActivityIds':[a['id'] for a in completed]}
    overdue=[a for a in acts if due_bucket(a)=='overdue']
    aging={'1–7 days':0,'8–30 days':0,'31–90 days':0,'Over 90 days':0}
    for a in overdue:
        n=(today-datetime.fromisoformat(a['dueDate']).date()).days
        aging['1–7 days' if n<=7 else '8–30 days' if n<=30 else '31–90 days' if n<=90 else 'Over 90 days']+=1
    baseline_path=manifest.get('baselineSnapshotPath')
    comparison={'available':False}
    if baseline_path and (ROOT/baseline_path/'crm.json').exists():
        baseline=json.loads((ROOT/baseline_path/'crm.json').read_text())
        def changed(old,new,fields):
            oi={x['id']:x for x in old}; ni={x['id']:x for x in new}
            diffs=[]
            for id in sorted(oi.keys()&ni.keys()):
                delta={k:{'before':oi[id].get(k),'after':ni[id].get(k)} for k in fields if oi[id].get(k)!=ni[id].get(k)}
                if delta: diffs.append({'id':id,'changes':delta})
            return sorted(ni.keys()-oi.keys()),sorted(oi.keys()-ni.keys()),diffs
        nd,rd,cd=changed(baseline['deals'],out['deals'],['title','pipelineId','stageId','status','value','owner','updatedAt','nextActivityDate','lastActivityDate'])
        na,ra,ca=changed(baseline['activities'],out['activities'],['done','type','dueDate','dealId','owner','completedAt'])
        comparison={'available':True,'baselineAt':baseline['snapshotAt'],'currentAt':out['snapshotAt'],
          'baselineDealCount':len(baseline['deals']),'currentDealCount':len(out['deals']),
          'baselineActivityCount':len(baseline['activities']),'currentActivityCount':len(out['activities']),
          'newDealIds':nd,'removedDealIds':rd,'changedDeals':cd,'newActivityIds':na,'removedActivityIds':ra,'changedActivities':ca,
          'note':'Snapshot differences are observed since the baseline, not a complete intervening event history. Missing source records need deletion/permission checks.'}
    history_file=PRIVATE/'pipedrive_stage_history.json'
    history=json.loads(history_file.read_text()) if history_file.exists() else {'complete':False,'fromDate':'2026-09-01','dealIdsReviewed':[],'events':[]}
    for event in history.get('events',[]):
        event['timestamp']=iso(event['timestamp'])
        if event['field']=='stage_id':
            for prefix in ['old','new']:
                raw=event.get(prefix+'Value')
                stage=stages.get(int(raw)) if raw is not None and str(raw).isdigit() else None
                event[prefix+'StageName']=stage.get('name') if stage else None
                event[prefix+'PipelineId']=stage.get('pipelineId') if stage else None
        event['commercialProgression']=None
    working_sales=[]
    parking_sales=[]
    for d in deals:
        stage=stages.get(d['stageId'],{}).get('name','')
        if d['pipelineId']!=1 or d['status']!='open' or stage.lower() in ['closed won','closed lost']: continue
        linked=[a for a in acts if a['dealId']==d['id']]
        stage_basis=d['stageChangedAt'] or d['createdAt']
        info={'dealId':d['id'],'title':d['title'],'stageId':d['stageId'],'stage':stage,'owner':d['owner'],
          'stageEnteredAt':stage_basis,'stageEntryDateBasis':'latest stage change' if d['stageChangedAt'] else 'creation date proxy',
          'daysAtCurrentStage':(today-datetime.fromisoformat(localdate(stage_basis)).date()).days if stage_basis else None,
          'undoneActivities':sum(not a['done'] for a in linked),'overdueActivities':sum(due_bucket(a)=='overdue' for a in linked),
          'futureActivities':sum(due_bucket(a)=='future' for a in linked),
          'futureActivityIds':[a['id'] for a in linked if due_bucket(a)=='future'],
          'nextScheduledDate':min((a['dueDate'] for a in linked if not a['done'] and a['dueDate']),default=None),
          'latestRecordedActivityAt':max((a['createdAt'] for a in linked if a['createdAt']),default=None)}
        (parking_sales if 'Parking Lot' in stage else working_sales).append(info)
    orphan=[a for a in acts if not a['dealId']]
    terminal_open=[d for d in deals if d['status']=='open' and stages.get(d['stageId'],{}).get('name','').lower() in ['closed won','closed lost']]
    inventory={**count_scope(acts),'overdueUndone':len(overdue),'byType':groups('type'),'byOwner':groups('owner'),'byReferenceType':groups('referenceType'),
      'automationReferencedActivities':sum(a.get('referenceType')=='automation' for a in acts),
      'overdueAgeBuckets':aging,'unlinkedActivities':len(orphan),'unlinkedActivityIds':[a['id'] for a in orphan],
      'noPersonOrCompanyOrDealLink':sum(not a['dealId'] and not a['personId'] and not a['organizationId'] for a in acts),
      'activitiesLinkedToMissingDeal':sum(bool(a['dealId']) and a['dealId'] not in {d['id'] for d in deals} for a in acts),
      'missingCreatedAt':sum(not a['createdAt'] for a in acts),'missingDueDate':sum(not a['dueDate'] for a in acts),
      'missingCompletedAtAmongDone':sum(a['done'] and not a['completedAt'] for a in acts),
      'latestBusinessActivityCreatedAt':max((a['createdAt'] for a in acts if a['createdAt']),default=None),
      'latestBusinessActivityCompletedAt':max((a['completedAt'] for a in acts if a['completedAt']),default=None)}
    review={'asOf':out['snapshotAt'],'inventory':inventory,'snapshotChanges':comparison,'history':history,
      'periods':{**{f'last{n}CompleteDays':period((today-timedelta(days=n)).isoformat(),end) for n in [7,30,90]},
        'sinceSeptember1':period('2026-09-01',day),'currentWeekToDate':period((today-timedelta(days=today.weekday())).isoformat(),day),
        'currentDayPartial':period(day,day)},
      'newestActivities':sorted(acts,key=lambda a:a['createdAt'] or '',reverse=True)[:20],
      'newestCompletedActivities':sorted([a for a in acts if a['done']],key=lambda a:a['completedAt'] or '',reverse=True)[:20],
      'workingSalesFollowUp':working_sales,'parkingSalesFollowUp':parking_sales,
      'openClosedStageDealIds':[d['id'] for d in terminal_open],
      'alerts':[
        {'id':'activity-recency','severity':'warning','title':'CRM task completion is not a full business-development activity log','detail':'Business completions and channel activity have different coverage; do not interpret zero CRM completions as zero outreach or meetings.'},
        {'id':'stage-status-conflicts','severity':'warning','title':'Open status in terminal-labelled stages','count':len(terminal_open),'dealIds':[d['id'] for d in terminal_open]},
        {'id':'pipeline-value','severity':'warning','title':'Open deal valuation is incomplete' if any(d['value'] for d in deals if d['status']=='open') else 'Open deal values are unpopulated','count':sum(not d['value'] for d in deals if d['status']=='open')},
        {'id':'overdue-backlog','severity':'warning','title':'Scheduled overdue tasks require triage','count':len(overdue)},
      ]}
    return review

def build():
    manifest = load('pipedrive_manifest.json')
    raw_deals = load('pipedrive_deals.json')
    raw_activities = load('pipedrive_activities.json')
    raw_pipelines = load('pipedrive_pipelines.json')
    raw_stages = load('pipedrive_stages.json')
    raw_types = load('pipedrive_activity_types.json')
    users = {u['id']:u.get('name') for u in load('pipedrive_users.json')}
    field_rows=load('pipedrive_deal_fields.json') if (PRIVATE/'pipedrive_deal_fields.json').exists() else []
    field_lookup={f['name']:f for f in field_rows}
    def custom(d,name):
        field=field_lookup.get(name,{})
        value=d.get(field.get('key'))
        if field.get('options') and value is not None:
            return next((o['label'] for o in field['options'] if str(o['id'])==str(value)),value)
        return value
    pipelines = [{'id':p['id'],'name':p.get('name'),'active':p.get('active'),'order':p.get('order_nr')} for p in raw_pipelines]
    stages = [{'id':s['id'],'name':s.get('name'),'pipelineId':s.get('pipeline_id'),'order':s.get('order_nr'),'active':s.get('active_flag')} for s in raw_stages]
    stage_lookup = {s['id']:s for s in stages}
    deals = []
    for d in raw_deals:
        owner = d.get('user_id', d.get('owner_id'))
        deals.append({'id':d['id'],'title':d.get('title'),'person':d.get('person_name') or ref(d.get('person_id')),'isTest':test_label(d.get('title')),
          'personId':ident(d.get('person_id')),'organizationId':ident(d.get('org_id')),
          'company':d.get('org_name') or ref(d.get('org_id')),'pipelineId':d.get('pipeline_id'),'stageId':d.get('stage_id'),
          'status':d.get('status'),'value':d.get('value'),'currency':d.get('currency'),
          'createdAt':iso(d.get('add_time')),'updatedAt':iso(d.get('update_time')),'stageChangedAt':iso(d.get('stage_change_time')),
          'wonAt':iso(d.get('won_time')),'lostAt':iso(d.get('lost_time')),
          'scheduledCallDate':custom(d,'Scheduled Call Date'),'lastCallDate':custom(d,'Last Call Date'),
          'lastCalendlyMeetingDate':custom(d,'Last Calendly Meeting'),'calendlyMeetingsCompleted':custom(d,'Calendly Meetings Completed'),
          'meetingOutcome':custom(d,'Meeting Outcome'),'hasTranscriptFlag':custom(d,'Has Fireflies Transcript'),
          'nextActivityDate':d.get('next_activity_date'),'lastActivityDate':d.get('last_activity_date'),
          'owner':ref(owner) if isinstance(owner, dict) else users.get(owner, owner)})
    activities = []
    test_deal_ids = {d['id'] for d in deals if d['isTest']}
    for a in raw_activities:
        owner = a.get('user_id', a.get('owner_id'))
        activities.append({'id':a['id'],'type':a.get('type'),'done':bool(a.get('done')),'isTest':a.get('deal_id') in test_deal_ids or test_label(a.get('subject')),
          'subject':safe_subject(a.get('subject')),'updatedAt':iso(a.get('update_time')),'dueTime':a.get('due_time') or None,
          'person':a.get('person_name'),'company':a.get('org_name'),'personId':a.get('person_id'),'organizationId':a.get('org_id'),
          'referenceType':a.get('reference_type'),'referenceId':a.get('reference_id'),
          'automationId':a.get('reference_id') if a.get('reference_type')=='automation' else None,
          'createdAt':iso(a.get('add_time')),'completedAt':iso(a.get('marked_as_done_time')),'dueDate':a.get('due_date'),
          'dealId':a.get('deal_id'),'owner':ref(owner) if isinstance(owner, dict) else users.get(owner, owner)})
    all_dates = [localdate(x['createdAt']) for x in deals if x['createdAt']]
    today = datetime.fromisoformat(manifest['snapshotAt'].replace('Z','+00:00')).astimezone(TZ).date()
    yesterday = today - timedelta(days=1)
    first = today - timedelta(days=30)
    assert len({d['id'] for d in deals}) == len(deals), 'Duplicate deal IDs in paginated snapshot'
    assert len({a['id'] for a in activities}) == len(activities), 'Duplicate activity IDs in paginated snapshot'
    business_deals = [d for d in deals if not d['isTest']]
    business_activities = [a for a in activities if not a['isTest']]
    def in_period(v):
        day = localdate(v)
        return day is not None and first.isoformat() <= day <= yesterday.isoformat()
    def period(start, end):
        return {
          'start':start,'end':end,
          'newDeals':sum(start <= (localdate(d['createdAt']) or '') <= end for d in business_deals),
          'latestUpdatedDeals':sum(start <= (localdate(d['updatedAt']) or '') <= end for d in business_deals),
          'wonDeals':sum(d['status']=='won' and start <= (localdate(d['wonAt']) or '') <= end for d in business_deals),
          'lostDeals':sum(d['status']=='lost' and start <= (localdate(d['lostAt']) or '') <= end for d in business_deals),
          'activitiesMarkedDone':sum(a['done'] and start <= (localdate(a['completedAt']) or '') <= end for a in business_activities),
          'callsDue':sum(a['type']=='call' and start <= (a['dueDate'] or '') <= end for a in business_activities),
          'callsMarkedDone':sum(a['type']=='call' and a['done'] and start <= (localdate(a['completedAt']) or '') <= end for a in business_activities),
        }
    value_by = defaultdict(lambda: {'count':0,'value':0})
    for d in business_deals:
        if d['status']=='open':
            k=(d['pipelineId'],d['stageId'],d['currency'])
            value_by[k]['count']+=1
            value_by[k]['value']+=d['value'] or 0
    open_by_stage = [{'pipelineId':p,'stageId':s,'currency':c,**v} for (p,s,c),v in value_by.items()]
    # Sales is a CRM pipeline scope, not a claim that every record is a qualified opportunity.
    sales_ids = [p['id'] for p in pipelines if p['name'].lower()=='sales pipeline']
    sales_values = defaultdict(lambda: {'count':0,'value':0})
    active_sales_values = defaultdict(lambda: {'count':0,'value':0})
    for d in business_deals:
        stage = stage_lookup.get(d['stageId'],{}).get('name','').lower()
        if d['status']=='open' and d['pipelineId'] in sales_ids and not any(x in stage for x in ['graveyard','nurture']):
            sales_values[d['currency']]['count']+=1
            sales_values[d['currency']]['value']+=d['value'] or 0
            if not any(x in stage for x in ['parking lot','closed won','closed lost']):
                active_sales_values[d['currency']]['count']+=1
                active_sales_values[d['currency']]['value']+=d['value'] or 0
    weekly=[]
    monday=today-timedelta(days=today.weekday())-timedelta(weeks=12)
    while monday<=today:
        end=min(monday+timedelta(days=6),yesterday)
        if end>=monday: weekly.append(period(monday.isoformat(),end.isoformat()))
        monday+=timedelta(weeks=1)
    quality = {
      'stageHistoryAvailable':False,'bookingsVerified':False,'heldCallsVerified':False,
      'missingDealCreatedAt':sum(not d['createdAt'] for d in deals),
      'missingDealStageChangedAt':sum(not d['stageChangedAt'] for d in deals),
      'completedActivitiesWithoutCompletedAt':sum(a['done'] and not a['completedAt'] for a in activities),
      'zeroValueOpenDeals':sum(d['status']=='open' and not d['value'] for d in deals),
      'testDealIds':sorted(test_deal_ids),'testActivityIds':[a['id'] for a in activities if a['isTest']],
      'excludedTestDeals':len(deals)-len(business_deals),'excludedTestActivities':len(activities)-len(business_activities),
      'openDealsInClosedLabelledStages':sum(d['status']=='open' and stage_lookup.get(d['stageId'],{}).get('name','').lower() in ['closed won','closed lost'] for d in business_deals),
      'pipelineValuePopulated':any(d['value'] for d in business_deals if d['status']=='open'),
      'pipelineValueComplete':all(bool(d['value']) for d in business_deals if d['status']=='open'),
      'zeroOrUnsetValueBusinessOpenDeals':sum(d['status']=='open' and not d['value'] for d in business_deals),
      'valuedBusinessOpenDeals':sum(d['status']=='open' and bool(d['value']) for d in business_deals),
      'verificationBasis':'CRM source snapshot alone. Separately confirmed owner/calendar evidence may substantiate bookings or held meetings without a matching CRM activity completion.',
      'updatedDateIsLatestOnly':True,
      'caveats':[
        'Current latest update timestamps count distinct records by their latest update only; they do not reconstruct all updates made during historical periods.',
        'Current stage and latest stage-change timestamp do not reconstruct stage movement history or demonstrate forward progression.',
        'Call due dates describe scheduled activity dates, not booking creation dates. Marked done describes CRM completion, not independent proof a call was held.',
        'Sales Pipeline values exclude Leads/Referral pipelines and nurture/graveyard stages. Values are source-entered and valuation basis is unverified; they are not recognized revenue or verified qualified pipeline.',
        'Won/lost dates are the current retained timestamps; reopened/re-won deal history is not reconstructed.',
        'Pipedrive timestamps lacking an explicit offset are interpreted as UTC; date-only due dates are retained unchanged.',
        'Scope is all accessible, non-deleted deals and accessible done/undone activities. Deleted records are excluded; account permissions may restrict visibility.'
        ,'Obvious test-labelled deals and activities are retained in the record inventory but excluded from all business summaries.'
        ,('Only part of the open-record inventory has a nonzero source-entered value. Show the valued portion and coverage; do not represent it as complete qualified pipeline or recognized revenue.' if any(d['value'] for d in business_deals if d['status']=='open') else 'All current open deal values are zero. Show pipeline valuation as unpopulated rather than claiming the commercial pipeline is worth zero.')
        ,'Open status can coexist with Closed Won/Closed Lost stage labels; stage labels are not substitutes for actual won/lost status.'
        ,'Collection is a paginated snapshot, not an atomic database transaction; records can change during collection.'
      ]}
    out = {
      'snapshotAt':manifest['snapshotAt'],'timezone':'America/Denver',
      'coverage':{'method':'read-only connector snapshot','dealsComplete':manifest['dealsComplete'],'activitiesComplete':manifest['activitiesComplete'],
        'earliestDealCreatedDate':min(all_dates) if all_dates else None,'latestDealCreatedDate':max(all_dates) if all_dates else None,
        'earliestActivityCreatedDate':min((localdate(a['createdAt']) for a in activities if a['createdAt']),default=None),
        'latestActivityCreatedAt':max((a['createdAt'] for a in activities if a['createdAt']),default=None),
        'latestActivityCompletedAt':max((a['completedAt'] for a in activities if a['completedAt']),default=None),
        'activityOwnerCounts':dict(Counter(a['owner'] for a in activities)),
        'reportingThrough':yesterday.isoformat(),'currentDayPartial':today.isoformat(),'pagination':manifest['pagination']},
      'pipelines':pipelines,'stages':stages,'activityTypes':[{'key':x.get('key_string'),'name':x.get('name')} for x in raw_types],
      'deals':deals,'activities':activities,
      'summary':{'dealCount':len(business_deals),'activityCount':len(business_activities),'inventoryDealCount':len(deals),'inventoryActivityCount':len(activities),'dealStatusCounts':dict(Counter(d['status'] for d in business_deals)),
        'openByStage':open_by_stage,'salesPipelineByCurrency':[{'currency':c,**v} for c,v in sales_values.items()],
        'activeSalesByCurrency':[{'currency':c,**v} for c,v in active_sales_values.items()],
        'acceptedOpportunityCount':None,
        'last30CompleteDays':period(first.isoformat(),yesterday.isoformat()),'weekly':weekly,
        'overdueUndoneActivities':sum(bool(not a['done'] and a['dueDate'] and a['dueDate']<today.isoformat()) for a in business_activities)},
      'quality':quality
    }
    out['assessment']=assess(out,manifest,raw_deals,raw_activities)
    title_groups=defaultdict(list)
    for deal in business_deals:
        key=re.sub(r'[^a-z0-9]+',' ',deal['title'].lower()).strip() if deal.get('title') else ''
        if key:title_groups[key].append(deal)
    out['assessment']['duplicateTitleGroups']=[{'normalizedTitle':key,'dealIds':[d['id'] for d in rows],
      'titles':[d['title'] for d in rows],'pipelineIds':[d['pipelineId'] for d in rows],
      'organizationIds':[d['organizationId'] for d in rows],'note':'Same normalized title is a review flag, not proof of a duplicate person, company or sales opportunity.'} for key,rows in title_groups.items() if len(rows)>1]
    known_values=defaultdict(lambda:{'records':0,'value':0})
    for deal in business_deals:
        if deal['status']=='open' and deal['value']:
            known_values[deal['currency']]['records']+=1
            known_values[deal['currency']]['value']+=deal['value']
    out['assessment']['valuationCoverage']={'businessOpenRecords':sum(d['status']=='open' for d in business_deals),
      'nonzeroValuedRecords':out['quality']['valuedBusinessOpenDeals'],'zeroOrUnsetRecords':out['quality']['zeroOrUnsetValueBusinessOpenDeals'],
      'knownPortionByCurrency':[{'currency':currency,**values} for currency,values in known_values.items()],
      'valuationBasisVerified':False,'completeQualifiedPipelineValue':None,
      'records':[{'dealId':d['id'],'title':d['title'],'value':d['value'],'currency':d['currency'],'stageId':d['stageId']} for d in business_deals if d['status']=='open' and d['value']]}
    custom_columns={'Scheduled Call Date':'scheduledCallDate','Last Call Date':'lastCallDate','Last Calendly Meeting':'lastCalendlyMeetingDate',
      'Calendly Meetings Completed':'calendlyMeetingsCompleted','Meeting Outcome':'meetingOutcome','Has Fireflies Transcript':'hasTranscriptFlag'}
    out['assessment']['customFieldCoverage']=[{'field':name,'key':key,'populatedRecords':sum(d.get(key) not in [None,''] for d in business_deals),
      'latestValue':max((str(d[key]) for d in business_deals if d.get(key) not in [None,'']),default=None) if key.endswith('Date') else None} for name,key in custom_columns.items()]
    out['assessment']['scheduledCallDateRecords']=[{'dealId':d['id'],'title':d['title'],'date':d['scheduledCallDate'],'owner':d['owner']} for d in business_deals if d['scheduledCallDate']]
    out['quality']['stageHistoryAvailable']=bool(out['assessment']['history'].get('events'))
    out['quality']['stageHistoryComplete']=False
    out['quality']['stageHistoryDealCount']=len(out['assessment']['history'].get('dealIdsReviewed',[]))
    out['quality']['stageHistoryEventCount']=len(out['assessment']['history'].get('events',[]))
    history_count=out['quality']['stageHistoryDealCount']
    history_asof=out['assessment']['history'].get('collectedAt') or out['assessment']['history'].get('sourceSnapshotAt')
    out['quality']['caveats'].append(f'Structured history is retained for a defined {history_count}-deal subset since September 1. Its collection date is separate from current record collection; these observed changes are not account-wide progression, and Closed Won stage entry is not won status or verified revenue.')
    out['coverage']['stageHistorySnapshotAt']=history_asof
    out['coverage']['collectionStartedAt']=manifest.get('collectionStartedAt')
    out['coverage']['collectionCompletedAt']=manifest['snapshotAt']
    out['coverage']['allOwnerActivitiesRequested']=manifest.get('filters',{}).get('activities',{}).get('user_id')==0
    out['coverage']['latestBusinessActivityCreatedAt']=out['assessment']['inventory']['latestBusinessActivityCreatedAt']
    out['coverage']['latestBusinessActivityCompletedAt']=out['assessment']['inventory']['latestBusinessActivityCompletedAt']
    if manifest.get('leadsInboxComplete'):
        inbox=load('pipedrive_leads_inbox.json')
        out['leadsInbox']={'complete':True,'activeCount':sum(not x.get('is_archived') for x in inbox),'archivedCount':sum(bool(x.get('is_archived')) for x in inbox),
          'note':'Leads Inbox records are separate from deals in the Leads Pipeline. Counts reflect accessible records only.'}
    out=redact_contact_addresses(out)
    OUTPUT.write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'deals':len(deals),'activities':len(activities),'summary':out['summary'],'quality':quality},indent=2))

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir',type=Path,default=PRIVATE)
    parser.add_argument('--output',type=Path,default=OUTPUT)
    args=parser.parse_args()
    PRIVATE=args.source_dir.resolve()
    OUTPUT=args.output.resolve()
    build()
