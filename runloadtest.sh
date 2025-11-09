#if from local run 
#ssh ec2-user@usejump.unbxd.io < ./runloadtest.sh

#from ubuntuserver
k6-run() {
    RPS=$1
    DURATION=$2
    HOST=$3
    which k6 && ./k6run.sh $RPS $DURATION $HOST
}

# Then run the load test:
# k6-run 200 180s http://$HOST