#!/bin/bash
# Usage: ./monitorrerankerpods.sh <SERVICE> <STATS_DURATION> <NAMESPACE>
# Example: ./monitorrerankerpods.sh reranker-demo 80 default
# Example: ./monitorrerankerpods.sh ner 80 search
# SERVICE: Service name to monitor (required)
# STATS_DURATION: How long to collect stats (in seconds, optional, default: 80)
# NAMESPACE: Kubernetes namespace to monitor (optional, default: search)

# watch -n 5 kubectl top pods -l algo=personalization
# kubectl top pods -l'algo in (personalization,ranking)' --no-headers
#kubectl top pod -lserving.knative.dev/service=ranking-f68e76d65c-predictor
# Cleanup function to kill background processes
# Trap Ctrl+C (SIGINT) and other termination signals

#run from ai-prod-us-east-1-eks@ip-10-0-40-71

# Check if SERVICE argument is provided (required)
if [ $# -eq 0 ]; then
    echo "Error: SERVICE argument is required"
    echo "Usage: $0 <SERVICE> [STATS_DURATION] [NAMESPACE]"
    echo "Example: $0 reranker-demo 80 default"
    echo "Example: $0 ner 80 search"
    exit 1
fi

SERVICE=$1
echo "Monitoring service: ${SERVICE}"

# Check if STATS_DURATION is provided, default to 80 if not
if [ $# -ge 2 ]; then
    STATS_DURATION=$2
    echo "Using stats duration: ${STATS_DURATION}s"
else
    STATS_DURATION=80
    echo "No stats duration provided, using default: ${STATS_DURATION}s"
fi

# Check if namespace is provided
if [ $# -ge 3 ]; then
    NAMESPACE=$3
    echo "Using namespace: ${NAMESPACE}"
else
    echo "No namespace provided, using default: search"
    NAMESPACE="search"
fi

# Function to get algo labels to monitor based on service
get_algo_labels() {
    local service=$1
    case "$service" in
        reranker-demo)
            echo "ranking,embeddings"
            ;;
        ner)
            echo "ner"
            ;;
        qcs)
            echo ""
            ;;
        *)
            echo ""
            ;;
    esac
}

# Get algo labels for the service
ALGO_LABELS=$(get_algo_labels "$SERVICE")

source s3_upload.sh;
trap cleanup SIGINT SIGTERM

#git fetch origin && git rebase origin/main
rm -f .s3_upload_queue  # Clear any existing queue

time_ist=$(TZ=Asia/Kolkata date +%Y%m%d-%H%M)

# Run monitor scripts
echo "📊 Starting monitoring..."

# Monitor the app
echo "  - Monitoring ${SERVICE} pods with label: app in (${SERVICE})"
python3 monitor-pod-resources.py --stats $STATS_DURATION --watch 5 -l "app in (${SERVICE})" -n $NAMESPACE --output ${time_ist}${SERVICE}.csv &
MONITOR_PID1=$!

# Monitor algo if applicable
if [ -n "$ALGO_LABELS" ]; then
    echo "  - Monitoring algo pods with label: algo in (${ALGO_LABELS})"
    python3 monitor-pod-resources.py --stats $STATS_DURATION --watch 5 -l "algo in (${ALGO_LABELS})" -n $NAMESPACE --output ${time_ist}${SERVICE}-algo.csv &
    MONITOR_PID2=$!
    
    # Wait for both monitors to complete
    echo "Waiting for both monitors to complete..."
    echo "  (Press Ctrl+C to stop and clean up background processes)"
    wait $MONITOR_PID1
    wait $MONITOR_PID2
    echo "✓ Both monitors completed"
else
    # Wait for single monitor to complete
    echo "Waiting for monitor to complete..."
    echo "  (Press Ctrl+C to stop and clean up background processes)"
    wait $MONITOR_PID1
    echo "✓ Monitor completed"
fi
echo ""

# Clear the trap after monitors complete
trap - SIGINT SIGTERM
# Upload all outputs to S3
echo "Uploading ${SERVICE} resource metrics to S3"
source s3_upload.sh;
run_s3_upload .s3_upload_queue



