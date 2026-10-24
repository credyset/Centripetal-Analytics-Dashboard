"""Apply durable opaque-source-ID publication exclusions to curated snapshots."""
from pathlib import Path
import copy
import json

ROOT=Path(__file__).resolve().parents[1]

def rules():
    policy=json.loads((ROOT/'PUBLICATION_REDACTIONS.json').read_text())
    assert policy['version']==1 and policy['records'], 'Publication exclusions must be explicitly configured'
    return {rule['sourceId']:rule for rule in policy['records']}

def record_rule(value,configured):
    for key in ('id','recordingId','sourceId'):
        source_id=value.get(key)
        if isinstance(source_id,str) and source_id in configured:
            return configured[source_id]
    return None

def apply_publication_redactions(snapshot):
    """Minimize matched records, including arbitrary later metadata children.

    Only curated copies use this handler. It never touches the raw/private source
    files, changes source IDs/counts, or makes commercial/effort decisions.
    """
    configured=rules()
    def visit(value):
        if isinstance(value,dict):
            rule=record_rule(value,configured)
            if rule:
                minimized={key:item for key,item in value.items() if key in rule['allowedFields']}
                minimized.update(title=rule['safeTitle'],classification=rule['safeClassification'],
                    classificationBasis=rule['safeClassificationBasis'],
                    publicationPolicy=copy.deepcopy(rule['publicationPolicy']))
                value.clear();value.update(minimized)
            for item in value.values():visit(item)
        elif isinstance(value,list):
            for item in value:visit(item)
    visit(snapshot)
    return snapshot

def validate_publication_redactions(snapshot):
    configured=rules()
    def visit(value):
        if isinstance(value,dict):
            rule=record_rule(value,configured)
            if rule:
                assert set(value)<=set(rule['allowedFields']), 'Excluded employment record restored unnecessary source fields'
                assert value.get('title')==rule['safeTitle'], 'Excluded employment record restored an identifying title'
                assert value.get('classification')==rule['safeClassification']
                assert value.get('classificationBasis')==rule['safeClassificationBasis'], 'Excluded employment record restored private assessment context'
                assert value.get('publicationPolicy')==rule['publicationPolicy'], 'Excluded employment record lost its publication policy'
            for item in value.values():visit(item)
        elif isinstance(value,list):
            for item in value:visit(item)
    visit(snapshot)
    return True
