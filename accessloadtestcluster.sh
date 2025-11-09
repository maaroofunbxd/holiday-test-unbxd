# Default command if none provided
CMD="${1:-runloadtest.sh}"
HOST=${2:-http://internal-a33ac7ecf86484bdb9a6a550a45a3f8d-2136975334.us-east-1.elb.amazonaws.com}
ssh -t ubuntu@ip-10-0-1-231 "
  cd ~/mrf/loadtest/holiday-test-unbxd && 
  git fetch origin >/dev/null 2>&1 && git rebase origin/main >/dev/null 2>&1 &&
  chmod -R u+rwX . &&
  sh $CMD $HOST
"

#HOST=$(ssh ec2-user@usejump.unbxd.io "bash -s" -- < ./accesscluster.sh "./get-service-host.sh reranker")
#ssh ec2-user@usejump.unbxd.io "bash -s" -- < ./accessloadtestcluster.sh "'sh runloadtest.sh'" $HOST