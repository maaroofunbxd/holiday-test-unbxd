# kubectl set env deploy/reranker-demo -nsearch --list
# kubectl set env deployment/reranker-demo -nsearch --containers="pyreranker" REDIS_CACHE_TTL=80
# aws s3 ls s3://unbxd-des/rerankerloadtest/
# aws s3 cp s3://unbxd-des/rerankerloadtest/ . --recursive --exclude "*" --include "*.jsonl"
# watch -n 5 kubectl top pods -l algo=personalization
# kubectl top pods -l'algo in (personalization,ranking)' --no-headers
#kubectl top pod -lserving.knative.dev/service=ranking-f68e76d65c-predictor
# Cleanup function to kill background processes
# Trap Ctrl+C (SIGINT) and other termination signals
source s3_upload.sh;
trap cleanup SIGINT SIGTERM

#run from ai-prod-us-east-1-eks@ip-10-0-40-71
cd ~/mrf; cd holiday-test-unbxd/;  
git fetch origin && git rebase origin/main
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
source s3_upload.sh;
run_s3_upload ~/mrf/holiday-test-unbxd/.s3_upload_queue \

cd ..


#run from ubuntu@ip-10-0-1-231
cd ~/mrf/loadtest/holiday-test-unbxd/; 
git fetch origin && git rebase origin/main 
FILES=$(find "$(pwd)/reranker-logs" -maxdepth 1 -name "*.jsonl" -type f | tr '\n' ',' | sed 's/,$//')
time_ist=$(TZ=Asia/Kolkata date +%Y%m%d-%H%M)
k6 run -e RPS=40 -e DURATION=60s -e HOST=http://internal-a33ac7ecf86484bdb9a6a550a45a3f8d-2136975334.us-east-1.elb.amazonaws.com -e INPUT_FILES="$FILES" --out json=${time_ist}raw-data.json --summary-export=${time_ist}summary.json reranker-load-test.js

# Add k6 output files to upload queue (using absolute paths)
echo "$(pwd)/${time_ist}raw-data.json" >> .s3_upload_queue
echo "$(pwd)/${time_ist}summary.json" >> .s3_upload_queue
echo "📝 k6 output files added to upload queue"
source s3_upload.sh;
run_s3_upload ~/mrf/loadtest/holiday-test-unbxd/.s3_upload_queue

cd ..
