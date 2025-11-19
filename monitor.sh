#!/bin/bash
# ============================================================================
# MONITOR - Run pod monitoring interactively or in background
# ============================================================================
# Usage:
#   ./monitor.sh [service] [region] [namespace] [duration]
#   ./monitor.sh --background [service] [region] [namespace] [duration]
#   ./monitor.sh --status [region]
#
# Examples:
#   ./monitor.sh qcs-demo ap-southeast-1prod ai 600              # Interactive
#   ./monitor.sh --background qcs-demo ap-southeast-1prod ai 600 # Background
#   ./monitor.sh --status ap-southeast-1prod                     # Check status

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
DURATION=${4:-600}

if [ "$STATUS" = true ]; then
  # ============================================================================
  # STATUS MODE - Check running monitors
  # ============================================================================
  echo "🔍 Checking monitoring status on $REGION..."
  echo ""
  
  CHECK_CMD="cd ~/mrf/holiday-test-unbxd && \
echo '=== Screen Sessions ===' && \
screen -ls 2>&1 | grep monitor || echo 'No monitor sessions' && \
echo '' && \
echo '=== Running Processes ===' && \
ps aux | grep -v grep | grep clustermonitor || echo 'No processes' && \
echo '' && \
echo '=== Recent Logs ===' && \
ls -lth monitor_output_*.log 2>/dev/null | head -3 || echo 'No logs' && \
echo '' && \
echo '=== Latest Output ===' && \
tail -15 \$(ls -t monitor_output_*.log 2>/dev/null | head -1) 2>/dev/null || echo 'No output'"
  
  ./accesscluster.sh "$REGION" "$CHECK_CMD"

elif [ "$BACKGROUND" = true ]; then
  # ============================================================================
  # BACKGROUND MODE - Run on remote server with screen
  # ============================================================================
  SESSION_NAME="monitor_${SERVICE}_$(date +%H%M%S)"
  TIMESTAMP=$(date +%Y%m%d_%H%M%S)
  LOG_FILE="monitor_output_${TIMESTAMP}.log"
  
  echo ""
  echo "📊 Starting monitoring in BACKGROUND mode"
  echo "════════════════════════════════════════════════════════════"
  echo "  Service:   $SERVICE"
  echo "  Region:    $REGION"
  echo "  Namespace: $NAMESPACE"
  echo "  Duration:  ${DURATION}s"
  echo "  Session:   $SESSION_NAME"
  echo "════════════════════════════════════════════════════════════"
  echo ""
  
  REMOTE_CMD="cd ~/mrf/holiday-test-unbxd && \
git fetch origin >/dev/null 2>&1 && \
git rebase origin/main >/dev/null 2>&1 && \
pip3 install --quiet pandas tabulate && \
screen -dmS $SESSION_NAME bash -c './clustermonitor.sh $SERVICE $DURATION $NAMESPACE | tee $LOG_FILE' && \
echo '✅ Screen session started: $SESSION_NAME' && \
echo '   Log file: $LOG_FILE' && \
echo '' && \
echo 'To reattach: screen -r $SESSION_NAME' && \
echo 'To check status: ./monitor.sh --status' && \
sleep 1 && \
screen -ls | grep monitor || echo 'Session created'"
  
  ./accesscluster.sh "$REGION" "$REMOTE_CMD"
  
  echo ""
  echo "✅ Monitoring started in background!"
  echo "✓ You can now close your laptop - it will continue running"
  echo ""
  echo "To check status:  ./monitor.sh --status $REGION"
  echo "To reattach:      ./accesscluster.sh $REGION 'screen -r $SESSION_NAME'"
  echo ""

else
  # ============================================================================
  # INTERACTIVE MODE - Traditional foreground execution
  # ============================================================================
  echo ""
  echo "📊 Starting monitoring in INTERACTIVE mode"
  echo "════════════════════════════════════════════════════════════"
  echo "  Service:   $SERVICE"
  echo "  Region:    $REGION"
  echo "  Namespace: $NAMESPACE"
  echo "  Duration:  ${DURATION}s"
  echo "════════════════════════════════════════════════════════════"
  echo ""
  echo "💡 Tip: Use --background to run this on the server and close your laptop"
  echo ""
  
  # Create temp commands file
  TEMP_FILE=$(mktemp)
  cat > "$TEMP_FILE" << EOF
pip3 install pandas tabulate
./clustermonitor.sh $SERVICE $DURATION $NAMESPACE
EOF
  
  ./accesscluster.sh "$REGION" "@$TEMP_FILE"
  
  rm -f "$TEMP_FILE"
fi
