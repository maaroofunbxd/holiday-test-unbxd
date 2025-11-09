#if from local run 
#ssh ec2-user@usejump.unbxd.io < ./runloadtest.sh
HOST=${1:-http://internal-a33ac7ecf86484bdb9a6a550a45a3f8d-2136975334.us-east-1.elb.amazonaws.com}

#from ubuntuserver
k6_run() {
    RPS=$1
    DURATION=$2
    HOST=$3
    which k6 && ./k6run.sh $RPS $DURATION $HOST
}

# Then run the load test:
k6_run 200 180s $HOST