import json
import sys
import pprint

json_file=sys.argv[1]
output_file=sys.argv[2]

with open(json_file) as data_file:
    data = json.load(data_file)

output = open(output_file, 'w')

for re in data['related_events']:
    for ar in re['articles']:
        output.write(ar + '\n')

output.close()

