#ubuntuserver
ssh -t ubuntu@ip-10-0-1-231 
 k6-run() {
    RPS=$1
    DURATION=$2
    cd ~/mrf/loadtest/holiday-test-unbxd/
    git fetch origin && git rebase origin/main
    which k6 && ./k6run.sh $RPS $DURATION
}

k6-run 120 60s;