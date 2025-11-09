#!/bin/bash
# Interactive access to loadtest cluster - lands in holiday-test-unbxd directory
# 
# Usage: ./accessloadtestcluster.sh [script_to_run]
# 
# Examples:
#   ./accessloadtestcluster.sh                   # Interactive mode
#   ./accessloadtestcluster.sh "sh runloadtest.sh"  # Run load test
#   ./accessloadtestcluster.sh "./k6run.sh"      # Run k6 tests
#   ./accessloadtestcluster.sh "kubectl get nodes"  # Run kubectl command

CMD="${1}"

if [ -z "$CMD" ]; then
  # Interactive mode - no command provided
  echo "Entering interactive mode on loadtest cluster..."
  echo "Suggested commands:"
  echo "  sh runloadtest.sh    # Run load test"
  echo "  ./k6run.sh           # Run k6 tests"
  echo "  kubectl get nodes    # List nodes"
  echo ""
  ssh -t ubuntu@ip-10-0-1-231 "cd ~/mrf/loadtest/holiday-test-unbxd && exec bash"
else
  # Run specific command/script
  ssh -t ubuntu@ip-10-0-1-231 "cd ~/mrf/loadtest/holiday-test-unbxd && git fetch origin >/dev/null 2>&1 && git rebase origin/main >/dev/null 2>&1 && $CMD"
fi

#HOST=$(ssh ec2-user@usejump.unbxd.io "bash -s" -- < ./accesscluster.sh "./get-service-host.sh reranker")
#ssh ec2-user@usejump.unbxd.io "bash -s" -- < ./accessloadtestcluster.sh "'sh runloadtest.sh'" $HOST