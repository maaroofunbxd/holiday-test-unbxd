#ubuntuserver
ssh usejump.unbxd.io
ssh -o StrictHostKeyChecking=yes ubuntu@ip-10-0-1-231
alias k6-run='cd ~/mrf/loadtest/holiday-test-unbxd/ && git fetch origin && git rebase origin/main && which k6 && ./k6run.sh' 
k6-run