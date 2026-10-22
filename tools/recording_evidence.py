"""Distinguish recording URLs from free text in the worksheet recording field."""
from urllib.parse import urlparse
import re


def recording_evidence_fields(value):
    text = str(value or '').strip()
    try:
        parsed = urlparse(text)
        is_url = bool(text and not re.search(r'\s', text) and
                      parsed.scheme.lower() in ('http', 'https') and parsed.hostname)
        is_loom = bool(is_url and parsed.hostname.lower() in ('loom.com', 'www.loom.com')
                       and re.fullmatch(r'/share/[A-Fa-f0-9]{32}/?', parsed.path))
    except ValueError:
        is_url = is_loom = False
    return {
        'hasRecordingFieldContent': bool(text),
        'hasRecordingLink': is_url,
        'recordingFieldKind': ('loom_url' if is_loom else 'other_url' if is_url else
                               'non_url_note' if text else 'empty'),
        'recordingFieldNote': text if text and not is_url else None,
    }


def apply_video_evidence_reviews(video):
    """Retain reviewed field/join evidence only for its exact source snapshot."""
    review = video.get('recordingFieldReview') or {}
    if review and review.get('appliesToSnapshotAt') == video.get('snapshotAt'):
        keyed = {(r['sourceRow'], r['profile']): r for r in review.get('records', [])}
        for row in video.get('rows', []):
            evidence = keyed.get((row.get('sourceRow'), row.get('id')))
            if evidence:
                for key in ('hasRecordingFieldContent', 'hasRecordingLink',
                            'recordingFieldKind', 'recordingFieldNote'):
                    row[key] = evidence[key]
        video.setdefault('summary', {}).update(
            recordingLinkRows=sum(bool(r.get('hasRecordingLink')) for r in video.get('rows', [])),
            recordingFieldNonemptyRows=review['nonemptyCells'],
            recordingFieldNonUrlNotes=review['nonUrlNotes'])
    crm = video.get('crmReconciliation') or {}
    if crm and crm.get('appliesToSnapshotAt') == video.get('snapshotAt'):
        keyed = {(r['sourceRow'], r['profile']): r for r in crm.get('records', [])}
        for row in video.get('rows', []):
            evidence = keyed.get((row.get('sourceRow'), row.get('id')))
            if evidence and evidence.get('crmDealId') and evidence.get('recordingFieldKind') == 'loom_url':
                row['matchedCrmDealId'] = evidence['crmDealId']
                row['matchedCrmPersonId'] = evidence.get('crmPersonId')
                row['crmMatchBasis'] = 'Exact LinkedIn profile and matching Loom asset in linked CRM note; original Sheet ID retained separately.'
    return video
