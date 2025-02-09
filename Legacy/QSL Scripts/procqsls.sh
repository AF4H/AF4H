#!/bin/bash

if ! [[ "$1" =~ [0-9]{4}-[0-9]{2}-[0-9]{2} ]]; then
	echo "Usage: ${0} [YYYY-MM-DD]"
	echo "Got: ${0} ${1}"
	exit 1
fi

FETCH_AFTER=${1}
FETCH_BEFORE="$(date +%Y-%m-%d)"
echo "Fetching logged QSLs from ${FETCH_AFTER} to ${FETCH_BEFORE}"

DATA_APIURL='https://xmldata.qrz.com/xml/1.31/?'
DATA_APIUSER='NULL'
DATA_APIPASS='NULL'
DATA_AGENTID='AF4Hbash0.01'

LOGBOOK_APIURL='https://logbook.qrz.com/api'
LOGBOOK_KEY='NULL'

RAWLOGDIR="$(mktemp -d)"
OUTDIR="/home/af4h/QSL/out/"

#DEBUG=1

cleanup(){
	if [ "${pwd}" = "${RAWLOGDIR}" ]; then cd; fi
	rm ${RAWLOGDIR}/*
	rmdir ${RAWLOGDIR}
}

main(){
	initialize_data;
	initialize_logbook;
	fetch_logs;
	process_logs;
	make_labels;
	print_labels;
	cleanup;
}

initialize_data(){
if [ "${DEBUG}" = "1" ]; then echo "Beginning initialize_data subroutine"; fi
#Initialize our connection to the QRZ data server
# TODO Save the key (export variable?) and test the validity of...
# IOW don't request an apikey unless it's needed...

DATA_APIKEY=$(
	curl \
		-d username=${DATA_APIUSER} \
		-d password=${DATA_APIPASS} \
		-d agent=${DATA_AGENTID} \
		${DATA_APIURL} 2>/dev/null |
		while read_dom; do
			if [[ ${ENTITY} = "Key" ]]; then
				echo ${CONTENT}
			fi
		done
	)

	if [ "${DEBUG}" = "1" ]; then echo DATA_APIKEY=${DATA_APIKEY}; fi
	if [ -z "${DATA_APIKEY}" ]; then echo WARNING: API KEY ERROR; exit 255; fi
}

initialize_logbook(){
#	echo "DATE,TIME,CALLSIGN,FREQ,MODE,RST,VIA,FNAME,NAME,ADDR1,ADDR2,STATE,ZIP,COUNTRY" > ${RAWLOGDIR}/logs.csv
	echo '"CALLSIGN","FNAME","NAME","ADDR1","ADDR2","STATE","ZIP","COUNTRY","FREQ","MODE","DATE","RST","TIME"' > ${RAWLOGDIR}/logs.csv
}


fetch_logs(){
	if [ "${DEBUG}" = "1" ]; then echo "Beginning fetch_logs subroutine"; echo "Log file: ${RAWLOGDIR}/logbook.adif"; fi
	curl \
		-d KEY=${LOGBOOK_KEY} \
 		-d ACTION=FETCH \
		-d OPTION=BETWEEN:${FETCH_AFTER}+${FETCH_BEFORE},TYPE:ADIF \
		-o ${RAWLOGDIR}/_logbook.adif \
		--no-progress-meter \
		${LOGBOOK_APIURL}

#	Correct the way the logbook downlods and turn it into a basic .adif
	cat ${RAWLOGDIR}/_logbook.adif | sed s/\&lt\;/\</g | sed s/\&gt\;/\>/g | grep ^\< | sed -r 's/:[0-9]{1,5}//g' | xargs >${RAWLOGDIR}/logbook.adif 2>/dev/null

#Make sure we actually have logs...
	if [[ $(wc -c ${RAWLOGDIR}/logbook.adif | cut -d\  -f1) -lt 10 ]]; then
		echo Log file too small.  Did we even get anything\?
		echo Log file ${RAWLOGDIR}/logbook.adif
		exit 255
	fi

}

process_logs() {
	if [ "${DEBUG}" = "1" ]; then echo "Beginning log processing"; fi
	cat ${RAWLOGDIR}/logbook.adif | while read_dom; do
			case ${ENTITY} in
				qso_date)
					echo -n \"${CONTENT^^}\", >>${RAWLOGDIR}/logs.csv
				;;
				time_on)
					echo -n \"${CONTENT^^}\", >>${RAWLOGDIR}/logs.csv
				;;
				call)
 					echo -n \"${CONTENT^^}\", >>${RAWLOGDIR}/logs.csv
					fetch_qth ${CONTENT}
				;;
				freq)
				    	echo -n \"${CONTENT^^}\", >>${RAWLOGDIR}/logs.csv
				;;
				mode)
				    	echo -n \"${CONTENT^^}\", >>${RAWLOGDIR}/logs.csv
				;;
				rst_sent)
				    	echo -n \"${CONTENT^^}\", >>${RAWLOGDIR}/logs.csv
				;;
				eor)
					echo -e '\n' >>${RAWLOGDIR}/logs.csv
				;;
			esac
		done
	sed -i s/\ \"/\"/g ${RAWLOGDIR}/logs.csv
	sed -i s/\,$//g ${RAWLOGDIR}/logs.csv
	echo -e "\n" >>${RAWLOGDIR}/logs.csv
	sed -i '/./!d' ${RAWLOGDIR}/logs.csv
}

fetch_qth() {
	if [ "${DEBUG}" = "1" ]; then echo "fetch_qth: ${DATA_APIURL}s=${DATA_APIKEY}\&callsign=${1}";fi
	curl ${DATA_APIURL}s=${DATA_APIKEY}\&callsign=${1}  2>/dev/null |
		while read_dom; do
			case ${ENTITY} in
				fname)
					   echo -n \"${CONTENT^^}\", >>${RAWLOGDIR}/logs.csv
					;;
				name)
					   echo -n \"${CONTENT^^}\", >>${RAWLOGDIR}/logs.csv
					;;
				addr1)
					   echo -n \"${CONTENT^^}\", >>${RAWLOGDIR}/logs.csv
					;;
				addr2)
					   echo -n \"${CONTENT^^}\", >>${RAWLOGDIR}/logs.csv
					;;
				state)
					   echo -n \"${CONTENT^^}\", >>${RAWLOGDIR}/logs.csv
					;;
				zip)
					   echo -n \"${CONTENT^^}\", >>${RAWLOGDIR}/logs.csv
					;;
				country)
					   echo -n \"${CONTENT^^}\", >>${RAWLOGDIR}/logs.csv
					;;
			esac
		done
}

OUTLABEL="${OUTDIR}/$(date +%Y-%m-%d-%H-%M-%S)-"

make_labels() {
	if [ "${DEBUG}" = "1" ]; then echo "make_labels"; fi
	if [ ! -d "${OUTDIR}" ]; then mkdir -p ${OUTDIR}; fi
	glabels-3-batch -o ${OUTLABEL}-Cards.pdf -i ${RAWLOGDIR}/logs.csv ~/QSL/QSL-ConfirmationLabel.glabels >/dev/null 2>&1
	#it's easiest for address labels for the CSV labels to be doubled
	#vs having glabels make 2 copies
	while read -r line; do 
		if [ "${DEBUG}" = "1" ]; then echo dupline: ${line}; fi
                echo ${line} >> ${RAWLOGDIR}/logs-dup.csv
		echo ${line} >> ${RAWLOGDIR}/logs-dup.csv
	done < ${RAWLOGDIR}/logs.csv
	tail -n+2 ${RAWLOGDIR}/logs-dup.csv | grep -Ev '^$' > ${RAWLOGDIR}/logs-addr.csv
	glabels-3-batch -o ${OUTLABEL}-Addresses.pdf -i ${RAWLOGDIR}/logs-addr.csv ~/QSL/QSL-AddrLabel.glabels >/dev/null 2>&1
}


print_labels() {
	lp -d DYMO41-Right ${OUTLABEL}-Cards.pdf
	lp -d DYMO41-Left ${OUTLABEL}-Addresses.pdf
}

read_dom () {
	local IFS=\>
	read -d \< ENTITY CONTENT
}

main;

