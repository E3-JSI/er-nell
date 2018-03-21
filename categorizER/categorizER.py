from eventregistry import *
import json
import argparse
import pdb

# parse the input arguments
parser = argparse.ArgumentParser()
parser.add_argument("keyword", help="Keyword to categorize.")
parser.add_argument("outputFile", help="Path to output file. (json)")
parser.add_argument("-a", "--apiKey", help="Event Registry API key (obtainable on you ER profile page).")
parser.add_argument("-c", "--max_concept_suggestions", action="store", type=int, default=3, help="Maximum number of concept suggestions (default: 3)")
parser.add_argument("-e", "--max_related_events", action="store", type=int, default=3, help="Maximum number of related events (default: 3)")
parser.add_argument("-k", "--events_for_keyword", action="store_true", default=False, help="get [max_related_events] directly related to the given keyword (default: [max_related_events] events per suggested concept)")
parser.add_argument("-ga", "--get_articles", action="store_true", default=False, help="get ER article URLs for the events")
parser.add_argument("-ma", "--max_articles_per_event", action="store", type=int, default=-1, help="Maximum number of articles per event (default: all)")
args = parser.parse_args()

# connect to Event Registry and log in if API key provided

if args.apiKey:
    er = EventRegistry(apiKey = args.apiKey)
else:
    er = EventRegistry()

query_result = {}

# get top most likely URIc for the keyword - the number of suggestions is given as parameter
query_result['concept_suggestions'] = er.suggestConcepts(args.keyword)[:args.max_concept_suggestions]

# get concept category information fo all suggested concepts
q = GetConceptInfo(
    [cs['uri'] for cs in query_result['concept_suggestions']],
    returnInfo = ReturnInfo(
        conceptInfo = ConceptInfoFlags(
            conceptClassMembership = True,
            conceptClassMembershipFull = True)))
concept_info = er.execQuery(q)

# copy the category info into the result json
for concept_suggestion in query_result['concept_suggestions']:
    concept_suggestion['categories'] = concept_info[concept_suggestion['uri']]['conceptClassMembershipFull']
    concept_suggestion['topCategory'] = concept_info[concept_suggestion['uri']]['conceptClassMembership']

# returned event info is the same for both types of queries
returnInfoSpec = ReturnInfo(
        eventInfo = EventInfoFlags(
            title = True,
            summary = False,
            articleCounts = False,
            concepts = False,
            categories = False,
            location = True,
            date = True))


def build_event(event_info):
    """Clean up and format the event info returned by ER."""
    event = {}
    event['uri'] = event_info['uri']
    event['fullUri'] = "http://eventregistry.org/event/" + event_info['uri']
    event['title'] = {'eng': event_info['title']['eng']}
    event['location'] = event_info['location']
    event['date'] = event_info['eventDate']
    return event


def get_articles(event_uri, er, max_articles):
    """Download articles for the event."""
    # prepare query for articles
    artQuery = QueryEventArticlesIter(event_uri)
    # build an iterator over evet articles
    artIter = artQuery.execQuery(
        er,
        maxItems = max_articles,
        returnInfo = ReturnInfo(
            articleInfo = ArticleInfoFlags(
                bodyLen = 0,
                title = False,
                body = False,
                eventUri = False)))
    # collect article source urls
    articles = [article["url"] for article in artIter]
    return articles


# return either top related events for the suggested concepts or directly for the keyord
if args.events_for_keyword:
# get related events for the keyword
    q = QueryEventsIter(
        keywords = args.keyword,
        lang = ['eng']) # events should have english info)
    keyword_event_iter = q.execQuery(
        er,
        sortBy = 'rel',
        maxItems = args.max_related_events,
        returnInfo = returnInfoSpec)

    query_result['related_events'] = []
    for event_info in keyword_event_iter:
        # clean up the returned json
        event = build_event(event_info)
        # get event articles if specified
        if args.get_articles:
            event['articles'] = get_articles(event['uri'], er, args.max_articles_per_event)

        query_result['related_events'].append(event)
else:
    # get related events for each concept
    for concept_suggestion in query_result['concept_suggestions']:
        q = QueryEventsIter(
            conceptUri=concept_suggestion['uri'],
            lang=['eng']) # events should have english info

        concept_event_iter = q.execQuery(
            er,
            sortBy = 'rel',
            maxItems = args.max_related_events,
            returnInfo = returnInfoSpec)

        concept_suggestion['related_events'] = []
        for event_info in concept_event_iter:
            # clean up the returned json
            event = build_event(event_info)
            # get event articles if specified
            if args.get_articles:
                event['articles'] = get_articles(event['uri'], er, args.max_articles_per_event)

            concept_suggestion['related_events'].append(event)

print "outputing results to: %s" % args.outputFile
with open(args.outputFile, 'w') as outfile:
    json.dump(query_result, outfile, indent=2)
