ssh -t ai 'sudo su - ai-prod-us-east-1-eks'

monitorpods() {
    STATS_DURATION=$1
    cd ~/mrf/holiday-test-unbxd/
    git fetch origin && git rebase origin/main
    ./monitorrerankerpods.sh $STATS_DURATION
}

#kubectl annotate deployment ranking-ec7d9fa992-predictor-00327-deployment -nsearch autoscaling.knative.dev/scale-down-delay=0s --overwrite
monitorpods 200;