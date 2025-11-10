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
#   REGION=us-east-1 ./accesscluster.sh "./clustermonitor.sh"  # Specify region

REGION=${REGION:-ap-southeast-1}
CMD="${1}"

# Set region-specific SSH access
if [ "$REGION" = "use-1d" ]; then
  SSH_HOST="ai"
  SSH_USER="ai-prod-us-east-1-eks"
elif [ "$REGION" = "ap-southeast-1" ]; then
  SSH_HOST="10.204.19.93"
  SSH_USER="ai-ap-southeast-1-eks"
else
  echo "Error: Unsupported region '$REGION'. Supported regions: use-1d, ap-southeast-1"
  exit 1
fi

echo "Using REGION=$REGION (SSH: $SSH_HOST, User: $SSH_USER)"

if [ -z "$CMD" ]; then
  # Interactive mode - no command provided
  echo "Entering interactive mode on cluster..."
  echo "Suggested commands:"
  echo "  ./clustermonitor.sh              # Monitor pods"
  echo "  ./get-service-host.sh reranker   # Get reranker host"
  echo "  kubectl get pods -n search       # List pods"
  echo ""
  ssh -t ec2-user@usejump.unbxd.io "ssh -t $SSH_HOST \"sudo su - $SSH_USER -c 'cd ~/mrf/holiday-test-unbxd && exec bash'\""
else
  # Run specific command/script
  ssh -t ec2-user@usejump.unbxd.io "ssh -t $SSH_HOST \"sudo su - $SSH_USER -c 'cd ~/mrf/holiday-test-unbxd && git fetch origin >/dev/null 2>&1 && git rebase origin/main >/dev/null 2>&1 && ${CMD}'\""
fi

#REGION=use-1d sh accesscluster.sh 'whoami'