monitorpods() {
    STATS_DURATION=$1
    NAMESPACE=$2
    ./monitorrerankerpods.sh $STATS_DURATION $NAMESPACE
}

monitorpods 660 search;