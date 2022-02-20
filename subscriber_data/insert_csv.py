import sys
import json
import csv

csvFilePath = sys.argv[1]
jsonFilePath = sys.argv[2]

with open(jsonFilePath, 'r') as f:
    subscriberDurations = json.load(f)

with open(csvFilePath, newline='') as f:
    reader = csv.reader(f)
    skipped = False
    for row in reader:
        if not skipped: # Skip the first row
            skipped = True
            continue
        username = row[0].lower()
        months = int(row[3])
        subscriberDurations[username] = months

with open(jsonFilePath, 'w') as f:
    json.dump(subscriberDurations, f)

print('There are {} total subs tracked.'.format(len(subscriberDurations.keys())))
