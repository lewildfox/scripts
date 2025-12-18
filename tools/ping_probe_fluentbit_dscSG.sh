#!/bin/bash

# List of IPs to ping
declare -A targets
targets=(
    ["PE_TselBRN"]="180.240.72.218"
    ["PE_TselTBS"]="180.240.197.162"
    ["PE2BDS"]="180.240.197.161"
    ["PE3BTC"]="180.240.72.217"
    ["DEA_JKT"]="221.132.221.1"
    ["DEA_SBY"]="221.132.221.9"
    ["DEA_GYG"]="39.192.64.17"
)

# Graphite server config
GRAPHITE_HOST="vans.telin.co.id"
GRAPHITE_PORT=2003
HOSTNAME="DSCSGDAMP1"
TIMESTAMP=$(date +%s)
METRIC="GrxPingPE"

# Fluentbit server config
FLUENTBIT_HOST="192.168.117.64"
FLUENTBIT_PORT=5140

date 

# Loop through targets
for name in "${!targets[@]}"; do
    ip=${targets[$name]}
    echo "Pinging $ip ($name)..."

    output=$(ssh admusr@180.240.196.178 "ping -c 10 $ip" 2>/dev/null | grep "loss\|rtt")
    echo "$output"
    # Extract packet loss
    packet_loss=$(echo "$output" | grep "packet loss" | awk -F',' '{print $3}' | awk '{print $1}' | tr -d '%')
    sr=$((100 - $packet_loss))

    # Extract RTT values
    rtt_line=$(echo "$output" | grep "rtt")
    if [[ -n "$rtt_line" ]]; then
        IFS='/' read -r rtt_min rtt_avg rtt_max rtt_mdev <<< "$(echo "$rtt_line" | awk -F'=' '{print $2}' | awk '{print $1}')"
    else
        rtt_min=0; rtt_avg=0; rtt_max=0; rtt_mdev=0
    fi

    # Prepare Graphite lines
    metrics="
$METRIC.$HOSTNAME.$name.sr $sr $TIMESTAMP
$METRIC.$HOSTNAME.$name.rtt_min $rtt_min $TIMESTAMP
$METRIC.$HOSTNAME.$name.rtt_avg $rtt_avg $TIMESTAMP
$METRIC.$HOSTNAME.$name.rtt_max $rtt_max $TIMESTAMP
$METRIC.$HOSTNAME.$name.rtt_mdev $rtt_mdev $TIMESTAMP
"
    echo "$metrics" | nc "$GRAPHITE_HOST" "$GRAPHITE_PORT"

    # Check for packet loss > 30% and send to Fluentbit
    if [[ "$packet_loss" -gt 30 ]]; then
        fluent_msg="DSC SG ping packetloss >30% to Telkomsel $name $ip"
        echo "Sending alert to Fluentbit: $fluent_msg"
        echo "$fluent_msg" | nc "$FLUENTBIT_HOST" "$FLUENTBIT_PORT"
    fi
done
