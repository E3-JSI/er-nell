import json
import sys

json_file=sys.argv[1]

with open(json_file) as data_file:
    data = json.load(data_file)

output = open('uri.list', 'w')

for dc in data['concept_suggestions']:
    output.write(dc['uri'] + '\n')

output.close()

