"""Prepare local-only referral inventory and historical website evidence.

These are full snapshots/full exported periods. They must not be filtered as
period activity or added to the five channel outcome totals.
"""
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
import csv
import hashlib
import io
import json
import re
import shutil
from urllib.parse import urlsplit
import openpyxl

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT.parent / 'LinkedIn Ads' / 'LinkedIn_GA4_Deep_Dive_2026-10-12'
PRIVATE = ROOT / 'data' / 'private'


def evidence(path):
    try:
        label = str(path.relative_to(ROOT.parent))
    except ValueError:
        label = str(path.relative_to(ROOT.parents[1]))
    return {'path': label,
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def ga4_export(path):
    text = path.read_text(encoding='utf-8-sig')
    def date(label):
        raw = next(line.split(':', 1)[1].strip() for line in text.splitlines()
                   if line.startswith('# ' + label + ':'))
        return datetime.strptime(raw, '%Y%m%d').date().isoformat()
    rows = list(csv.DictReader(io.StringIO('\n'.join(
        line for line in text.splitlines() if line and not line.startswith('#')))))
    return {'start': date('Start date'), 'end': date('End date'), 'rows': rows}


def metric(value, label, basis, note=''):
    return {'value': value, 'label': label, 'basis': basis, 'note': note}


def newsletter():
    handoff = ROOT.parents[1] / 'outputs' / '01a0c61a-a3f0-77b2-9a8a-e86cde0350df' / 'newsletter_dashboard_source_handoff_2026-10-14.md'
    text = handoff.read_text()
    def count(label):
        found = re.search(r'^\| ' + re.escape(label) + r' \| ([\d,]+) \|', text, re.M)
        assert found, f'Newsletter source missing {label}'
        return int(found.group(1).replace(',', ''))
    metrics = {key: count(label) for key, label in {
        'delivered': 'Successfully delivered', 'uniqueOpens': 'Unique opens',
        'totalOpens': 'Total opens', 'uniqueClickers': 'Unique clicks',
        'totalClicks': 'Total clicks', 'bounced': 'Bounced',
        'unsubscribed': 'Unsubscribed', 'spam': 'Spam', 'notSent': 'Not sent'}.items()}
    warning = 'Sender linked to this campaign was deleted; Pipedrive says the campaign is not being sent.'
    assert 'sender linked to this campaign has been deleted' in text
    snapshot = {'retrievedDate': '2026-10-14', 'retrievalTimezone': 'America/Denver',
                'sourceUrl': 'https://centripetaladvisors.pipedrive.com/marketing/automated-campaigns/3',
                'campaignId': 3, 'campaignName': 'Newsletter 3.0',
                'campaignState': 'Active', 'senderWarning': warning,
                'coverage': 'Cumulative campaign history through retrieval; platform does not expose distinct data-through timestamp.',
                'basis': 'cumulative', 'metrics': metrics, 'provenance': evidence(handoff)}
    (PRIVATE / 'newsletter_campaign3_snapshot.json').write_text(json.dumps(snapshot, indent=2) + '\n')
    return {'id': 'newsletter', 'name': 'Email / newsletter', 'kind': 'acquisition',
            'scope': 'Pipedrive automated campaign 3, Newsletter 3.0; team live read-only handoff.',
            'asOf': '2026-10-14', 'coverage': snapshot['coverage'], 'status': 'Current snapshot · sending stopped',
            'basis': 'cumulative', 'dateFilterable': False, 'warning': warning,
            'alert': 'Newsletter sending is stopped: Pipedrive reports the linked sender was deleted. Restore the sender/automation and verify delivery.',
            'activity': [metric(metrics['delivered'], 'Delivered messages', 'cumulative', warning),
                         metric(metrics['bounced'], 'Bounced messages', 'cumulative', 'Count only; no unsupported bounce-rate denominator.')],
            'responses': [metric(metrics['uniqueOpens'], 'Unique openers', 'cumulative', 'Recipient count; privacy protection limits open precision.'),
                          metric(metrics['uniqueClickers'], 'Unique clickers', 'cumulative', 'Recipients, not total clicks; may overlap openers and unsubscribers.')],
            'outcomes': [metric(None, 'Newsletter-sourced opportunities', 'unverified', 'Recipient-to-CRM linkage and source evidence are required.'),
                         metric(metrics['unsubscribed'], 'Unsubscribed recipients', 'cumulative', 'List-health outcome; not sales conversion.')],
            'nextStep': 'Repair the deleted sender and verify the welcome automation before assuming ongoing delivery; retain dated campaign snapshots.',
            'href': 'sources', 'sourceUrl': snapshot['sourceUrl'], 'metrics': metrics,
            'rates': {'openRate': metrics['uniqueOpens'] / metrics['delivered'],
                      'clickRate': metrics['uniqueClickers'] / metrics['delivered'],
                      'clickToOpenRate': metrics['uniqueClickers'] / metrics['uniqueOpens']},
            'provenance': [evidence(handoff)],
            'notes': ['Cumulative engagement is not selected-date sends. Do not sum opens, clicks or recipient states into unique reach.',
                      'Pipedrive labels unique clickers / unique openers click-through rate; dashboard uses click-to-open rate.',
                      'Account subscriber-capacity badge is not this campaign audience size.']}


def normalized_profile(value):
    if not value:
        return None
    value = str(value).strip()
    parts = urlsplit(value if '://' in value else 'https://' + value)
    host = (parts.hostname or '').lower().removeprefix('www.')
    if host.endswith('linkedin.com'):
        host = 'linkedin.com'
    return host + parts.path.rstrip('/').lower()


def pulley():
    path = ROOT.parent / 'Centripetal_Pulley_Contact_Research_2026-10-14_connected.xlsx'
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    raw = list(wb['Contact Research'].values)
    rows = [dict(zip(raw[0], r)) for r in raw[1:] if r[0]]
    priority_raw = list(wb['Charles Video Priority'].values)
    priority = [dict(zip(priority_raw[0], r)) for r in priority_raw[1:] if r[0]]
    urls = {normalized_profile(r['linkedin_url']) for r in rows}
    assert None not in urls and len(urls) == len(rows), 'Pulley contact profiles must be unique'
    assert {normalized_profile(r['linkedin_url']) for r in priority} <= urls, 'Priority list must be a subset'
    video = json.loads((ROOT / 'data' / 'video.json').read_text())
    video_urls = {normalized_profile(r['linkedin']) for r in video['rows'] if r.get('linkedin')}
    connected = Counter(r['linkedin_connection_status'] or 'Not connected in supplied export' for r in rows)
    status = Counter(r['video_dm_status'] for r in rows)
    counts = {'contacts': len(rows), 'companies': len({r['universe_id'] for r in rows}),
              'connected': connected['Connected'], 'readyForVideo': status['Ready for Video DM'],
              'notConnectedInExport': status['Not connected in supplied export'],
              'companyMismatchHolds': status['Hold — current company mismatch / legacy'],
              'priorActivityHolds': status['Hold — prior LinkedIn activity'],
              'prioritySubset': len(priority), 'overlappingVideoProfiles': len(urls & video_urls)}
    wb.close()
    return {'id': 'pulley', 'name': 'Target research / Pulley', 'kind': 'support',
            'scope': 'Connected Pulley contact-research workbook; company research and video-ready queue, not sending activity.',
            'asOf': '2026-10-14', 'coverage': 'Current research workbook inventory',
            'status': 'Current research snapshot', 'basis': 'snapshot', 'dateFilterable': False,
            'activity': [metric(counts['contacts'], 'Researched contacts', 'snapshot', f"Across {counts['companies']} company universe IDs; not qualified opportunities."),
                         metric(counts['prioritySubset'], 'Priority subset', 'snapshot', 'Included in the researched contacts; do not add to total.')],
            'responses': [metric(counts['connected'], 'Connected in supplied export', 'snapshot', 'Connection status, not new acceptances in selected dates.'),
                          metric(counts['readyForVideo'], 'Ready for Video DM', 'snapshot', 'Preparation status; no DM send is established.')],
            'outcomes': [metric(None, 'Verified sends / qualified outcomes', 'unverified', 'No actual sends, replies, bookings or qualified outcomes supplied.')],
            'nextStep': f"Review {counts['companyMismatchHolds']} company-mismatch holds and {counts['priorActivityHolds']} prior-activity holds; reconcile existing Video DM profiles before sending.",
            'href': 'video', 'metrics': counts,
            'sourceUrl': 'https://drive.google.com/file/d/1eui4Gik_6z08ssg_f--QXONYa8wB8gdn/view',
            'provenance': [evidence(path), evidence(ROOT / 'data' / 'video.json')],
            'notes': [f"{counts['notConnectedInExport']} contacts are not connected in the supplied export; {counts['overlappingVideoProfiles']} normalized LinkedIn profiles overlap the current Video DM sheet.",
                      'The priority tab is a subset of Contact Research. Research, connections and readiness are not sent messages or qualified leads.']}


def build():
    crm_path = ROOT / 'data' / 'crm.json'
    crm = json.loads(crm_path.read_text())
    assert crm['coverage']['dealsComplete'], 'Referral inventory requires complete paginated deals'
    referral_ids = {p['id'] for p in crm['pipelines'] if p['name'] == 'Referral Pipeline'}
    assert referral_ids == {4}, 'Review referral pipeline definition if configuration changes'
    referrals = [d for d in crm['deals'] if d['pipelineId'] in referral_ids
                 and not d['isTest'] and d['status'] == 'open']
    stages = Counter(d['stageId'] for d in referrals)
    stage_names = {s['id']: s['name'] for s in crm['stages']}
    for stage_id, name in {28: 'Intro Promised', 29: 'Intro Made',
                           31: 'Opportunity ( Referred )', 38: 'Office Hours'}.items():
        assert stage_names[stage_id] == name, 'Review changed stage meaning'
    snapshot_note = 'Current open non-test CRM records; not new activity during the selected dates.'
    referral_vector = {
        'id': 'referrals', 'name': 'Referrals & partners', 'kind': 'acquisition',
        'scope': 'All accessible, open non-test records in Pipedrive Referral Pipeline; all owners.',
        'asOf': crm['snapshotAt'], 'coverage': 'Current stage inventory',
        'status': 'Current snapshot', 'basis': 'snapshot', 'dateFilterable': False,
        'activity': [
            metric(len(referrals), 'Open referral-pipeline records', 'snapshot', snapshot_note),
            metric(stages[26] + stages[39] + stages[42], 'Circle / Inner Circle / Amigos', 'snapshot', snapshot_note),
            metric(stages[38], 'Office Hours records', 'snapshot', 'Inventory only; not completed office-hours meetings.')],
        'responses': [
            metric(stages[28], 'At Intro Promised', 'snapshot', snapshot_note),
            metric(stages[29], 'At Intro Made', 'snapshot', snapshot_note)],
        'outcomes': [
            metric(stages[31], 'At Opportunity (Referred)', 'snapshot',
                   'Current stage label; not independently verified accepted opportunities or newly referred deals.'),
            metric(None, 'Referral-sourced wins', 'unverified',
                   'Source linkage and won-history verification are needed.')],
        'nextStep': 'Record referral source, introduction dates and linked sales deal; retain stage history.',
        'href': 'crm', 'provenance': [evidence(crm_path)],
        'stageInventory': [{'stageId': i, 'stage': stage_names[i], 'count': n}
                           for i, n in sorted(stages.items())],
        'excludedTestRecords': sum(d['isTest'] for d in crm['deals'] if d['pipelineId'] in referral_ids),
    }

    validated_path = AUDIT / 'Analysis' / 'validated_metrics.json'
    validated = json.loads(validated_path.read_text())
    periods = []
    provenance = [evidence(validated_path)]
    PRIVATE.mkdir(parents=True, exist_ok=True)
    for key, local in [('GA4/Campaign_Period/', 'ga4_campaign_traffic.csv'),
                       ('GA4/Last_90_Days/', 'ga4_90d_traffic.csv')]:
        record = validated['ga4'][key]
        source = AUDIT / record['canonical']
        export = ga4_export(source)
        measures = {'sessions': 'Sessions', 'engaged_sessions': 'Engaged sessions',
                    'events': 'Event count', 'key_events': 'Key events'}
        totals = {k: sum(float(r[col]) for r in export['rows']) for k, col in measures.items()}
        assert all(totals[k] == record[k] for k in measures), 'GA4 export must reconcile with completed audit'
        periods.append({'start': export['start'], 'end': export['end'], 'basis': 'historical',
                        'dateFilterable': False, **{k: int(v) for k, v in totals.items()},
                        'engagement_rate': record['engagement_rate'],
                        'sourceRows': [{'sourceMedium': r['Session source / medium'],
                                        'sessions': int(r['Sessions']),
                                        'engagedSessions': int(r['Engaged sessions'])}
                                       for r in export['rows']],
                        'source': str(source.relative_to(ROOT.parent))})
        shutil.copyfile(source, PRIVATE / local)
        provenance.append(evidence(source))
    current = periods[0]
    event_path = AUDIT / 'GA4' / 'Campaign_Period' / 'Events_Event_name (3).csv'
    events = ga4_export(event_path)
    assert events['start'] == current['start'] and events['end'] == current['end']
    form_starts = sum(int(r['Event count']) for r in events['rows'] if r['Event name'] == 'form_start')
    shutil.copyfile(event_path, PRIVATE / 'ga4_campaign_events.csv')
    provenance.append(evidence(event_path))
    website_handoff = ROOT.parent / 'site-concept-research' / 'analytics-handoff-20261014' / 'website-inbound-evidence.json'
    website_meta = json.loads(website_handoff.read_text())
    for p, meta in zip(periods, website_meta['website_periods']):
        assert p['start'].replace('-', '') == meta['period_start']
        assert p['end'].replace('-', '') == meta['period_end']
        assert p['sessions'] == meta['sessions']
        assert next(x['sha256'] for x in provenance if x['path'] == p['source']) == meta['sha256']
        p['sourceTimezone'] = meta['source_timezone']
        p['collectedDate'] = meta['collected_date']
    provenance.append(evidence(website_handoff))
    website_vector = {
        'id': 'website', 'name': 'Website & inbound', 'kind': 'acquisition',
        'scope': 'Centripetal Advisors GA4 property, All Users; retained completed audit exports.',
        'asOf': current['collectedDate'], 'coverage': f"{current['start']}–{current['end']} · America/New_York",
        'sourceTimezone': current['sourceTimezone'], 'reportingThrough': current['end'],
        'status': 'Historical audited export', 'basis': 'historical', 'dateFilterable': False,
        'activity': [
            metric(current['sessions'], 'Website sessions', 'historical', 'Full displayed export period; not selected-date sessions.'),
            metric(current['events'], 'Recorded events', 'historical', 'Includes browsing and automatic events; not leads.')],
        'responses': [metric(current['engaged_sessions'], 'Engaged sessions', 'historical',
                             'Engagement is not a qualified response or sales lead.')],
        'outcomes': [
            metric(current['key_events'], 'Recorded key events', 'historical',
                   'Tracking gap: zero recorded key events does not establish zero actual leads or bookings.'),
            metric(None, 'Verified inbound leads / bookings', 'unverified',
                   'Successful inquiry and confirmed booking events were not verified in the audit.')],
        'nextStep': 'Refresh GA4 exports and verify successful inquiry and confirmed booking tracking before attributing inbound outcomes.',
        'href': 'sources', 'periods': periods, 'provenance': provenance,
        'diagnostics': {'formStarts': form_starts,
                        'note': 'form_start is diagnostic event activity, not submitted forms or unique leads.'},
    }
    out = {'vectors': [referral_vector, website_vector, newsletter(), pulley()], 'notes': [
        'Referrals are a current CRM stage inventory. Website numbers are complete historical export periods. Neither changes with the global date filter.',
        'Referral pipeline records overlap CRM inventory; website sessions may overlap paid/organic/outreach influence. Do not add vectors into a unique-prospect or sourced-pipeline total.',
        'GA4 coverage retains America/New_York property export date boundaries. Collected October 13, reporting through October 12; period aggregates cannot be rebucketed to Mountain time.',
        'The 90-day website period is contextual and overlaps the campaign period; these periods are not comparable lengths or additive.',
        'Newsletter is cumulative delivery and engagement history. Pulley is a research-support inventory. Neither provides selected-date sends or independently verified sales outcomes.',
    ], 'dataQuality': [
        {'source': 'referrals', 'issue': 'Current stage is not stage history or confirmed referral attribution.'},
        {'source': 'website', 'issue': 'Historical through October 12; no later GA4 collection is represented.'},
        {'source': 'website', 'issue': f'{form_starts} form_start events are diagnostic only; zero key events reflects an outcome-measurement gap.'},
        {'source': 'newsletter', 'issue': 'Sender linked to campaign 3 was deleted; the campaign is not being sent despite an Active campaign state.'},
        {'source': 'pulley', 'issue': 'Research/contact readiness overlaps Video DM inventory and is not send, reply, booking or qualification evidence.'},
    ]}
    target = ROOT / 'data' / 'extras.json'
    target.write_text(json.dumps(out, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'output': str(target), 'referralRecords': len(referrals),
                      'referralStageCounts': dict(stages), 'websitePeriods': [
                          {k: p[k] for k in ('start', 'end', 'sessions', 'engaged_sessions', 'events', 'key_events')}
                          for p in periods], 'formStartDiagnostics': form_starts}, indent=2))


if __name__ == '__main__':
    build()
