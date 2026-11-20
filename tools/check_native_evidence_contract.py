"""Reject incomplete native message records before public snapshot publication."""
from copy import deepcopy
from datetime import date, datetime
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]

def validate_native_evidence(video):
    events=(video.get('messageDateReview') or {}).get('platformObservedEvents',[])
    for event in events:
        assert isinstance(event,dict), 'Native message must be a keyed record'
        assert any(isinstance(event.get(k),str) and event[k].strip() for k in
                   ('dedupKey','observationId','sourceMessageId')), 'Native message needs stable identity'
        assert isinstance(event.get('profileId'),str) and event['profileId'].strip(), 'Native message needs a source profile'
        assert event.get('direction') in ('inbound','outbound'), 'Native direction is unresolved'
        day=event.get('date')
        assert isinstance(day,str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}',day), 'Native message needs a source day'
        try:date.fromisoformat(day)
        except ValueError as error:raise AssertionError('Native source day is invalid') from error
        observed=event.get('observedAt')
        assert isinstance(observed,str) and re.search(r'T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$',observed), 'Native observation needs its original offset clock'
        try:datetime.fromisoformat(observed.replace('Z','+00:00'))
        except ValueError as error:raise AssertionError('Native observation clock is invalid') from error
        assert event.get('videoIncluded') is None or type(event['videoIncluded']) is bool, 'Native video flag cannot be a truthy string'
        if event.get('videoIncluded') is True:
            assert any(isinstance(event.get(k),str) and event[k].strip() for k in
                       ('assetId','loomAssetId')), 'Observed native video needs a source asset ID'
    return True

def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot',type=Path,default=ROOT/'data/shared-dashboard.json')
    args=parser.parse_args()
    data=json.loads(args.snapshot.read_text());validate_native_evidence(data.get('video') or {})
    event={'dedupKey':'profile|source-message','profileId':'profile','date':'2026-11-13',
           'observedAt':'2026-11-14T18:00:00Z','direction':'outbound','videoIncluded':True,'assetId':'asset'}
    video={'messageDateReview':{'platformObservedEvents':[event]}}
    before=deepcopy(video);validate_native_evidence(video);assert video==before
    invalid=[dict(event,profileId=''),dict(event,assetId=''),dict(event,observedAt=None),
             dict(event,observedAt='2026-11-14'),dict(event,date='2026-11-31'),
             dict(event,direction='sent'),dict(event,videoIncluded='true'),dict(event,dedupKey='')]
    for row in invalid:
        try:validate_native_evidence({'messageDateReview':{'platformObservedEvents':[row]}})
        except AssertionError:pass
        else:raise AssertionError('Incomplete native source record passed publication gate')
    # An unknown video flag on a text observation is retained as unknown.
    validate_native_evidence({'messageDateReview':{'platformObservedEvents':[dict(event,videoIncluded=None,assetId=None)]}})
    print('Native evidence contract: retained source identity/day/capture/asset fields and eight malformed-record rejections passed.')

if __name__=='__main__':main()
