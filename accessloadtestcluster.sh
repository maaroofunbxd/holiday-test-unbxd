#!/bin/bash
# Interactive access to loadtest cluster - lands in holiday-test-unbxd directory
# 
# Usage: ./accessloadtestcluster.sh [script_to_run|@file]
# 
# Examples:
#   ./accessloadtestcluster.sh                   # Interactive mode
#   HOST=http://host.com ./accessloadtestcluster.sh "sh runloadtest.sh"  # Run with HOST
#   HOST=http://host.com ./accessloadtestcluster.sh @loadtestcluster-commands.txt  # Read commands from file
#   REGION=use-1d HOST=http://host.com ./accessloadtestcluster.sh @loadtestcluster-commands.txt  # Specify region and host

REGION=${REGION:-ap-southeast-1}
HOST=${HOST:-http://internal-aacb4a1ef44964e9a8d7979f74de2ea7-218368305.ap-southeast-1.elb.amazonaws.com}

# Check if first argument starts with @ (file reference)
if [[ "${1}" == @* ]]; then
  # Remove @ prefix and read from file
  CMD_FILE="${1:1}"
  if [ -f "$CMD_FILE" ]; then
    CMD=$(cat "$CMD_FILE")
    echo "Reading commands from file: $CMD_FILE"
  else
    echo "Error: File not found: $CMD_FILE"
    exit 1
  fi
else
  CMD="${1}"
fi

if [ -z "$CMD" ]; then
  # Interactive mode - no command provided
  echo "Entering interactive mode on loadtest cluster..."
  echo "Using REGION=$REGION, HOST=$HOST"
  echo "Suggested commands:"
  echo "  sh runloadtest.sh    # Run load test"
  echo "  ./k6run.sh           # Run k6 tests"
  echo "  kubectl get nodes    # List nodes"
  echo ""
  ssh -t ec2-user@usejump.unbxd.io "ssh -t ubuntu@ip-10-0-1-231 'cd ~/mrf/loadtest/holiday-test-unbxd && export REGION=$REGION && export HOST=$HOST && exec bash'"
else
  # Run specific command/script
  echo "Running with REGION=$REGION, HOST=$HOST"
  ssh -t ec2-user@usejump.unbxd.io "ssh -t ubuntu@ip-10-0-1-231 'cd ~/mrf/loadtest/holiday-test-unbxd && git fetch origin >/dev/null 2>&1 && git rebase origin/main >/dev/null 2>&1 && export REGION=$REGION && export HOST=$HOST && $CMD'"
fi

#HOST=$(ssh ec2-user@usejump.unbxd.io "bash -s" -- < ./accesscluster.sh "./get-service-host.sh reranker")
#ssh ec2-user@usejump.unbxd.io "bash -s" -- < ./accessloadtestcluster.sh "'sh runloadtest.sh'" $HOST

#REGION=use-1d HOST=http://internal-a33ac7ecf86484bdb9a6a550a45a3f8d-2136975334.us-east-1.elb.amazonaws.com sh accessloadtestcluster.sh
#./accessloadtestcluster.sh 'git fetch origin && git rebase origin/main && exit'

#HOST=http://$(./accesscluster.sh use-1d "./get-service-host.sh ner-demo" 2>&1 | grep -oE '[a-z0-9-]+\.[a-z0-9-]+\.elb\.amazonaws\.com' | head -1) REGION=use-1d ./accessloadtestcluster.sh @loadtestcluster-commands.txt
