#if from local run 
#ssh ec2-user@usejump.unbxd.io < ./runloadtest.sh
HOST=${1:-http://internal-aacb4a1ef44964e9a8d7979f74de2ea7-218368305.ap-southeast-1.elb.amazonaws.com}
REGION=${REGION:-ap-southeast-1}

#from ubuntuserver
k6_run() {
    RPS=$1
    DURATION=$2
    HOST=$3
    SERVICE=${4:-reranker}
    K6_SCRIPT=${5:-reranker-load-test.js}
    export REGION=$REGION
    which k6 && ./k6run.sh $RPS $DURATION $HOST $SERVICE $K6_SCRIPT
}

stress_test() {
    START_RPS=$1
    MAX_RPS=$2
    RAMP_DURATION=$3
    HOLD_DURATION=$4
    HOST=$5
    SERVICE=${6:-reranker}
    K6_SCRIPT=${7:-reranker-stress-test.js}
    export REGION=$REGION
    which k6 && ./run-stress-test.sh $START_RPS $MAX_RPS $RAMP_DURATION $HOLD_DURATION $HOST $SERVICE $K6_SCRIPT
}

# Then run the load test:
echo "Running with REGION=$REGION"
#k6_run 100 600s $HOST ner reranker-load-test.js

# Or run stress test to find max RPS:
stress_test 0 25 5m 2m $HOST qcs reranker-stress-test.js

#HOST=http://internal-aacb4a1ef44964e9a8d7979f74de2ea7-218368305.ap-southeast-1.elb.amazonaws.com REGION=ap-southeast-1 ./accessloadtestcluster.sh
#HOST=http://internal-a33ac7ecf86484bdb9a6a550a45a3f8d-2136975334.us-east-1.elb.amazonaws.com REGION=use-1d ./accessloadtestcluster.sh
#MAX rps
#cd reranker-use-1d-logs/ ; echo "$(cat *.jsonl | wc -w) / (10*60)" | bc -l
