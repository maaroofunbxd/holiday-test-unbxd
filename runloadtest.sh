#if from local run 
#ssh ec2-user@usejump.unbxd.io < ./runloadtest.sh
HOST=${1:-http://internal-aacb4a1ef44964e9a8d7979f74de2ea7-218368305.ap-southeast-1.elb.amazonaws.com}
REGION=${REGION:-ap-southeast-1}

#from ubuntuserver
k6_run() {
    RPS=$1
    DURATION=$2
    HOST=$3
    export HOST=$HOST
    export REGION=$REGION
    which k6 && ./k6run.sh $RPS $DURATION $HOST
}

# Then run the load test:
echo "Running with REGION=$REGION"
k6_run 50 60s $HOST

#HOST=http://internal-aacb4a1ef44964e9a8d7979f74de2ea7-218368305.ap-southeast-1.elb.amazonaws.com REGION=ap-southeast-1 ./accessloadtestcluster.sh
#HOST=http://internal-a33ac7ecf86484bdb9a6a550a45a3f8d-2136975334.us-east-1.elb.amazonaws.com REGION=use-1d ./accessloadtestcluster.sh
#MAX rps
#cd reranker-use-1d-logs/ ; echo "$(cat *.jsonl | wc -w) / (10*60)" | bc -l
