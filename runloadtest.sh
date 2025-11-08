#if from local run 
#ssh ec2-user@usejump.unbxd.io < ./runloadtest.sh

#from ubuntuserver
ssh -t ubuntu@ip-10-0-1-231 
 k6-run() {
    RPS=$1
    DURATION=$2
    cd ~/mrf/loadtest/holiday-test-unbxd/
    git fetch origin && git rebase origin/main
    which k6 && ./k6run.sh $RPS $DURATION
}

k6-run 200 180s;