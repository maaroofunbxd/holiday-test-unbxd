# Default command if none provided
CMD="${1:-runloadtest.sh}"
HOST=${2:-http://internal-a33ac7ecf86484bdb9a6a550a45a3f8d-2136975334.us-east-1.elb.amazonaws.com}
ssh -t ubuntu@ip-10-0-1-231 "
  cd ~/mrf/loadtest/holiday-test-unbxd && 
  git fetch origin >/dev/null 2>&1 && git rebase origin/main >/dev/null 2>&1 &&
  echo '=== DEBUG INFO ===' &&
  echo 'Current user:' && whoami && id &&
  echo 'Current directory:' && pwd &&
  echo 'reranker-load-test.js permissions:' && ls -la reranker-load-test.js &&
  echo 'reranker-ap-southeast-1-logs directory permissions:' && ls -ld reranker-ap-southeast-1-logs/ &&
  echo 'Sample files in logs directory:' && ls -la reranker-ap-southeast-1-logs/ | head -5 &&
  echo 'Can I read a sample file:' && head -1 reranker-ap-southeast-1-logs/reranker_requests_reranker-7b7c7b946c-qr5lh_goreranker_20251101_164000.jsonl 2>&1 | head -c 100 &&
  echo '' && echo '=== END DEBUG ===' &&
  sh $CMD $HOST
"

#HOST=$(ssh ec2-user@usejump.unbxd.io "bash -s" -- < ./accesscluster.sh "./get-service-host.sh reranker")
#ssh ec2-user@usejump.unbxd.io "bash -s" -- < ./accessloadtestcluster.sh "'sh runloadtest.sh'" $HOST