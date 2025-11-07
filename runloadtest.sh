#ubuntuserver
ssh -t ubuntu@ip-10-0-1-231 
 k6-run() {
    cd ~/mrf/loadtest/holiday-test-unbxd/
    git fetch origin && git rebase origin/main
    which k6 && ./k6run.sh
}

k6-run;