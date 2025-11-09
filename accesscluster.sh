#if from local run 
#ssh ec2-user@usejump.unbxd.io "bash -s" -- < ./accesscluster.sh "pwd"

#!/bin/bash
CMD="${1:-./clustermonitor.sh}"

ssh -t ai "
  sudo su - ai-prod-us-east-1-eks -c '
    cd ~/mrf/holiday-test-unbxd &&
    git fetch origin >/dev/null 2>&1 && git rebase origin/main >/dev/null 2>&1 &&
    ${CMD}
  '
"