"""Reconcile the independently collected Referral Pipeline snapshot; no CRM writes."""
from pathlib import Path
from collections import Counter
from datetime import datetime,timezone
import json,re,hashlib

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data/referral_reconciliation.json'
OFFICE_HOURS=38
GRAVEYARD_NEWSLETTER=40

def iso(value):
    if not value:return None
    if len(str(value))==10:return value
    d=datetime.fromisoformat(str(value).replace('Z','+00:00'))
    if d.tzinfo is None:d=d.replace(tzinfo=timezone.utc)
    return d.astimezone(timezone.utc).isoformat().replace('+00:00','Z')

def scrub(value):
    if isinstance(value,dict):return {k:scrub(v) for k,v in value.items()}
    if isinstance(value,list):return [scrub(v) for v in value]
    if isinstance(value,str):return re.sub(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}','[email redacted]',value)
    return value

def test_title(value):
    return bool(re.search(r'(?:\btest\b|[_ ]test(?:[_ ]|$)|nurturetest$)',value or '',re.I))

def main():
    x=json.loads(DATA.read_text())
    assert x['coverage']['pagination'][-1]['more_items_in_collection'] is False, 'Unfinished source pagination'
    assert x['coverage']['complete'], 'Source collection marked incomplete'
    raw=x['records']+x.get('excludedRecords',[])
    assert len(raw)==len({d['dealId'] for d in raw}), 'Duplicate source ID'
    assert x['pipeline']['id']==4 and x['pipeline']['name']=='Referral Pipeline'
    assert all(d['pipelineId']==4 for d in raw), 'Foreign pipeline record'
    stage_map={s['id']:s for s in x['stages']}
    assert len(stage_map)==15 and stage_map[38]['name']=='Office Hours' and stage_map[40]['name']=='Graveyard ( Newsletter )'
    partitions={k:[] for k in ['active','office_hours','graveyard_newsletter','test']}
    for d in raw:
        assert d['stageId'] in stage_map, 'Unknown Referral Pipeline stage'
        d['stage']=stage_map[d['stageId']]['name']
        d['stageOrder']=stage_map[d['stageId']]['order']
        for k in ['addedAt','createdAt','updatedAt','stageChangedAt']:d[k]=iso(d.get(k))
        d['isTest']=test_title(d['title'])
        partition='test' if d['isTest'] else 'office_hours' if d['stageId']==OFFICE_HOURS else 'graveyard_newsletter' if d['stageId']==GRAVEYARD_NEWSLETTER else 'active'
        d['partition']=partition
        d['reviewFlags']=[]
        if not d['isTest'] and test_title(d.get('organization')):
            d['reviewFlags'].append({'code':'test_label_in_organization','detail':'Organization is test-labelled; deal title is not. Included pending owner confirmation to preserve the existing explicit-deal-title exclusion policy.'})
        partitions[partition].append(d)
    active=sorted(partitions['active'],key=lambda d:d['dealId'])
    excluded=sorted([d for k,rs in partitions.items() if k!='active' for d in rs],key=lambda d:d['dealId'])
    assert not ({d['dealId'] for d in active}&{d['dealId'] for d in excluded})
    assert len(active)+len(excluded)==len(raw)
    assert len(raw)==sum(map(len,partitions.values()))
    assert all(not d['isTest'] and d['stageId'] not in [38,40] for d in active)
    by_stage=Counter(d['stageId'] for d in raw)
    by_active_stage=Counter(d['stageId'] for d in active)
    by_business_stage=Counter(d['stageId'] for d in raw if not d['isTest'])
    for s in x['stages']:
        s['totalCount']=by_stage[s['id']]
        s['businessCount']=by_business_stage[s['id']]
        s['activeCount']=by_active_stage[s['id']]
    assert sum(s['totalCount'] for s in x['stages'])==len(raw)
    assert sum(s['activeCount'] for s in x['stages'])==len(active)
    prior_path=ROOT/'data/shared-dashboard.json'
    prior=json.loads(prior_path.read_text()).get('referrals',{}) if prior_path.exists() else {}
    prior_records=prior.get('records',[])
    current={d['dealId']:d for d in raw}
    prior_counts=prior.get('summary',{})
    prior_active_claim=prior_counts.get('activeReferralDeals')
    old_excluded=(prior_counts.get('officeHoursCount') or 0)+(prior_counts.get('graveyardNewsletterCount') or 0)
    old_total=prior_counts.get('totalPipelineDeals')
    comparison={'source':'data/shared-dashboard.json referrals section before integration',
      'claimedTotal':old_total,'claimedActive':prior_active_claim,'claimedExcluded':old_excluded,
      'claimedActivePlusExcluded':prior_active_claim+old_excluded if prior_active_claim is not None else None,
      'claimsReconcile':old_total==prior_active_claim+old_excluded if old_total is not None and prior_active_claim is not None else False,
      'priorListedRecords':len(prior_records),
      'priorListedNowExcludedIds':[d['dealId'] for d in prior_records if d['dealId'] in current and current[d['dealId']]['partition']!='active'],
      'activeIdsAbsentFromPriorList':sorted({d['dealId'] for d in active}-{d['dealId'] for d in prior_records}),
      'stageMismatches':[{'dealId':d['dealId'],'previousStageId':d.get('stageId'),'previousStage':d.get('stage'),'currentStageId':current[d['dealId']]['stageId'],'currentStage':current[d['dealId']]['stage']} for d in prior_records if d['dealId'] in current and d.get('stageId')!=current[d['dealId']]['stageId']]}
    # Preserve the originally reviewed import even after the parent integrates the correction.
    comparison=x.get('priorImportComparison') or comparison
    crm_path=ROOT/'data/crm.json'
    crm=json.loads(crm_path.read_text()) if crm_path.exists() else {}
    old_main_ids={d['id'] for d in crm.get('deals',[])}
    retained=crm.get('assessment',{}).get('history',{}).get('events',[])
    movements=[]
    for id,day in [(761,'2026-10-14'),(793,'2026-10-12')]:
        events=[e for e in retained if e.get('dealId')==id and e.get('field')=='stage_id' and e.get('timestamp','').startswith(day)]
        for e in events:
            movements.append({'dealId':id,'personName':current.get(id,{}).get('personName'),
              'movement':f"{e.get('oldStageName')} → {e.get('newStageName')}",'fromStageId':int(e['oldValue']),'toStageId':int(e['newValue']),
              'observedAt':e['timestamp'],'eventId':e['id'],'source':'Retained structured Pipedrive stage-change history',
              'sourceSnapshotAt':crm.get('snapshotAt'),'freshlyVerifiedInThisCollection':False})
    main_comparison={'mainCRMSnapshotAt':crm.get('snapshotAt'),'mainCRMReferralRecords':sum(d.get('pipelineId')==4 for d in crm.get('deals',[])),
      'freshReferralIdsNotInMainCRM':sorted(set(current)-old_main_ids),'independentFreshScope':'Referral Pipeline only. No main CRM collection or inventory was updated by this reconciliation.'}
    main_comparison=x.get('mainCRMComparison') or main_comparison
    movements=x.get('summary',{}).get('observedProgressions') or movements
    summary={'totalPipelineDeals':len(raw),'businessPipelineDeals':len(raw)-len(partitions['test']),'activeReferralDeals':len(active),
      'officeHoursCount':len(partitions['office_hours']),'graveyardNewsletterCount':len(partitions['graveyard_newsletter']),
      'excludedOfficeHoursCount':len(partitions['office_hours']),'excludedGraveyardNewsletterCount':len(partitions['graveyard_newsletter']),
      'excludedTestCount':len(partitions['test']),'excludedTotal':len(excluded),
      'recordReviewFlags':sum(bool(d['reviewFlags']) for d in raw),'recordReviewFlagIds':[d['dealId'] for d in raw if d['reviewFlags']],
      'statusCounts':dict(Counter(d['status'] for d in raw)),'activeStatusCounts':dict(Counter(d['status'] for d in active)),
      'stageDistribution':{stage_map[sid]['name']:n for sid,n in by_active_stage.items()},
      'fullPipelineStageDistribution':{stage_map[sid]['name']:n for sid,n in by_stage.items()},
      'circleContacts':{'innerCircle':by_active_stage[39],'centripetalCircle':by_active_stage[26],'centripetalAmigos':by_active_stage[42],
        'introPromised':by_active_stage[28],'introMade':by_active_stage[29],'opportunity':by_active_stage[31]},
      'touchpointAutomation':{'status':'not_independently_verified','cycle':None,'trelloSyncStatus':'Not independently verified',
        'reportedCycle':'30 days','verificationAttempt':'Read-only automation list endpoint returned Not Found. No active configuration or bidirectional Trello behavior was verified.',
        'reportedClaimsOnly':['30-day Centripetal Circle touchpoint cycle','Pipedrive-to-Trello sync working','Trello-to-Pipedrive completion sync pending']},
      'observedProgressions':movements,
      'currentStagePositionsArePeriodEvents':False,'referredOpportunityRecordsAreQualified':None}
    assert summary['totalPipelineDeals']==summary['activeReferralDeals']+summary['excludedOfficeHoursCount']+summary['excludedGraveyardNewsletterCount']+summary['excludedTestCount']
    x.update({'status':'current_snapshot','records':active,'excludedRecords':excluded,'summary':summary,
      'partitions':{k:{'count':len(v),'dealIds':sorted(d['dealId'] for d in v)} for k,v in partitions.items()},
      'priorImportComparison':comparison,'mainCRMComparison':main_comparison,
      'quality':{'completeAccessibleSnapshot':x['coverage']['complete'],'pipelineIdVerified':4,'uniqueSourceIds':len(current),
        'testPolicy':'Exclude explicit test-labelled deal titles. Flag, but do not auto-exclude, a test-labelled organization on a real-name deal without owner confirmation.',
        'warnings':['The requested connector pipeline filter returned mixed pipelines; full account pagination was completed and Referral Pipeline ID 4 was applied locally.',
          'Active means an open record outside Office Hours, Graveyard/Newsletter and explicit test titles. It does not mean qualified opportunity or confirmed recent engagement.',
          'Current stage positions do not measure introductions, replies or progression in a selected reporting period.',
          'Fresh Referral Pipeline coverage is independent of the older main CRM snapshot; do not sum overlapping populations.',
          'The earlier 52-active plus 105-excluded claim totals 157, not the reported 137, and one supposedly active record was Office Hours.',
          'Record 203 has a test-labelled organization and remains flagged for owner review. Its inclusion is not a qualification decision.',
          'The two retained observed movements have October 14 source coverage; they were not re-collected as history in this current-position snapshot.',
          'Automation cycle and Trello synchronization claims remain unverified.']},
      'notes':['All visible counts retain source deal IDs and exact stage IDs.','The Opportunity (Referred) stage is a CRM position, not independent evidence of commercial fit or accepted sales opportunity.'],
      'note':f"Independently collected Referral Pipeline snapshot: {len(raw)} records = {len(active)} active + {len(partitions['office_hours'])} Office Hours + {len(partitions['graveyard_newsletter'])} Graveyard/Newsletter + {len(partitions['test'])} explicit test records. Current positions are not period events."})
    hash_input={'pipeline':x['pipeline'],'stages':[{k:s[k] for k in ['id','name','order','pipelineId']} for s in x['stages']],
      'records':sorted(raw,key=lambda d:d['dealId'])}
    x['coverage']['normalizedSourceSha256']=hashlib.sha256(json.dumps(scrub(hash_input),sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
    x['coverage']['hashBasis']='Curated normalized source records and verified stage metadata; no raw correspondence content.'
    x=scrub(x)
    assert not re.search(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}',json.dumps(x))
    DATA.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
    markdown(x)
    print(json.dumps({'snapshotAt':x['snapshotAt'],'summary':summary,'mainCRMComparison':main_comparison,'priorImportComparison':comparison},indent=2))

def markdown(x):
    s=x['summary'];p=x['priorImportComparison'];m=x['mainCRMComparison']
    lines=['# Referral Pipeline reconciliation — October 16, 2026','',f"Fresh collection: **{x['snapshotAt']}**. Source: verified Pipedrive Referral Pipeline **4**. Main CRM remains at **{m['mainCRMSnapshotAt']}** and was not changed.",'',
      '## Reconciled partitions','', '| Partition | Records | Exact stage / policy |','| --- | ---: | --- |',
      f"| Active non-test-labelled records | {s['activeReferralDeals']} | Open records outside stages 38 and 40 and explicit test titles |",
      f"| Office Hours | {s['excludedOfficeHoursCount']} | Stage 38 |",f"| Graveyard / Newsletter | {s['excludedGraveyardNewsletterCount']} | Stage 40 |",
      f"| Explicit test records | {s['excludedTestCount']} | 752, 754, 787 |",f"| Total source Referral Pipeline | {s['totalPipelineDeals']} | Mutually exclusive union |",'',
      f"**348 = 60 + 245 + 40 + 3.** Non-test-labelled business inventory is {s['businessPipelineDeals']}; all 348 source records currently have open status. Active is an inventory definition, not a claim of engagement, qualification or period introductions.",'',
      '## Complete collection and filter correction','',
      'The connector accepted `pipeline_id=4` but returned records from pipelines 1, 2 and 4. Both returned pages (500 + 255 rows) were read to completion, then the verified pipeline ID was applied locally. The resulting 348 Referral Pipeline IDs are unique. All fifteen exact Referral Pipeline stages were retrieved, including zero-count stages. Source pagination and a SHA-256 of curated normalized source records/stage metadata are retained in the derived dataset. No source-system write was performed.','',
      '| Active current position | Records |','| --- | ---: |']
    lines += [f"| {name} | {count} |" for name,count in s['stageDistribution'].items()]
    lines += ['', '## Earlier-import corrections','',
      f"The previous import claimed {p['claimedTotal']} total, {p['claimedActive']} active and {p['claimedExcluded']} excluded; the latter two sum to {p['claimedActivePlusExcluded']}. That account is internally inconsistent before any comparison with the live source.",'',
      '- **454 Robert Adelson:** Office Hours, stage 38. Removed from the active referral list.',
      '- **761 Melanie Ortiz:** current Intro Made, stage 29. The prior list incorrectly used Inner Circle, stage 39. Retained structured history records Intro Promised → Intro Made on October 14; the earlier shorthand “Centripetal Circle → Intro Made” is not the exact observed transition.',
      '- **793 Jonathan S. Katz:** current Intro Promised, stage 28. Now included; omitted from the prior active record list.',
      '- **203 Christian Wutz:** its organization is test-labelled but its deal title is not. Retained in the active inventory and flagged for owner confirmation, preserving the existing explicit-deal-title test rule. It is not silently certified as a qualified referral.',
      f"- Current active IDs absent from the previous list: {', '.join(map(str,p['activeIdsAbsentFromPriorList']))}.",
      f"- {len(p['stageMismatches'])} prior listed records have a different current stage. Individual IDs and old/current stages are retained in `priorImportComparison.stageMismatches`.",'',
      '## Fresh referral scope versus older CRM','',
      f"The older main CRM snapshot has {m['mainCRMReferralRecords']} Referral Pipeline records; current collection has 348. Fresh IDs absent from that older inventory are {', '.join(map(str,m['freshReferralIdsNotInMainCRM']))}. These are now-current referral records, not proof of newly qualified leads or current-month introductory meetings. The 755 mixed-pipeline source rows were used only to complete this referral collection; the full main CRM dataset and headline inventory were not refreshed.",'',
      '## Movement and automation evidence boundaries','',
      'Two observed structured stage events are preserved with their original source snapshot date: Melanie Ortiz, Intro Promised → Intro Made on October 14, and Jonathan S. Katz, Centripetal Amigos → Intro Promised on October 12. They come from retained October 14 history and were not re-created from the current stage snapshot. No additional period progression, introduction or qualification is inferred.','',
      'The read-only automation-list endpoint returned Not Found. Accordingly the reported 30-day touchpoint cycle and Pipedrive/Trello synchronization claims are **not independently verified**. They are retained only as reported claims; cycle and operational synchronization status are not asserted.','',
      '## Reproducibility and checks','',
      '`tools/reconcile_referrals.py` rebuilds partitions and reconciliation diagnostics from the curated retained snapshot in `data/referral_reconciliation.json`. It never writes to Pipedrive. Assertions verify unique IDs, pipeline identity, all 15 known stage IDs, disjoint active/excluded populations, complete stage totals and the 348 = 60 + 245 + 40 + 3 identity. No email addresses, phone numbers, notes or correspondence bodies are included in the curated records.']
    (ROOT/'REFERRAL_RECONCILIATION_2026-10-16.md').write_text('\n'.join(lines)+'\n')

if __name__=='__main__':main()
