"""Update Waalaxy with Oct invitation data and populate Referrals from Pipedrive."""
import json

with open('data/shared-dashboard.json') as f:
    d = json.load(f)

# ============================================================
# 1. WAALAXY — append Sep 15 – Oct 15 invitation data
# ============================================================

waalaxy_csv = [
    ("2026-09-18", 17, 31),
    ("2026-10-05", 17, 62),
    ("2026-10-06", 25, 59),
    ("2026-10-07", 17, 68),
    ("2026-10-12", 29, 138),
    ("2026-10-13", 9, 44),
]

existing_dates = {e['date'] for e in d['waalaxy']['daily']}
for date_str, accepted, sent in waalaxy_csv:
    if date_str not in existing_dates:
        d['waalaxy']['daily'].append({
            "date": date_str,
            "invitationsSent": sent,
            "invitationsAccepted": accepted
        })

d['waalaxy']['daily'].sort(key=lambda x: x['date'])
d['waalaxy']['coverage']['end'] = '2026-10-15'
d['waalaxy']['status'] = 'partial'
d['waalaxy']['snapshotAt'] = '2026-10-15'
d['waalaxy']['metrics']['recentInvitationsSent_Sep15_Oct15'] = 402
d['waalaxy']['metrics']['recentInvitationsAccepted_Sep15_Oct15'] = 114
d['waalaxy']['notes'].append(
    "October 15, 2026: Invitation activity (sent/accepted) from Charles's Waalaxy export "
    "covering Sep 15 – Oct 15, 2026. Three burst periods: Sep 18 (31 sent), "
    "Oct 5–7 (189 sent), Oct 12–13 (182 sent). Total: 402 sent, 114 accepted "
    "(28% accept rate). Invitation-only data; message sends, replies and campaign "
    "breakdowns are not included in this export."
)
d['waalaxy']['accessReview']['newestDatedActivity'] = '2026-10-13'

print(f"Waalaxy: {len(d['waalaxy']['daily'])} daily entries, coverage through {d['waalaxy']['coverage']['end']}")

# ============================================================
# 2. REFERRALS — populate from Pipedrive pipeline 4
# ============================================================

stage_map = {
    26: "Centripetal Circle",
    28: "Intro Promised",
    31: "Opportunity ( Referred )",
    38: "Office Hours",
    39: "Inner Circle",
    40: "Graveyard ( Newsletter )",
    42: "Centripetal Amigos"
}

referral_deals = [
    {"id": 103, "title": "Long Pham", "stage_id": 42, "person_name": "Long Pham", "org_name": None, "add_time": "2024-11-04", "update_time": "2026-10-12"},
    {"id": 104, "title": "Nate Littlewood", "stage_id": 26, "person_name": "Nate Littlewood", "org_name": None, "add_time": "2024-11-04", "update_time": "2026-04-07"},
    {"id": 105, "title": "Porter McKay", "stage_id": 28, "person_name": "Porter McKay", "org_name": "Avid Bank", "add_time": "2024-11-04", "update_time": "2026-10-13"},
    {"id": 152, "title": "Leverage VC", "stage_id": 26, "person_name": "David Rabinovici", "org_name": "Leverage VC", "add_time": "2025-07-18", "update_time": "2026-08-03"},
    {"id": 203, "title": "Christian Wutz", "stage_id": 26, "person_name": "Christian Wutz", "org_name": "REDYSET TEST blerp", "add_time": "2026-02-24", "update_time": "2026-10-13"},
    {"id": 214, "title": "Avenue Growth Partners", "stage_id": 26, "person_name": "Emmanuel Onakoya", "org_name": "Avenue Growth Partners", "add_time": "2026-03-04", "update_time": "2026-08-20"},
    {"id": 440, "title": "Aryeh Hoffman", "stage_id": 42, "person_name": "Aryeh Hoffman", "org_name": "Megadata", "add_time": "2026-08-13", "update_time": "2026-10-12"},
    {"id": 441, "title": "Naftali Halberg", "stage_id": 31, "person_name": "Naftali Halberg", "org_name": "Ginossar", "add_time": "2026-08-13", "update_time": "2026-09-18"},
    {"id": 442, "title": "Sammy Abdullah", "stage_id": 39, "person_name": "Sammy Abdullah", "org_name": "Blossom Street Ventures", "add_time": "2026-08-13", "update_time": "2026-10-07"},
    {"id": 443, "title": "Howard Friedman", "stage_id": 31, "person_name": "Howard Friedman", "org_name": "Columbia University", "add_time": "2026-08-13", "update_time": "2026-09-04"},
    {"id": 452, "title": "Mike Silva", "stage_id": 26, "person_name": "Mike Silva", "org_name": "Silva Lining HR", "add_time": "2026-09-03", "update_time": "2026-09-16"},
    {"id": 454, "title": "Robert Adelson", "stage_id": 38, "person_name": "Robert Adelson", "org_name": "Osage Venture Partners", "add_time": "2026-09-04", "update_time": "2026-09-04"},
    {"id": 494, "title": "Bobby Ocampo", "stage_id": 39, "person_name": "Bobby Ocampo", "org_name": "Blueprint Equity", "add_time": "2026-09-04", "update_time": "2026-09-21"},
    {"id": 495, "title": "Michael Merritt", "stage_id": 39, "person_name": "Michael Merritt", "org_name": "Blueprint Equity", "add_time": "2026-09-04", "update_time": "2026-10-15"},
    {"id": 497, "title": "Reuven Mashitz", "stage_id": 39, "person_name": "Reuven Mashitz", "org_name": "Careflow", "add_time": "2026-09-04", "update_time": "2026-09-21"},
    {"id": 500, "title": "Itay Fried", "stage_id": 42, "person_name": "Itay Fried", "org_name": "Megadata", "add_time": "2026-09-04", "update_time": "2026-10-12"},
    {"id": 508, "title": "Loson Stockton", "stage_id": 26, "person_name": "Loson Stockton", "org_name": "Vista Point Advisors", "add_time": "2026-09-04", "update_time": "2026-09-21"},
    {"id": 510, "title": "Ari Ashkenas", "stage_id": 26, "person_name": "Ari Ashkenas", "org_name": "PopUpTalent", "add_time": "2026-09-04", "update_time": "2026-09-21"},
    {"id": 511, "title": "Sidharth Kakkar", "stage_id": 42, "person_name": "Sidharth Kakkar", "org_name": "Subscript", "add_time": "2026-09-04", "update_time": "2026-10-12"},
    {"id": 522, "title": "Jack DeWolf", "stage_id": 26, "person_name": "Jack DeWolf", "org_name": "Restore AI", "add_time": "2026-09-04", "update_time": "2026-09-21"},
    {"id": 523, "title": "Brian Parks", "stage_id": 26, "person_name": "Brian Parks", "org_name": "Bigfoot Capital", "add_time": "2026-09-04", "update_time": "2026-09-21"},
    {"id": 525, "title": "Carter Hawthorne", "stage_id": 26, "person_name": "Carter Hawthorne", "org_name": "Bigfoot Capital", "add_time": "2026-09-04", "update_time": "2026-09-21"},
    {"id": 527, "title": "Don Erwin", "stage_id": 26, "person_name": "Don Erwin", "org_name": "MontPac", "add_time": "2026-09-04", "update_time": "2026-10-06"},
    {"id": 758, "title": "Ben Murray", "stage_id": 39, "person_name": "Ben Murray", "org_name": None, "add_time": "2026-09-30", "update_time": "2026-09-30"},
    {"id": 759, "title": "Devo Harris", "stage_id": 39, "person_name": "Devo Harris", "org_name": None, "add_time": "2026-09-30", "update_time": "2026-09-30"},
    {"id": 760, "title": "Harry Horowitz", "stage_id": 39, "person_name": "Harry Horowitz", "org_name": None, "add_time": "2026-09-30", "update_time": "2026-09-30"},
    {"id": 761, "title": "Melanie Ortiz", "stage_id": 39, "person_name": "Melanie Ortiz", "org_name": None, "add_time": "2026-09-30", "update_time": "2026-09-30"},
    {"id": 762, "title": "Shalom Reinman", "stage_id": 39, "person_name": "Shalom Reinman", "org_name": None, "add_time": "2026-09-30", "update_time": "2026-09-30"},
    {"id": 763, "title": "Joseph Simpson", "stage_id": 39, "person_name": "Joseph Simpson", "org_name": None, "add_time": "2026-09-30", "update_time": "2026-09-30"},
    {"id": 764, "title": "Alan Faulkner", "stage_id": 26, "person_name": "Alan Faulkner", "org_name": None, "add_time": "2026-09-30", "update_time": "2026-09-30"},
    {"id": 765, "title": "Andrew Woodruff", "stage_id": 26, "person_name": "Andrew Woodruff", "org_name": None, "add_time": "2026-09-30", "update_time": "2026-09-30"},
    {"id": 766, "title": "Bardia Moayedi", "stage_id": 26, "person_name": "Bardia Moayedi", "org_name": None, "add_time": "2026-09-30", "update_time": "2026-09-30"},
    {"id": 767, "title": "Bart Macdonald", "stage_id": 26, "person_name": "Bart Macdonald", "org_name": None, "add_time": "2026-09-30", "update_time": "2026-09-30"},
    {"id": 768, "title": "Ben Neuwirth", "stage_id": 26, "person_name": "Ben Neuwirth", "org_name": None, "add_time": "2026-09-30", "update_time": "2026-09-30"},
    {"id": 769, "title": "Daniel Schoenbrun", "stage_id": 26, "person_name": "Daniel Schoenbrun", "org_name": None, "add_time": "2026-09-30", "update_time": "2026-09-30"},
    {"id": 770, "title": "Eric Broad", "stage_id": 26, "person_name": "Eric Broad", "org_name": None, "add_time": "2026-09-30", "update_time": "2026-09-30"},
    {"id": 771, "title": "Mike Firmage", "stage_id": 26, "person_name": "Mike Firmage", "org_name": None, "add_time": "2026-09-30", "update_time": "2026-09-30"},
    {"id": 772, "title": "Michael Wallace", "stage_id": 26, "person_name": "Michael Wallace", "org_name": None, "add_time": "2026-09-30", "update_time": "2026-09-30"},
    {"id": 773, "title": "Jake Colognesi", "stage_id": 26, "person_name": "Jake Colognesi", "org_name": None, "add_time": "2026-09-30", "update_time": "2026-09-30"},
    {"id": 774, "title": "Jamie Vinick", "stage_id": 26, "person_name": "Jamie Vinick", "org_name": None, "add_time": "2026-09-30", "update_time": "2026-09-30"},
    {"id": 775, "title": "Jonathan Detzel", "stage_id": 26, "person_name": "Jonathan Detzel", "org_name": None, "add_time": "2026-09-30", "update_time": "2026-09-30"},
    {"id": 776, "title": "Kevin Corelli", "stage_id": 26, "person_name": "Kevin Corelli", "org_name": None, "add_time": "2026-09-30", "update_time": "2026-09-30"},
    {"id": 777, "title": "Mike Lyon", "stage_id": 26, "person_name": "Mike Lyon", "org_name": None, "add_time": "2026-09-30", "update_time": "2026-09-30"},
    {"id": 778, "title": "Michael Rose", "stage_id": 26, "person_name": "Michael Rose", "org_name": None, "add_time": "2026-09-30", "update_time": "2026-09-30"},
    {"id": 779, "title": "Dan Williams", "stage_id": 26, "person_name": "Dan Williams", "org_name": None, "add_time": "2026-09-30", "update_time": "2026-09-30"},
    {"id": 780, "title": "Rocco Natalicchio", "stage_id": 26, "person_name": "Rocco Natalicchio", "org_name": None, "add_time": "2026-09-30", "update_time": "2026-09-30"},
    {"id": 781, "title": "Roey Herzfeld", "stage_id": 26, "person_name": "Roey Herzfeld", "org_name": None, "add_time": "2026-09-30", "update_time": "2026-09-30"},
    {"id": 782, "title": "Sandy Kory", "stage_id": 26, "person_name": "Sandy Kory", "org_name": None, "add_time": "2026-09-30", "update_time": "2026-09-30"},
    {"id": 783, "title": "David Kim", "stage_id": 26, "person_name": "David Kim", "org_name": None, "add_time": "2026-09-30", "update_time": "2026-09-30"},
    {"id": 784, "title": "Matt Cohen", "stage_id": 26, "person_name": "Matt Cohen", "org_name": None, "add_time": "2026-09-30", "update_time": "2026-09-30"},
    {"id": 785, "title": "Matt Long", "stage_id": 26, "person_name": "Matt Long", "org_name": None, "add_time": "2026-09-30", "update_time": "2026-09-30"},
    {"id": 786, "title": "Tim Richardson", "stage_id": 26, "person_name": "Tim Richardson", "org_name": None, "add_time": "2026-09-30", "update_time": "2026-09-30"},
]

from collections import Counter
stage_counts = Counter(stage_map.get(deal["stage_id"], "Unknown") for deal in referral_deals)

records = []
for deal in referral_deals:
    records.append({
        "dealId": deal["id"],
        "title": deal["title"],
        "personName": deal["person_name"],
        "organization": deal["org_name"],
        "stage": stage_map.get(deal["stage_id"], f"Unknown ({deal['stage_id']})"),
        "stageId": deal["stage_id"],
        "status": "open",
        "addedAt": deal["add_time"],
        "updatedAt": deal["update_time"],
    })

d['referrals'] = {
    "status": "current_snapshot",
    "snapshotAt": "2026-10-15",
    "coverage": {
        "source": "Pipedrive Referral Pipeline (pipeline_id=4)",
        "collectedAt": "2026-10-15",
        "scope": "Active referral contacts excluding Office Hours (77) and Graveyard/Newsletter (28)"
    },
    "summary": {
        "totalPipelineDeals": 137,
        "activeReferralDeals": len(records),
        "stageDistribution": dict(stage_counts),
        "circleContacts": {
            "innerCircle": sum(1 for d2 in referral_deals if d2["stage_id"] == 39),
            "centripetalCircle": sum(1 for d2 in referral_deals if d2["stage_id"] == 26),
            "centripetalAmigos": sum(1 for d2 in referral_deals if d2["stage_id"] == 42),
            "introPromised": sum(1 for d2 in referral_deals if d2["stage_id"] == 28),
            "opportunity": sum(1 for d2 in referral_deals if d2["stage_id"] == 31)
        },
        "officeHoursCount": 77,
        "graveyardNewsletterCount": 28,
        "touchpointAutomation": {
            "status": "configured",
            "cycle": "30 days",
            "trelloSyncStatus": "Pipedrive to Trello working; Trello to Pipedrive completion sync pending"
        },
        "observedProgressions": [
            {"dealId": 761, "personName": "Melanie Ortiz", "movement": "Centripetal Circle to Intro Made", "observedAt": "2026-10-14"},
            {"dealId": 793, "personName": "Jonathan S. Katz", "movement": "Centripetal Amigos to Intro Promised", "observedAt": "2026-10-12"}
        ]
    },
    "stages": [
        {"id": 42, "name": "Centripetal Amigos", "order": 1},
        {"id": 26, "name": "Centripetal Circle", "order": 2},
        {"id": 39, "name": "Inner Circle", "order": 3},
        {"id": 28, "name": "Intro Promised", "order": 6},
        {"id": 31, "name": "Opportunity ( Referred )", "order": 10},
        {"id": 38, "name": "Office Hours", "order": 14},
        {"id": 40, "name": "Graveyard ( Newsletter )", "order": 15}
    ],
    "records": records,
    "note": "Referral Pipeline snapshot from Pipedrive. 137 total deals; 52 active referral records shown (excluding 77 Office Hours and 28 Graveyard/Newsletter). Touchpoint automation configured for Centripetal Circle with 30-day cycle. Two referral progressions observed in October 2026."
}

# Update sources entry for referrals
for src in d['sources']:
    if src.get('id') == 'referrals':
        src['status'] = 'Current snapshot'
        src['asOf'] = '2026-10-15'
        src['coverage'] = '137 pipeline deals; 52 active referral records'
    if src.get('id') == 'waalaxy':
        src['status'] = 'Partial (invitation activity through Oct 15)'
        src['asOf'] = '2026-10-15'
        src['coverage'] = {'start': '2024-12-13', 'end': '2026-10-15'}

with open('data/shared-dashboard.json', 'w') as f:
    json.dump(d, f, ensure_ascii=False, indent=2)
    f.write('\n')

print(f"Referrals: {len(records)} active records populated")
print(f"  Stage distribution: {dict(stage_counts)}")
print("shared-dashboard.json updated successfully")
