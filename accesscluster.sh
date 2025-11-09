#if from local run 
#ssh ec2-user@usejump.unbxd.io "bash -s" -- < ./accesscluster.sh "pwd"

#!/bin/bash
# Interactive access to cluster - lands in holiday-test-unbxd directory
# 
# Usage: ./accesscluster.sh [script_to_run]
# 
# Examples:
#   ./accesscluster.sh                           # Interactive mode
#   ./accesscluster.sh "./clustermonitor.sh"     # Run monitoring script
#   ./accesscluster.sh "kubectl get pods -n search"  # Run kubectl command
#   ./accesscluster.sh "./get-service-host.sh reranker"  # Get service host

CMD="${1}"

if [ -z "$CMD" ]; then
  # Interactive mode - no command provided
  echo "Entering interactive mode on cluster..."
  echo "Suggested commands:"
  echo "  ./clustermonitor.sh              # Monitor pods"
  echo "  ./get-service-host.sh reranker   # Get reranker host"
  echo "  kubectl get pods -n search       # List pods"
  echo ""
  ssh -t ec2-user@usejump.unbxd.io 'ssh -t ai "sudo su - ai-prod-us-east-1-eks -c \"cd ~/mrf/holiday-test-unbxd && exec bash\""'
else
  # Run specific command/script
  ssh -t ec2-user@usejump.unbxd.io "ssh -t ai \"sudo su - ai-prod-us-east-1-eks -c 'cd ~/mrf/holiday-test-unbxd && git fetch origin >/dev/null 2>&1 && git rebase origin/main >/dev/null 2>&1 && ${CMD}'\""
fi