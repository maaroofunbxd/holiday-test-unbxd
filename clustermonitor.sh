#ai aws us
ssh usejump.unbxd.io
ssh -o StrictHostKeyChecking=yes ai
sudo su - ai-prod-us-east-1-eks
alias monitorpods='cd ~/mrf/holiday-test-unbxd/ && git fetch origin && git rebase origin/main && ./monitorrerankerpods.sh'
monitorpods