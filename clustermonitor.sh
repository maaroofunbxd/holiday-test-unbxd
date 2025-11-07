ssh -t ai 'sudo su - ai-prod-us-east-1-eks'

monitorpods() {
    STATS_DURATION=$1
    cd ~/mrf/holiday-test-unbxd/
    git fetch origin && git rebase origin/main
    ./monitorrerankerpods.sh $STATS_DURATION
}

monitorpods 80;