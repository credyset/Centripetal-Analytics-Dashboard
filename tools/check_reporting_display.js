/* Selected-period display and heterogeneous source-coverage regression checks. */
'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const app=fs.readFileSync(path.join(__dirname,'../app.js'),'utf8').replace(/\ninit\(\);\s*$/,'');
const ctx=vm.createContext({Intl,Date,URL,setTimeout:()=>{},document:{querySelector:()=>null}});
vm.runInContext(app,ctx);
const run=s=>vm.runInContext(s,ctx);
ctx.input={meta:{},content:{creatorAnalytics:{coverage:{start:'2026-07-25',end:'2026-10-22',finalDayPartial:true},summary:{impressions:9999,membersReached:777,socialEngagements:50},exportAnalytics:{coverage:{start:'2026-10-18',end:'2026-10-22',finalDayPartial:true},daily:[{date:'2026-10-18',impressions:800},{date:'2026-10-19',impressions:0},{date:'2026-10-20',impressions:27},{date:'2026-10-21',impressions:5},{date:'2026-10-22',impressions:null}],followers:{daily:[]}}}}};
run("S.data=input;S.start='2026-10-19';S.end='2026-10-21';");
const primary=()=>JSON.parse(run("JSON.stringify(vectorData().find(r=>r.id==='content').activity[0])"));
assert.equal(primary().value,'32'); // Excludes October 18 and the fixed 90-day total.
assert.equal(primary().basis,'period');
run("S.start='2026-10-19';S.end='2026-10-19';");
assert.equal(primary().value,'0'); // An explicit source zero remains measured.
run("S.start='2026-10-19';S.end='2026-10-22';");
assert.equal(primary().value,null); // One unavailable source value is not coerced to zero.
assert.equal(primary().basis,'partial');
run("S.start='2026-10-23';S.end='2026-10-23';");
assert.equal(primary().value,null); // No covered days must not fall back to a 90-day total.
assert.match(primary().note,/0 retained UTC source days.*incomplete/);
assert.equal(run("vectorData().find(r=>r.id==='content').activity[1].value"),'777');
assert.equal(run("vectorData().find(r=>r.id==='content').activity[1].basis"),'snapshot');

const coverage=value=>{ctx.coverage=value;return run('sourceCoverageLabel(coverage)');};
assert.match(coverage({earliestDealCreatedDate:'2024-09-11',reportingThrough:'2026-10-21',observedThrough:'2026-10-22',currentDayPartial:true}),/earliest retained deal created Sep 11, 2024.*Complete reporting days through Oct 21, 2026.*Observed through Oct 22, 2026.*partial/);
assert.match(coverage({scope:'Current referral positions, not period events',reportingThrough:'2026-10-21'}),/Current referral positions, not period events.*Oct 21, 2026/);
assert.match(coverage({oldestIndexedAt:'2026-09-18T19:00:00Z',newestIndexedAt:'2026-10-21T14:30:00Z',completeForActualHeldMeetings:false}),/Indexed recordings reviewed.*Actual held-meeting coverage is incomplete/);
assert.match(coverage({start:'2026-07-16',end:'2026-11-13',endExclusive:true,eventStartMinInclusive:'2026-07-16T06:00:00Z'}),/end exclusive.*Scheduled-start scope.*attendance are not established/);
assert.equal(coverage('Fixed source window'),'Fixed source window');
assert.equal(coverage(null),'Coverage not supplied');
assert.equal(coverage({}),'Coverage not supplied');
console.log('Reporting display: selected-date impressions, missing/zero handling, fixed reach and source-specific coverage passed.');
