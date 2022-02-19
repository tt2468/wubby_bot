import sys
import json

with open('ham_checkins.json') as f:
    data = json.load(f)

members = {}

for checkinId in data.keys():
    for member in data[checkinId]['members']:
        if member not in members:
            members[member] = 0
        members[member] += 1

members = dict(sorted(members.items(), key=lambda item: item[1]))

print(json.dumps(members, indent=2))
