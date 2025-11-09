# Default command if none provided
CMD="${1:-./runloadtest.sh}"

ssh -t ubuntu@ip-10-0-1-231 "
  cd ~/mrf/loadtest/holiday-test-unbxd &&
  sudo ${CMD}
"