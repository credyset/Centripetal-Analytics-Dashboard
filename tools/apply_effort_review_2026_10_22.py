"""Apply the dated owner effort decision and evidence context without inferred hours."""
from pathlib import Path
from datetime import datetime, timezone
import copy
import json
from apply_effort_estimate import apply_effort_estimate
from prepare_shared_snapshot import curate_snapshot

ROOT=Path(__file__).resolve().parents[1]


def apply_review(data, reviewed_at):
    effort=data['time']
    rows={row['id']:row for row in effort['workstreams']}
    additions={
        'video-dm':[
            {'date':'2026-10-19','label':'Christian confirmed research-account sign-in and the browser session so prospect checks could continue. Two access messages are one coordination cluster; no duration inferred.'},
            {'date':'2026-10-22','label':'Christian confirmed reloading the Pipedrive research tab for net-new prospect checks. This supports access coordination, not measured work duration.'}],
        'dashboard':[
            {'date':'2026-10-21','label':'Christian directed commercial-evidence and source reconciliation, including CRM/inbox checks. This is review context, not an independently timed session.'},
            {'date':'2026-10-22','label':'Christian reviewed the held-trigger interpretation and directed GitHub publication, then clarified the October 16 estimate cutoff and supplied 3.75 additional non-meeting hours. The addition is counted once overall.'}],
        'investor-partner':[
            {'date':'2026-10-20','label':'Christian identified departed investor contacts and requested current replacements at Arthur Ventures, Osage and Generator. Research execution and generated contact counts are not human time.'},
            {'date':'2026-10-21','label':'Christian directed healthcare-partner research across 29 firms with current-role, verified-email and credit-limit requirements. The deliverable supports coordination scope, not measured duration.'}]
    }
    if 'investor-partner' not in rows:
        row={'id':'investor-partner','title':'Investor/contact QA and partner research direction',
             'evidenceDates':[], 'evidence':[],
             'humanInvolvementBasis':'Direct Christian requests establish research direction and review. No hours are allocated by workstream; agent research/enrichment is excluded.',
             'planningAllowance':{'enabled':False,'hoursLow':0,'hoursHigh':0,
                'kind':'Evidence context only; no separate workstream hours allocated',
                'scope':'Included only in the owner-provided overall estimate; no additional hours inferred.'}}
        effort['workstreams'].append(row);rows[row['id']]=row
    for ident,evidence in additions.items():
        row=rows[ident]
        known={(e['date'],e['label']) for e in row.get('evidence',[])}
        row.setdefault('evidence',[]).extend(copy.deepcopy(e) for e in evidence if (e['date'],e['label']) not in known)
        row['evidenceDates']=sorted(set(row.get('evidenceDates',[]))|{e['date'] for e in evidence})
    # Retain source reviews without obsolete carry-forward wording or duplicate
    # notes. The original estimate remains in the canonical decision's baseline.
    notes=[]
    for note in effort.get('notes',[]):
        if note.startswith(('October22 review extends','October 22 review extends')):
            continue
        if note.startswith('October 21 refresh review:'):
            note='October 21 recording review confirmed six associated source recordings, five after duplicate removal, totaling 228.58 audio minutes. No newer exact-Christian matching recording was found in the retained indexed list; audio duration is not attendance or worked time.'
        if note.startswith('Drive revision metadata attributes'):
            note='Drive revision metadata attributes 14 retained October file revisions on nine Mountain dates to Christian. This supports activity dates only; it does not establish human work duration, billing or additional hours.'
        if note.startswith('Nonmeeting estimates cover assumed'):
            note='Non-meeting effort is the owner-provided overall estimate; dated workstream evidence gives context without allocating hours.'
        if note=='These figures are a draft reconstruction, not a timesheet or billing record.':
            note='The non-meeting range is an owner estimate; associated audio is a separate proxy. These are not a timesheet or billing record.'
        if note not in notes:notes.append(note)
    effort['notes']=notes
    apply_effort_estimate(effort)
    effort.update(snapshotAt=reviewed_at,reviewedAsOf='2026-10-22')
    for card in data['sources']:
        if card['id']=='time':
            card.update(asOf=reviewed_at,checkedAt='2026-10-22',coverage=copy.deepcopy(effort['period']),
                status='Current owner nonmeeting estimate; separately dated recording evidence',
                note='Christian confirmed the October 1–16 baseline of 14.5–15.75 hours and supplied 3.75 additional non-meeting hours for October 17–22. Updated estimate:18.25–19.5 hours. Recording-source dates and the 228.58-minute proxy are unchanged; duration and attendance are not independently measured.')
    return data


def main():
    path=ROOT/'data/shared-dashboard.json'
    before=json.loads(path.read_text())
    decision=json.loads((ROOT/'EFFORT_ESTIMATE.json').read_text())
    assert before['meta'].get('reportingAsOfDate','')<='2026-10-22', 'A newer reporting period requires a newer review.'
    assert decision['confirmedOn']<='2026-10-22', 'A newer owner decision requires a newer review.'
    stamp=datetime.now(timezone.utc).isoformat()
    data=curate_snapshot(apply_review(copy.deepcopy(before),stamp))
    for key in ('ads','crm','video','waalaxy','content','referrals','meetings','outcomes'):
        assert data[key]==before[key],f'Unexpected source or outcome change:{key}'
    assert data['time']['meetings']==before['time']['meetings']
    data['meta'].update(generatedAt=stamp,revision='October 22 owner effort addition, selected-period content headline and source coverage presentation',
        lastRevisionNote='Owner-provided non-meeting estimate updated by3.75 hours; source rows and commercial outcomes unchanged. Content headline now uses the selected daily evidence.')
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    local=ROOT/'data/dashboard.json'
    if local.exists():local.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'nonMeetingLow':data['time']['summary']['nonMeetingEstimateHoursLow'],
        'nonMeetingHigh':data['time']['summary']['nonMeetingEstimateHoursHigh'],
        'recordingProxyMinutes':data['time']['meetings']['summary']['recordedMinutes'],
        'businessSourceRowsUnchanged':True}))


if __name__=='__main__':main()
