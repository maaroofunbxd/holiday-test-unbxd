ssh -t ai 'sudo su - ai-prod-us-east-1-eks'

monitorpods() {
    cd ~/mrf/holiday-test-unbxd/
    git fetch origin && git rebase origin/main
    ./monitorrerankerpods.sh
}

monitorpods;