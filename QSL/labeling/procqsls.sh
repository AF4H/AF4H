#!/bin/bash

source .env

if ! [[ "$1" =~ [0-9]{4}-[0-9]{2}-[0-9]{2} ]]; then
	echo "Usage: ${0} [YYYY-MM-DD]"
	echo "Got: ${0} ${1}"
	exit 1
fi

FETCH_AFTER=${1}
FETCH_BEFORE="$(date +%Y-%m-%d)"
echo "Fetching logged QSLs from ${FETCH_AFTER} to ${FETCH_BEFORE}"

RAWLOGDIR="$(mktemp -d)"

main(){
	if [ "${DEBUG}" = "1" ]; then initialdebug; fi
	initialize_data;
	initialize_logbook;
	fetch_logs;
	process_logs;
	make_labels;
	print_labels;
	cleanup;
}

cleanup(){
	if [ "${pwd}" = "${RAWLOGDIR}" ]; then cd; fi
	rm ${RAWLOGDIR}/*
	rmdir ${RAWLOGDIR}
}

initialdebug(){
	echo 'Variable definitions from .env:'
	for i in `cat .env | grep [A-Z]\= | cut -d\= -f1`; do
		echo "${i}: $( eval echo \$${i})"
	done
}

initialize_data(){
	if [ "${DEBUG}" = "1" ]; then echo "Beginning initialize_data subroutine"; fi

	# 1. Check if we have a cached key and a timestamp
	local cache_valid=0
	if [ -n "${QRZ_APIKEY}" ] && [ -n "${QRZ_APIKEY_DATE}" ]; then
		# Calculate the age of the key in seconds
		local current_time=$(date +%s)
		local key_time=$(date -d "${QRZ_APIKEY_DATE}" +%s 2>/dev/null || echo 0)
		local age=$(( current_time - key_time ))

		# 86400 seconds = 24 hours (we use 80000 to be safe and clear before expiry)
		if [ $age -lt 80000 ] && [ $age -ge 0 ]; then
			cache_valid=1
			if [ "${DEBUG}" = "1" ]; then echo "Using cached QRZ_APIKEY from ${QRZ_APIKEY_DATE}"; fi
		fi
	fi

	# 2. If the cache isn't valid, fetch a new key from QRZ
	if [ $cache_valid -eq 0 ]; then
		if [ "${DEBUG}" = "1" ]; then echo "Cached key missing or expired. Requesting a new one..."; fi
		
		local new_key=$(
			curl -s \
				-d username=${QRZ_APIUSER} \
				-d password=${QRZ_APIPASS} \
				-d agent=${QRZ_AGENTID} \
				${QRZ_APIURL} |
				while read_dom; do
					if [[ ${ENTITY} = "Key" ]]; then
						echo ${CONTENT}
					fi
				done
		)

		if [ -z "${new_key}" ]; then 
			echo "WARNING: API KEY ERROR"
			exit 255
		fi

		# Update the active variable environment
		QRZ_APIKEY="${new_key}"
		QRZ_APIKEY_DATE="$(date '+%Y-%m-%d %H:%M:%S')"

		# 3. Save the new values back into the .env file
		# Strip out existing keys to prevent duplicates, then append the fresh ones
		sed -i '/^QRZ_APIKEY=/d' .env
		sed -i '/^QRZ_APIKEY_DATE=/d' .env
		echo "QRZ_APIKEY='${QRZ_APIKEY}'" >> .env
		echo "QRZ_APIKEY_DATE='${QRZ_APIKEY_DATE}'" >> .env
		
		if [ "${DEBUG}" = "1" ]; then echo "Saved new QRZ_APIKEY to .env"; fi
	fi
}

initialize_logbook(){
	# Strict order maps directly to the array printer below
	echo '"MODE","TIME","RST","DATE","CALL","FREQ"' > ${RAWLOGDIR}/logs.csv
	echo '"CALL","FNAME","NAME","ADDR1","ADDR2","STATE","ZIP","COUNTRY"' | tee ${RAWLOGDIR}/addr.csv > ${RAWLOGDIR}/addr-dup.csv
}

fetch_logs(){
	if [ "${DEBUG}" = "1" ]; then echo "Beginning fetch_logs subroutine"; echo "Log file: ${RAWLOGDIR}/logbook.adif"; echo "API Key: ${QRZ_LOGBOOK_APIKEY}";fi
	curl \
		-d KEY="${QRZ_LOGBOOK_APIKEY}" \
		-d ACTION=FETCH \
		-d OPTION=BETWEEN:${FETCH_AFTER}+${FETCH_BEFORE},TYPE:ADIF \
		-o ${RAWLOGDIR}/logbook-raw.adif \
		--no-progress-meter \
		${QRZ_LOGBOOK_APIURL}

	sed 's/&lt;/</g; s/&gt;/>/g' "${RAWLOGDIR}/logbook-raw.adif" \
	| sed 's/^.*ADIF=//' \
	| grep '^<' \
	| sed -r 's/:[0-9]{1,5}//g' \
	> "${RAWLOGDIR}/logbook.adif" 2>/dev/null

	if [[ $(wc -c ${RAWLOGDIR}/logbook.adif | cut -d\  -f1) -lt 10 ]]; then
		echo Log file too small. Did we even get anything\?
		echo Log file ${RAWLOGDIR}/logbook.adif
		exit 255
	fi
}

process_logs() {
	if [ "${DEBUG}" = "1" ]; then echo "Beginning log processing"; fi
	
	# Declare local associative array to buffer our QSO tags
	declare -A qso
	
	cat ${RAWLOGDIR}/logbook.adif | while read_dom; do
		if [ "${DEBUG}" = "1" ]; then echo Entity ${ENTITY}\: ${CONTENT^^}; fi
		
		case ${ENTITY,,} in
			call)     qso[call]="${CONTENT^^}" ;;
			qso_date) qso[date]="${CONTENT^^}" ;;
			freq_rx)  qso[freq]="${CONTENT^^}" ;;
			time_on)  qso[time]="${CONTENT^^}" ;;
			mode)     qso[mode]="${CONTENT^^}" ;;
			rst_rcvd) qso[rst]="${CONTENT^^}"  ;;
			eor)
				# Pull address from XML data service before saving QSO
				fetch_qth "${qso[call]}"
				
				# Write out tags in the exact header schema order
				echo "\"${qso[mode]}\",\"${qso[time]}\",\"${qso[rst]}\",\"${qso[date]}\",\"${qso[call]}\",\"${qso[freq]}\"" >> ${RAWLOGDIR}/logs.csv
				
				# Flush tracking array for the next QSO block
				unset qso
				declare -A qso
				;;
		esac
	done
}

fetch_qth() {
	if [ "${DEBUG}" = "1" ]; then echo "fetch_qth: ${QRZ_APIURL}s=${QRZ_APIKEY}&callsign=${1}";fi

	declare -A addr
	addr[call]="${1^^}"

	local qrz_xml
	qrz_xml=$(curl -s --user-agent "${QRZ_AGENTID}" "${QRZ_APIURL}s=${QRZ_APIKEY}&callsign=${1}")

	xml_get() {
		echo "$qrz_xml" | grep -oP "(?<=<$1>).*?(?=</$1>)" | head -1
	}

	addr[fname]=$(xml_get fname)
	addr[name]=$(xml_get name)
	addr[addr1]=$(xml_get addr1)
	addr[addr2]=$(xml_get addr2)
	addr[state]=$(xml_get state)
	addr[zip]=$(xml_get zip)
	addr[country]=$(xml_get country)

	for field in fname name addr1 addr2 state zip country; do
		addr[$field]="${addr[$field]^^}"
	done

	echo "\"${addr[call]}\",\"${addr[fname]}\",\"${addr[name]}\",\"${addr[addr1]}\",\"${addr[addr2]}\",\"${addr[state]}\",\"${addr[zip]}\",\"${addr[country]}\"" >> ${RAWLOGDIR}/addr.csv
}

OUTLABEL="${QSL_OUTDIR}/$(date +%Y-%m-%d-%H-%M-%S)"

make_labels() {
	if [ "${DEBUG}" = "1" ]; then echo "make_labels"; fi
	if [ ! -d "${OUTLABEL}" ]; then mkdir -p ${OUTLABEL}; fi
	if [ "${DEBUG}" = "1" ]; then echo "RAWLOGDIR ${RAWLOGDIR}"; fi
	if [ "${DEBUG}" = "1" ]; then echo "QSL_LABELDIR ${QSL_LABELDIR}"; fi
	glabels-3-batch -o ${OUTLABEL}/Cards.pdf -i ${RAWLOGDIR}/logs.csv ${CARD_LABEL} >/dev/null 2>&1
	
	tail -n+2 ${RAWLOGDIR}/addr.csv | while read -r line; do 
		if [ "${DEBUG}" = "1" ]; then echo dupline: ${line}; fi
		echo ${line} >> ${RAWLOGDIR}/addr-dup.csv
		echo ${line} >> ${RAWLOGDIR}/addr-dup.csv
	done
	echo '"CALL","FNAME","NAME","ADDR1","ADDR2","STATE","ZIP","COUNTRY"' > ${RAWLOGDIR}/logs-addr.csv
	tail -n+2 ${RAWLOGDIR}/addr-dup.csv | grep -Ev '^$' >> ${RAWLOGDIR}/logs-addr.csv
	glabels-3-batch -o ${OUTLABEL}/Addresses.pdf -i ${RAWLOGDIR}/logs-addr.csv ${ADDR_LABEL} >/dev/null 2>&1
}

print_labels() {
	if [ -z "${CARD_PRINTER}" ]; then 
		echo "Card Printer not set, not printing cards"
	else
		lp -d "${CARD_PRINTER}" ${OUTLABEL}/Cards.pdf
	fi

	if [ -z "${ADDR_PRINTER}" ]; then
		echo "Address label printer not set, not printing address labels"
	else
		lp -d "${ADDR_PRINTER}" ${OUTLABEL}/Addresses.pdf
	fi
}

read_dom() {
    local IFS=\>

    read -d \< ENTITY CONTENT
    local rc=$?

    # Strip CR/LF
    CONTENT=$(echo -n "$CONTENT" | tr -d '\r\n')
    ENTITY=$(echo -n "$ENTITY" | tr -d '\r\n')

    # Only stop if we hit EOF and didn't read anything
    if [[ $rc -ne 0 && -z "$ENTITY" && -z "$CONTENT" ]]; then
        return 1
    fi

    return 0
}

main;
