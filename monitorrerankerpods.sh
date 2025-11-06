# watch -n 5 kubectl top pods -l algo=personalization
# kubectl top pods -l'algo in (personalization,ranking)' --no-headers
#kubectl top pod -lserving.knative.dev/service=ranking-f68e76d65c-predictor
# Cleanup function to kill background processes
# Trap Ctrl+C (SIGINT) and other termination signals

#run from ai-prod-us-east-1-eks@ip-10-0-40-71
cd ~/mrf/holiday-test-unbxd/ || { echo "❌ Not in holiday-test-unbxd directory. Exiting."; exit 1; }

source s3_upload.sh;
trap cleanup SIGINT SIGTERM

#git fetch origin && git rebase origin/main
rm -f .s3_upload_queue  # Clear any existing queue

time_ist=$(TZ=Asia/Kolkata date +%Y%m%d-%H%M)

# Run both monitor scripts simultaneously in background
echo "📊 Starting parallel monitoring..."
echo "  - Monitoring reranker-demo pods..."
python3 monitor-pod-resources.py --stats 80 --watch 5  -l "app in (reranker-demo)" --output ${time_ist}reranker-demo.csv &
MONITOR_PID1=$!

echo "  - Monitoring ranking/embedding pods..."
python3 monitor-pod-resources.py --stats 80 --watch 5  -l "algo in (ranking,embedding)" --output ${time_ist}ranking-embedding.csv &
MONITOR_PID2=$!

# Wait for both monitors to complete
echo "Waiting for both monitors to complete..."
echo "  (Press Ctrl+C to stop and clean up background processes)"
wait $MONITOR_PID1
wait $MONITOR_PID2
echo "✓ Both monitors completed"
echo ""

# Clear the trap after monitors complete
trap - SIGINT SIGTERM
# Upload all outputs to S3
echo "Uploading reranker-demo, ranking/embedding isvc resource metrics to S3"
source s3_upload.sh;
run_s3_upload ~/mrf/holiday-test-unbxd/.s3_upload_queue \



