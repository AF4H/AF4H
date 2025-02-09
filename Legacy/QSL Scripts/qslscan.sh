#!/bin/bash

STORPATH="~/QSL/cards"

if [ -z ${3} ]; then
	echo "USAGE: ${0} (QSL|SWL|HFTIX) (CALLSIGN) (DATE:YYYY-MM-DD)"
	exit 255
fi

scanimage -d 'brother5:bus2;dev6' --format=png --resolution 100 --AutoDocumentSize=yes --source "Automatic Document Feeder(left aligned,Duplex)" --batch-count=2 --batch-print --batch="${STORPATH}/${1^^}/${2^^}:${3^^}-%d.png"

