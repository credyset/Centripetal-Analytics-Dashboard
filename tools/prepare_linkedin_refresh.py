"""Prepare an isolated October 16 LinkedIn review without changing dashboard inputs.

Source collection is a manual, authenticated, read-only browser export. This script
does not access credentials, call LinkedIn, publish data, or modify existing inputs.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import shutil
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
RAW = DATA / 'private/channels/2026-10-16'
DOWNLOADS = Path('/Users/christianwutz/Downloads')
DATE = '2026-10-16'
FIELDS = {'Total Spent': 'spend', 'Impressions': 'impressions', 'Clicks': 'clicks',
          'Lead Forms Opened': 'opens', 'Leads': 'leads', 'Video Views': 'videoViews',
          'Video Views at 25%': 'video25', 'Video Views at 50%': 'video50',
          'Video Views at 75%': 'video75', 'Video Completions': 'videoCompletions',
          'Appointments Booked': 'platformAppointmentsReported'}


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def n(value):
    return float(str(value or '0').replace(',', ''))


def day(value):
    return datetime.strptime(value, '%m/%d/%Y').date().isoformat()


def source(path):
    return {'file': path.name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def parse_export(path):
    text = path.read_text(encoding='utf-16')
    meta = {}
    for label, key in [('Report Start', 'start'), ('Report End', 'end'), ('Date Generated', 'generated')]:
        value = re.search(rf'"{label}: ([^"]+)"', text).group(1)
        parsed = datetime.strptime(value, '%B %d, %Y, %I:%M %p').replace(tzinfo=ZoneInfo('UTC'))
        meta[key] = parsed.isoformat()
    header = text.index('Start Date (in UTC)\t')
    rows = list(csv.DictReader(io.StringIO(text[header:]), delimiter='\t'))
    assert all('Centripetal' in r['Account Name'] and r['Currency'] == 'USD' for r in rows)
    assert meta['start'].startswith('2026-09-04') and meta['end'].startswith('2026-10-16')
    return rows, meta


def sums(rows):
    values = {out: round(sum(n(r.get(field)) for r in rows), 2) for field, out in FIELDS.items()}
    for key in values:
        if key != 'spend':
            assert values[key].is_integer()
            values[key] = int(values[key])
    return values


def daily(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[day(row['Start Date (in UTC)'])].append(row)
    return [{'date': date, **sums(values)} for date, values in sorted(groups.items())]


def paid():
    for src, target in [('account_515259390_campaign_performance_report (6).csv', 'adsets_daily_utf16.tsv'),
                        ('account_515259390_creative_performance_report (8).csv', 'creatives_daily_utf16.tsv')]:
        if not (RAW / target).exists():
            shutil.copyfile(DOWNLOADS / src, RAW / target)
    rows, meta = parse_export(RAW / 'adsets_daily_utf16.tsv')
    creative_rows, creative_meta = parse_export(RAW / 'creatives_daily_utf16.tsv')
    assert meta == creative_meta
    assert len({(r['Ad Set ID'], day(r['Start Date (in UTC)'])) for r in rows}) == len(rows)
    assert len({(r['Ad ID'], day(r['Start Date (in UTC)'])) for r in creative_rows}) == len(creative_rows)
    assert sums(rows) == sums(creative_rows)
    aggregate = sums(rows)
    controls = {'spend': 3328.98, 'impressions': 23206, 'clicks': 100, 'opens': 59, 'leads': 4}
    assert all(aggregate[k] == value for k, value in controls.items())
    result = read(DATA / 'ads.json')
    prior = json.loads(json.dumps(result))
    if not (RAW / 'prior_ads.json').exists():
        write(RAW / 'prior_ads.json', prior)
    source_date = datetime.fromisoformat(meta['generated']).astimezone(ZoneInfo('America/Denver')).date().isoformat()
    assert source_date == DATE
    result.update({'status': 'available', 'snapshotAt': DATE, 'preparedAt': DATE,
                   'collectedAt': meta['generated'], 'reportGeneratedAt': meta['generated'],
                   'refreshMode': 'manual_authenticated_export',
                   'coverage': {'start': '2026-09-04', 'end': '2026-10-16'},
                   'dateBasis': 'UTC daily reporting buckets from LinkedIn; not convertible to Mountain days without hourly data',
                   'daily': daily(rows)})
    campaign_map = {r['id']: r for r in result['campaigns']}
    assert set(campaign_map) == {r['Ad Set ID'] for r in rows}
    for id, campaign in campaign_map.items():
        group = [r for r in rows if r['Ad Set ID'] == id]
        latest = max(group, key=lambda r: day(r['Start Date (in UTC)']))
        campaign.update({**sums(group), 'daily': daily(group), 'name': latest['Ad Set Name'],
                         'objective': latest['Ad Set Objective'], 'statusAsOfExport': latest['Ad Set Status'],
                         'parentCampaignId': latest['Campaign ID']})
    result['totals'] = {'spend': aggregate['spend'], 'impressions': aggregate['impressions'],
                        'clicks': aggregate['clicks'], 'formOpens': aggregate['opens'],
                        'rawLeads': aggregate['leads'], 'qualifiedLeads': prior['totals']['qualifiedLeads'],
                        'videoViews': aggregate['videoViews'], 'videoCompletions': aggregate['videoCompletions']}
    result['creatives'] = []
    for id in sorted({r['Ad ID'] for r in creative_rows}):
        group = [r for r in creative_rows if r['Ad ID'] == id]
        latest = max(group, key=lambda r: day(r['Start Date (in UTC)']))
        result['creatives'].append({'id': id, 'name': latest['Ad Name'], 'adSetId': latest['Ad Set ID'],
                                    'campaignCode': campaign_map[latest['Ad Set ID']]['code'],
                                    'parentCampaignId': latest['Campaign ID'], 'objective': latest['Ad Set Objective'],
                                    'statusAsOfExport': latest['Ad Status'], **sums(group), 'daily': daily(group)})
    # Lead status is carried from owner confirmations; platform conversions never qualify a lead.
    assert len(result['leads']) == aggregate['leads'] == 4
    assert [r['company'] for r in result['leads'] if r['disposition'] == 'qualified_warm'] == ['NuVee']
    result['notes'] = [
        'Fresh authenticated export from account 515259390, generated October 17 at 00:51 UTC (October 16 Mountain), covering September 4–October 16 UTC.',
        'October 16 UTC has ended; October 16 Mountain remains in progress at collection. UTC daily buckets are preserved, and platform figures may restate.',
        'A–E are ad sets, displayed as campaign variants for continuity with the audit. E is configured for website visits despite its video-views name.',
        'The platform raw submission count remains four. Fresh lead-detail downloads are still blocked by Company Page / Lead Gen Forms permissions.',
        'Retained source exports contain four unique submission IDs; NuVee remains owner-qualified/warm, Venus Ai Consulting remains unqualified. No qualification or sales progress was inferred from the fresh ad export.',
        'One platform-reported appointment is not counted as a verified booked or held meeting. CRM / owner meeting confirmations remain separate.'
    ]
    result['review'] = {'checkedAt': DATE, 'sourceAsOf': meta['generated'],
                        'accountId': '515259390', 'rawAdSetRows': len(rows), 'rawCreativeRows': len(creative_rows),
                        'dailyBuckets': len(result['daily']), 'uniqueAdSets': len(result['campaigns']),
                        'uniqueAds': len(result['creatives']), 'latestCompleteUTCDate': '2026-10-16',
                        'currentMountainDateIncomplete': True,
                        'leadDetailAccess': {'status': 'permission_blocked', 'checkedAt': DATE,
                                            'reason': 'Company Page admin or Lead Gen Forms manager paid admin permission required.'},
                        'priorCoverageEnd': prior['coverage']['end'],
                        'changeSincePriorSnapshot': {key: round(result['totals'][key] - prior['totals'][key], 2)
                                                     for key in ['spend', 'impressions', 'clicks', 'formOpens', 'rawLeads']},
                        'checks': {'adsetCreativeTotalsAgree': True, 'dailyKeysUnique': True,
                                   'browserControlTotalsAgree': True, 'ownerDispositionsPreserved': True}}
    result['sources'] = [source(RAW / 'adsets_daily_utf16.tsv'), source(RAW / 'creatives_daily_utf16.tsv')]
    write(DATA / 'ads_refresh.json', result)
    return result


def public_number(text):
    match = re.fullmatch(r'[\s\u200b]*([\d,]+)[\s\u200b]*', text or '')
    return int(match.group(1).replace(',', '')) if match else None


def public_content():
    result = read(DATA / 'content.json')
    if not (RAW / 'prior_content.json').exists():
        write(RAW / 'prior_content.json', result)
    prior = result.get('publicObservations', {})
    company = read(RAW / 'company_recent_posts.json')
    personal = read(RAW / 'charles_public_posts.json')
    # Only the Charles-authored company reposts are used here; a company-original
    # container can include Charles in comments and is not therefore a Charles post.
    company_posts = []
    for row in company:
        if 'Centripetal Advisors reposted this' not in row['text'].split('Book an appointment')[0]:
            continue
        after = row['text'].split('Book an appointment\n', 1)[1]
        lines = [x.strip() for x in after.split('\n') if x.strip()]
        label, title = lines[0].split('•')[0].strip(), lines[1]
        values = {'reactions': None, 'comments': None, 'reposts': None}
        for item in row['labels']:
            if match := re.fullmatch(r'You and ([\d,]+) others', item):
                values['reactions'] = int(match.group(1).replace(',', '')) + 1
            elif match := re.fullmatch(r'([\d,]+) reactions?', item):
                values['reactions'] = int(match.group(1).replace(',', ''))
            elif match := re.match(r'([\d,]+) comments? on Charles Solomon', item):
                values['comments'] = int(match.group(1).replace(',', ''))
            elif match := re.match(r'([\d,]+) reposts? of Charles Solomon', item):
                values['reposts'] = int(match.group(1).replace(',', ''))
        company_posts.append({'url': f'https://www.linkedin.com/feed/update/{row["urn"]}/',
                               'account': 'Charles Solomon', 'distributedBy': 'Centripetal Advisors',
                               'kind': 'company_repost_of_charles_post', 'title': title,
                               'publishedAt': None, 'publishedRelativeLabel': label, 'observedAt': DATE,
                               **values, 'impressions': None, 'clicks': None, 'boosted': None})
    posts = []
    for index, row in enumerate(personal):
        paragraphs = row['paragraphs']
        label_index = next(i for i, x in enumerate(paragraphs) if re.fullmatch(r'\d+(?:h|d|w|mo)(?: • Edited)?', x))
        body = paragraphs[label_index+1]
        title = body.split('\n')[0].strip()
        values = {'reactions': None, 'comments': None, 'reposts': None}
        for b in row['buttons']:
            if (b['label'] or '').startswith('Reaction button state:'):
                values['reactions'] = public_number(b['text'])
            if b['label'] in ['Comment', 'Repost']:
                values['comments' if b['label'] == 'Comment' else 'reposts'] = public_number(b['text'])
        linked_article = next((x['href'] for x in row['links'] if '/pulse/' in x['href']), None)
        known = next((x for x in company_posts if x['title'][:100] == title[:100]), None)
        post = {'id': hashlib.sha256(title.encode()).hexdigest()[:16], 'url': known['url'] if known else linked_article,
                'urlKind': 'post' if known else ('linked_article' if linked_article else None),
                'sourceUrl': 'https://www.linkedin.com/in/solomoncharles/recent-activity/all/',
                'account': 'Charles Solomon', 'kind': 'charles_public_post', 'title': title,
                'publishedAt': None, 'publishedRelativeLabel': paragraphs[label_index], 'observedAt': DATE,
                **values, 'impressions': None, 'clicks': None, 'boosted': None}
        if known:
            post['distributedBy'] = 'Centripetal Advisors'
            for key in values:
                if post[key] is None:
                    post[key] = known[key]
        posts.append(post)
    for post in company_posts:
        if not any(x['url'] == post['url'] for x in posts):
            posts.append(post)
    result['publicObservations'] = {
        'checkedAt': DATE, 'sourceAsOf': DATE, 'status': 'current_public_only',
        'profiles': [{'name': 'Charles Solomon', 'url': 'https://www.linkedin.com/in/solomoncharles/',
                      'followers': 11486, 'checkedAt': DATE},
                     {'name': 'Centripetal Advisors', 'url': 'https://www.linkedin.com/company/centripetal-advisors/',
                      'followers': 867, 'checkedAt': DATE}],
        'posts': posts,
        'sample': {'charlesVisiblePostContainers': len(personal), 'companyCharlesRepostContainers': len(company_posts),
                   'uniqueDisplayedPosts': len(posts), 'completePublishingHistory': False,
                   'companyFeedSort': 'Recent', 'charlesFeedView': 'All activity / Posts'},
        'notes': [
            'Public visitor data checked October 16. Charles recent activity includes posts shown as 3h and 4h old at collection; company visitor feed was explicitly sorted Recent.',
            'The current authenticated account is Christian Wutz. Charles is a non-self profile and the company page is a visitor view; private impressions, reach, clicks and boosted breakdown are unavailable.',
            'Post engagement is a point-in-time public counter, not engagement occurring within a date-filtered reporting period.',
            'This visible post sample is incomplete. Relative publication labels are preserved; exact publication dates are not inferred.',
            'A missing counter is null, not zero. Public article URLs are distinguished from post permalinks; unavailable permalinks remain null.',
            'Charles posts reposted by the company are deduplicated by the observed underlying post where known. They must not contribute their engagement twice.',
            'Current public observations are separate from historical private analytics and do not refresh historical impressions or daily trends.'
        ]}
    result['accessReview'] = {'status': 'partial_public_only', 'checkedAt': DATE,
                              'reason': 'Current browser session is Christian Wutz; Charles is non-self and company page has visitor navigation, not analytics admin controls.',
                              'newestPrivateCharlesCoverageEnd': '2026-09-10',
                              'newestPrivateCompanyCoverageEnd': '2025-07-20',
                              'publicFollowers': {'Charles Solomon': 11486, 'Centripetal Advisors': 867}}
    result['review'] = {'checkedAt': DATE, 'privateContentSourceAsOf': result['snapshotAt'],
                        'publicContentSourceAsOf': DATE, 'newerPrivateExportFound': False,
                        'priorPublicObservationDate': prior.get('checkedAt'),
                        'netFollowerChangeSincePrior': {
                            p['name']: p['followers'] - next((v['followers'] for v in prior.get('profiles', []) if v['name'] == p['name']), p['followers'])
                            for p in result['publicObservations']['profiles']}}
    write(DATA / 'content_refresh.json', result)
    return result


def report(ads, content):
    totals = ads['totals']
    lines = [
        '# LinkedIn source refresh review — October 16, 2026', '',
        'Read-only collection is complete. This review prepares isolated refresh files; it does not apply or publish dashboard changes.', '',
        '## LinkedIn Ads', '',
        'Authenticated account: **515259390**, linked to Centripetal company page **66767979**. New ad-set and creative daily exports were generated **October 17 at 00:51 UTC / October 16 at 18:51 Mountain**.', '',
        '**Coverage: September 4–October 16, 2026, UTC.** October 16 UTC had ended at collection. October 16 Mountain was still in progress. Daily buckets retain the platform timezone; they cannot be accurately rebucketed into Mountain days without hourly data. Figures can restate.', '',
        f'**Totals:** ${totals["spend"]:,.2f} spent; {totals["impressions"]:,} impressions; {totals["clicks"]} clicks; {totals["formOpens"]} form opens; {totals["rawLeads"]} submissions; {totals["qualifiedLeads"]} owner-qualified lead.', '',
        '| Variant | Objective | Spend | Impressions | Clicks | Opens | Submissions |',
        '|---|---|---:|---:|---:|---:|---:|']
    for row in ads['campaigns']:
        lines.append(f'| {row["code"]} | {row["objective"]} | ${row["spend"]:,.2f} | {row["impressions"]:,} | {row["clicks"]} | {row["opens"]} | {row["leads"]} |')
    delta = ads['review']['changeSincePriorSnapshot']
    lines += ['', f'Compared with the retained October 14 snapshot: **+${delta["spend"]:,.2f} spend, +{delta["impressions"]:,.0f} impressions, {delta["clicks"]:+.0f} clicks, {delta["rawLeads"]:+.0f} submissions.**', '',
              'The two fresh exports agree on totals. They contain **106 ad-set daily rows, 107 creative daily rows, 43 calendar buckets, five delivered ad sets and six ads**; row keys are unique.', '',
              '**Lead quality:** NuVee remains qualified/warm and Venus Ai Consulting remains unqualified. No fresh qualification or meeting outcome is inferred from ad conversion counts. Fresh lead detail downloads remain blocked by LinkedIn Company Page / Lead Gen Forms manager permissions. Retained lead sources contain four unique submission IDs; the platform count remains four.', '',
              '## LinkedIn content', '',
              '**Current public followers:** Charles Solomon **11,486**; Centripetal company page **867**. These are net increases of **21** and **15** from the October 14 observations, not daily follower acquisition counts.', '',
              '**Fresh public content sample:** 20 visible Charles post containers and seven Charles posts reposted by the company. One known overlapping post is deduplicated, leaving 26 displayed post observations. New Charles activity includes today’s CAC/pro forma posts, shown as 3h and 4h old at collection. The company feed was sorted Recent.', '',
              'Public reaction, comment and repost counters are point-in-time observations. Missing counters remain null. Relative publication labels remain relative; publication dates are not invented. The sample does not establish total publishing cadence or period-specific engagement.', '',
              '**Private analytics remain historical:** latest verified Charles export covers September 11, 2025–September 10, 2026; company page export covers April 22–July 20, 2025. No newer private Charles/company content workbook was found in the inspected local sources. Current authenticated browser is Christian Wutz, so Charles renders as a non-self profile and the company page renders visitor controls. Current private impressions, reach, clicks and organic/boosted breakdown were unavailable.', '',
              '## Prepared files and application guidance', '',
              '- `data/ads_refresh.json`: updated campaign/ad daily metrics, objectives, source timing and reconciliation checks.',
              '- `data/content_refresh.json`: retains historical private analytics and adds separate October 16 public observations.',
              '- Raw downloads and browser evidence stay under `data/private/channels/2026-10-16/`; do not publish or commit raw exports.',
              '- Existing `ads.json`, `content.json`, application code and shared dashboard snapshot were not changed by this review.',
              '- Apply owner-confirmed held-call status in the CRM/meeting reconciliation step separately; the paid platform appointment column is not that confirmation.', '']
    expected = content['publicObservations']['sample']
    # Keep prose counts tied to the actual normalized sample.
    lines = [x.replace('seven Charles posts', f'{expected["companyCharlesRepostContainers"]} Charles posts')
              .replace('26 displayed', f'{expected["uniqueDisplayedPosts"]} displayed') for x in lines]
    (ROOT / 'LINKEDIN_REFRESH_2026-10-16.md').write_text('\n'.join(lines))


if __name__ == '__main__':
    RAW.mkdir(parents=True, exist_ok=True)
    ads = paid()
    content = public_content()
    report(ads, content)
    print(json.dumps({'adsTotals': ads['totals'], 'adRows': ads['review']['rawAdSetRows'],
                      'creativeRows': ads['review']['rawCreativeRows'], 'publicContent': content['publicObservations']['sample']}))
