from eventregistry import *
import json
import argparse

# parse the input arguments
parser = argparse.ArgumentParser()
parser.add_argument("keyword", help="Keyword to categorize.")
parser.add_argument("--login", help="Event Registry login information. (format: 'username:password')")
parser.add_argument("--max_concept_suggestions", action="store", type=int, default=3, help="Maximum number of concept suggestions (default: 3)")
parser.add_argument("--max_related_events", action="store", type=int, default=3, help="Maximum number of related events (default: 3)")
parser.add_argument("--events_for_keyword", action="store_true", default=False, help="get [max_related_events] directly related to the given keyword (default: [max_related_events] events per suggested concept)")
parser.add_argument("--get_articles", action="store_true", default=False, help="get ER article URLs for the events")
args = parser.parse_args()

# connect to Event Registry and log in if login info provided
er = EventRegistry()
if args.login:
    if len(args.login.split(':')) != 2:
        print "incorrect login info format; expecting 'username:password'"
        exit(0)
    else:
        print er.login(*tuple(args.login.split(':')))['desc']

query_result = {}

# get top most likely URIc for the keyword - the number of suggestions is given as parameter
query_result['concept_suggestions'] = er.suggestConcepts(args.keyword)[:args.max_concept_suggestions]

# print json.dumps(query_result, indent=2)
# print

# get concept category information fo all suggested concepts
q = GetConceptInfo([cs['uri'] for cs in query_result['concept_suggestions']], returnInfo = ReturnInfo(conceptInfo = ConceptInfoFlags(conceptClassMembership = True, conceptClassMembershipFull = True)))
concept_info = er.execQuery(q)

# copy the category info into the result json
for concept_suggestion in query_result['concept_suggestions']:
    concept_suggestion['categories'] = concept_info[concept_suggestion['uri']]['conceptClassMembershipFull']
    concept_suggestion['topCategory'] = concept_info[concept_suggestion['uri']]['conceptClassMembership']

# return either top related events for the suggested concepts or directly for the keyord
if args.events_for_keyword:
# get related events for the keyword
    q = QueryEvents(lang=['eng']) # events should have english info
    q.addKeyword(args.keyword)
    q.addRequestedResult(
        RequestEventsInfo(
            count = 3,
            sortBy = "rel",
            returnInfo = ReturnInfo(
                eventInfo = EventInfoFlags(
                    title=True,
                    summary=False,
                    articleCounts=False,
                    concepts=False,
                    categories=False,
                    location=True,
                    date=True))))
    keyword_events = er.execQuery(q)

    # get articles for the events
    if args.get_articles:
        q = QueryEvent([event["uri"] for event in keyword_events['events']['results']])
        q.addRequestedResult(RequestEventArticleUris())
        event_articles = er.execQuery(q)


    query_result['related_events'] = []
    for event_info in keyword_events['events']['results']:
        # clean up the returned json
        event = {}
        event['uri'] = event_info['uri']
        event['fullUri'] = "http://eventregistry.org/event/" + event_info['uri']
        event['title'] = {'eng': event_info['title']['eng']}
        event['location'] = event_info['location']
        event['date'] = event_info['eventDate']
        event['articles'] = []
        if args.get_articles:
            event['articles'] = [
                "http://eventregistry.org/article/%s" % auri
                for auri in event_articles[event_info['uri']]['articleUris']['results']]

        query_result['related_events'].append(event)
else:
    # get related events for each concept
    for concept_suggestion in query_result['concept_suggestions']:
        q = QueryEvents(lang=['eng']) # events should have english info
        q.addConcept(concept_suggestion['uri'])
        q.addRequestedResult(
            RequestEventsInfo(
                count = 3,
                sortBy = "rel",
                returnInfo = ReturnInfo(
                    eventInfo = EventInfoFlags(
                        title=True,
                        summary=False,
                        articleCounts=False,
                        concepts=False,
                        categories=False,
                        location=True,
                        date=True))))
        concept_events = er.execQuery(q)

        # get articles for the events
        if args.get_articles:
            q = QueryEvent([event["uri"] for event in concept_events['events']['results']])
            q.addRequestedResult(RequestEventArticleUris())
            event_articles = er.execQuery(q)

        concept_suggestion['related_events'] = []
        for event_info in concept_events['events']['results']:
            # clean up the returned json
            event = {}
            event['uri'] = event_info['uri']
            event['fullUri'] = "http://eventregistry.org/event/" + event_info['uri']
            event['title'] = {'eng': event_info['title']['eng']}
            event['location'] = event_info['location']
            event['date'] = event_info['eventDate']
            if args.get_articles:
                event['articles'] = [
                    "http://eventregistry.org/article/%s" % auri
                    for auri in event_articles[event_info['uri']]['articleUris']['results']]

            concept_suggestion['related_events'].append(event)

print json.dumps(query_result, indent=2)