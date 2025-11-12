#!/bin/bash

# 🔥 K6 STRESS TEST - Find Maximum RPS
# This script gradually ramps up load to find the breaking point

# Usage examples:
# ./run-stress-test.sh 10 500 5m 2m http://host.com                              # Use defaults
# ./run-stress-test.sh 50 1000 10m 3m http://host.com reranker                   # With service
# ./run-stress-test.sh 50 1000 10m 3m http://host.com reranker custom-stress.js  # Custom script

set -e  # Exit on error

# ============================================================================
# CONFIGURATION
# ============================================================================

# Check if all required arguments are provided
if [ $# -lt 5 ]; then
    echo "Usage: $0 <START_RPS> <MAX_RPS> <RAMP_DURATION> <HOLD_DURATION> <HOST> [SERVICE] [K6_SCRIPT]"
    echo ""
    echo "Examples:"
    echo "  $0 10 500 5m 2m http://service-host.example.com"
    echo "  $0 50 1000 10m 3m http://internal-load-balancer.com reranker"
    echo "  $0 50 1000 10m 3m http://host.com reranker olympus-stress-test.js"
    echo ""
    echo "Parameters:"
    echo "  START_RPS       - Starting RPS (e.g., 10)"
    echo "  MAX_RPS         - Maximum target RPS (e.g., 500)"
    echo "  RAMP_DURATION   - Time to ramp from START to MAX (e.g., 5m, 10m)"
    echo "  HOLD_DURATION   - Time to hold at MAX RPS (e.g., 2m, 5m)"
    echo "  HOST            - Service host URL (required)"
    echo "  SERVICE         - Service name for log directory (optional, default: reranker)"
    echo "  K6_SCRIPT       - K6 test script to run (optional, default: reranker-stress-test.js)"
    exit 1
fi

# Arguments
START_RPS=$1
MAX_RPS=$2
RAMP_DURATION=$3
HOLD_DURATION=$4
HOST=$5
SERVICE=${6:-${SERVICE:-reranker}}
K6_SCRIPT=${7:-${K6_SCRIPT:-reranker-stress-test.js}}

# Region and file discovery
WORK_DIR=$(pwd)
REGION=${REGION:-ap-southeast-1}

# Find all JSONL files - can be overridden via INPUT_FILES env var
if [ -z "$INPUT_FILES" ]; then
    FILES=$(find "$WORK_DIR/${SERVICE}-${REGION}-logs" -maxdepth 1 -name "*.jsonl" -type f 2>/dev/null | tr '\n' ',' | sed 's/,$//' || echo "")
else
    FILES=$INPUT_FILES
fi

# Timestamp for output files
TIME_IST=$(TZ=Asia/Kolkata date +%Y%m%d-%H%M)

# ============================================================================
# VALIDATION
# ============================================================================

if [ -z "$FILES" ]; then
    echo "⚠️  WARNING: No JSONL files found in ${SERVICE}-${REGION}-logs/"
    echo "    Make sure you have extracted payloads before running the test."
    echo "    You can set INPUT_FILES env var to specify files manually"
    echo ""
    read -p "    Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# ============================================================================
# DISPLAY TEST CONFIGURATION
# ============================================================================

echo ""
echo "🔥 K6 STRESS TEST CONFIGURATION"
echo "═══════════════════════════════════════════════════════════"
echo "  📈 Start RPS:        $START_RPS"
echo "  🎯 Target Max RPS:   $MAX_RPS"
echo "  ⏱️  Ramp Duration:    $RAMP_DURATION"
echo "  ⏸️  Hold Duration:    $HOLD_DURATION"
echo "  🌐 Host:             $HOST"
echo "  🔧 Service:          $SERVICE"
echo "  📜 K6 Script:        $K6_SCRIPT"
echo "  🗂️  Input Files:      $(echo "$FILES" | tr ',' '\n' | wc -l) JSONL files"
echo "  📂 Region:           $REGION"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "📝 Test will ramp from $START_RPS to $MAX_RPS RPS over $RAMP_DURATION"
echo "   then hold at $MAX_RPS for $HOLD_DURATION to find the breaking point."
echo ""

# Countdown before starting
for i in {3..1}; do
    echo "Starting in $i..."
    sleep 1
done
echo "🚀 Starting stress test..."
echo ""

# ============================================================================
# RUN K6 STRESS TEST
# ============================================================================

# Build k6 command
K6_CMD="k6 run"
K6_CMD="$K6_CMD -e START_RPS=$START_RPS"
K6_CMD="$K6_CMD -e MAX_RPS=$MAX_RPS"
K6_CMD="$K6_CMD -e RAMP_DURATION=$RAMP_DURATION"
K6_CMD="$K6_CMD -e HOLD_DURATION=$HOLD_DURATION"
K6_CMD="$K6_CMD -e HOST=$HOST"

if [ -n "$FILES" ]; then
    K6_CMD="$K6_CMD -e INPUT_FILES=\"$FILES\""
fi

# Output files
K6_CMD="$K6_CMD --out json=${TIME_IST}stress-test-raw.json"
K6_CMD="$K6_CMD --summary-export=${TIME_IST}stress-test-summary.json"
K6_CMD="$K6_CMD $WORK_DIR/$K6_SCRIPT"

# Execute
echo "⚙️  Running: $K6_CMD"
echo ""

eval $K6_CMD

# ============================================================================
# POST-TEST ACTIONS
# ============================================================================

echo ""
echo "✅ Stress test completed!"
echo ""
echo "📊 Output files:"
echo "   - ${TIME_IST}stress-test-raw.json"
echo "   - ${TIME_IST}stress-test-summary.json"
echo ""

# Add to S3 upload queue if script exists
if [ -f ".s3_upload_queue" ] && [ -f "s3_upload.sh" ]; then
    echo "$(pwd)/${TIME_IST}stress-test-raw.json" >> .s3_upload_queue
    echo "$(pwd)/${TIME_IST}stress-test-summary.json" >> .s3_upload_queue
    echo "📤 Output files added to S3 upload queue"
    
    source s3_upload.sh
    run_s3_upload ~/mrf/loadtest/holiday-test-unbxd/.s3_upload_queue
fi

# ============================================================================
# ANALYSIS TIPS
# ============================================================================

echo ""
echo "💡 ANALYSIS TIPS:"
echo "───────────────────────────────────────────────────────────"
echo "1. Check the error rate - when does it spike above 5-10%?"
echo "2. Check p95/p99 latencies - when do they exceed SLA?"
echo "3. Look for the RPS where both metrics start degrading"
echo "4. That's your maximum sustainable RPS!"
echo ""
echo "To analyze results:"
echo "  python plot_k6_metrics.py ${TIME_IST}stress-test-raw.json"
echo ""

