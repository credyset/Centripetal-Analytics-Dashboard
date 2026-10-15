"""Inventory October deliverable evidence without treating agent work as human hours."""
from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import json
import subprocess

ROOT=Path(__file__).resolve().parents[1]
CENTRI=ROOT.parent
TZ=ZoneInfo('America/Denver')

def artifact(path,kind,evidence_date,date_basis,establishes,limitation='Does not measure Christian\'s human time.'):
    p=CENTRI/path
    if not p.is_file(): raise FileNotFoundError(p)
    return {'path':str(p),'relativePath':str(p.relative_to(CENTRI)), 'evidenceType':kind,'evidenceDate':evidence_date,
      'dateBasis':date_basis,'exists':True,'modifiedAt':datetime.fromtimestamp(p.stat().st_mtime,TZ).isoformat(),
      'establishes':establishes,'timeLimitation':limitation}

def commits(path):
    result=subprocess.run(['git','log','--since=2026-10-01','--until=2026-10-16','--date=iso-strict',
      '--format=%H%x09%aI%x09%an%x09%s'],cwd=CENTRI/path,text=True,capture_output=True,check=True)
    rows=[]
    for line in result.stdout.splitlines():
        sha,at,author,subject=line.split('\t',3)
        rows.append({'sha':sha,'timestamp':at,'authorMetadata':author,'subject':subject})
    return {'repository':str(CENTRI/path),'relativePath':path,'commits':rows,'count':len(rows),
      'interpretation':'Commit author and timestamps are implementation provenance, not proof of human execution or hours. Mirrored publication commits are not extra tasks.'}

def build():
    now=datetime.now(timezone.utc)
    streams=[]
    def add(id,title,dates,artifacts,rounds,human_basis,scope,exclusions,confidence='medium'):
        streams.append({'id':id,'title':title,'evidenceDates':dates,'artifacts':artifacts,
          'deliveryExecution':'Agent-assisted research, implementation, validation or packaging. No direct human execution timer was supplied.',
          'humanRole':'Christian: direction, business decisions, review, clarification and coordination where supported; Charles\'s prospecting/call activity is excluded.',
          'humanInvolvementBasis':human_basis,'humanInvolvementConfidence':confidence,'trackedHumanMinutes':None,
          'planningAllowance':{'enabled':False,'ownerConfirmed':False,'kind':'Unconfirmed review and coordination assumption',
            'assumedReviewRounds':rounds,'minutesPerRoundLow':15,'minutesPerRoundHigh':45,
            'minutesLow':rounds*15,'minutesHigh':rounds*45,'hoursLow':rounds/4,'hoursHigh':rounds*3/4,
            'scope':scope,'excludes':exclusions,'confidence':'low','actualTimeCanBeOutsideRange':True,
            'notAStatisticalConfidenceInterval':True}})
    add('pulley','Pulley account research and contact prioritization',['2026-10-02','2026-10-06','2026-10-14'],[
      artifact('pulley_universe_and_icp_segmentation_2026-10-02.md','dated research deliverable','2026-10-02','Document date and dated filename','Evidence-backed company universe, ICP segmentation and documented research boundaries.'),
      artifact('pulley_contact_assembly_summary_2026-10-06.json','generated artifact manifest','2026-10-06','generated_at timestamp','102 companies, 204 contact rows and 30 priority contacts; these are agent-produced outputs, not 204 human research tasks.'),
      artifact('Centripetal_Pulley_Contact_Research_2026-10-14_connected.xlsx','dated reconciliation workbook','2026-10-14','Dated filename and corroborating dashboard source review','Connection/relationship reconciliation added to retained contact research.'),
      artifact('analytics_dashboard/SOURCE_REVIEW.md','dated cross-project source review','2026-10-14','Document heading/date','Pulley priority tab is a subset and relationship classifications do not establish new period activity.')],3,
      'Deliverables reflect staged scope and relationship-priority choices. Christian\'s exact review sessions/durations require his confirmation; source existence alone does not establish them.',
      'Three assumed combined review rounds: company/ICP scope, contact/priority deliverable, connection reconciliation.',
      ['Automated company/contact searches and enrichment','Charles\'s Video DM recording or sending','Dashboard integration counted under dashboard'])
    add('website','Website concept and resource refinements',['2026-10-08','2026-10-09','2026-10-10'],[
      artifact('site-concept-research/site-v1/SITE_ARCHITECTURE.md','dated architecture and decision record','2026-10-10','October checkpoints plus repository history','Records user-directed resource hierarchy, LinkedIn/Media treatment, guide/tool reference choices and concept boundaries.'),
      artifact('site-concept-research/site-v1/INDEPENDENT_REFINEMENTS_REVIEW.md','dated QA closeout','2026-10-10','Explicit October 10 heading','Resource provenance, score-band correction, responsive/interaction QC and remaining human editorial decisions.'),
      artifact('site-concept-research/site-v1/tools/deeper-qc-20261010.json','generated QA evidence','2026-10-10','Dated filename and linked review','Automated/browser implementation checks, not Christian time records.')],6,
      'Architecture record explicitly attributes priorities and refinements to the user; 29 October 8–10 commits corroborate implementation chronology. Commit author metadata does not prove Christian typed the changes.',
      'Six assumed review clusters: scope/services, resource architecture, guides, tools/diagnostic, LinkedIn/Media, final quality review.',
      ['Agent coding and browser checks','Copied baseline and old August work','October 14 inbound analytics handoff counted under dashboard','Production/client delivery by Charles'])
    add('paid-audit','LinkedIn/GA4 audit and branded reference report',['2026-10-13'],[
      artifact('LinkedIn Ads/LinkedIn_GA4_Deep_Dive_2026-10-12/Analysis/Centripetal_LinkedIn_GA4_Audit_2026-10-12.md','reconciled analytical deliverable','2026-10-13','Collection date in package; filename October 12 is the performance cutoff','Campaign/GA4 reconciliation and findings. Performance-date span is not labor duration.'),
      artifact('LinkedIn Ads/LinkedIn_GA4_Deep_Dive_2026-10-12/Analysis/lead_disposition_owner_notes.md','dated direct-owner decision record','2026-10-13','Document heading and retained user statements','Christian supplied/clarified lead dispositions, including NuVee qualified and warm.'),
      artifact('LinkedIn Ads/LinkedIn_GA4_Deep_Dive_2026-10-12/Analysis/font_revision_validation.json','formatting revision validation','2026-10-13','Companion report date and revision manifest','Text preserved and font cap applied after user formatting feedback.'),
      artifact('LinkedIn Ads/LinkedIn_GA4_Deep_Dive_2026-10-12/Analysis/pagination_revision_validation.json','native-viewer revision validation','2026-10-13','Companion report date; native Pages verification manifest','Fourteen-page native Pages verification after owner reported pagination defects. Rendering elapsed time is excluded.')],4,
      'Direct conversation requests establish lead feedback, targeting/report scope and two formatting review rounds; timestamps of active human review are not supplied.',
      'Four assumed combined rounds: data/lead scope, targeting/report decisions, typography feedback, native pagination review.',
      ['Agent exports/calculations/report generation/rendering','Campaign period elapsed days','October 14 dashboard refresh counted under dashboard'])
    add('video-dm','Video DM workflow review and source repairs',['2026-10-14'],[
      artifact('analytics_dashboard/MEETING_SOURCE_REVIEW.md','dated authorized source-change review','2026-10-14','October 14 addendum','Documents a separate owner-authorized repair of two Video DM profile URLs; inventory/status changes are not sends.'),
      artifact('data/video_dm_next40_final_v5.csv','candidate research artifact with weak work-date evidence',None,'Modification metadata October 6 only; embedded enrichment findings are September 29','Retains outreach preparation. Its mtime is not sufficient to assign the underlying work to October or to Christian.')],1,
      'October 14 review explicitly records separately owner-authorized profile repairs. Earlier October-modified batches need chat corroboration before adding review allowances.',
      'One assumed round for Christian\'s October 14 source repair/coordination; additional batch work remains unconfirmed.',
      ['Charles\'s recording, outreach and calls','Automated enrichment and sheet reads','Pulley contact prioritization','Dashboard metric/source design'])
    add('dashboard','Analytics scope, source reconciliation and publication review',['2026-10-14'],[
      artifact('analytics_dashboard/PLAN.md','dated owner requirements and decision record','2026-10-14','Explicit plan date and owner-confirmed decisions','Browser team dashboard; equal activity/outcome weight; social-account scope; daily/manual freshness; Mountain Monday–Sunday weeks.'),
      artifact('analytics_dashboard/DEPLOYMENT.md','dated publication record','2026-10-14','Explicit publication date and retained version identifiers','Private repository plus owner-approved public Sites deployment and approved prepared-data scope.'),
      artifact('analytics_dashboard/REFRESH_REVIEW_2026-10-14.md','dated cross-source refresh closeout','2026-10-14','Explicit heading/date and collection timestamps','Fresh paid/CRM/workbook/Calendly evidence reconciled. Source collection duration is not Christian time.'),
      artifact('site-concept-research/analytics-handoff-20261014/WEBSITE_INBOUND_HANDOFF.md','dated website analytics handoff','2026-10-14','Prepared October 14 heading','Reused website/GA4 evidence, source limits and attribution decisions; counted once within dashboard.')],5,
      'The current conversation directly records Christian\'s requirements, account/calendar answers, hosting/repository choice, approval to proceed, and iterative review directions. Implementation and connector collection were agent-assisted.',
      'Five assumed combined rounds: requirements/calendar, metric/source definitions, hosting/repository, publication/data scope, refreshed-source operating review.',
      ['Agent implementation/runtime/tool waiting','Read-only CRM and calendar collection','Mirrored Sites commits as separate work','Earlier Ads audit and website implementation','This retrospective time-estimate exercise'])
    excluded=[
      {'id':'newsletter-prior-verification','title':'Newsletter contact verification baseline','reason':'Local plans and checkpoints explicitly date September 10–11, 2026. No October duration or October human-work log was found. October signup/verification work requires separate chat or delivery evidence.',
       'evidence':[artifact('plan_deliverables/newsletter_email_only_scope_and_plan_v1.md','historical scoped plan','2026-09-10','Explicit document date','September 2,088-row contact-verification scope; excluded from October hour model.'),artifact('plan_deliverables/newsletter_email_verification_v1/newsletter_email_verification_checkpoint_v12.md','historical verification checkpoint','2026-09-11','Explicit document date','September infrastructure audit; not October human time.')], 'minutesLow':0,'minutesHigh':0,'includedInAssumedRange':False},
      {'id':'old-video-findings','title':'September Video DM enrichment findings','reason':'The enrichment findings explicitly say September 29 despite an October 1 modification timestamp. File-copy/save timestamps cannot re-date all underlying work.',
       'evidence':[artifact('data/video_dm_next40_enrichment_findings_v1.md','historical research note','2026-09-29','Document heading','September enrichment results; October mtime does not establish October human work.')],'includedInAssumedRange':False},
      {'id':'charles-activity','title':'Charles\'s prospect meetings, video delivery and outreach','reason':'These are Centripetal business-development outputs performed by Charles, not Christian\'s labor. Count only Christian\'s separately verified participation, not the company\'s whole activity inventory.','includedInAssumedRange':False},
      {'id':'agent-runtime','title':'Agent execution, file timestamp spans and commit intervals','reason':'No agent elapsed time, unattended wait, rendering duration, source export date range, or commit-to-commit interval is converted into Christian human hours.','includedInAssumedRange':False}
    ]
    histories=[commits(s) for s in ['site-concept-research/site-v1','sites/centripetal-advisors-concept','analytics_dashboard','analytics_dashboard/public_site']]
    low=sum(s['planningAllowance']['minutesLow'] for s in streams);high=sum(s['planningAllowance']['minutesHigh'] for s in streams)
    out={'schemaVersion':1,'preparedAt':now.isoformat(),'timezone':'America/Denver',
      'period':{'start':'2026-10-01','through':'2026-10-15','asOf':now.astimezone(TZ).isoformat(),'currentDayPartial':True},
      'person':'Christian Wutz','purpose':'Evidence-backed workstream inventory plus explicitly unconfirmed coordination allowances, separate from meeting time.',
      'trackedNonMeetingMinutes':None,'verifiedMeetingMinutes':None,
      'meetingTimeHandling':'Parent workflow reconciles Christian participation and actual meeting durations separately. This file includes no meeting hours.',
      'summary':{'confirmedHumanTimeLogFound':False,'actualHumanHours':'Unknown; not zero.',
        'illustrativeAssumedRange':{'enabled':False,'ownerConfirmed':False,'minutesLow':low,'minutesHigh':high,'hoursLow':low/60,'hoursHigh':high/60,
          'label':'Unconfirmed review/coordination allowance only','confidence':'low','notTrackedTime':True,'notAnUpperBoundOnActualWork':True},
        'evidenceConfidence':'High for dated October deliverable existence; mixed for human involvement; low for unconfirmed duration assumptions.'},
      'workstreams':streams,'excludedOrPending':excluded,'repositoryEvidence':histories,
      'rules':['No total combines meetings and assumptions until overlaps are reconciled.','Do not add task/deliverable counts to meeting hours.','Parallel agents and repeated file versions do not create extra Christian hours.',
        'If work occurred during an included meeting, remove that time from the nonmeeting allowance.','No estimate is billing-ready without Christian\'s review/adjustment.',
        'Review-round counts are adjustable analyst assumptions, not observed session counts.','Absence of a local timesheet does not prove no work or no time tracking elsewhere.'],
      'auditScope':{'read':'Centripetal-only local artifacts, project-scoped Git logs and this task\'s direct user conversation; no unrelated project logs or private correspondence.',
        'notRead':'EasyOps/Logic logs; mail/chat message bodies; private device activity or browsing histories.'}}
    (ROOT/'data/time_work_evidence.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
    lines=['# Christian — October 2026 nonmeeting work evidence','',
      'Coverage: October 1–15, 2026, America/Denver. October 15 is partial. This is a local Centripetal artifact audit, not a timesheet.','',
      '**No direct Christian human-hours log was found in the reviewed sources. Actual nonmeeting time is unknown, not zero.** Dated deliverables support the existence and scope of work; agent execution, file modification spans and commit intervals do not establish Christian\'s active time. Meeting time is reconciled separately by the parent workflow.','',
      '## October workstreams and direct evidence','',
      '| Workstream | October evidence | Illustrative coordination allowance |','| --- | --- | --- |']
    for s in streams:lines.append(f"| {s['title']} | {', '.join(s['evidenceDates'])} | {s['planningAllowance']['hoursLow']:g}–{s['planningAllowance']['hoursHigh']:g} hours, unconfirmed |")
    lines+=['',f'If all five optional assumptions are enabled, the illustrative sum is **{low/60:g}–{high/60:g} hours**, based on 19 assumed review rounds at 15–45 minutes each. The defaults are disabled and owner-unconfirmed. This is an adjustable planning allowance, not recorded time, not a statistical interval, not a ceiling on real work, and not an invoiceable claim.','']
    for s in streams:
        lines += ['## '+s['title'],'',s['humanInvolvementBasis'],'', '**Allowance scope:** '+s['planningAllowance']['scope'],'', '**Exclude:** '+'; '.join(s['planningAllowance']['excludes'])+'.','']
        for e in s['artifacts']:lines.append(f"- `{e['relativePath']}` — {e['evidenceType']}; date basis: {e['dateBasis']}. {e['establishes']}")
        lines.append('')
    lines += ['## Exclusions and unresolved October scope','']
    for e in excluded:lines += ['- **'+e['title']+':** '+e['reason']]
    lines += ['', '## Repository evidence and overlap control','']
    for h in histories:lines.append(f"- `{h['relativePath']}`: {h['count']} October commits. Author metadata is provenance only; it does not establish human typing time. Publication mirrors belong to their original workstream.")
    lines += ['', 'The website October 8–10 commits and review record support concept development, not live production migration or measured SEO outcomes. The October 14 analytics source handoff belongs to dashboard coordination, not an extra website allowance. Paid-source refresh work belongs to dashboard integration after the original paid-audit/report work. Pulley priority preparation is separate from Video DM sheet repair; Charles\'s own video production and outreach are excluded.','',
      '## Before using an estimated total','',
      '1. Reconcile actual Christian meeting participation and measured duration separately.','2. Ask Christian to confirm or change review-round counts and minutes per round; add October newsletter/Video DM work only when the relevant thread or artifact establishes it.','3. Remove any coordination already included in meeting time or another workstream.','4. Preserve a clear “estimated and unconfirmed” label until the owner approves the retrospective estimate.','',
      'The inventory is reproducible with `tools/prepare_time_work.py`; structured evidence and all assumptions are retained in `data/time_work_evidence.json`. No unrelated project logs, private correspondence, device-activity records or browser history were read.']
    (ROOT/'TIME_WORK_REVIEW.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'workstreams':len(streams),'rangeHours':[low/60,high/60],'rangeEnabled':False,'trackedMinutes':None,'repos':[(h['relativePath'],h['count']) for h in histories]},indent=2))

if __name__=='__main__':build()
