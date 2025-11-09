#if from local run 
#ssh ec2-user@usejump.unbxd.io < ./accesscluster.sh

ssh -t ai 'sudo su - ai-prod-us-east-1-eks'
#ssh -t ai 'sudo su - ai-ap-southeast-1-eks' 

cd ~/mrf/holiday-test-unbxd/
git fetch origin && git rebase origin/main

./clustermonitor.sh


