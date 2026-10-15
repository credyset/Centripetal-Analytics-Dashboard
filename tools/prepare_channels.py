"""Prepare read-only source exports for the local dashboard; no network access."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import shutil
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
CENTRIPETAL = ROOT.parent
AUDIT = CENTRIPETAL / 'LinkedIn Ads/LinkedIn_GA4_Deep_Dive_2026-10-12'
DATA = ROOT / 'data'
PRIVATE = DATA / 'private/channels'
DOWNLOADS = Path('/Users/christianwutz/Downloads')
PREPARED = '2026-10-14'


def copy_source(path: Path, label: str) -> dict:
    target = PRIVATE / label
    target.parent.mkdir(parents=True, exist_ok=True)
    if path.resolve() != target.resolve():
        shutil.copyfile(path, target)
    return {'file': label, 'sha256': hashlib.sha256(target.read_bytes()).hexdigest()}


def write(name: str, data: dict):
    DATA.mkdir(parents=True, exist_ok=True)
    target = DATA / name
    rendered = json.dumps(data, indent=2, ensure_ascii=False) + '\n'
    if target.exists() and target.read_text() != rendered:
        history = PRIVATE / 'history'
        history.mkdir(parents=True, exist_ok=True)
        old_hash = hashlib.sha256(target.read_bytes()).hexdigest()[:12]
        shutil.copyfile(target, history / f'{target.stem}_{old_hash}.json')
    target.write_text(rendered)


def number(value):
    if value is None or str(value).strip() == '':
        return None
    return float(str(value).replace(',', ''))


def integer(value):
    result = number(value)
    return int(result) if result is not None else None


def day(value):
    if isinstance(value, datetime):
        return value.date().isoformat()
    if not value:
        return None
    for fmt in ['%m/%d/%Y', '%b %d, %Y', '%Y-%m-%d']:
        try:
            return datetime.strptime(str(value), fmt).date().isoformat()
        except ValueError:
            pass
    raise ValueError(f'Unexpected date: {value}')


def ads():
    metrics_file = AUDIT / 'Analysis/validated_metrics.json'
    metrics = json.loads(metrics_file.read_text())
    fresh_file = PRIVATE / 'ads_daily_2026-10-14_utf16.tsv'
    daily_file = fresh_file if fresh_file.exists() else AUDIT / 'LinkedIn/Current_Daily/account_515259390_campaign_performance_report (2).csv'
    access = json.loads((DATA / 'channel_access_review.json').read_text()) if (DATA / 'channel_access_review.json').exists() else {}
    lead_file = AUDIT / 'Analysis/lead_dispositions.csv'
    text = daily_file.read_text(encoding='utf-16')
    header = text.index('Start Date (in UTC)\t')
    rows = list(csv.DictReader(io.StringIO(text[header:]), delimiter='\t'))
    expected_ids = {x['ad_set_id'] for x in metrics['performance']}
    assert {x['Ad Set ID'] for x in rows} == expected_ids
    assert all('Centripetal' in x['Account Name'] and x['Currency'] == 'USD' for x in rows)
    daily = defaultdict(lambda: {'spend': 0, 'impressions': 0, 'clicks': 0, 'opens': 0, 'leads': 0})
    campaign_daily = defaultdict(list)
    for row in rows:
        date = day(row['Start Date (in UTC)'])
        item = {'date': date, 'spend': number(row['Total Spent']),
                'impressions': integer(row['Impressions']), 'clicks': integer(row['Clicks']),
                'opens': integer(row['Lead Forms Opened']), 'leads': integer(row['Leads'])}
        for key in ['spend', 'impressions', 'clicks', 'opens', 'leads']:
            daily[date][key] += item[key]
        campaign_daily[row['Ad Set ID']].append(item)
    leads = []
    with lead_file.open() as handle:
        lead_rows = list(csv.DictReader(handle))
    for row in lead_rows:
        leads.append({'date': row['submission_date'], 'company': row['company'],
                      'disposition': row['disposition'],
                      'campaign': 'D' if row['ad_set_id'] == '891464353' else 'C',
                      'qualificationAsOf': row['disposition_as_of'],
                      'meetingBooked': None, 'meetingHeld': None})
    campaigns = []
    metric_map = {'Total Spent': 'spend', 'Impressions': 'impressions', 'Clicks': 'clicks',
                  'Lead Forms Opened': 'opens', 'Leads': 'leads', 'Video Views': 'videoViews',
                  'Video Completions': 'videoCompletions', 'Appointments Booked': 'platformAppointmentsReported'}
    for code, row in zip('ABCDE', metrics['performance']):
        source_rows = [x for x in rows if x['Ad Set ID'] == row['ad_set_id']]
        latest = max(source_rows, key=lambda x: day(x['Start Date (in UTC)']))
        aggregated = {out: round(sum(number(x[field]) or 0 for x in source_rows), 2) for field, out in metric_map.items()}
        qualified = sum(1 for lead in leads if lead['campaign'] == code and lead['disposition'] == 'qualified_warm')
        campaigns.append({'id': row['ad_set_id'], 'code': code, 'name': latest['Ad Set Name'],
                          **aggregated, 'qualified': qualified,
                          'objective': latest['Ad Set Objective'], 'statusAsOfExport': latest['Ad Set Status'],
                          'daily': sorted(campaign_daily[row['ad_set_id']], key=lambda x: x['date'])})
    totals = {key: round(sum(x[source_key] for x in campaigns), 2) for key, source_key in
              [('spend', 'spend'), ('impressions', 'impressions'), ('clicks', 'clicks'),
               ('formOpens', 'opens'), ('rawLeads', 'leads'), ('videoViews', 'videoViews'), ('videoCompletions', 'videoCompletions')]}
    totals['qualifiedLeads'] = sum(x['qualified'] for x in campaigns)
    daily_rows = [{'date': date, **{k: round(v, 2) if k == 'spend' else v for k, v in values.items()}}
                  for date, values in sorted(daily.items())]
    assert round(sum(x['spend'] for x in daily_rows), 2) == totals['spend']
    for field, total_field in [('impressions', 'impressions'), ('clicks', 'clicks'), ('opens', 'formOpens'), ('leads', 'rawLeads')]:
        assert sum(x[field] for x in daily_rows) == totals[total_field]
    assert len(leads) <= totals['rawLeads']
    assert sum(x['qualified'] for x in campaigns) == totals['qualifiedLeads']
    if fresh_file.exists():
        for key, expected in access['paid']['browserControlTotals'].items():
            assert totals[key] == expected, (key, totals[key], expected)
    data = {'status': 'available', 'snapshotAt': '2026-10-14' if fresh_file.exists() else '2026-10-13', 'preparedAt': PREPARED,
            'collectedAt': access.get('paid', {}).get('collectedAt') if fresh_file.exists() else None,
            'reportGeneratedAt': access.get('paid', {}).get('reportGeneratedAt') if fresh_file.exists() else None,
            'refreshMode': 'manual_authenticated_export',
            'coverage': {'start': min(daily), 'end': max(daily)},
            'dateBasis': 'UTC day buckets supplied by LinkedIn; not rebucketed into Mountain days',
            'totals': totals, 'campaigns': campaigns, 'daily': daily_rows,
            'leads': sorted(leads, key=lambda x: x['date']),
            'notes': [('Fresh authenticated Campaign Manager export collected October 14, 2026; coverage through October 14 UTC. Figures may restate after export.' if fresh_file.exists() else 'Historical audited baseline; current campaign delivery after October 12 is not included.'),
                      'Paid metrics retain LinkedIn UTC day buckets. They cannot be converted accurately to the dashboard’s Mountain days without hourly data; October 14 Mountain is still in progress at collection.',
                      'A–E are ad sets, displayed as campaign variants for continuity with the audit.',
                      'NuVee is the only owner-confirmed qualified lead and is warm. Qualification confirmation was supplied October 13; meeting status and progress dates are unconfirmed.',
                      'One platform-reported appointment is not treated as a verified booked or held call.',
                      'Fresh lead detail downloads are blocked by LinkedIn Company Page/Lead Gen Forms permissions. The fresh raw count remains four; existing owner dispositions are retained without inferred new qualifications.',
                      'Campaign E is configured for website visits despite its video-views name.'],
            'sources': [copy_source(metrics_file, 'ads_validated_metrics.json'),
                        copy_source(daily_file, 'ads_daily_2026-10-14_utf16.tsv' if fresh_file.exists() else 'ads_daily_utf16.tsv'),
                        copy_source(lead_file, 'ads_lead_dispositions.csv')]}
    write('ads.json', data)


def waalaxy():
    source = CENTRIPETAL / 'data/charles_all_prospects_jul2026.csv'
    with source.open(encoding='utf-8-sig') as handle:
        rows = list(csv.DictReader(handle))
    people = defaultdict(list)
    for row in rows:
        key = row['linkedinUrl'].strip().rstrip('/').lower()
        assert key
        people[key].append(row)
    metric_fields = {'messageRecipients': ('messageSent', 'Yes'), 'replyingProspects': ('messageReplied', 'Yes'),
                     'connectedProspects': ('profileStatus', 'connected'), 'pendingProspects': ('profileStatus', 'pending')}
    totals = {'uniqueProspects': len(people), 'exportRows': len(rows), 'duplicateRows': len(rows) - len(people)}
    for name, (field, value) in metric_fields.items():
        totals[name] = sum(any(r[field] == value for r in records) for records in people.values())
    totals['connectionRequestedProspects'] = sum(any(r['connectionRequestDate'] for r in records) for records in people.values())
    daily = defaultdict(Counter)
    list_members = defaultdict(list)
    for records in people.values():
        for field, out in [('importDate', 'prospectsImported'), ('connectionRequestDate', 'connectionRequestsFirstRecorded'),
                           ('connectedAt', 'connectionsRecorded'), ('firstMessageAt', 'firstMessageRecipients'),
                           ('lastLinkedinReplyDate', 'lastReplyingProspects')]:
            dates = [r[field] for r in records if r[field]]
            if dates:
                date = max(dates) if 'last' in field else min(dates)
                daily[date][out] += 1
        for list_name in {r['prospectList'] for r in records}:
            list_members[list_name].append(records)
    lists = []
    for name, members in list_members.items():
        lists.append({'name': name, 'prospects': len(members),
                      'messageRecipients': sum(any(r['messageSent'] == 'Yes' for r in records) for records in members),
                      'replyingProspects': sum(any(r['messageReplied'] == 'Yes' for r in records) for records in members)})
    data = {'status': 'historical', 'account': 'Charles Solomon', 'snapshotAt': '2026-07-06', 'preparedAt': PREPARED,
            'coverage': {'start': min(daily), 'end': max(daily)}, 'dateBasis': 'Export contains date-only fields; timezone not supplied',
            'metrics': totals, 'daily': [{'date': date, **counts} for date, counts in sorted(daily.items())],
            'lists': sorted(lists, key=lambda x: -x['prospects']), 'campaigns': [],
            'notes': ['Historical Charles export from July 6, 2026; no current Charles workspace was accessible during concept collection.',
                      'Metrics count unique prospect profiles by normalized LinkedIn URL. Four duplicate rows were merged with logical OR for status flags.',
                      'Message recipients and replying prospects are people with Yes flags, not total messages or replies.',
                      'Reply dates are the last recorded reply for each person; they do not form a complete reply-event history.',
                      'Prospect lists are not campaign histories. No current campaign-level sending totals or positive-reply classifications are available.',
                      'Recent Downloads exports could not be verified as Charles’s account and were excluded. Jess is excluded.'],
            'sources': [copy_source(source, 'charles_all_prospects_jul2026.csv')]}
    review_file = DATA / 'channel_access_review.json'
    if review_file.exists():
        data['accessReview'] = json.loads(review_file.read_text())['waalaxy']
    write('waalaxy.json', data)


def content():
    charles_file = DOWNLOADS / 'AggregateAnalytics_Charles Solomon_2025-09-11_2026-09-10.xlsx'
    company_file = CENTRIPETAL / 'source_materials/DriveDownload_3.19.26/Analytics/Page Analytics/CA_PAGE_content_1753211803952.xlsx'
    personal = openpyxl.load_workbook(charles_file, data_only=True, read_only=True)
    discovery = dict(personal['DISCOVERY'].values)
    daily = [{'date': day(row[0]), 'account': 'Charles Solomon', 'impressions': integer(row[1]),
              'engagements': integer(row[2])} for row in list(personal['ENGAGEMENT'].values)[1:] if row[0]]
    follower_rows = list(personal['FOLLOWERS'].values)
    followers = integer(follower_rows[0][1])
    followers_daily = [{'date': day(row[0]), 'newFollowers': integer(row[1]), 'account': 'Charles Solomon'}
                       for row in follower_rows[3:] if row[0]]
    posts = {}
    for row in list(personal['TOP POSTS'].values)[3:]:
        for offset, metric in [(0, 'engagements'), (4, 'impressions')]:
            if not row[offset]:
                continue
            url = row[offset]
            post = posts.setdefault(url, {'date': day(row[offset+1]), 'title': None, 'url': url,
                                         'account': 'Charles Solomon', 'impressions': None, 'engagements': None,
                                         'reactions': None, 'comments': None, 'reposts': None, 'clicks': None,
                                         'views': None, 'boosted': None, 'scope': 'top_posts_in_reporting_window',
                                         'metricCoverage': {'start': '2025-09-11', 'end': '2026-09-10'}})
            post[metric] = integer(row[offset+2])
    page = openpyxl.load_workbook(company_file, data_only=True, read_only=True)
    post_rows = list(page['All posts'].values)
    headers = post_rows[1]
    for row in post_rows[2:]:
        values = dict(zip(headers, row))
        if not values.get('Post link'):
            continue
        posts[values['Post link']] = {'date': day(values['Created date']), 'title': values['Post title'],
                                     'url': values['Post link'], 'account': 'Centripetal Advisors',
                                     'impressions': integer(values['Impressions']), 'reactions': integer(values['Likes']),
                                     'comments': integer(values['Comments']), 'reposts': integer(values['Reposts']),
                                     'clicks': integer(values['Clicks']), 'views': integer(values['Views']),
                                     'boosted': False if values['Post type'] == 'Organic' else None,
                                     'scope': 'company_page_export',
                                     'metricCoverage': {'start': '2025-04-22', 'end': '2025-07-20'}}
    page_daily_rows = list(page['Metrics'].values)
    page_headers = page_daily_rows[1]
    for row in page_daily_rows[2:]:
        values = dict(zip(page_headers, row))
        if not values.get('Date'):
            continue
        daily.append({'date': day(values['Date']), 'account': 'Centripetal Advisors',
                      'impressions': integer(values['Impressions (total)']),
                      'organicImpressions': integer(values['Impressions (organic)']),
                      'sponsoredImpressions': integer(values['Impressions (sponsored)']),
                      'clicks': integer(values['Clicks (total)']),
                      'reactions': integer(values['Reactions (total)']),
                      'comments': integer(values['Comments (total)']), 'reposts': integer(values['Reposts (total)'])})
    page_dates = [x['date'] for x in daily if x['account'] == 'Centripetal Advisors']
    page_coverage = {'start': min(page_dates), 'end': max(page_dates)}
    for post in posts.values():
        if post['account'] == 'Centripetal Advisors':
            post['metricCoverage'] = page_coverage
    assert sum(row['impressions'] for row in daily if row['account'] == 'Charles Solomon') == integer(discovery['Impressions'])
    data = {'status': 'historical', 'snapshotAt': '2026-09-11', 'preparedAt': PREPARED,
            'coverage': {'start': min(x['date'] for x in daily), 'end': max(x['date'] for x in daily)},
            'dateBasis': 'LinkedIn export dates; company page dates are UTC, personal export timezone unspecified',
            'accounts': [{'name': 'Charles Solomon', 'coverage': {'start': '2025-09-11', 'end': '2026-09-10'},
                          'impressions': integer(discovery['Impressions']), 'membersReached': integer(discovery['Members reached']),
                          'engagements': sum(x.get('engagements', 0) for x in daily if x['account'] == 'Charles Solomon'),
                          'followers': followers, 'followersAsOf': '2026-09-10',
                          'newFollowers': sum(x['newFollowers'] for x in followers_daily)},
                         {'name': 'Centripetal Advisors', 'coverage': page_coverage,
                          'impressions': sum(x['impressions'] for x in daily if x['account'] == 'Centripetal Advisors'),
                          'clicks': sum(x.get('clicks', 0) for x in daily if x['account'] == 'Centripetal Advisors')}],
            'posts': sorted(posts.values(), key=lambda x: x['date'], reverse=True),
            'daily': sorted(daily, key=lambda x: (x['date'], x['account'])), 'followersDaily': followers_daily,
            'notes': ['Charles’s latest on-disk aggregate covers September 11, 2025–September 10, 2026. Company page content covers April–July 2025. Neither is current October performance.',
                      'Charles’s post rows combine top engagement and top impression rankings; the export is not an exhaustive publishing log.',
                      'Null values mean unavailable. Personal post titles and per-post clicks, reactions and video views were not supplied in this aggregate export.',
                      'Personal ranking metrics are measured within the export reporting window; publication dates do not turn them into lifetime metrics.',
                      'No current boosted-post analytics have been collected. Unknown boosted status stays unknown, and paid spend must not be added twice.',
                      'Daily exposure can include older posts. Daily impressions do not measure posts published.',
                      'Current Charles/profile and company admin analytics were unavailable through the authenticated browser account during concept collection.'],
            'sources': [copy_source(charles_file, 'charles_aggregate_2025-09-11_2026-09-10.xlsx'),
                        copy_source(company_file, 'company_content_2025.xlsx')]}
    public_file = PRIVATE / 'public_observations_2026-10-14.json'
    if public_file.exists():
        data['publicObservations'] = json.loads(public_file.read_text())
    review_file = DATA / 'channel_access_review.json'
    if review_file.exists():
        data['accessReview'] = json.loads(review_file.read_text())['organic']
    write('content.json', data)


if __name__ == '__main__':
    ads()
    waalaxy()
    content()
    print('Prepared ads.json, waalaxy.json, content.json from source exports.')
