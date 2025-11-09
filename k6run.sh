#!/bin/bash
# Usage: ./k6run.sh <RPS> <DURATION> <HOST>
# Example: ./k6run.sh 100 60s http://internal-a33ac7ecf86484bdb9a6a550a45a3f8d-2136975334.us-east-1.elb.amazonaws.com

# Check if arguments are provided
if [ $# -ne 3 ]; then
    echo "Usage: $0 <RPS> <DURATION> <HOST>"
    echo "Example: $0 100 60s http://service-host.example.com"
    exit 1
fi

RPS=$1
DURATION=$2
HOST=$3

echo "Running load test with RPS=$RPS, DURATION=$DURATION, and HOST=$HOST"

#run from ubuntu@ip-10-0-1-231
FILES=$(find "$(pwd)/reranker-logs" -maxdepth 1 -name "*.jsonl" -type f | tr '\n' ',' | sed 's/,$//')
#20251103-1810
time_ist=$(TZ=Asia/Kolkata date +%Y%m%d-%H%M)
k6 run -e RPS=$RPS -e DURATION=$DURATION -e HOST=$HOST -e INPUT_FILES="$FILES" --out json=${time_ist}raw-data.json --summary-export=${time_ist}summary.json reranker-load-test.js

# Add k6 output files to upload queue (using absolute paths)
echo "$(pwd)/${time_ist}raw-data.json" >> .s3_upload_queue
echo "$(pwd)/${time_ist}summary.json" >> .s3_upload_queue
echo "📝 k6 output files added to upload queue"
source s3_upload.sh;
run_s3_upload ~/mrf/loadtest/holiday-test-unbxd/.s3_upload_queue

#docker run --rm -v `pwd`:/data -i grafana/k6 run - < reranker-load-test-recs.js