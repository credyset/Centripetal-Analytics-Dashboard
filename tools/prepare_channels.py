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
    shutil.copyfile(path, target)
    return {'file': label, 'sha256': hashlib.sha256(target.read_bytes()).hexdigest()}


def write(name: str, data: dict):
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / name).write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')


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
    daily_file = AUDIT / 'LinkedIn/Current_Daily/account_515259390_campaign_performance_report (2).csv'
    lead_file = AUDIT / 'Analysis/lead_dispositions.csv'
    text = daily_file.read_text(encoding='utf-16')
    header = text.index('Start Date (in UTC)\t')
    rows = list(csv.DictReader(io.StringIO(text[header:]), delimiter='\t'))
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
    for code, row in zip('ABCDE', metrics['performance']):
        qualified = sum(1 for lead in leads if lead['campaign'] == code and lead['disposition'] == 'qualified_warm')
        campaigns.append({'id': row['ad_set_id'], 'code': code, 'name': row['name'],
                          'spend': row['Total Spent'], 'impressions': integer(row['Impressions']),
                          'clicks': integer(row['Clicks']), 'opens': integer(row['Lead Forms Opened']),
                          'leads': integer(row['Leads']), 'qualified': qualified,
                          'objective': row['objective'], 'statusAsOfExport': row['status'],
                          'videoViews': integer(row['Video Views']),
                          'videoCompletions': integer(row['Video Completions']),
                          'platformAppointmentsReported': integer(row['Appointments Booked']),
                          'daily': sorted(campaign_daily[row['ad_set_id']], key=lambda x: x['date'])})
    totals = {'spend': 3056.57, 'impressions': 21050, 'clicks': 94, 'formOpens': 57,
              'rawLeads': 4, 'qualifiedLeads': 1, 'videoViews': 8973, 'videoCompletions': 336}
    daily_rows = [{'date': date, **{k: round(v, 2) if k == 'spend' else v for k, v in values.items()}}
                  for date, values in sorted(daily.items())]
    assert round(sum(x['spend'] for x in daily_rows), 2) == totals['spend']
    for field, total_field in [('impressions', 'impressions'), ('clicks', 'clicks'), ('opens', 'formOpens'), ('leads', 'rawLeads')]:
        assert sum(x[field] for x in daily_rows) == totals[total_field]
    assert len(leads) == totals['rawLeads']
    assert sum(x['qualified'] for x in campaigns) == totals['qualifiedLeads']
    data = {'status': 'available', 'snapshotAt': '2026-10-13', 'preparedAt': PREPARED,
            'coverage': {'start': '2026-09-04', 'end': '2026-10-12'},
            'dateBasis': 'UTC day buckets supplied by LinkedIn; not rebucketed into Mountain days',
            'totals': totals, 'campaigns': campaigns, 'daily': daily_rows,
            'leads': sorted(leads, key=lambda x: x['date']),
            'notes': ['Historical audited baseline; current campaign delivery after October 12 is not included.',
                      'A–E are ad sets, displayed as campaign variants for continuity with the audit.',
                      'NuVee is the only owner-confirmed qualified lead and is warm. Qualification confirmation was supplied October 13; meeting status and progress dates are unconfirmed.',
                      'One platform-reported appointment is not treated as a verified booked or held call.',
                      'Campaign E is configured for website visits despite its video-views name.'],
            'sources': [copy_source(metrics_file, 'ads_validated_metrics.json'),
                        copy_source(daily_file, 'ads_daily_utf16.tsv'),
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
    write('content.json', data)


if __name__ == '__main__':
    ads()
    waalaxy()
    content()
    print('Prepared ads.json, waalaxy.json, content.json from source exports.')
