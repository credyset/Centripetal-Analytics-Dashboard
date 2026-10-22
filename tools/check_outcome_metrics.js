/* Business rules, date boundaries and incomplete-coverage behavior for the
 * Charles-only outcome strip. Run with node tools/check_outcome_metrics.js. */
'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const app=fs.readFileSync(require('node:path').join(__dirname,'../app.js'),'utf8').replace(/\ninit\(\);\s*$/,'');
const ctx=vm.createContext({Intl,Date,URL,setTimeout:()=>{},document:{querySelector:()=>null}});
vm.runInContext(app,ctx);
const run=s=>vm.runInContext(s,ctx);
const evaluate=(outcomes,start='2026-10-19',end='2026-10-21')=>{
  ctx.input=outcomes;ctx.startDate=start;ctx.endDate=end;
  run('S.data={outcomes:input,meta:{}};S.start=startDate;S.end=endDate;');
  return JSON.parse(run('JSON.stringify((()=>{const m=selectedOutcomeMetrics();return {calls:m.calls.length,companies:m.companies.length,qualified:m.qualified.length,unknown:m.qualificationUnknown.length,accepted:m.accepted.length,wins:m.wins.length,labels:[outcomeCount(m.calls.length,m.callsComplete),outcomeCount(m.qualified.length,m.qualificationComplete),outcomeCount(m.accepted.length,m.acceptedComplete),outcomeCount(m.wins.length,m.winsComplete)]}})())'));
};
const call=(id,company,date,extra={})=>({conversationId:id,companyKey:company,company,heldAt:date,charlesParticipated:true,prospectMeeting:true,heldConfirmed:true,qualification:'qualified',qualificationConfirmedOn:'2026-10-21',...extra});
const empty={scope:'charles_only',heldCalls:[],opportunityAcceptances:[],clientWins:[],coverage:{}};
assert.deepEqual(evaluate(empty).labels,['Pending','Pending','Pending','Pending']);

// One real meeting may appear in three systems. Repeat meetings count once per
// session, while the qualified-company count deduplicates the company.
let ledger={...empty,heldCalls:[call('a','alpha','2026-10-19'),call('a','alpha','2026-10-19'),call('b','alpha','2026-10-20'),call('c','beta','2026-10-20',{qualification:'unqualified'}),call('scheduled','gamma','2026-10-20',{heldConfirmed:false}),call('other-owner','delta','2026-10-20',{charlesParticipated:false}),call('internal','epsilon','2026-10-20',{prospectMeeting:false}),call('boundary','zeta','2026-10-19T05:00:00Z')]};
assert.deepEqual(evaluate(ledger),{calls:3,companies:2,qualified:1,unknown:0,accepted:0,wins:0,labels:['≥3','≥1','Pending','Pending']});

// Qualification is the latest explicit company disposition, but the company
// must have a held call in the chosen period to enter the qualified cohort.
ledger={...empty,heldCalls:[call('old-alpha','alpha','2026-10-06',{qualificationConfirmedOn:'2026-10-16'}),call('new-alpha','alpha','2026-10-20',{qualification:'unqualified'}),call('old-beta','beta','2026-10-06')]};
assert.equal(evaluate(ledger).qualified,0);
ledger={...empty,heldCalls:[call('conflict-a','alpha','2026-10-19'),call('conflict-b','alpha','2026-10-20',{qualification:'unqualified'})]};
assert.equal(evaluate(ledger).unknown,1);

// A repeat acceptance is not a new opportunity. Explicit acceptance and a
// next step are mandatory; automatic CRM creation never supplies either.
ledger={...empty,opportunityAcceptances:[{opportunityId:'old',acceptedAt:'2026-10-06',charlesAccepted:true,nextStep:'Proposal review'},{opportunityId:'old',acceptedAt:'2026-10-20',charlesAccepted:true,nextStep:'Follow-up'},{opportunityId:'new',acceptedAt:'2026-10-20',charlesAccepted:true,nextStep:'Discovery with finance lead'},{opportunityId:'no-step',acceptedAt:'2026-10-20',charlesAccepted:true},{opportunityId:'unaccepted',acceptedAt:'2026-10-20',nextStep:'Automated task'}],clientWins:[{companyKey:'first',wonAt:'2026-10-20',charlesCommercialOwner:true,firstTimeClient:true,winConfirmed:true},{companyKey:'first',wonAt:'2026-10-21',charlesCommercialOwner:true,firstTimeClient:true,winConfirmed:true},{companyKey:'existing',wonAt:'2026-10-20',charlesCommercialOwner:true,firstTimeClient:false,winConfirmed:true},{companyKey:'label-only',wonAt:'2026-10-20',charlesCommercialOwner:true,firstTimeClient:true}]};
assert.equal(evaluate(ledger).accepted,1);assert.equal(evaluate(ledger).wins,1);

// An email reschedule can invalidate the assumed day without invalidating the
// owner's attendance confirmation. Count once only inside the entire date range.
ledger={...empty,heldCalls:[call('rescheduled','venus',null,{heldDateRange:{start:'2026-10-15',end:'2026-10-16'},qualification:'unqualified'})]};
assert.equal(evaluate(ledger,'2026-10-01','2026-10-21').calls,1);
assert.equal(evaluate(ledger,'2026-10-15','2026-10-15').calls,0);
assert.equal(evaluate(ledger,'2026-10-16','2026-10-16').calls,0);
const reconciledRange={...ledger,coverage:{heldCalls:{status:'complete',start:'2026-10-01',end:'2026-10-21'},qualification:{status:'complete',start:'2026-10-01',end:'2026-10-21'}}};
assert.deepEqual(evaluate(reconciledRange,'2026-10-15','2026-10-15').labels.slice(0,2),['Pending','Pending']);
assert.deepEqual(evaluate(reconciledRange,'2026-10-12','2026-10-18').labels.slice(0,2),['1','0']);
// First documentation is not automatically original commercial acceptance.
ledger={...empty,opportunityAcceptances:[{opportunityId:'existing',acceptedAt:'2026-10-05',charlesAccepted:true,nextStep:'Contract review',originalAcceptanceDateVerified:false}]};
assert.equal(evaluate(ledger,'2026-10-01','2026-10-21').accepted,0);

// Zero is allowed only after the owner reconciles the entire selected window.
const coverage=Object.fromEntries(['heldCalls','qualification','opportunityAcceptances','clientWins'].map(k=>[k,{status:'complete',start:'2026-10-01',end:'2026-10-21'}]));
assert.deepEqual(evaluate({...empty,coverage}).labels,['0','0','0','0']);
assert.deepEqual(evaluate({...empty,coverage},'2026-09-30','2026-10-21').labels,['Pending','Pending','Pending','Pending']);
assert.equal(evaluate({...ledger,scope:'all_team'}).calls,0);
assert.equal(run("weekStart('2026-10-21')"),'2026-10-19');
// A newly prepared dashboard must not turn old CRM data into a zero for this
// week, or extrapolate a weekly zero beyond the last complete retained day.
run("S.data={meta:{generatedAt:'2026-10-22T01:00:00Z'},crm:{snapshotAt:'2026-10-17T00:52:01Z',coverage:{earliestDealCreatedDate:'2024-09-11',reportingThrough:'2026-10-15'},deals:[]}};S.start='2026-10-19';S.end='2026-10-21';");
assert.equal(run('crmDateAvailable(normalizeCRM())'),false);
assert.equal(run("weekly([],'createdAt').length"),0);
run("S.start='2026-10-01';");
assert.equal(run('crmDateAvailable(normalizeCRM())'),false);
assert.equal(run("weekly([],'createdAt').at(-1).date"),'2026-10-12');
run("S.end='2026-10-15';");
assert.equal(run('crmDateAvailable(normalizeCRM())'),true);
run("S.end='2026-10-21';S.data.crm.coverage.observedThrough='2026-10-21';S.data.crm.coverage.reportingThrough='2026-10-20';");
assert.equal(run('crmDateAvailable(normalizeCRM())'),true);
assert.equal(run('crmCoverageNote(normalizeCRM()).includes("current day is partial")'),true);
ctx.profile={creatorAnalytics:{snapshotAt:'2026-10-22T01:00:00Z',coverage:{start:'2026-07-25',end:'2026-10-22',sourcePreset:'90 days',finalDayPartial:true},summary:{impressions:100,socialEngagements:10},comparison:{percentChange:258,periodLabel:'prior 90 days'},topPosts:[]}};
assert.equal(run('creatorContentEvidence(profile).includes("Impressions vs prior 90 days")'),true);
assert.equal(run('creatorContentEvidence(profile).includes("7-day source window")'),false);
ctx.calendar={snapshotAt:'2026-10-15T02:58:42Z',coverage:{complete:true,start:'2026-07-16',end:'2026-11-13'}};
run("S.start='2026-10-19';S.end='2026-10-21';");
assert.equal(run('calendarCreationAvailable(calendar)'),false);
run("S.start='2026-10-01';S.end='2026-10-13';");
assert.equal(run('calendarCreationAvailable(calendar)'),true);
run("S.end='2026-10-14';");
assert.equal(run('calendarCreationAvailable(calendar)'),false);
// A flow export contains value edits alongside stage changes. Value edits
// must not render as extra stage transitions with blank from/to stages.
run(`S.start='2026-10-19';S.end='2026-10-21';
  var capturedHistoryTables={};
  table=(id,title,rows)=>{capturedHistoryTables[id]=rows;return '';};
  var mixedHistory={deals:[{id:1,title:'Prospect'}],assessment:{history:{events:[],dealIdsReviewed:[1]},freshSelectedDealHistory:{dealIdsReviewed:[1],events:[
    {id:'stage',dealId:1,field:'stage_id',timestamp:'2026-10-20T16:00:00Z',oldStageName:'Intro Meeting',newStageName:'Follow-up'},
    {id:'value',dealId:1,field:'value',timestamp:'2026-10-20T16:01:00Z',oldValue:'0',newValue:'2000'}]}}};
  crmHistoryReview(mixedHistory,mixedHistory);`);
assert.equal(run('capturedHistoryTables["crm-fresh-stage-events"].length'),1);
assert.equal(run('capturedHistoryTables["crm-fresh-stage-events"][0].id'),'stage');
console.log('Charles outcome metrics: cohort, deduplication, scope, Mountain dates, and unknown/zero rules passed.');
