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
NAMESPACE=${3:-ai}
COMMANDS_FILE=${4:-loadtestcluster-commands.sh}

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

echo "📡 Getting service host from cluster..."
FULL_OUTPUT=$(./accesscluster.sh $REGION "./get-service-host.sh $SERVICE $NAMESPACE" 2>&1)
echo "$FULL_OUTPUT"
echo ""

HOST_VALUE=$(echo "$FULL_OUTPUT" | grep -oE '[a-z0-9-]+\.[a-z0-9-]+\.elb\.amazonaws\.com' | head -1)

if [ -z "$HOST_VALUE" ]; then
  echo "❌ Error: Could not extract service host"
  exit 1
fi

HOST="http://${HOST_VALUE}"
echo "✅ Host: $HOST"
echo ""

# Verify commands file exists
if [ ! -f "$COMMANDS_FILE" ]; then
  echo "❌ Error: Commands file not found: $COMMANDS_FILE"
  exit 1
fi

COMMANDS=$(cat "$COMMANDS_FILE")

if [ "$BACKGROUND" = true ]; then
  # ============================================================================
  # BACKGROUND MODE - Run on loadtest server with screen
  # ============================================================================
  SESSION_NAME="loadtest_${SERVICE}_$(date +%H%M%S)"
  TIMESTAMP=$(date +%Y%m%d_%H%M%S)
  LOG_FILE="loadtest_${SERVICE}_${TIMESTAMP}.log"
  
  echo "🔥 Starting load test in BACKGROUND mode..."
  echo ""
  
  REMOTE_CMD="cd ~/mrf/loadtest/holiday-test-unbxd && git fetch origin >/dev/null 2>&1 && git rebase origin/main >/dev/null 2>&1 && export REGION=$REGION && export HOST=$HOST && screen -dmS $SESSION_NAME -L -Logfile $LOG_FILE bash -c '$COMMANDS' && echo 'Screen session started: $SESSION_NAME' && echo 'Log file: $LOG_FILE' && echo 'To reattach: screen -r $SESSION_NAME' && echo 'To check status: ./loadtest.sh --status' && sleep 1 && screen -ls | grep loadtest || echo 'Session created'"
  
  ssh -t ec2-user@usejump.unbxd.io "ssh -t ubuntu@ip-10-0-1-231 '$REMOTE_CMD'"
  
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
  
  HOST=$HOST REGION=$REGION ./accessloadtestcluster.sh "@$COMMANDS_FILE"
  
  echo ""
  echo "✅ Load test completed!"
  echo ""
  echo "📊 Next Steps:"
  echo "   ./accesscluster.sh $REGION \"./uploadtos3.sh $SERVICE\""
  echo "   sh ./process_logs.sh ${SERVICE}-${REGION}-logs ${SERVICE} ${SERVICE} ${REGION}"
  echo ""
fi
