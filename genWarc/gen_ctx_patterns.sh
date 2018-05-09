#!/bin/bash

#this script should take a CPL's learned patterns file
#and generate a WARC file for each of its contextual patterns

apiKey=$1
search_param_file=$2

rm -f er_search_results.json.tmp
rm -f webpage_list.tmp
mkdir -p logs

#flag to build a filename for links of returned pages
counter=0

#for all learned patterns
while read line; do

    search_param=$line

    #perform search query on ER
    python ../categorizER/categorizER.py --apiKey $apiKey --get_articles -e 100 -r 40 "$search_param" er_search_results.json.tmp

    #parse the url from the search results
    python uriExtractor.py er_search_results.json.tmp webpage_list.tmp

    #for all webpages extracted from ER
    while read line; do

        #send control message
        echo generating WARC for $line based on search param $ctx_pattern

        #generate a WARC file of the webpage
        ./genWarc $line $counter

        let counter++

    done < webpage_list.tmp

    #create log file
    mv webpage_list.tmp logs/webpage_list.$counter

done < $search_param_file

tar cfv logs.tar.gz logs
