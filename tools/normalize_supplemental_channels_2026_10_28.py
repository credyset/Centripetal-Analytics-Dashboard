"""Normalize fresh aggregate-only Charles profile and Waalaxy observations.
Reads local retained UI only; writes private patches, never shared data.
"""
from pathlib import Path
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
import copy,hashlib,json,re
ROOT=Path(__file__).resolve().parents[1]
DIR=ROOT/'data/private/refresh_2026_10_28'
def read(p):return json.loads(p.read_text())
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def local_day(iso):return datetime.fromisoformat(iso.replace('Z','+00:00')).astimezone(ZoneInfo('America/Denver')).date().isoformat()
shared=read(ROOT/'data/shared-dashboard.json')
# Aggregate-only profile viewers: chart bounds are not aggregate bounds.
p=DIR/'linkedin';meta=read(p/'profile_aggregate_meta.json');text=(p/'profile_aggregate_ax.txt').read_text()
assert meta['account']=='Charles Solomon' and 'button Charles Solomon Me'in text and 'Past 90 days'in text
assert f"text {meta['profileViewers']:,} Profile viewers"in text
assert 'Line chart with 13 data points'in text and '2026-08-06 00:00:00 to 2026-10-29 00:00:00'in text
assert 'Week from Thursday, Oct 29, 2026, 267. Viewers.'in text
profile=copy.deepcopy(shared['content']['creatorAnalytics']['profileAnalytics'])
profile.update(snapshotAt=meta['observedAt'],collectedAt=meta['observedAt'],profileViewers=meta['profileViewers'])
profile['coverage'].update(exactDateBoundariesEstablished=False,start=None,end=None,dailyCoverageAvailable=False,completeForSelectedDashboardDates=False)
profile['chartMetadata'].update(meta['chart'],sourceTimezone=None,dateLabelsEstablishAggregateBoundaries=False,weeklyBucketsSummed=False,bucketCompletenessEstablished=False)
profile['evidence'].update(sourceSha256=digest(p/'profile_aggregate_ax.txt'),collectionTimeBasis='Actual authenticated aggregate UI observation timestamp retained in the root collection metadata',primaryContentVerified=True,readOnly=True)
assert profile['sourceTimezone']is None and profile['coverage']['start']is None
save(p/'profile_analytics_patch.json',profile)
# Waalaxy Home keeps a fixed source window and has no inferred daily action dates.
p=DIR/'waalaxy';meta=read(p/'home_meta.json');text=(p/'home_source_ax.txt').read_text()
assert meta['account']=='Charles Solomon' and 'text Charles Solomon'in text and 'linkedin.com/in/solomoncharles'in text
for expected in ['155 Accepted invitations','503 Invitations','0 Messages','0 Visits','0 Follows','2 Answered messages','30.8 % Acceptance rate','1.3 % Response rate Actions sent','01 Oct','29 Oct']:assert expected in text,expected
home=copy.deepcopy(shared['waalaxy']['accountAnalytics']);at=meta['observedAt'];day=local_day(at)
home.update(snapshotAt=at,collectedAt=at,collectedOn=day,reportingLocalDate=day,preparedAt=datetime.now(timezone.utc).isoformat(),collectionTimestampBasis='Actual authenticated Home observation timestamp retained separately from root preparation; not an upstream sync/generation time.')
home['sourceWindow'].update(preset=meta['preset'],displayedStartDate=meta['displayedStart'],displayedEndDate=meta['displayedEnd'],finalDayPartial=True,sourceTimezone=None,exactStartTimestamp=None,exactEndTimestamp=None,dateBasis=f'Source chart labels October 1–29 with a partial final day; source timezone is unavailable. Collection occurred {day} Mountain; no UTC/Mountain event attribution is inferred.')
home['metrics'].update(invitationActionsSent=503,invitationAcceptancesReported=155,messageActionsSent=0,answeredMessagesReported=2,profileVisitActionsSent=0,profileFollowActionsSent=0)
home['platformDisplayedRates'].update(acceptancePercent=30.8,responsePercent=1.3,denominatorDefinitions=None,cohortRateEstablished=False)
home['integration'].update(displayAs='Charles Waalaxy · October 1–29 (partial) · fixed source window',includeInSelectedPeriodTotals=False,mergeIntoDailySeries=False,mergeWithSelectedConnectedPeople=False,existingDailyInvitationSource={'action':'Preserve or update only from independently dated CSV evidence','scope':'Daily source-date invitation history is separate; no daily buckets are inferred from Home aggregates.'},sourceOverlapsExistingDailyHistory=True,replacesAccountAccessGap='Current Charles identity and fixed Home totals are verified. A separately supplied owner CSV is handled independently; complete message and acceptance event history remains unavailable.')
home['limits']=['Home aggregates and the invitation CSV/selected-person sheet use separate collection clocks and source definitions; do not add overlapping populations.',f'The source chart ends October 29 with a partial final day; source timezone is unknown. The observation occurred {day} Mountain.','This fixed source window does not supply exact event dates, weekly totals or matched invitation cohorts.','The browser export control did not yield a file in this observation. Any owner-supplied CSV is independently collected and normalized; Home is never used to manufacture daily rows.','Current Home/CSV totals can reconcile numerically without establishing exact acceptance-event dates, complete history or sender provenance for the separate person subset.','Zero platform message, visit and follow actions do not establish zero manual LinkedIn outreach or Video DM sends.','Two answered messages are not two verified unique prospects, positive replies, video-specific replies, qualification, meetings, opportunities or wins.','Acceptance/response percentages are descriptive platform displays; matched invitation and message denominators remain unknown.','Current Home identity does not establish the sender or last successful upstream synchronization time for the separate worksheet.']
home['evidence']={'sourceSha256':digest(p/'home_source_ax.txt'),'readOnly':True,'minimalAggregateOnly':True}
save(p/'account_analytics_patch.json',home)
print(json.dumps({'profilePatch':'linkedin/profile_analytics_patch.json','profileViewers':profile['profileViewers'],'profileSourceClock':profile['snapshotAt'],'waalaxyPatch':'waalaxy/account_analytics_patch.json','waalaxySourceClock':home['snapshotAt'],'waalaxyMetrics':home['metrics'],'dailyInvitationBucketsModified':False}))
