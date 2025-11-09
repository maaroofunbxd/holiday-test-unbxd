#if from local run 
#ssh ec2-user@usejump.unbxd.io "bash -s" -- < ./accesscluster.sh "pwd"

#!/bin/bash
CMD="${1:-./clustermonitor.sh}"

ssh -t ai "
  sudo su - ai-prod-us-east-1-eks -c '
    cd ~/mrf/holiday-test-unbxd &&
    git fetch origin && git rebase origin/main &&
    ${CMD}
  '
"