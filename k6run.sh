#!/bin/bash
# Usage: ./k6run.sh <RPS> <DURATION> <HOST> [SERVICE] [K6_SCRIPT]
# Example: ./k6run.sh 100 60s http://internal-a33ac7ecf86484bdb9a6a550a45a3f8d-2136975334.us-east-1.elb.amazonaws.com
# Example with service: ./k6run.sh 100 60s http://host.com reranker
# Example with custom script: ./k6run.sh 100 60s http://host.com reranker reranker-stress-test.js

# Check if arguments are provided
if [ $# -lt 3 ]; then
    echo "Usage: $0 <RPS> <DURATION> <HOST> [SERVICE] [K6_SCRIPT]"
    echo "Example: $0 100 60s http://service-host.example.com"
    echo "Example with service: $0 100 60s http://service-host.example.com reranker"
    echo "Example with custom script: $0 100 60s http://host.com reranker reranker-stress-test.js"
    echo ""
    echo "Environment variables:"
    echo "  SERVICE        - Service name for log directory (default: reranker)"
    echo "  REGION         - Region for log directory (default: ap-southeast-1)"
    echo "  INPUT_FILES    - Override input files (comma-separated)"
    exit 1
fi

RPS=$1
DURATION=$2
HOST=$3
SERVICE=${4:-${SERVICE:-reranker}}  # Use 4th arg, fallback to env var, default to "reranker"

# K6 script to run - can be 5th argument or default
K6_SCRIPT=${5:-${K6_SCRIPT:-reranker-load-test.js}}

echo "Running load test with RPS=$RPS, DURATION=$DURATION, HOST=$HOST, SERVICE=$SERVICE"
echo "Using K6 script: $K6_SCRIPT"

#run from ubuntu@ip-10-0-1-231
WORK_DIR=$(pwd)
REGION=${REGION:-ap-southeast-1}

# Find input files - can be overridden via INPUT_FILES env var
if [ -z "$INPUT_FILES" ]; then
    FILES=$(find "$WORK_DIR/${SERVICE}-${REGION}-logs" -maxdepth 1 -name "*.jsonl" -type f 2>/dev/null | tr '\n' ',' | sed 's/,$//')
    if [ -z "$FILES" ]; then
        echo "⚠️  WARNING: No JSONL files found in ${SERVICE}-${REGION}-logs/"
        echo "You can set INPUT_FILES env var to specify files manually"
    fi
else
    FILES=$INPUT_FILES
fi

#20251103-1810
time_ist=$(TZ=Asia/Kolkata date +%Y%m%d-%H%M)

# # Fix ownership of jsonl files if they're owned by root
# sudo chown -R ubuntu:ubuntu ${SERVICE}-ap-southeast-1-logs/ 2>/dev/null || true

# Run k6 WITHOUT sudo (snap confinement prevents sudo k6 from accessing /home/ubuntu)
k6 run -e RPS=$RPS -e DURATION=$DURATION -e HOST=$HOST -e INPUT_FILES="$FILES" --out json=${time_ist}raw-data.json --summary-export=${time_ist}summary.json "$WORK_DIR/$K6_SCRIPT"

# Add k6 output files to upload queue (using absolute paths)
if [ -f ".s3_upload_queue" ] && [ -f "s3_upload.sh" ]; then
    echo "$(pwd)/${time_ist}raw-data.json" >> .s3_upload_queue
    echo "$(pwd)/${time_ist}summary.json" >> .s3_upload_queue
    echo "📝 k6 output files added to upload queue"
    echo ""
    echo "📤 Full S3 Paths:"
    echo "   s3://unbxd-des/rerankerloadtest/${time_ist}raw-data.json"
    echo "   s3://unbxd-des/rerankerloadtest/${time_ist}summary.json"
    echo ""
    source s3_upload.sh;
    run_s3_upload ~/mrf/loadtest/holiday-test-unbxd/.s3_upload_queue
fi

#docker run --rm -v `pwd`:/data -i grafana/k6 run - < reranker-load-test-recs.js