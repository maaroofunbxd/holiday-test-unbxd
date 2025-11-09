#if from local run 
#ssh ec2-user@usejump.unbxd.io < ./runloadtest.sh

#from ubuntuserver
k6-run() {
    RPS=$1
    DURATION=$2
    which k6 && ./k6run.sh $RPS $DURATION
}

k6-run 200 180s;