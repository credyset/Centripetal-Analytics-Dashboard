"""Normalize retained October 16 CRM sources into separate, coherent review outputs."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from collections import Counter
import contextlib,hashlib,importlib.util,io,json,re,subprocess,sys

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'data/private/crm_refresh_2026-10-16'
CRM=ROOT/'data/crm_refresh.json'
REFERRALS=ROOT/'data/referral_refresh.json'

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def main():
    baseline=SOURCE/'baseline/crm.json'
    assert baseline.exists(),'Preserve the old baseline before collecting source data'
    baseline_hash=hashlib.sha256(baseline.read_bytes()).hexdigest()
    original_main_hash=hashlib.sha256((ROOT/'data/crm.json').read_bytes()).hexdigest()
    manifest=json.loads((SOURCE/'pipedrive_manifest.json').read_text())
    assert manifest['dealsComplete'] and manifest['activitiesComplete']
    for key in ['deals','done','undone']:
        assert manifest['pagination'][key][-1]['more_items_in_collection'] is False
    subprocess.run([sys.executable,str(ROOT/'tools/prepare_crm.py'),'--source-dir',str(SOURCE),'--output',str(CRM)],stdout=subprocess.DEVNULL,check=True)
    crm=json.loads(CRM.read_text())
    crm['coverage']['sourceHashes']={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(SOURCE.glob('pipedrive_*.json'))}
    crm['coverage']['baselineSnapshotSha256']=baseline_hash
    crm['coverage']['normalizationOutput']='Separate refreshed dataset; prior data/crm.json preserved pending parent integration.'
    crm['quality']['organizationTestLabelReviewIds']=[d['id'] for d in crm['deals'] if not d['isTest'] and re.search(r'\btest\b',d.get('company') or '',re.I)]
    crm['quality']['organizationTestLabelPolicy']='Flag only; a test-labelled organization does not auto-exclude a real-name deal without owner confirmation.'
    CRM.write_text(json.dumps(crm,indent=2,ensure_ascii=False)+'\n')
    # Reuse the tested partitioner without changing its earlier output or review document.
    template=json.loads((ROOT/'data/referral_reconciliation.json').read_text())
    current=[d for d in crm['deals'] if d['pipelineId']==4]
    template['snapshotAt']=crm['snapshotAt']
    template['stages']=[{'id':s['id'],'name':s['name'],'order':s['order'],'pipelineId':s['pipelineId']} for s in crm['stages'] if s['pipelineId']==4]
    template['records']=[{'dealId':d['id'],'id':d['id'],'title':d['title'],'personName':d['person'],'organization':d['company'],
      'personId':d['personId'],'organizationId':d['organizationId'],'pipelineId':4,'stageId':d['stageId'],'status':d['status'],
      'owner':d['owner'],'addedAt':d['createdAt'],'createdAt':d['createdAt'],'updatedAt':d['updatedAt'],'stageChangedAt':d['stageChangedAt'],
      'nextActivityDate':d['nextActivityDate'],'lastActivityDate':d['lastActivityDate'],'value':d['value'],'currency':d['currency']} for d in current]
    template['excludedRecords']=[]
    template['coverage']={'source':'Referral Pipeline 4 derived from the same fully paginated all-pipeline CRM refresh','collectedAt':crm['snapshotAt'],
      'scope':'All accessible non-deleted records in the verified Referral Pipeline; current positions, not period events.','complete':True,
      'independentSnapshot':False,'parentCRMSnapshotAt':crm['snapshotAt'],'parentCRMSource':'data/crm_refresh.json',
      'requestedFilter':manifest['filters']['deals'],'connectorPipelineFilterHonored':None,'observedSourcePipelineIds':[1,2,4],
      'accountRowsCollected':len(crm['deals']),'pagination':manifest['pagination']['deals'],'appliedLocalFilter':'pipeline_id == 4',
      'collectionStartedAt':crm['coverage']['collectionStartedAt'],'collectionCompletedAt':crm['snapshotAt']}
    template['mainCRMComparison']={'mainCRMSnapshotAt':crm['snapshotAt'],'mainCRMSource':'data/crm_refresh.json',
      'mainCRMReferralRecords':len(current),'freshReferralIdsNotInMainCRM':[],
      'independentFreshScope':'Referrals and refreshed main CRM share the same source snapshot; overlapping populations must not be added.'}
    REFERRALS.write_text(json.dumps(template,indent=2,ensure_ascii=False)+'\n')
    reconcile=module('current_referral_reconciler',ROOT/'tools/reconcile_referrals.py')
    reconcile.DATA=REFERRALS
    reconcile.markdown=lambda data:None
    with contextlib.redirect_stdout(io.StringIO()):reconcile.main()
    refs=json.loads(REFERRALS.read_text())
    refs['quality']['warnings']=[w for w in refs['quality']['warnings'] if not w.startswith('The requested connector pipeline filter') and not w.startswith('Fresh Referral Pipeline coverage is independent')]
    refs['quality']['warnings'].insert(0,'This referral section and refreshed CRM inventory derive from the same complete all-pipeline source read. Pipeline 4 was applied locally by design.')
    REFERRALS.write_text(json.dumps(refs,indent=2,ensure_ascii=False)+'\n')
    assert {d['id'] for d in crm['deals'] if d['pipelineId']==4}=={r['dealId'] for r in refs['records']+refs['excludedRecords']}
    assert crm['snapshotAt']==refs['snapshotAt']
    assert len(crm['deals'])==len({d['id'] for d in crm['deals']})==755
    assert len(crm['activities'])==len({a['id'] for a in crm['activities']})==924
    assert sum(not d['isTest'] for d in crm['deals'])==751
    assert sum(not a['isTest'] for a in crm['activities'])==919
    assert crm['coverage']['reportingThrough']=='2026-10-15'
    assert crm['coverage']['stageHistorySnapshotAt']=='2026-10-15T03:03:19Z'
    assert not re.search(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}',json.dumps(crm)+json.dumps(refs))
    assert hashlib.sha256(baseline.read_bytes()).hexdigest()==baseline_hash
    assert hashlib.sha256((ROOT/'data/crm.json').read_bytes()).hexdigest()==original_main_hash
    report(crm,refs)
    print(json.dumps({'snapshotAt':crm['snapshotAt'],'crmRecords':len(crm['deals']),'crmActivities':len(crm['activities']),
      'businessDeals':crm['summary']['dealCount'],'businessActivities':crm['summary']['activityCount'],
      'referralPartitions':{k:v['count'] for k,v in refs['partitions'].items()},'reportingThrough':crm['coverage']['reportingThrough'],
      'mainCRMUnchanged':True,'checks':'passed'},indent=2))

def report(crm,refs):
    s=crm['summary'];a=crm['assessment'];i=a['inventory'];v=a['valuationCoverage'];c=a['snapshotChanges']
    at=datetime.fromisoformat(crm['snapshotAt'].replace('Z','+00:00')).astimezone(ZoneInfo('America/Denver')).strftime('%B %d, %Y, %I:%M %p %Z')
    active=[d for d in crm['deals'] if not d['isTest']]
    lines=['# CRM refresh — October 16, 2026','',f'Collected **{at}** ({crm["snapshotAt"]}). Read-only source collection. No Pipedrive records were changed. Refreshed data is held separately for parent integration; the earlier `data/crm.json` remains preserved.','',
      '## Complete current source scope','',
      '- 755 unique accessible non-deleted deals: pages 500 + 255.',
      '- 924 unique activities across accessible owners: 547 done and 377 undone. Both activity states were explicitly requested with user_id 0; response owner IDs were checked.',
      '- Three pipelines, 33 stages, nine activity types, five configured users and 82 deal fields read.',
      '- Four explicit test deals (178, 752, 754, 787) and five test activities excluded from business reporting. Record 203 retains its organization test-label review flag and remains included pending owner confirmation.',
      f'- Business reporting: {s["dealCount"]} deals ({s["dealStatusCounts"]["open"]} open, one won, one lost) and {s["activityCount"]} activities.',
      '- Reporting cutoff: October 15 complete Mountain day; October 16 is current-day partial.',
      '- The old normalized CRM and old source/history manifest were backed up under `data/private/crm_refresh_2026-10-16/baseline/`. Fresh source files have independent manifests and hashes.','',
      '## Changes since October 14 source snapshot','',
      f'- {len(c["newDealIds"])} newly observed deal IDs, one no-longer-observed ID (756, previously Predictable Labs). This is not proof of deletion; visibility or record consolidation requires separate confirmation.',
      f'- {len(c["changedDeals"])} retained deal IDs have changed compared fields; {sum("stageId" in d["changes"] for d in c["changedDeals"])} have different current stage positions. No compared deal status changed.',
      '- One newly observed activity, 1091: Charles’s monthly Centripetal Circle touchpoint for Dana Billsky Asher, created and due October 16, with an explicit automation reference. No previously compared activity completion, type, due date, owner or deal link changed.',
      '- New stage 43 is Video DM Outreach in Leads Pipeline; stage 44 is New Lead in Sales Pipeline. Current business inventory has 44 records in Video DM Outreach. Stage membership does not establish an actual Video DM send.',
      '- Normalized-title review groups include Venus AI (791, 805), Menos AI (795, 799, 818), Talvy (806, 831), and furl (808, 830). Organization IDs are retained. These are review flags, not automatic entity merges; record creations are not necessarily net-new companies.','',
      '## Activity and dated-window assessment','',
      f'- Business activity inventory: {i["done"]} marked done; {i["undone"]} undone, comprising {i["overdue"]} overdue, {i["dueToday"]} due today, and {i["future"]} future activity. No undone activity lacks a due date.',
      f'- {i["automationReferencedActivities"]} business activities carry an explicit automation reference. A missing reference does not prove manual creation.',
      '- Latest legitimate recorded completion remains August 19. That is a CRM recording gap, not proof of no later meetings or outreach.',
      '- Last 30 complete days, September 16–October 15: 44 new deal records, 111 records whose latest update falls in the window, 24 created activities and zero legitimate recorded completions. Latest-update metrics do not reconstruct every earlier edit.',
      '- October 16 activity 1091 belongs only to current-day partial reporting, not the complete-day metrics. NuVee’s existing activity 1090 remains due November 17.','',
      '## Valuation correction','',
      '**The earlier “all open values are unpopulated” statement is no longer current.** Three open Sales/Intro Meeting records now carry nonzero source-entered values:', '',
      '| Deal ID | Source title | USD value |','| --- | --- | ---: |']
    for r in v['records']:lines.append(f'| {r["dealId"]} | {r["title"]} | {r["value"]:,.0f} |')
    lines += ['',f'The known portion totals **$20,000 across three of {v["businessOpenRecords"]} business open records**. The other {v["zeroOrUnsetRecords"]} have zero or unset values. Valuation basis is unverified; this is not a complete qualified pipeline valuation, contracted value or recognized revenue. Nineteen open-status records still occupy Closed Won/Lost-labelled stages.','',
      '## Retained history versus current records','',
      'Current deals and activities were freshly collected October 16. The 33 retained structured stage events across a 44-deal subset were collected October 14 and are explicitly labelled with their original source timestamp. No new history was invented from the 20 current-position differences. Scope remains partial, and numeric stage order is not interpreted as forward commercial progress.',
      '', '## Referral coherence','',
      'The refreshed Referral Pipeline is derived from this exact full-CRM source snapshot. It reconciles **348 = 60 active + 245 Office Hours + 40 Graveyard/Newsletter + three explicit tests**. The same 348 IDs occur in refreshed CRM and refreshed referrals. The two outputs share their snapshot timestamp and should be integrated together. Current positions remain inventory; Opportunity (Referred) is not independent qualification.','',
      '## Owner confirmations and evidence layers','',
      'This collector does not infer qualification or attendance from a stage, a scheduled activity, or a completion flag. The parent workflow has separate current owner confirmation that NuVee’s October 6 call and Venus’s October 15 call were held; those confirmations must be retained with their own provenance in the meeting/outcome layer. Owner confirmation can establish held status even when no matching CRM activity was completed. It does not automatically change qualification or create opportunity/revenue evidence.',
      '', '## Prepared outputs and checks','',
      '- `data/crm_refresh.json`: fresh normalized CRM, current activity/valuation diagnostics, comparison to preserved baseline, and explicitly dated retained history.',
      '- `data/referral_refresh.json`: same-snapshot referral partitions and curated records.',
      '- `tools/refresh_crm_snapshot.py`: repeatable normalization and reconciliation from retained fresh private snapshots.',
      '- Assertions cover unique IDs, completed pagination, test exclusions, source-date boundaries, same-snapshot referral ID equality, no embedded email addresses, and preservation of the original main CRM/baseline files. No notes, correspondence bodies, phone fields or contact emails are published in these curated outputs.']
    (ROOT/'CRM_REFRESH_2026-10-16.md').write_text('\n'.join(lines)+'\n')

if __name__=='__main__':main()
