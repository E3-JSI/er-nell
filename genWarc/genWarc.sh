#!/bin/bash

#this is a script that takes one URI and build its
#correspondent WARC file and stores the files in the warc
#directory

webpage=$1	#the webpage uri to be converted into warc
counter=$2      #a reference counter to build the filename

mkdir -p warc
mkdir -p tmp_files

wget --mirror --warc-file=file_$counter \
    --html-extension --convert-links \
    --execute robots=off --directory-prefix=. --span-hosts \
    --domains=example.com,www.example.com,cdn.example.com \
    --wait=10 \
    --random-wait \
    -P tmp_files \
    $webpage

mv *.warc.gz warc
rm -r tmp_files
