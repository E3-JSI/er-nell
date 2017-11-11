import json
import sys

json_file=sys.argv[1]
output_file=sys.argv[2]

with open(json_file) as data_file:
    data = json.load(data_file)

output = open(output_file, 'w')

for dc in data['concept_suggestions']:
    output.write(dc['uri'] + '\n')

output.close()

