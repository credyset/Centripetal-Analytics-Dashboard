"""Normalize retained Charles Chrome accessibility evidence; never publishes it.

The complete source chart was captured read-only in Charles's signed-in Chrome
window. This file only parses that retained UI evidence and produces a private
integration patch. Source-day boundaries stay UTC.
"""
import copy
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from apply_charles_creator_snapshot import normalize

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / 'data/private/refresh_2026_10_21'
SOURCE = PRIVATE / 'creator_90_days_ax.txt'


def build():
    text = SOURCE.read_text()
    assert 'button Charles Solomon Me' in text
    assert 'linkedin.com/in/solomoncharles/' in text
    assert 'button 90 days' in text and 'button Cumulative' in text
    assert 'Daily data is recorded in UTC' in text
    pattern = r'image (?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday), ([A-Z][a-z]{2} \d{1,2}, 2026), ([\d,]+)\. Impressions\.'
    points = [{'date': datetime.strptime(day, '%b %d, %Y').date().isoformat(),
               'cumulativeImpressions': int(value.replace(',', ''))}
              for day, value in re.findall(pattern, text)]
    assert len(points) == 90
    assert points[0]['date'] == '2026-07-25'
    assert points[-1]['date'] == '2026-10-22'
    dates = [datetime.fromisoformat(p['date']).date() for p in points]
    assert all(b-a == timedelta(days=1) for a, b in zip(dates, dates[1:]))
    assert points[-1]['cumulativeImpressions'] == 58532

    # The capture file's write time is retained as observation time; preparation
    # time is separate, and no new source collection is claimed by re-running.
    observed = datetime.fromtimestamp(SOURCE.stat().st_mtime, timezone.utc)
    snapshot = observed.isoformat().replace('+00:00', 'Z')
    checked = observed.astimezone(ZoneInfo('America/Denver')).date().isoformat()
    source = {
        'snapshotAt': snapshot, 'checkedAt': checked, 'sourcePreset': '90 days',
        'account': {'name': 'Charles Solomon',
                    'profileUrl': 'https://www.linkedin.com/in/solomoncharles/',
                    'identityVerified': True,
                    'identityBasis': 'Signed-in Charles Solomon Me control and matching solomoncharles sidebar in the Centreptal Advisors x RedySet Chrome window'},
        'url': 'https://www.linkedin.com/analytics/creator/content/',
        'method': 'Read-only native Chrome accessibility observation in the owner-designated Charles profile',
        'coverage': {'start': points[0]['date'], 'end': points[-1]['date'],
                     'sourceTimezone': 'UTC', 'sourcePreset': '90 days',
                     'finalDayPartial': True, 'completeDaysThrough': '2026-10-21',
                     'observedMountainDate': checked,
                     'accountScope': 'Charles personal creator content only'},
        'summary': {'impressions': 58532, 'membersReached': 32032,
                    'socialEngagements': 543, 'reactions': 466, 'comments': 66,
                    'reposts': 4, 'saves': 7, 'sendsOnLinkedIn': 0,
                    'linkEngagements': 10, 'premiumCustomButtonEngagements': 8,
                    'visitsToLinksInAllPosts': 2,
                    'inNetworkPercent': 30, 'outOfNetworkPercent': 70},
        'comparison': {'metric': 'impressions', 'percentChange': 258,
                       'label': '258% higher versus prior 90 days',
                       'periodLabel': 'prior 90 days', 'sourceReported': True,
                       'priorValue': None,
                       'note': 'Platform-reported rounded comparison; current final UTC day is partial. Do not reconstruct an exact prior count.'},
        'chart': {'metric': 'impressions', 'display': 'Cumulative',
                  'sourceDateBasis': 'Daily data is recorded in UTC', 'points': points},
        'topPosts': [
            {'activityId': '7486401068025737216',
             'title': 'Pricing stories beside public SaaS revenue multiples',
             'titleBasis': 'Minimal topic label derived from visible post excerpt',
             'url': 'https://www.linkedin.com/feed/update/urn:li:share:7483246265091256320/',
             'analyticsUrl': 'https://www.linkedin.com/analytics/post-summary/urn:li:activity:7486401068025737216/',
             'impressions': 19069, 'engagements': 20, 'publishedAt': None},
            {'activityId': '7508255841335103488',
             'title': 'Pulley is shutting down: what operators should do, and what it says about cap table software',
             'url': 'https://www.linkedin.com/feed/update/urn:li:ugcPost:7508255840668160000/',
             'analyticsUrl': 'https://www.linkedin.com/analytics/post-summary/urn:li:activity:7508255841335103488/',
             'impressions': 9754, 'engagements': 14, 'publishedAt': None},
            {'activityId': '7487569282596380673',
             'title': 'SaaSpocalypse and software defensibility in an AI world',
             'titleBasis': 'Minimal topic label derived from visible post excerpt',
             'url': 'https://www.linkedin.com/feed/update/urn:li:share:7487569279584841729/',
             'analyticsUrl': 'https://www.linkedin.com/analytics/post-summary/urn:li:activity:7487569282596380673/',
             'impressions': 2246, 'engagements': 20, 'publishedAt': None}
        ],
        'notes': [
            'Current signed-in Charles creator snapshot, collected from his owner-designated Chrome window; Christian profile and public-feed observations were not substituted.',
            'The source covers July 25–October 22 UTC. October 22 UTC is partial even though the observation occurred October 21 Mountain time. UTC daily buckets are not relabelled as Mountain days.',
            'Daily impressions are first differences of all 90 cumulative chart points. Daily social engagements, daily unique reach and daily link engagements are unavailable from this chart.',
            'Social engagements sum reactions, comments, reposts, saves and LinkedIn sends. The separate 10 link engagements comprise 8 custom-button engagements and 2 post-link visits; none are added to social engagements.',
            'Three visible top posts are a ranked sample measured in the 90-day analytics window; they do not represent lifetime metrics or a complete publishing register. Publication dates remain unknown.',
            'Current company-page private performance and an explicit organic-versus-sponsored split are not supplied by this Charles personal creator view.',
            'The retained 90-day chart closes the former September 11–October 10 private daily impression gap; current daily social engagement counts remain unavailable.',
            'This is an on-demand UI observation, not an unattended daily integration.'
        ],
        'evidence': {'sourceFileSha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                     'observationTimeBasis': 'Write time of the retained read-only Chrome accessibility capture'}
    }
    creator = normalize(source)
    old = json.loads((ROOT / 'data/shared-dashboard.json').read_text())
    content = copy.deepcopy(old['content'])
    content.setdefault('historicalCoverage', copy.deepcopy(content['coverage']))
    content['creatorAnalytics'] = creator
    content['snapshotAt'] = creator['snapshotAt']
    content['status'] = 'current_creator_snapshot_with_historical_reference'
    content['coverage'] = {'start': min(content['coverage']['start'], creator['coverage']['start']),
                           'end': creator['coverage']['end']}
    rows = {(r['account'], r['date']): copy.deepcopy(r) for r in content['daily']}
    preserved_engagement_days = 0
    for row in creator['daily']:
        key = (row['account'], row['date'])
        prior = rows.get(key, {})
        merged = {**prior, **row}
        # New chart only supplies impressions. Do not erase genuine historical
        # engagement fields with null, or claim their unspecified timezone is UTC.
        if prior.get('engagements') is not None:
            merged['engagements'] = prior['engagements']
            merged['engagementsSource'] = 'Retained historical Charles export'
            merged['engagementsSourceTimezone'] = prior.get('engagementsSourceTimezone', 'unspecified in historical export')
            merged['engagementsSourceDateBasis'] = 'Original historical export date; not rebucketed to UTC'
            preserved_engagement_days += 1
        rows[key] = merged
    content['daily'] = sorted(rows.values(), key=lambda r: (r['date'], r['account']))
    content['accessReview'].update(
        status='current_charles_creator_access', checkedAt=checked,
        reason='Owner-designated Charles Chrome identity verified. Current personal 90-day creator view collected; current company-page private and sponsored splits not collected.',
        currentCharlesPrivateCoverage=creator['coverage'],
        newestPrivateCharlesCoverageEnd=creator['coverage']['end'])
    content['review'] = {'kind': 'signed_in_charles_creator', 'snapshotAt': snapshot,
                         'identityVerified': True, 'sourceWindow': creator['coverage'],
                         'scope': '90-day personal creator view; company/private sponsored analytics remain separate'}
    content['notes'] = [n for n in content.get('notes', [])
                        if not n.startswith('Current signed-in Charles creator analytics cover')]
    content['notes'].append('Current signed-in Charles creator daily impressions cover July 25–October 22 UTC, final day partial. Historical engagement counts keep their original export dates and unspecified personal-export timezone; they are not erased by the new impression-only chart. Fixed-window social totals, unique reach, historical exports and public observations retain separate scopes.')
    source_row = copy.deepcopy(next(s for s in old['sources'] if s['id'] == 'content'))
    source_row.update(status='Current Charles 90-day creator snapshot; historical company reference',
                      asOf=snapshot, checkedAt=checked,
                      coverage='Charles creator July 25–October 22 UTC, final day partial; historical company analytics remain separately dated',
                      method='Read-only Charles signed-in Chrome creator analytics plus retained exports and public observations',
                      note='58,532 impressions, 32,032 members reached and 543 social engagements in the fixed 90-day source window. All 90 cumulative points reconcile. Daily impressions derived; daily social engagements, current company analytics, and organic/sponsored separation remain incomplete.')
    totals = {label: sum(r['impressions'] for r in creator['daily'] if start <= r['date'] <= end)
              for label, start, end in [('octoberUtcThrough21', '2026-10-01', '2026-10-21'),
                                       ('weekUtcOct19Through21', '2026-10-19', '2026-10-21'),
                                       ('octoberUtcThrough22Partial', '2026-10-01', '2026-10-22')]}
    patch = {'creatorAnalytics': creator, 'content': content, 'source': source_row,
             'validation': {'pointCount': len(points),
                            'sumDerivedImpressions': sum(r['impressions'] for r in creator['daily']),
                            'socialComponents': sum(creator['summary'][k] for k in ['reactions', 'comments', 'reposts', 'saves', 'sendsOnLinkedIn']),
                            'preservedHistoricalEngagementDays': preserved_engagement_days,
                            'utcSourceBucketTotals': totals,
                            'periodTotalsAreMountainTime': False}}
    (PRIVATE / 'creator_patch.json').write_text(json.dumps(patch, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'snapshotAt': snapshot, 'checkedAt': checked,
                      'validation': patch['validation']}))


if __name__ == '__main__':
    build()
