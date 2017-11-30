import json
import logging
import gzip
import sys
from collections import Counter
import pdb
import subprocess
import argparse
import traceback

log_level = logging.INFO

logging.basicConfig(
	level = log_level,
	format = "%(asctime)s| %(message)s",
	datefmt = "%H:%M:%S")

NELL_RELATIONS_TSV = "../../NELL_resources/relations.tsv"
NELL_PATTERNS_DUMP = "../../NELL_resources/NELL.08m.1035.extractionPatterns.csv.gz"


def get_NELL_rel_names(nell_relations_fnm):
	"""Get the names of relations in NELL."""
	rel_names = set([])
	with open(nell_relations_fnm) as infile:
		logging.info("Reading relation names from {0}".format(nell_relations_fnm))
		# skip header line
		header = infile.readline()
		# read the relation name from each line
		duplicate_n = 0
		for line in infile:
			if line.isspace():
				break

			# relation name is in the first column
			rel_name = line.split('\t', 1)[0]
			if rel_name in rel_names:
				duplicate_n += 1
			rel_names.add(rel_name)

	logging.info("Read names of {0} relations".format(len(rel_names)))
	logging.debug("Found {0} duplicates".format(duplicate_n))
	return sorted(rel_names)


def download_relations(relation_names, zenodotus_path, output_jsonl):
	"""
	Scrape relations from the NELL website using the external tool 'zenodotus'.
	Store results into a jsonl file.
	"""
	logging.info("Going to download data for %d relations" % len(relation_names))

	# list of relations for which the download was unsuccessful
	missed_relations = []

	# call zenodotus for each relation and store the output
	with open(output_jsonl, 'w') as outfile:
		for rel_i, relation in enumerate(relation_names):
			logging.info("Downloading relation %d of %d: %s" % (rel_i, len(relation_names), relation))
			# example call: java -jar zenodotus.jar -gr acquired
			zen_out = subprocess.check_output(["java", "-jar", zenodotus_path, "-gr", relation.lower()])
			zen_out = zen_out.splitlines(False)

			# test if returned output is ok
			if len(zen_out) != 4:
				logging.info("Zenodotus error on relation %s:\n%s" % (relation, '\n'.join(zen_out)) )
				missed_relations.append(relation)
				continue

			#assert len(zen_out) == 4, "Bad zenodotus output\n" + '\n'.join(zen_out)

			try:
				test = json.loads(zen_out[2])
			except Exception as e:
				logging.info("Unable to parse output for relation %s:\n%s" % (relation, str(e)))
				#raise e
				missed_relations.append(relation)
				continue

			outfile.write(zen_out[2] + "\n")

	logging.info("DONE!")

	return missed_relations



def open_maybe_gzip(fnm):
	"""Unzip a file before opening if its filename ends with .gz."""
	if fnm.endswith(".gz"):
		return gzip.open(fnm)
	else:
		return open(fnm)


def get_NELL_patterns(nell_patterns_fnm, relations):
	"""Get extraction patterns for given relations from a NELL dump file."""
	patterns = {}
	with open_maybe_gzip(nell_patterns_fnm) as infile:
		logging.info("Reading relation patterns from {0}".format(nell_patterns_fnm))
		# skip header line
		header = infile.readline()
		# read the pattern from each line contatining a relation - skip entities
		for line_i, line in enumerate(infile):
			prop_name, _, pattern, _ = line.split("\t", 3)
			#logging.debug("Read pattern: {0} - {1}".format(prop_name, pattern))
			if line_i % 1000 == 0:
				print "\rProcessed {0} lines".format(line_i),
				sys.stdout.flush()
			# collect only paterns for specified relations
			if prop_name in relations:
				patterns[pattern] = prop_name
	print
	logging.info("Read {0} patterns".format(len(patterns)))
	return patterns


def get_patterns_mapping(
		nell_relations_fnm,
		nell_patterns_fnm,
		mapping_fnm):
	# get all NELL relation names
	rel_names = get_NELL_rel_names(NELL_RELATIONS_TSV)
	# get all relation extraction patterns
	patterns = get_NELL_patterns(NELL_PATTERNS_DUMP, rel_names)
	# dump the mapping into file
	logging.info("Dumping pattern mapping into {0}".format(mapping_fnm))
	with open(mapping_fnm, "w") as outfile:
		json.dump(patterns, outfile)


def main_get_patterns():
	get_patterns_mapping(
		NELL_RELATIONS_TSV,
		NELL_PATTERNS_DUMP,
		"pattern_mapping.json")


def plot_pageRank_histogram(article):
	"""Plot the histogram for annotations' page rank distribution."""
	import matplotlib.pyplot as plt

	pRank = [annot["pageRank"] for annot in article["annotations"]["annotations"]]
	print len(pRank)
	plt.hist(pRank, 50)
	plt.show()


# TODO: Our tokenization is not the same as NELLs: eg. Nell: "John's" -> ["John", "'s"] vs. Wikifier: "John's" -> ["John's"]
#       find a way to consolidate this
def get_context_between(word_i1, word_i2, annotations):
	"""Get the context between two words."""
	# start with the first word
	context = annotations["words"][word_i1+1]
	# add the rest of the context (if any)
	for word_i in xrange(word_i1+2, word_i2):
		context += annotations["spaces"][word_i] + annotations["words"][word_i]
	return context


def get_wiki_triples(
		wikifier_annotations,
		min_pRank,
		context_size):
	# collect annotation mentions sorted by location
	annot_mentions = []
	for annotation in wikifier_annotations["annotations"]:
		for mention in annotation["support"]:
			annot_mentions.append(
				((mention["wFrom"], mention["wTo"]),
				annotation["url"]))
	annot_mentions.sort()

	triples = Counter()
	# find all mention pairs close enough and collect them with the context in between
	for m1_i, mention1 in enumerate(annot_mentions):
		for mention2 in annot_mentions[m1_i+1:]:
			mention_dist = mention2[0][0] - mention1[0][1]
			# stop when out of context range
			if mention_dist > context_size + 1:
				break

			# if in range and not overlapping or adjacent, collect triplet with context
			if mention_dist > 1:
				context = get_context_between(
					mention1[0][1],
					mention2[0][0],
					wikifier_annotations)

				triples[(mention1[1], context, mention2[1])] += 1

	return triples


def check_nell_patters(nell_patterns, triples):
	"""Check for and return triples which contain patters of NELL relations."""

	triples = {
		triple:cnt
		for triple, cnt in triples.iteritems()
		if triple[1] in nell_patterns}

	# extracted_rels = []
	# if triple[1] in nell_patterns:
	# 	for rel in nell_patterns[triple[1]]:
	# 		if

	return triples


def parse_rel_ptrns(rel_data_fnm):
	"""Parse relation patterns from jsonl dump."""
	logging.info('Reading relation data from %s' % rel_data_fnm)

	rels = []
	patterns = {}
	with open(rel_data_fnm) as infile:
		for line in infile:
			rel_data = json.loads(line)
			# only take relations with patterns
			if 'metadata' not in rel_data or 'extractionPatterns' not in rel_data['metadata']:
				continue

			# load (some of) the relation data
			try:
				rel = {
					'name': rel_data['relation_name'],
					'range': rel_data.get('relation_range', None),
					'domain': rel_data.get('relation_domain', None),
					'uri': rel_data['link'],
					'patterns': []
					}
			except:
				traceback.print_exception(*sys.exc_info())
				pdb.set_trace()
			rels.append(rel)
			# load patterns and link them to the relation
			for pattern in rel_data['metadata']['extractionPatterns']:
				# pattern is expected to be properly formatted
				order = None
				if pattern.startswith('arg1') and pattern.endswith('arg2'):
					order = '1-2'
				elif pattern.startswith('arg2') and pattern.endswith('arg1'):
					order = '2-1'
				else:
					print "skipped pattern for rel: %s - %s" % (rel['name'], pattern)
					continue
				# clip the explicit arguments and link relation and pattern
				ptrn = pattern[5:-5]
				rel['patterns'].append(ptrn)
				# the same pattern can indicate multiple relations
				pattern_rels = patterns.get(ptrn, [])
				pattern_rels.append({
					'rel': rel,
					'order': order})
				patterns[ptrn] = pattern_rels

	logging.info('parsed info about:\n%d relations\n%d patterns' % (len(rels), len(patterns)))

	return rels, patterns

def main_extract(args):
	# parse relations and patterns data
	rels, patterns = parse_rel_ptrns(args.rel_file)

	# patterns[", the EU's"] = "test_rel"

	# with open("data/FB_WA_event_annotated.json") as infile:
	with open(args.arts_file) as infile:
		article = json.load(infile).values()[0].values()[5]

	all_triples = get_wiki_triples(article["annotations"], 0.003, 5)

	nell_triples = check_nell_patters(patterns, all_triples)

	for x in nell_triples.iteritems():
		print x

	pdb.set_trace()


def main_dl_rels(args):
	relation_names = get_NELL_rel_names(args.rel_def)
	#missed_relations = download_relations(["acquired", "worksFor", "fakerel"], "zenodotus.jar", "TEST.jsonl")
	missed_relations = download_relations(relation_names, args.zenodotus_jar, args.outfile)

	print "\nmissed %d relations:" % len(missed_relations)
	for mr in missed_relations:
		print mr


if __name__ == '__main__':
	# create the top-level parser
	parser = argparse.ArgumentParser(prog="Nell pattern relation extraction code")
	subparsers = parser.add_subparsers()

	parser_extract = subparsers.add_parser('extract', help='extract relations from file')
	parser_extract.add_argument('rel_file', type=str, help='NELL relations data jsonl file')
	parser_extract.add_argument('arts_file', type=str, help='articles json file')
	parser_extract.set_defaults(action="extract")

	parser_dl = subparsers.add_parser('dl', help='download relation patterns from NELL')
	parser_dl.add_argument('rel_def', type=str, help='NELL relations tsv file')
	parser_dl.add_argument('zanodotus_jar', type=str, help='path ot zenodotus jar file')
	parser_dl.add_argument('outfile', type=str, help='output filename')
	parser_dl.set_defaults(action="dl")

	args = parser.parse_args()

	if args.action == 'extract':
		main_extract(args)
	elif args.action == 'dl':
		main_dl_rels(args)