# kubectl set env deploy/reranker-demo -nsearch --list
# kubectl set env deployment/reranker-demo -nsearch --containers="pyreranker" REDIS_CACHE_TTL=80
# aws s3 ls s3://unbxd-des/rerankerloadtest/
# aws s3 cp s3://unbxd-des/rerankerloadtest/ . --recursive --exclude "*" --include "*.jsonl"
# watch -n 5 kubectl top pods -l algo=personalization
# kubectl top pods -l'algo in (personalization,ranking)' --no-headers

#run from ai-prod-us-east-1-eks@ip-10-0-40-71
cd ~/mrf; cd holiday-test-unbxd/;  
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
wait $MONITOR_PID1
wait $MONITOR_PID2
echo "✓ Both monitors completed"
echo ""

cd ..


#run from ubuntu@ip-10-0-1-231
cd ~/mrf/loadtest/holiday-test-unbxd/;  
FILES=$(find "$(pwd)/reranker-logs" -maxdepth 1 -name "*.jsonl" -type f | tr '\n' ',' | sed 's/,$//')
time_ist=$(TZ=Asia/Kolkata date +%Y%m%d-%H%M)
k6 run -e RPS=40 -e DURATION=60s -e HOST=http://internal-a33ac7ecf86484bdb9a6a550a45a3f8d-2136975334.us-east-1.elb.amazonaws.com -e INPUT_FILES="$FILES" --out json=${time_ist}raw-data.json --summary-export=${time_ist}summary.json reranker-load-test.js

# Add k6 output files to upload queue (using absolute paths)
echo "$(pwd)/${time_ist}raw-data.json" >> .s3_upload_queue
echo "$(pwd)/${time_ist}summary.json" >> .s3_upload_queue
echo "📝 k6 output files added to upload queue"

cd ..


# ========================================
# Upload all files in queue to S3
# ========================================
echo ""
echo "========================================="
echo "📤 Uploading all outputs to S3..."
echo "========================================="

# Collect all queue files from both directories
QUEUE_FILES=(
    ~/mrf/holiday-test-unbxd/.s3_upload_queue
    ~/mrf/loadtest/holiday-test-unbxd/.s3_upload_queue
)

upload_count=0
for queue_file in "${QUEUE_FILES[@]}"; do
    if [ -f "$queue_file" ]; then
        echo "Processing queue: $queue_file"
        
        # Read queue file and upload each file
        while IFS= read -r file_path; do
            # Skip empty lines
            [ -z "$file_path" ] && continue
            
            if [ -f "$file_path" ]; then
                aws s3 cp "$file_path" s3://unbxd-des/rerankerloadtest/ && echo "  ✓ Uploaded: $(basename $file_path)" || echo "  ✗ Failed: $(basename $file_path)"
                ((upload_count++))
            else
                echo "  ⚠ File not found: $file_path"
            fi
        done < "$queue_file"
        
        # Clean up queue file
        rm -f "$queue_file"
    fi
done

echo "========================================="
echo "✓ Uploaded $upload_count file(s) to S3"
echo "========================================="
echo ""


