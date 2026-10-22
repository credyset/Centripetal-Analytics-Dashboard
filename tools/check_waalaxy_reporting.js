/* Invitation source-date totals stay separate from fixed Home and message data. */
'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const app=fs.readFileSync(path.join(__dirname,'../app.js'),'utf8').replace(/\ninit\(\);\s*$/,'');
const ctx=vm.createContext({Intl,Date,URL,setTimeout:()=>{},document:{querySelector:()=>null}});
vm.runInContext(app,ctx);const run=s=>vm.runInContext(s,ctx);
ctx.fixture={meta:{},waalaxy:{snapshotAt:'2026-10-21T12:00:00Z',invitationCollectedAt:'2026-10-22T14:00:00Z',
  invitationCoverage:{start:'2026-10-01',end:'2026-10-22',currentDayPartial:true},
  daily:Array.from({length:22},(_,n)=>({date:`2026-10-${String(n+1).padStart(2,'0')}`,invitationsSent:0,invitationsAccepted:0})),
  accountAnalytics:{collectedOn:'2026-10-22',sourceWindow:{displayedStartDate:'2026-10-01',displayedEndDate:'2026-10-22',finalDayPartial:true},metrics:{invitationActionsSent:430,invitationAcceptancesReported:132,messageActionsSent:0,answeredMessagesReported:2}}}};
ctx.fixture.waalaxy.daily[4].invitationsSent=371;ctx.fixture.waalaxy.daily[4].invitationsAccepted=110;
ctx.fixture.waalaxy.daily[18].invitationsSent=59;ctx.fixture.waalaxy.daily[18].invitationsAccepted=22;
run("S.data=fixture;S.start='2026-10-19';S.end='2026-10-22';");
const vector=()=>JSON.parse(run("JSON.stringify(vectorData().find(r=>r.id==='waalaxy'))"));
assert.equal(vector().cardActivity.value,'59');assert.equal(vector().cardOutcome.value,'22');
assert.equal(vector().cardOutcome.label,'Accepted · export date buckets');
assert.equal(vector().cardOutcome.basis,'partial');
assert.match(vector().cardOutcome.note,/accepted-event dates.*not established/);
assert.equal(vector().responses.find(r=>r.label==='Answered messages reported').value,'2');
assert.equal(vector().responses.find(r=>r.label==='Answered messages reported').basis,'snapshot');
assert.equal(vector().activity.find(r=>r.label==='Platform message actions').value,'0');
assert.equal(run('selectedInvitations().ratio'),null);
run("S.start='2026-10-01';");
assert.equal(vector().cardActivity.value,'430');assert.equal(vector().cardOutcome.value,'132');
// The matching Home totals are neither added nor substituted for the selection.
run("S.start='2026-10-20';S.end='2026-10-21';");
assert.equal(vector().cardActivity.value,'0');assert.equal(vector().cardOutcome.value,'0');
assert.equal(vector().cardActivity.basis,'period');
run("S.start='2026-10-23';S.end='2026-10-23';");
assert.equal(vector().cardActivity.value,null);assert.equal(vector().cardOutcome.value,null);
// An unavailable value must not be silently coerced into a source zero.
run("S.start='2026-10-19';S.end='2026-10-22';fixture.waalaxy.daily[20].invitationsAccepted=null;");
assert.equal(vector().cardOutcome.value,null);
// Missing source dates are partial coverage, even inside declared boundaries.
run("fixture.waalaxy.daily=fixture.waalaxy.daily.filter(r=>r.date!=='2026-10-20');S.end='2026-10-21';");
assert.equal(vector().cardActivity.basis,'partial');
console.log('Waalaxy display: selected date buckets, explicit zero/missing values, no cohort rate, and separate fixed Home messages/replies passed.');
