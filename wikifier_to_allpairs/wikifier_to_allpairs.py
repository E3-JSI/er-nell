import os
import gzip
import pdb
import codecs
import argparse
from lxml import etree
#from nltk.tokenize.punkt import PunktSentenceTokenizer
from nltk.data import load
from nltk.tokenize import WhitespaceTokenizer
from itertools import izip

# dict of supported languages; {ISO_code: name}
LANG = {
	"cze": "czech",
	"dan": "danish",
	"dut": "dutch",
	"eng": "english",
	"est": "estonian",
	"fin": "finnish",
	"fre": "french",
	"ger": "german",
	"gre": "greek",
	"ita": "italian",
	"nob": "norwegian",
	"pol": "polish",
	"por": "portuguese",
	"slv": "slovene",
	"spa": "spanish",
	"swe": "swedish",
	"tur": "turkish"
}

# load nltk's pre-prepared sentence splitters
SENT_SPLITTER = {
	lang_code: load('tokenizers/punkt/{0}.pickle'.format(lang)) for lang_code, lang in LANG.iteritems()
}

# whitespace tokenizer used for splitting sentences into word spans
WHITESPACE_TOKNIZER = WhitespaceTokenizer()

CONTEXT_SIZE = 5

class TextSpan(object):
	def __init__(self, start, end, text, annotation = None):
		self.start, self.end = start, end
		self.annotation = annotation
		self.text = text
	def __repr__(self):
		return '[%d,%d]' % (self.start, self.end)
	def __eq__(self, other):
		# self == other
		return self.start == other.start and self.end == other.end
	# def __le__(self, other):
	# 	#return (self.begin, self.end) <= (other.begin, other.end)
	# 	return self.end <= other.begin
	def sub(self, other):
		# self <= other
		return self.start >= other.start and self.end <= other.end
	def strictsub(self, other):
		# self < other = self <= other and self != other
		return self.sub(other) and not self == other
	def is_annotated(self):
		return self.annotation is not None


def print_langs():
	"""
	Prints out the supported languages and their abbreviations.
	Language support is conditioned on sentence splitting capability. 
	Sentence splitters for more languages can be learned.
	"""
	print "supported languages: " 
	print '\n'.join(["    %s - %s" % (c,lang) for c,lang in LANG.iteritems()])


def get_articles_from_NF_file(filename, lang={'eng'}):
    """Parse the annotated articles from the Newsfeed xml file."""
    xml = etree.parse(filename)
    # take just the articles with desired languages
    return [article for article in xml.getroot() if article.xpath('lang')[0].text in lang]


def get_articles_from_annotator_file(filename):
    """Parse the annotated articles from the xml file obtained directly from the annotation service."""
    xml = etree.parse(filename)
    # the xml files from the annotator only have one item as root
    return [xml.getroot()]


def show_xml(el):
    """Utility function for pretty printing xml subtrees."""
    print etree.tostring(el, pretty_print=True)


def get_cleartext(article):
	"""Grab the article cleartext."""
	# read article cleartext in unicode and removing <p> tags if they are used
	# also strip trailing whitespace because they are irrelevant
	# do not impact word offsets and may interfere with the end punctuation removal
	
	# if xml contains tag "body-xlike" take its content, otherwise check whole xml
	if article.find('body-xlike'):
		cleartext_node = article.xpath('body-xlike/item/text')[0]
	else:
		cleartext_node = article.xpath('//item/text')[0]

	cleartext = etree.tostring(cleartext_node, method='text', encoding='unicode')
	return cleartext.rstrip().replace('\n', ' ')


def get_article_lang(article):
	"""Grab the article language (as ISO code) if specified in the xml."""
	return article.xpath('lang')[0].text


def parse_article_text(cleartext, lang):
	"""Grab the article cleartext and compute sentence and word spans."""
	# type should be Pythons internal unicode
	# print type(cleartext)
	
	# # use language-appropriate sentence splitter and then split each sentence into words on whitespace
	# spans = [((s,e), [x for x in WHITESPACE_TOKNIZER.span_tokenize(cleartext[s:e])]) for s,e in SENT_SPLITTER[article.xpath('lang')[0].text].span_tokenize(cleartext)]

	# split text to sentence spans
	sent_spans = SENT_SPLITTER[lang].span_tokenize(cleartext)
	# remove punctuation
	sent_spans = [(s,e-1) if cleartext[e-1] in {'.', '!', '?'} else (s,e) for s,e in sent_spans]

	# split the senteces into words
	spans = []
	for sent_start, sent_end in sent_spans:
		word_spans = []
		for relative_word_start, relative_word_end in WHITESPACE_TOKNIZER.span_tokenize(cleartext[sent_start:sent_end]):
			# if 'content' in cleartext[sent_start + word_start:sent_start + word_end]:
			# 	pdb.set_trace()

			# word start and end are computed relative to the sentence - recompute them so they are indices in cleartext
			word_start = relative_word_start + sent_start
			word_end = relative_word_end + sent_start

			# remove commas and semicolons - will add them back later
			if cleartext[word_end - 1] in {',', ';'}:
				word_end -= 1
			# create the textSpan object representing the word
			word_spans.append(TextSpan(word_start, word_end, cleartext[word_start:word_end]))
		# create the textSpan object representing the sentence
		spans.append( (TextSpan(sent_start, sent_end, cleartext[sent_start:sent_end]), word_spans) )

	# spans = [(TextSpan(s, e, cleartext[s:e]), [TextSpan(s + x[0], s + x[1], cleartext[s + x[0]:s + x[1]]) for x in WHITESPACE_TOKNIZER.span_tokenize(cleartext[s:e])]) for s,e in sent_spans]

	# # DEBUG
	# for (s,e), words in sentences:
	# 	print repr(cleartext[s:e]), '\n'
	# 	print [cleartext[s:e][ws:we] for ws,we in words], '\n\n'
	
	return spans


def get_xlike_annotations(article, cleartext):
	"""Collect xlike-type annotations and return them ordered by mentions."""
	# if xml contains tag "body-xlike" take its content, otherwise check whole xml
	if article.find('body-xlike'):
		annotations = article.xpath('body-xlike//annotation')
	else:
		annotations = article.xpath('//item/annotations/annotation')

	ordered_annotations = []	
	for annotation in annotations:
		for mention in annotation.xpath('mentions/mention'):
			# parse mention borders
			m_start = int(mention.get('start'))
			m_end = int(mention.get('end'))
			# build the textSpan object representing the anotation mention
			ordered_annotations.append( TextSpan(m_start, m_end, cleartext[m_start:m_end], annotation) )
	ordered_annotations = sorted(ordered_annotations, cmp = lambda a,b: a.end - b.start)

	return ordered_annotations


def get_allpairs_data(article, lang = None):
	"""Produce allpairs data from an annotated article."""
	# get article cleartext
	cleartext = get_cleartext(article)
	# get article language if not given
	if lang is None:
		lang = get_article_lang(article)
	# obtain sentence/word spans
	sw_spans = parse_article_text(cleartext, lang)

	# get annotations and order them by their mentions
	annotations = get_xlike_annotations(article, cleartext)

	# split annotations by sentences
	sent_annotations = []
	# iterate over ordered sentences
	for sent_span, _ in sw_spans:
		i = 0
		# collect all annotation mentions in the current sentence
		while i < len(annotations) and annotations[i].end <= sent_span.end:
			i += 1
		# pop the collected annotations
		sent_annotations.append(annotations[:i])
		annotations = annotations[i:]

	# # DEBUG
	# for sent, sas in izip(sw_spans, sent_annotations):
	# 	print sent[0]
	# 	for a in sas:
	# 		print '\t', a.start, a.end, a.annotation.get('displayName'), 'str: >%s<' % cleartext[a.start:a.end]
	
	# initialize allpairs data lists
	prec_contexts, succ_contexts, triples = [], [], []

	# compute allpairs data per sentence and collect it
	for (sent_span, word_spans), sas in izip(sw_spans, sent_annotations):
		pc, sc, tr = get_allpairs_data_sent(sent_span, word_spans, sas)
		prec_contexts.extend(pc)
		succ_contexts.extend(sc)
		triples.extend(tr)

	# pdb.set_trace()
	return prec_contexts, succ_contexts, triples


def get_allpairs_data_article_list(article_list, return_spec=['contexts', 'triples'], lang=None):
	"""
	Produce allpairs data from a list of annotated articles.
	Return either just the contexts or the triples or both.
	"""
	if not ('contexts' in return_spec or 'triples' in return_spec):
		raise ValueError("Return value should be specified. Possible flags: 'contexts', 'triples'.")

	if 'contexts' in return_spec:
		contexts = []
	if 'triples' in return_spec:
		triples = []

	for article in article_list:
		pc, sc, trip = get_allpairs_data(article, lang)
		if 'contexts' in return_spec:
			contexts.extend(sc)
			contexts.extend([(entity, context) for (context, entity) in pc])
		if 'triples' in return_spec:
			triples.extend(trip)

	if 'contexts' in return_spec and 'triples' in return_spec:
		return contexts, triples
	elif 'contexts' in return_spec:
		return contexts
	elif 'triples' in return_spec:
		return triples


def get_allpairs_data_article(article, return_spec=['contexts', 'triples'], lang=None):
	"""
	Produce allpairs data from an annotated article.
	Return either just the contexts or the triples or both.
	"""
	# wrap article in a single-element-list and call the list function
	return get_allpairs_data_article_list([article], return_spec, lang)


def to_sent_index(index, sentence_span):
	"""Get the index from the entire text recomputed to be relative to the sentence."""
	return index - sentence_span.start


def get_allpairs_data_sent(sentence_span, word_spans, annotations):
	"""Get allpairs data for given sentence."""
	merged_spans = []
	tmp_annotations = [a for a in annotations]
	for word_span in word_spans:
		# if the current word is already covered by the last span (annotation) in the merged spans skip it
		if merged_spans != [] and word_span.sub(merged_spans[-1]):
			continue
		# if the current word is covered by the next annotation add the annotation to the merged spans and skip the word
		elif tmp_annotations != [] and word_span.sub(tmp_annotations[0]):
			merged_spans.append(tmp_annotations.pop(0))
		# if the current word is not covered by any annotation add it to the merged spans
		else:
			merged_spans.append(word_span)

	# initialize allpairs data lists
	prec_contexts, succ_contexts, triples = [], [], []

	# iterate over the ordered sentence elemets (words and annotations) and grab contexts of annotations
	for el_i, element_span in enumerate(merged_spans):
		if element_span.is_annotated():

			####################################################################
			# CHECK PRECEDING CONTEXT
			####################################################################

			# go back over the preceding up to CONTEXT_SIZE + 1 elements and check if any are annotated
			# if yes ignore the preceding context (a triplet for it was genereted at the preceding annotatation)
			prec_contains_annotation = False
			for prev_i in xrange(el_i-1, el_i-1-(CONTEXT_SIZE + 1), -1):
				# stop when out of range
				if prev_i == -1:
					prev_i += 1
					break
				# if annotation found stop
				if merged_spans[prev_i].is_annotated():
					prec_contains_annotation = True
					break

			# if we reached the first element out of context, fix back the index
			if prev_i == el_i-(CONTEXT_SIZE + 1):
				prev_i += 1

			# if no annotation was found in preceding context collect it
			if not prec_contains_annotation and el_i != prev_i:
				# compute sentence-relative context borders
				context_start = to_sent_index(merged_spans[prev_i].start, sentence_span)
				context_end = to_sent_index(merged_spans[el_i-1].end, sentence_span)
				# collect the preceding context; add underscore to indicate where the entity occurs
				prec_contexts.append( (sentence_span.text[context_start:context_end] + '_' , element_span.text) )

			####################################################################
			# CHECK SUCCEEDING CONTEXT (+ TRIPLETS)
			####################################################################

			# go forward over the succeeding up to CONTEXT_SIZE + 1 elements and check if any are annotated
			# if yes collect a triplet
			succ_contains_annotation = False
			for succ_i in xrange(el_i+1, el_i+1+(CONTEXT_SIZE + 1)):
				# stop when out of range
				if succ_i == len(merged_spans):
					succ_i -= 1
					break
				# if annotation found stop and collect triple
				if merged_spans[succ_i].is_annotated():
					succ_contains_annotation = True
					# compute sentence-relative context borders
					context_start = to_sent_index(merged_spans[el_i+1].start, sentence_span)
					context_end = to_sent_index(merged_spans[succ_i-1].end, sentence_span)
					# collect the triple if the two annotations are not one next to the other
					if context_end - context_start > 1:
						triples.append( (element_span.text, sentence_span.text[context_start:context_end], merged_spans[succ_i].text) )
					break

			# if we reached the first element out of context, fix back the index
			if succ_i == el_i+1+(CONTEXT_SIZE + 1):
				succ_i -= 1

			# if no annotation was found in succeeding context collect it
			if not succ_contains_annotation and el_i != succ_i:
				# compute sentence-relative context borders
				context_start = to_sent_index(merged_spans[el_i+1].start, sentence_span)
				context_end = to_sent_index(merged_spans[succ_i].end, sentence_span)
				succ_contexts.append( (element_span.text, '_' + sentence_span.text[context_start:context_end]) )



	# # DEBUG
	# print ' '.join([ws.text if not ws.is_annotated() else '[%s]' % ws.text for ws in merged_spans]), '\n'

	return prec_contexts, succ_contexts, triples


def output_allpairs_data(filename, contexts=None, triples=None, append = False):
	"""
	Write allpairs data into separate files.
	Can also append data to existing files.
	"""
	# file opening mode set to append if specified
	file_mode = "a" if append else "w"

	# output each dataset in its own file with the appropriate suffix
	if contexts is not None:
		with codecs.open(filename + '_contexts', file_mode, encoding = 'utf8') as outfile:
			# if appending to file first add newline to separate from previous content
			if append:
				outfile.write('\n')
			# write data in tab-separated columns
			outfile.write('\n'.join('\t'.join(data_tuple) for data_tuple in contexts))

	if triples is not None:
		with codecs.open(filename + '_triples', file_mode, encoding = 'utf8') as outfile:
			# if appending to file first add newline to separate from previous content
			if append:
				outfile.write('\n')
			# write data in tab-separated columns
			outfile.write('\n'.join('\t'.join(data_tuple) for data_tuple in triples))


def process_dir(directory, lang, outfile):
	"""Extract allpairs data from all xml files in the given directory."""
	# initialize aggregation lists
	contexts, triples = [], []
	for filename in os.listdir(directory):
		# print progress
		filepath = os.path.join(directory, filename)
		print "processing:", filepath
		
		# read the (only) article in the file
		[article] = get_articles_from_annotator_file(filepath)
		# compute the allpairs data
		cs, ts = get_allpairs_data_article(article, lang=lang)
		# add the computed data to aggregation lists
		contexts.extend(cs)
		triples.extend(ts)

	output_allpairs_data(outfile, contexts=contexts, triples=triples)


def process_file(filename, lang, outfile):
	"""Extract allpairs data from all xml files in the given directory."""
	# initialize aggregation lists
	print "processing:", filename
		
	# read the (only) article in the file
	[article] = get_articles_from_annotator_file(filename)
	contexts, triples = get_allpairs_data_article(article, lang=lang)

	output_allpairs_data(outfile, contexts=contexts, triples=triples)



def underline(line):
	"""Print out a line and underline it with '-' characters."""
	return line + '\n' + '-' * len(line)


def test():
    articles = get_articles_from_NF_file('public-news-2016-02-18T09-29-59Z.xml.gz')

    for a in articles:
    	#spans = parse_article_text(a)

    	#annotations = get_xlike_annotations(a)

    	prec_contexts, succ_contexts, triples = get_allpairs_data(a)

    	print underline('PRECEDING CONTEXTS:')
    	print ('\n'.join( '%s    |    %s' % (context, annotation) for context, annotation in prec_contexts )).encode('utf8')

    	print '\n\n' + underline('SUCCEEDING CONTEXTS:')
    	print ('\n'.join( '%s    |    %s' % (annotation, context) for annotation, context in succ_contexts )).encode('utf8')

    	print '\n\n' + underline('TRIPLES:')
    	print ('\n'.join( '%s    |    %s    | %s' % (annotation1, context, annotation2) for annotation1, context, annotation2 in triples )).encode('utf8')

    	output_allpairs_data((prec_contexts, succ_contexts, triples), 'test', True)
    	pdb.set_trace()	


def main():
	# parse the input arguments
	parser = argparse.ArgumentParser()
	# parser.add_argument("directory", help="Path to directory with annotated article xml files.")
	parser.add_argument("lang", help="Language of the articles (ISO code). See supported languages using the --lsl option.")
	parser.add_argument("outfile", help="Path to output file(s). Three files will be created: [outfile]_prec, [outfile]_succ and [outfile]_triple")
	parser.add_argument("--lsl", action="store_true", default=False, help="print supported languages and exit")
	subparsers = parser.add_subparsers(help='process directory or single file?')

	parser_dir = subparsers.add_parser('dir', help='process xmls from a given directory')
	parser_dir.add_argument('dir_name', type=str, help='target directory name')
	parser_dir.set_defaults(action="process_dir")

	parser_dir = subparsers.add_parser('file', help='process given xml file')
	parser_dir.add_argument('filename', type=str, help='target xml file name')
	parser_dir.set_defaults(action="process_file")

	args = parser.parse_args()

	# output supported languages
	if args.lsl:
		print_langs()
		exit(1)

	if args.action == 'process_file':
		process_file(args.filename, args.lang, args.outfile)
	elif args.action == 'process_dir':
		process_dir(args.dir_name, args.lang, args.outfile)


if __name__ == '__main__':
    main()
