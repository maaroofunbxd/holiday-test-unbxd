# Default command if none provided
CMD="${1:-runloadtest.sh}"
HOST=${2:-http://internal-a33ac7ecf86484bdb9a6a550a45a3f8d-2136975334.us-east-1.elb.amazonaws.com}
ssh -t ubuntu@ip-10-0-1-231 "
  cd ~/mrf/loadtest/holiday-test-unbxd && 
  git fetch origin >/dev/null 2>&1 && git rebase origin/main >/dev/null 2>&1 &&
  echo '=== DEBUG INFO ===' &&
  echo 'Current user:' && whoami && id &&
  echo 'Looking for .jsonl files:' && find reranker-ap-southeast-1-logs/ -name '*.jsonl' -type f | head -5 &&
  echo 'Permissions on .jsonl files:' && find reranker-ap-southeast-1-logs/ -name '*.jsonl' -type f -exec ls -la {} \; | head -10 &&
  echo 'Can I read the specific file from error:' && ls -la reranker-ap-southeast-1-logs/reranker_requests_reranker-7b7c7b946c-qr5lh_goreranker_20251101_164000.jsonl 2>&1 &&
  echo 'Trying to read it:' && head -c 100 reranker-ap-southeast-1-logs/reranker_requests_reranker-7b7c7b946c-qr5lh_goreranker_20251101_164000.jsonl 2>&1 &&
  echo '' && echo '=== END DEBUG ===' &&
  sh $CMD $HOST
"

#HOST=$(ssh ec2-user@usejump.unbxd.io "bash -s" -- < ./accesscluster.sh "./get-service-host.sh reranker")
#ssh ec2-user@usejump.unbxd.io "bash -s" -- < ./accessloadtestcluster.sh "'sh runloadtest.sh'" $HOST