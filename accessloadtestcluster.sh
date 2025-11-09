ssh -t ubuntu@ip-10-0-1-231 
cd ~/mrf/loadtest/holiday-test-unbxd/
git fetch origin && git rebase origin/main
./runloadtest.sh