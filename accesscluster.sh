#if from local run 
#ssh ec2-user@usejump.unbxd.io "bash -s" -- < ./accesscluster.sh "pwd"

#!/bin/bash
# Interactive access to cluster - lands in holiday-test-unbxd directory
# 
# Usage: ./accesscluster.sh [REGION] [script_to_run|@file]
# 
# Examples:
#   ./accesscluster.sh                           # Interactive mode
#   ./accesscluster.sh use-1d "./clustermonitor.sh"  # Run with specific region
#   ./accesscluster.sh use-1d @commands.txt      # Read commands from file with region
#   ./accesscluster.sh ap-southeast-1 "kubectl get pods -n search"  # Run kubectl command

REGION=${1:-ap-southeast-1}

# Check if second argument starts with @ (file reference)
if [[ "${2}" == @* ]]; then
  # Remove @ prefix and read from file
  CMD_FILE="${2:1}"
  if [ -f "$CMD_FILE" ]; then
    CMD=$(cat "$CMD_FILE")
    echo "Reading commands from file: $CMD_FILE"
  else
    echo "Error: File not found: $CMD_FILE"
    exit 1
  fi
else
  CMD="${2}"
fi

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