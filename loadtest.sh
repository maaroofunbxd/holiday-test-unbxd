#!/bin/bash
# ============================================================================
# LOAD TEST - Run load test interactively or in background
# ============================================================================
# Usage:
#   ./loadtest.sh [service] [region] [namespace] [commands_file]
#   ./loadtest.sh --background [service] [region] [namespace] [commands_file]
#   ./loadtest.sh --status
#
# Examples:
#   ./loadtest.sh qcs-demo ap-southeast-1prod ai                    # Interactive
#   ./loadtest.sh --background qcs-demo ap-southeast-1prod ai       # Background
#   ./loadtest.sh --status                                          # Check status

set -e

# Parse flags
BACKGROUND=false
STATUS=false
if [[ "$1" == "-b" ]] || [[ "$1" == "--background" ]]; then
  BACKGROUND=true
  shift
elif [[ "$1" == "--status" ]]; then
  STATUS=true
  shift
fi

SERVICE=${1:-qcs-demo}
REGION=${2:-ap-southeast-1prod}
ARG_NS=${3:-}
COMMANDS_FILE=${4:-loadtestcluster-commands.sh}

if [ -f "$(dirname "$0")/services.py" ]; then
  eval "$(python3 "$(dirname "$0")/services.py" export-env "$SERVICE" --region "$REGION" 2>/dev/null)" || true
  SERVICE="${K8S_SERVICE:-$SERVICE}"
fi
NAMESPACE="${ARG_NS:-${NAMESPACE:-ai}}"

if [ "$STATUS" = true ]; then
  # ============================================================================
  # STATUS MODE - Check running load tests
  # ============================================================================
  echo "🔍 Checking load test status..."
  echo ""
  
  CHECK_CMD="cd ~/mrf/loadtest/holiday-test-unbxd && \
echo '=== Screen Sessions ===' && \
screen -ls 2>&1 | grep loadtest || echo 'No loadtest sessions' && \
echo '' && \
echo '=== Running k6 Processes ===' && \
ps aux | grep -v grep | grep k6 || echo 'No k6 processes' && \
echo '' && \
echo '=== Recent Logs ===' && \
ls -lth loadtest_*.log 2>/dev/null | head -3 || echo 'No logs' && \
echo '' && \
echo '=== Latest Output ===' && \
tail -20 \$(ls -t loadtest_*.log 2>/dev/null | head -1) 2>/dev/null || echo 'No output'"
  
  ssh -t ec2-user@usejump.unbxd.io "ssh -t ubuntu@ip-10-0-1-231 '$CHECK_CMD'"
  exit 0
fi

# ============================================================================
# GET SERVICE HOST (Common for both modes)
# ============================================================================

echo ""
echo "🚀 LOAD TEST RUNNER"
if [ "$BACKGROUND" = true ]; then
  echo "Mode: BACKGROUND (can close laptop)"
else
  echo "Mode: INTERACTIVE (foreground)"
fi
echo "════════════════════════════════════════════════════════════"
echo "  Service:   $SERVICE"
echo "  Region:    $REGION"
echo "  Namespace: $NAMESPACE"
echo "  Commands:  $COMMANDS_FILE"
echo "════════════════════════════════════════════════════════════"
echo ""

if [ -n "${HOST:-}" ] && [[ "$HOST" == http://* || "$HOST" == https://* ]]; then
  echo "Using HOST override: $HOST"
  echo ""
else
  echo "📡 Getting service host from cluster..."
  FULL_OUTPUT=$(./accesscluster.sh "$REGION" "./get-service-host.sh $SERVICE $NAMESPACE" 2>&1)
  echo "$FULL_OUTPUT"
  echo ""

  HOST_VALUE=$(echo "$FULL_OUTPUT" | awk -F= '/^SERVICE_HOST=/{print $2}' | tail -1 | tr -d '\r')
  if [ -z "$HOST_VALUE" ]; then
    HOST_VALUE=$(echo "$FULL_OUTPUT" | grep -oE '[a-z0-9-]+\.[a-z0-9-]+\.elb\.amazonaws\.com' | head -1)
  fi
  if [ -z "$HOST_VALUE" ]; then
    HOST_VALUE=$(echo "$FULL_OUTPUT" | grep -oE '([0-9]{1,3}\.){3}[0-9]{1,3}' | tail -1)
  fi

  if [ -z "$HOST_VALUE" ]; then
    echo "❌ Error: Could not extract service host (need ELB hostname or IP)"
    exit 1
  fi

  HOST="http://${HOST_VALUE}"
  echo "✅ Host: $HOST"
  echo ""
fi

# Verify commands file exists
if [ ! -f "$COMMANDS_FILE" ]; then
  echo "❌ Error: Commands file not found: $COMMANDS_FILE"
  exit 1
fi

COMMANDS=$(cat "$COMMANDS_FILE")
COMMANDS="${COMMANDS//\$HOST/$HOST}"

if [ "$BACKGROUND" = true ]; then
  # ============================================================================
  # BACKGROUND MODE - Run on loadtest server with screen
  # ============================================================================
  SESSION_NAME="loadtest_${SERVICE}_$(date +%H%M%S)"
  TIMESTAMP=$(date +%Y%m%d_%H%M%S)
  LOG_FILE="loadtest_${SERVICE}_${TIMESTAMP}.log"
  
  echo "🔥 Starting load test in BACKGROUND mode..."
  echo ""
  
  # Write commands to temp file to execute on remote
  TEMP_CMD=$(mktemp)
  cat > "$TEMP_CMD" << EOF
cd ~/mrf/loadtest/holiday-test-unbxd
git fetch origin >/dev/null 2>&1
git rebase origin/main >/dev/null 2>&1
export REGION='${LOG_REGION:-$REGION}'
export HOST='$HOST'
export S3_BUCKET='${S3_BUCKET:-}'
export S3_PREFIX='${S3_PREFIX:-}'
export PAYLOAD_MODE='${PAYLOAD_MODE:-jsonl}'
export SERVICE='${LOG_PREFIX:-$SERVICE}'
screen -dmS $SESSION_NAME bash -c '$COMMANDS > $LOG_FILE 2>&1'
sleep 3
echo '✅ Screen session started: $SESSION_NAME'
echo '   Log file: $LOG_FILE'
screen -ls | grep loadtest || echo 'Session may have exited - check logs'
echo 'To reattach: screen -r $SESSION_NAME'
echo 'To check logs: tail -f $LOG_FILE'
EOF

  ssh -t ec2-user@usejump.unbxd.io "ssh -t ubuntu@ip-10-0-1-231 'bash -s'" < "$TEMP_CMD"
  rm -f "$TEMP_CMD"
  
  echo ""
  echo "✅ Load test started in background!"
  echo "✓ You can now close your laptop - it will continue running"
  echo ""
  echo "To check status:  ./loadtest.sh --status"
  echo "To reattach:      ./accessloadtestcluster.sh 'screen -r $SESSION_NAME'"
  echo ""

else
  # ============================================================================
  # INTERACTIVE MODE - Traditional foreground execution
  # ============================================================================
  echo "🔥 Running load test in INTERACTIVE mode..."
  echo ""
  echo "💡 Tip: Use --background to run this on the server and close your laptop"
  echo ""
  
  HOST=$HOST REGION="${LOG_REGION:-$REGION}" S3_BUCKET="${S3_BUCKET:-}" \
    S3_PREFIX="${S3_PREFIX:-}" PAYLOAD_MODE="${PAYLOAD_MODE:-jsonl}" \
    SERVICE="${LOG_PREFIX:-$SERVICE}" \
    ./accessloadtestcluster.sh "@$COMMANDS_FILE"
  
  echo ""
  echo "✅ Load test completed!"
  echo ""
  echo "📊 Next Steps:"
  echo "   ./holiday.sh report ${LOG_PREFIX:-$SERVICE} $REGION --s3 --open"
  echo ""
fi
