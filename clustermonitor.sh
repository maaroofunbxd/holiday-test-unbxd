monitorpods() {
    SERVICE=$1
    STATS_DURATION=$2
    NAMESPACE=$3
    ./monitorrerankerpods.sh $SERVICE $STATS_DURATION $NAMESPACE
}

monitorpods $1 $2 $3;