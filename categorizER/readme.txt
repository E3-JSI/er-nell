This document describes the use of asknell's interface script  to Event Registry (ER) - categorizER.py. The script receives a keyword as input and returns likely concepts the keyword could identify in Event Registry along with their category information and a small set of related events as justification.

INSTALLATION:
-------------
The eventregistry Python API (https://github.com/gregorleban/EventRegistry) is needed. It is available over pip:
pip install eventregistry

This script assumes version 6.3.1 of the eventregistry module.

USE:
-------------------

usage: categorizER.py [-h] [--apiKey API]
                      [--max_concept_suggestions MAX_CONCEPT_SUGGESTIONS]
                      [--max_related_events MAX_RELATED_EVENTS]
                      [--events_for_keyword]
                      keyword

positional arguments:
  keyword               Keyword to categorize.

optional arguments:
  -h, --help            show this help message and exit
  --apiKey APIKEY       Event Registry API key (obtainable on you ER profile
                        page).
  --max_concept_suggestions MAX_CONCEPT_SUGGESTIONS
                        Maximum number of concept suggestions (default: 3)
  --max_related_events MAX_RELATED_EVENTS
                        Maximum number of related events (default: 3)
  --events_for_keyword  get [max_related_events] directly related to the given
                        keyword (default: [max_related_events] events per
                        suggested concept)


EXAMPLES:
---------
python categorizER.py --apiKey 6291ab8b-84fa-4752-89a5-14d790f445e9 Obama
python categorizER.py --apiKey 6291ab8b-84fa-4752-89a5-14d790f445e9 "Star Wars"


PARAMETERS:
-----------
Parameter values are set to desired values by default. They enable easy control over the query load NELL sends to ER. If we find in future that ER is overloaded by NELL or NELL needs more data per query, we will communicate new parameter values. At the moment the script returns at most 3 concept suggestions with each at most 3 related events.


APIKEY:
------
API key is needed since Event Registry limits the number of API requests. This way we can raise this limit for NELL.


OUTPUT:
.......
An example output can be seen in output.txt. The first two lines contain information regarding the ER host used and if the login was successful. The rest is JSON output from the ER.

The JSON structure is as follows:

{
  "concept_suggestions": [
    {
      "uri": "_Wikipedia_uri_",
      "label": {
        "eng": "_label_"
      },
      "score": _score_,
      "topCategory": [
        "_DBpedia_category_URI_"
      ],
      "type": "_type_",
      "id": "_id_",
      "categories": [
        "_DBpedia_category_URI_",
        ...
      ],
      "related_events": [
        {
          "fullUri": "_ER_event_URI_",
          "date": "_detected_event_date_",
          "location": {
            "country": {
              "type": "_locaton_type_",
              "label": {
                "eng": "_label_"
              }
            },
            "type": "_location_type_",
            "label": {
              "eng": "_label_"
            }
          },
          "uri": "_ER_event_id_",
          "title": {
            "eng": _extracted_event_title_"
          }
        },
        ...
      ]
    },
  ...
  ]
}


MAPPING TO ASKNELL:
-------------------
Using results to query "New York" in asknell for reference.

Each suggestion in the "concept_suggestions" list corresponds to a possible entity found in the asknell output top (e.g. new_york_city (city), new_york_city (stateorprovince), new_york (company)... for "New York"). It is identified by its Wikipedia URI, label, a simple type (person, org, ...) and an associated confidence score.

Each concept can also belong to a set of categories listed in the "categories" field (with the most likely one being repeated in "topCategory"). These categories correspond to the categories in the bottom half of asknell's output (such as "city" and "island" for new_york_city (city) in the case of "New York").

Finally each concept suggestion also has a list of related events collected by ER. Each event has a title ("title"/"eng") the link to its ER page ("fullUri"), extracted event date ("date") and location ("location"). Date and location may not be present for each event since ER may not have extracted them successfully. Location can be extracted as just country or country and city. In the latter case the "location" field will have a "country" subfield and the data in the "location" field is the location city. If there is no "country" subfield then the data in the "location" field is the location country. This data can be displayed in the why link for individual suggested concepts or its categories if it's a better match with asknell's structure.