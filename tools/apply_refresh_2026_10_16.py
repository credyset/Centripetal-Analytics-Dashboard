"""Assemble reviewed source supplements without advancing unchanged feed dates.

Requires the retained, ignored outputs of the named read-only source reviews.
The tracked shared snapshot remains the portable publication input.
"""
from datetime import datetime, timezone
from pathlib import Path
import json
import copy
from prepare_shared_snapshot import curate_snapshot, preserve_newer_shared_sources

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'


def read(name):
    return json.loads((DATA / name).read_text())


def build():
    current = read('shared-dashboard.json')
    previous = copy.deepcopy(current)
    for key, filename in [('crm','crm_refresh.json'), ('referrals','referral_refresh.json'),
                          ('ads','ads_refresh.json'), ('content','content_refresh.json'),
                          ('video','video_refresh.json'), ('time','time.json')]:
        current[key] = read(filename)
    fresh_w = read('waalaxy_refresh.json')
    # Selected prospect attributes cannot replace account-wide historical flags
    # or invitation action day buckets. Keep all three dated scopes distinct.
    current['waalaxy'].update(snapshotAt=fresh_w['snapshotAt'],
        sheetSubset=fresh_w['sheetSubset'], sheetSubsetCollectedAt=fresh_w['snapshotAt'],
        sheetSubsetAccountVerification=fresh_w['accountVerification'],
        sheetSubsetUpstreamSyncAt=fresh_w['upstreamSyncAt'])
    current['meta'].update(generatedAt=current['crm']['snapshotAt'],
        defaultReportingThrough=current['crm']['coverage']['reportingThrough'],
        revision='Reviewed October 16 source refresh and owner-confirmed outcomes')
    sources = {s['id']:s for s in current['sources']}
    sources['crm'].update(asOf=current['crm']['snapshotAt'], status='Current snapshot')
    sources['referrals'].update(asOf=current['referrals']['snapshotAt'],
        note='Collected with the main CRM snapshot. Current referral stage positions are not dated requests, introductions or qualified outcomes.')
    sources['video'].update(asOf=current['video']['snapshotAt'],
        note='428 prospect rows and both complete worksheet tabs reviewed. 57 ready rows; 29 explicit Sent/Done statuses. These are undated inventory, not verified period sends. Upstream sync time is unreported.')
    sources['ads'].update(asOf=current['ads']['collectedAt'], coverage=current['ads']['coverage'],
        checkedAt='2026-10-16',
        note='Campaign and creative exports reconcile through October 16 UTC. Lead detail access remains permission-blocked; four retained dispositions remain in use. Owner separately confirms the two linked calls as held; NuVee alone remains qualified/warm.')
    sources['content'].update(checkedAt='2026-10-16',
        note='Private Charles daily analytics end September 10, 2026; company private baseline is 2025. October 16 public followers and 26 distinct visible post observations are separate dated evidence, not private impressions or a publishing census.')
    sources['waalaxy'].update(asOf=fresh_w['snapshotAt'], checkedAt='2026-10-16',
        status='Current selected prospect snapshot; partial invitation export',
        method='Read-only connected-prospect worksheet, retained invitation CSV and historical prospect flags',
        coverage='October 16 selected prospect collection; invitations September 15–October 15; historical account flags through June 26')
    sources['time'].update(asOf=current['time']['snapshotAt'],coverage=current['time']['period'],
        method='Fresh Fireflies metadata and speaker identity review; prior scoped calendar evidence; owner-adjusted nonmeeting assumptions',
        note='Christian only, October 1–16 MTD; October 16 partial. Five deduplicated recording durations, 228.58 audio minutes. Separate owner-specified nonmeeting estimate is 14.5–15.75 hours; actual attendance/work hours remain unknown.')
    sources['meetings']['note'] = 'Calendar source retains its collection date. The owner separately confirmed the two linked lead calls as held October 16; this is a bounded set, not complete held-call coverage.'
    current['sources'] = list(sources.values())
    result = curate_snapshot(preserve_newer_shared_sources(current, previous))
    text = json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    (DATA/'shared-dashboard.json').write_text(text)
    (DATA/'dashboard.json').write_text(text)
    print(json.dumps({'reportingThrough':result['meta']['defaultReportingThrough'],
        'timeThrough':result['time']['period']['end'],
        'heldCalls':result['meetings']['summary']['ownerConfirmedLinkedHeldCalls']}))


if __name__=='__main__':
    build()
