/* Normalize a fresh Charles workbook and its visible, identity-verified UI.
 * Reads local files only. Writes a private patch, never the shared snapshot. */
'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const XLSX=require('/Users/christianwutz/mcp-servers/centripetal/node_modules/xlsx');
const ROOT=path.resolve(__dirname,'..');
const DIR=path.resolve(process.argv[2]||path.join(ROOT,'data/private/refresh_2026_10_28/linkedin'));
const file=path.join(DIR,'creator.xlsx'),uiFile=path.join(DIR,'source_ax.txt');
const originalDownload=process.argv[3]||'/Users/christianwutz/Downloads/AggregateAnalytics_Charles Solomon_2026-08-01_2026-10-29.xlsx';
const ui=fs.readFileSync(uiFile,'utf8'),workbook=XLSX.readFile(file);
const sheet=name=>{assert(workbook.Sheets[name],`Missing worksheet ${name}`);return XLSX.utils.sheet_to_json(workbook.Sheets[name],{header:1,defval:null});};
const sha=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const integer=value=>{assert(value!==null&&value!==undefined&&value!=='','Missing numeric source field');const n=Number(String(value).replaceAll(',',''));assert(Number.isInteger(n)&&n>=0,`Invalid source count ${value}`);return n;};
const date=value=>{const m=String(value).match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);assert(m,`Invalid source date ${value}`);return `${m[3]}-${m[1].padStart(2,'0')}-${m[2].padStart(2,'0')}`;};
const sum=(rows,key)=>rows.reduce((n,r)=>n+r[key],0);
// Retain the pre-refresh comparison source so replaying after integration
// cannot turn the earlier-to-current source difference into an invented zero.
const baselineFile=path.join(DIR,'baseline_previous_creator.json');
const previous=fs.existsSync(baselineFile)?JSON.parse(fs.readFileSync(baselineFile,'utf8')):
  JSON.parse(fs.readFileSync(path.join(ROOT,'data/shared-dashboard.json'),'utf8')).content.creatorAnalytics;
if(!fs.existsSync(baselineFile))fs.writeFileSync(baselineFile,JSON.stringify(previous,null,2)+'\n');
assert(ui.includes('button Charles Solomon Me')&&ui.includes('linkedin.com/in/solomoncharles/')&&ui.includes('button 90 days')&&ui.includes('Daily data is recorded in UTC'),'Charles/window identity not established');
const observedAt=fs.statSync(uiFile).mtime.toISOString();
const retainedAt=fs.statSync(file).mtime.toISOString();
let downloadedAt=null;
if(fs.existsSync(originalDownload)){
  assert.equal(sha(originalDownload),sha(file),'Retained file differs from original download');
  downloadedAt=fs.statSync(originalDownload).mtime.toISOString();
}
const sourceAt=downloadedAt||retainedAt;
const discovery=sheet('DISCOVERY'),window=String(discovery[0][1]).split(' - ');
assert.equal(window.length,2);const start=date(window[0]),end=date(window[1]);
const impressions=integer(discovery.find(r=>r[0]==='Impressions')[1]),membersReached=integer(discovery.find(r=>r[0]==='Members reached')[1]);
const engagement=sheet('ENGAGEMENT');assert.deepEqual(engagement[0],['Date','Impressions','Engagements']);
const daily=engagement.slice(1).map(r=>({date:date(r[0]),impressions:integer(r[1]),engagements:integer(r[2])}));
assert.equal(daily.length,90);assert.equal(daily[0].date,start);assert.equal(daily.at(-1).date,end);
assert.equal(new Set(daily.map(r=>r.date)).size,daily.length);
daily.forEach((r,i)=>{if(i)assert.equal((Date.parse(r.date)-Date.parse(daily[i-1].date))/86400000,1);});
assert.equal(sum(daily,'impressions'),impressions,'Workbook discovery does not reconcile to worksheet days');
const points=[...ui.matchAll(/image (?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday), ([A-Z][a-z]{2} \d{1,2}, \d{4}), ([\d,]+)\. Impressions\./g)].map(m=>({date:new Date(`${m[1]} 12:00:00 UTC`).toISOString().slice(0,10),cumulativeImpressions:integer(m[2])}));
assert.equal(points.length,daily.length);
const differences=[];let cumulative=0;
daily.forEach((row,i)=>{cumulative+=row.impressions;assert.equal(points[i].date,row.date);if(points[i].cumulativeImpressions!==cumulative)differences.push({date:row.date,uiCumulative:points[i].cumulativeImpressions,exportCumulative:cumulative,difference:points[i].cumulativeImpressions-cumulative});});
function following(label){const m=ui.match(new RegExp(`text ${label}\\n\\s*\\d+ text ([\\d,]+)`));assert(m,`Missing UI ${label}`);return integer(m[1]);}
function preceding(label){const m=ui.match(new RegExp(`text ([\\d,]+)\\n\\s*\\d+ text ${label}`));assert(m,`Missing UI ${label}`);return integer(m[1]);}
const uiImpressions=preceding('Impressions'),reachMatch=ui.match(/text ([\d,]+) Members reached/);assert(reachMatch);
const uiReach=integer(reachMatch[1]);
const network=ui.match(/In-network \(followers and connections\) (\d+)% Out-of-network (\d+)%/);assert(network);
const summary={impressions,membersReached,socialEngagements:preceding('Social engagements'),reactions:following('Reactions'),comments:following('Comments'),reposts:following('Reposts'),saves:following('Saves'),sendsOnLinkedIn:following('Sends on LinkedIn'),linkEngagements:preceding('Link engagements'),premiumCustomButtonEngagements:following('Premium custom button engagements'),visitsToLinksInAllPosts:following('Visits to links in all posts'),inNetworkPercent:integer(network[1]),outOfNetworkPercent:integer(network[2]),exportEngagements:sum(daily,'engagements')};
assert.equal(sum(['reactions','comments','reposts','saves','sendsOnLinkedIn'].map(k=>({v:summary[k]})),'v'),summary.socialEngagements);
const comparison=ui.match(/text (\d+)%\n\s*\d+ text vs\. prior 90 days/);assert(comparison);
const priorDay=new Date(Date.parse(end)-86400000).toISOString().slice(0,10);
const observedMountainDate=new Intl.DateTimeFormat('en-CA',{timeZone:'America/Denver',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(observedAt));
const coverage={...previous.coverage,start,end,sourceTimezone:'UTC',sourcePreset:'90 days',finalDayPartial:true,completeDaysThrough:priorDay,observedMountainDate,sourceMayRestate:true};
const postRows=sheet('TOP POSTS');assert(String(postRows[0][0]).includes('Maximum of 50 posts'));assert.equal(postRows[2][0],'Post URL');
const posts=new Map();let engagementRows=0,impressionRows=0;
for(const [offset,metric] of [[0,'engagements'],[4,'impressions']])for(const row of postRows.slice(3)){
  if(!row[offset])continue;
  const url=new URL(row[offset]);assert.equal(url.hostname,'www.linkedin.com');
  const idMatch=url.pathname.match(/(ugcPost|share)-(\d+)/);assert(idMatch,'No stable source post identity');
  const postId=`${idMatch[1]}:${idMatch[2]}`,publishedAt=date(row[offset+1]),prior=posts.get(postId);if(prior)assert.equal(prior.publishedAt,publishedAt);
  const p=prior||{postId,url:String(row[offset]),publishedAt,account:'Charles Solomon',impressions:null,engagements:null,impressionRank:null,engagementRank:null};
  const rank=metric==='impressions'?++impressionRows:++engagementRows;p[metric]=integer(row[offset+2]);p[metric==='impressions'?'impressionRank':'engagementRank']=rank;posts.set(postId,p);
}
assert(impressionRows<=50&&engagementRows<=50);

// Current top posts come only from the fresh, visible UI and stable workbook IDs.
const topSection=ui.slice(ui.indexOf('text Top performing posts'),ui.indexOf('text Top demographics'));
const uiTopBlocks=[...topSection.matchAll(/link ([\d,]+) impressions • ([\d,]+) engagements View analytics, Value: (?:https?:\/\/)?linkedin\.com\/analytics\/post-summary\/urn:li:activity:(\d+)\/([\s\S]*?)(?=\n[^\n]*link [\d,]+ impressions|\n[^\n]*link Show more|$)/g)];
assert.equal(uiTopBlocks.length,3,'Fresh visible top-three block is incomplete');
const topicLabels={'ugcPost:7519009661807845376':'AppWork acquisition of Paraspot AI','share:7483246265091256320':'Pricing stories beside public SaaS revenue multiples','ugcPost:7508255840668160000':'Pulley closure and cap-table migration'};
const topPosts=uiTopBlocks.map((match,index)=>{
 const post=match[4].match(/link Value: (?:https?:\/\/)?linkedin\.com\/feed\/update\/urn:li:(ugcPost|share):(\d+)\/,[^\n]+/);assert(post,'Fresh top-post stable feed identity missing');
 const postId=`${post[1]}:${post[2]}`,record=posts.get(postId);assert(record,'Fresh UI post not present in the retained workbook rankings');
 const sourceImpressions=integer(match[1]),sourceEngagements=integer(match[2]);assert.equal(record.impressions,sourceImpressions,'Fresh top-post impression mismatch');
 if(record.engagements!==null)assert.equal(record.engagements,sourceEngagements,'Fresh top-post engagement mismatch');
 assert(topicLabels[postId],'Fresh post needs a minimal grounded topic label');
 return{postId,activityId:match[3],title:topicLabels[postId],titleBasis:'Minimal topic label derived from current visible post excerpt',url:`https://www.linkedin.com/feed/update/urn:li:${postId}/`,analyticsUrl:`https://www.linkedin.com/analytics/post-summary/urn:li:activity:${match[3]}/`,impressions:sourceImpressions,engagements:sourceEngagements,publishedAt:record.publishedAt,rank:index+1,sourceSnapshotAt:observedAt,measurementWindow:{start,end,sourceTimezone:'UTC'},metricBasis:'Fresh visible top-performing-post row, independently matched to stable workbook post ID'};
});
const historicalTopPostReviews=[...(previous.historicalTopPostReviews||[])];
if(previous.topPosts?.length&&!historicalTopPostReviews.some(r=>r.sourceSnapshotAt===previous.snapshotAt))historicalTopPostReviews.push({sourceSnapshotAt:previous.snapshotAt,measurementWindow:{start:previous.coverage.start,end:previous.coverage.end,sourceTimezone:previous.coverage.sourceTimezone},records:previous.topPosts,note:'Historical source snapshot only; these older metrics do not populate current top-post rows.'});

const followerRows=sheet('FOLLOWERS'),followerDate=String(followerRows[0][0]).match(/^Total followers on (.+)$/);assert(followerDate);assert.equal(date(followerDate[1]),end);
const followers=integer(followerRows[0][1]);assert.deepEqual(followerRows[2],['Date','New followers']);
const followerDaily=followerRows.slice(3).map(row=>({date:date(row[0]),newFollowers:integer(row[1])}));assert.deepEqual(followerDaily.map(r=>r.date),daily.map(r=>r.date));
const reconciliation={identityVerified:true,workbookDailyRows:daily.length,workbookImpressionsReconciled:true,uiCumulativePointCount:points.length,uiCumulativeDifferences:differences,uiImpressions,exportImpressions:impressions,uiReach,exportReach:membersReached,allSourceCountsReconciled:differences.length===0&&uiImpressions===impressions&&uiReach===membersReached};
fs.writeFileSync(path.join(DIR,'creator_reconciliation_review.json'),JSON.stringify(reconciliation,null,2)+'\n');
assert(reconciliation.allSourceCountsReconciled,'Non-atomic UI/export difference recorded privately. Retain export values; obtain a fresh matching UI before integrating this patch.');
const notes=[
  `Impressions and all ${daily.length} direct worksheet days reconcile to the separately retained cumulative UI chart.`,
  `Export Engagements total ${summary.exportEngagements}; separate UI social total ${summary.socialEngagements} and link total ${summary.linkEngagements} retain distinct definitions. No daily social/link allocation is inferred from their numeric difference.`,
  'Ranked posts include publication dates outside the measurement window. The capped ranked subset is not a complete publishing census or lifetime-performance export.',
  'New followers are source additions, not net audience growth; fixed-window unique reach is not a daily series.',
  `${end} UTC is partial. Source values can restate, including earlier dates; updated totals do not all represent new activity since collection.`
];
const exportAnalytics={snapshotAt:sourceAt,collectedAt:sourceAt,coverage,source:'Authenticated Charles creator workbook',engagementDefinition:'Original worksheet field Engagements; broader source measure kept separate from the signed-in UI Social engagements. Daily social-only components are not supplied.',daily,summary:{impressions,membersReached,engagements:summary.exportEngagements},postCoverage:{completePublishingHistory:false,rankingCapPerMetric:50,engagementRankedRows:engagementRows,impressionRankedRows:impressionRows,uniqueRankedPosts:posts.size,measurementWindow:{start,end,sourceTimezone:'UTC'},note:'Union of separately capped engagement and impression rankings, deduplicated by stable source post ID. Publication dates select posts; performance belongs to the export window. Missing metrics remain null; no publishing census is inferred.'},rankedPosts:[...posts.values()].sort((a,b)=>(a.impressionRank??1000)-(b.impressionRank??1000)),followers:{snapshotOn:end,total:followers,daily:followerDaily,newFollowersInWindow:sum(followerDaily,'newFollowers'),definition:'Source new followers, not net change; unfollows and opening inventory are unavailable.'},demographics:{audience:sheet('AUDIENCE DEMOGRAPHICS').slice(1).map(row=>({category:row[0],value:row[1],percentageLabel:row[2]})),content:sheet('CONTENT DEMOGRAPHICS').slice(1).map(row=>({category:row[0],value:row[1],percentageLabel:row[2]})),note:'Rounded/suppressed percentage labels remain text. Audience and content populations differ; no unduplicated population total is inferred.'},notes};
const creator={...previous,snapshotAt:observedAt,collectedAt:observedAt,checkedAt:observedMountainDate,coverage,summary,method:'Fresh authenticated Charles Chrome workbook, independently reconciled to retained creator UI',comparison:{...previous.comparison,percentChange:integer(comparison[1]),label:`${comparison[1]}% versus prior 90 days (platform display)`},chart:{...previous.chart,points},daily:daily.map(row=>({...row,engagements:null,exportEngagements:row.engagements,account:'Charles Solomon',sourceId:'charles_creator_export',sourceTimezone:'UTC',currentDayPartial:row.date===end,derivation:'Direct XLSX worksheet row, impression values reconciled to separately observed cumulative UI'})),exportAnalytics,topPosts,historicalTopPostReviews,notes,evidence:{sourceFileSha256:sha(file),uiFileSha256:sha(uiFile),observationTimeBasis:'Visible UI capture write time; original download completion and retained-copy time distinguished.',originalDownloadCompletedAt:downloadedAt,retainedCopyAt:retainedAt}};
const selected=(a,b)=>{const rows=daily.filter(r=>a<=r.date&&r.date<=b),follow=followerDaily.filter(r=>a<=r.date&&r.date<=b);return {start:a,end:b,retainedDays:rows.length,impressions:sum(rows,'impressions'),exportEngagements:sum(rows,'engagements'),newFollowers:sum(follow,'newFollowers'),finalDayPartial:b===end};};
const previousDays=new Map(previous.exportAnalytics.daily.map(row=>[row.date,row]));
const restatedDaily=daily.filter(row=>previousDays.has(row.date)&&(['impressions','engagements'].some(k=>row[k]!==previousDays.get(row.date)[k]))).map(row=>({date:row.date,prior:previousDays.get(row.date),current:row}));

const previousRows=previous.exportAnalytics.daily,commonStart=[previous.coverage.start,start].sort().at(-1),commonEnd=[previous.coverage.end,end].sort()[0];
const previousCommon=previousRows.filter(r=>commonStart<=r.date&&r.date<=commonEnd),currentCommon=daily.filter(r=>commonStart<=r.date&&r.date<=commonEnd);
assert.deepEqual(previousCommon.map(r=>r.date),currentCommon.map(r=>r.date));
const newRows=daily.filter(r=>!previousDays.has(r.date)),currentDates=new Set(daily.map(r=>r.date)),droppedRows=previousRows.filter(r=>!currentDates.has(r.date));
const commonImpressionRestatement=sum(currentCommon,'impressions')-sum(previousCommon,'impressions'),commonEngagementRestatement=sum(currentCommon,'engagements')-sum(previousCommon,'engagements');
const totalDifference=impressions-previous.summary.impressions;
assert.equal(totalDifference,sum(newRows,'impressions')-sum(droppedRows,'impressions')+commonImpressionRestatement,'Rolling-window decomposition does not reconcile');
const rollingWindowComparison={priorWindow:previous.coverage,currentWindow:{start,end,sourceTimezone:'UTC'},commonWindow:{start:commonStart,end:commonEnd,days:currentCommon.length,priorImpressions:sum(previousCommon,'impressions'),currentImpressions:sum(currentCommon,'impressions'),impressionRestatementDifference:commonImpressionRestatement,priorExportEngagements:sum(previousCommon,'engagements'),currentExportEngagements:sum(currentCommon,'engagements'),exportEngagementRestatementDifference:commonEngagementRestatement},newlyCoveredDates:newRows.map(r=>r.date),newlyCoveredImpressions:sum(newRows,'impressions'),droppedDates:droppedRows.map(r=>r.date),droppedImpressions:sum(droppedRows,'impressions'),rollingTotalDifference:totalDifference,isPureGrowthSincePriorCollection:false,note:'Current and prior rolling 90-day windows differ. Newly covered source days, dropped source days and restated common-day values are shown separately. Unique reach and fixed-window social totals cannot be decomposed into new activity from aggregate differences.'};
creator.comparisonToPreviousSource=rollingWindowComparison;
const selectedEnd=observedMountainDate<end?observedMountainDate:end;
const validation={...reconciliation,exportEngagements:summary.exportEngagements,socialEngagements:summary.socialEngagements,rankedPosts:posts.size,followers,newFollowers:exportAnalytics.followers.newFollowersInWindow,week:selected('2026-10-26',selectedEnd),month:selected('2026-10-01',selectedEnd),rollingWindowComparison,restatedDaily,freshTopPosts:topPosts.length,priorProfileAnalyticsRetainedWithOriginalClock:creator.profileAnalytics?.snapshotAt||null};

const patch={creatorAnalytics:creator,validation};
fs.writeFileSync(path.join(DIR,'creator_latest_patch.json'),JSON.stringify(patch,null,2)+'\n');
console.log(JSON.stringify({...validation,restatedDailyCount:restatedDaily.length,restatedDaily:undefined}));
