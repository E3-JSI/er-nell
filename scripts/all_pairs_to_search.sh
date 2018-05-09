#!/bin/bash

#simple script to prepare an all pairs data file
#to be used as search paramenter file on the generation
#of WARC files

all_pairs_file=$1

rm search_param.out

while read line; do

    ctx_pattern=$(echo "$line" | cut -f1 | sed -e 's/_//')
   
    echo $ctx_pattern >> search_param.out

done < $all_pairs_file
