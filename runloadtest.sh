#if from local run 
#ssh ec2-user@usejump.unbxd.io < ./runloadtest.sh
HOST=${1:-http://internal-aacb4a1ef44964e9a8d7979f74de2ea7-218368305.ap-southeast-1.elb.amazonaws.com}

#from ubuntuserver
k6_run() {
    RPS=$1
    DURATION=$2
    HOST=$3
    which k6 && ./k6run.sh $RPS $DURATION $HOST
}

# Then run the load test:
k6_run 100 180s $HOST