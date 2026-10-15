"""Build the private, minimal CRM dashboard dataset from retained read-only snapshots."""
import json
import re
from pathlib import Path
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from collections import Counter, defaultdict

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / 'data' / 'private'
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
    return bool(re.search(r'(?:\btest\b|[_ ]test(?:[_ ]|$))',value or '',re.I))

def build():
    manifest = load('pipedrive_manifest.json')
    raw_deals = load('pipedrive_deals.json')
    raw_activities = load('pipedrive_activities.json')
    raw_pipelines = load('pipedrive_pipelines.json')
    raw_stages = load('pipedrive_stages.json')
    raw_types = load('pipedrive_activity_types.json')
    users = {u['id']:u.get('name') for u in load('pipedrive_users.json')}
    pipelines = [{'id':p['id'],'name':p.get('name'),'active':p.get('active'),'order':p.get('order_nr')} for p in raw_pipelines]
    stages = [{'id':s['id'],'name':s.get('name'),'pipelineId':s.get('pipeline_id'),'order':s.get('order_nr'),'active':s.get('active_flag')} for s in raw_stages]
    stage_lookup = {s['id']:s for s in stages}
    deals = []
    for d in raw_deals:
        owner = d.get('user_id', d.get('owner_id'))
        deals.append({'id':d['id'],'title':d.get('title'),'person':d.get('person_name') or ref(d.get('person_id')),'isTest':test_label(d.get('title')),
          'company':d.get('org_name') or ref(d.get('org_id')),'pipelineId':d.get('pipeline_id'),'stageId':d.get('stage_id'),
          'status':d.get('status'),'value':d.get('value'),'currency':d.get('currency'),
          'createdAt':iso(d.get('add_time')),'updatedAt':iso(d.get('update_time')),'stageChangedAt':iso(d.get('stage_change_time')),
          'wonAt':iso(d.get('won_time')),'lostAt':iso(d.get('lost_time')),
          'nextActivityDate':d.get('next_activity_date'),'lastActivityDate':d.get('last_activity_date'),
          'owner':ref(owner) if isinstance(owner, dict) else users.get(owner, owner)})
    activities = []
    test_deal_ids = {d['id'] for d in deals if d['isTest']}
    for a in raw_activities:
        owner = a.get('user_id', a.get('owner_id'))
        activities.append({'id':a['id'],'type':a.get('type'),'done':bool(a.get('done')),'isTest':a.get('deal_id') in test_deal_ids or test_label(a.get('subject')),
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
        ,'All current open deal values are zero. Show pipeline valuation as unpopulated rather than claiming the commercial pipeline is worth zero.'
        ,'Open status can coexist with Closed Won/Closed Lost stage labels; stage labels are not substitutes for actual won/lost status.'
        ,'Collection is a paginated snapshot, not an atomic database transaction; records can change during collection.'
      ]}
    out = {
      'snapshotAt':manifest['snapshotAt'],'timezone':'America/Denver',
      'coverage':{'method':'read-only connector snapshot','dealsComplete':manifest['dealsComplete'],'activitiesComplete':manifest['activitiesComplete'],
        'earliestDealCreatedDate':min(all_dates) if all_dates else None,'latestDealCreatedDate':max(all_dates) if all_dates else None,
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
    (ROOT / 'data' / 'crm.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'deals':len(deals),'activities':len(activities),'summary':out['summary'],'quality':quality},indent=2))

if __name__=='__main__': build()
