#if from local run 
#ssh ec2-user@usejump.unbxd.io < ./clustermonitor.sh

ssh -t ai 'sudo su - ai-prod-us-east-1-eks'
#ssh -t ai 'sudo su - ai-ap-southeast-1-eks' 

monitorpods() {
    STATS_DURATION=$1
    NAMESPACE=$2
    cd ~/mrf/holiday-test-unbxd/
    git fetch origin && git rebase origin/main
    ./monitorrerankerpods.sh $STATS_DURATION $NAMESPACE
}

monitorpods 200 search;