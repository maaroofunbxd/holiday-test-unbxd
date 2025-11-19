#!/bin/bash
# ============================================================================
# RUN TEST - Run both monitoring and load test (interactive or background)
# ============================================================================
# Usage:
#   ./run-test.sh [service] [region] [namespace] [duration]
#   ./run-test.sh --background [service] [region] [namespace] [duration]
#
# Examples:
#   ./run-test.sh qcs-demo ap-southeast-1prod ai 600              # Interactive
#   ./run-test.sh --background qcs-demo ap-southeast-1prod ai 600 # Background

set -e

# Parse flags
BACKGROUND=false
if [[ "$1" == "-b" ]] || [[ "$1" == "--background" ]]; then
  BACKGROUND=true
  shift
fi

SERVICE=${1:-qcs-demo}
REGION=${2:-ap-southeast-1prod}
NAMESPACE=${3:-ai}
DURATION=${4:-600}
COMMANDS_FILE=${5:-loadtestcluster-commands.sh}

echo ""
echo "🎯 FULL TEST RUNNER"
if [ "$BACKGROUND" = true ]; then
  echo "Mode: BACKGROUND (can close laptop)"
else
  echo "Mode: INTERACTIVE (foreground)"
fi
echo "════════════════════════════════════════════════════════════"
echo "  Service:          $SERVICE"
echo "  Region:           $REGION"
echo "  Namespace:        $NAMESPACE"
echo "  Monitor Duration: ${DURATION}s"
echo "  Load Commands:    $COMMANDS_FILE"
echo "════════════════════════════════════════════════════════════"
echo ""

if [ "$BACKGROUND" = true ]; then
  # ============================================================================
  # BACKGROUND MODE - Both in background
  # ============================================================================
  
  echo "Step 1/2: Starting monitoring..."
  ./monitor.sh --background "$SERVICE" "$REGION" "$NAMESPACE" "$DURATION"
  
  echo ""
  echo "Step 2/2: Starting load test..."
  ./loadtest.sh --background "$SERVICE" "$REGION" "$NAMESPACE" "$COMMANDS_FILE"
  
  echo ""
  echo "════════════════════════════════════════════════════════════"
  echo "✅ BOTH TESTS STARTED IN BACKGROUND!"
  echo "════════════════════════════════════════════════════════════"
  echo ""
  echo "✓ You can now CLOSE YOUR LAPTOP - tests will continue"
  echo ""
  echo "📊 Check status:"
  echo "   ./monitor.sh --status $REGION"
  echo "   ./loadtest.sh --status"
  echo ""
  echo "📥 After completion:"
  echo "   ./accesscluster.sh $REGION \"./uploadtos3.sh $SERVICE\""
  echo "   sh ./process_logs.sh ${SERVICE}-${REGION}-logs ${SERVICE} ${SERVICE} ${REGION}"
  echo ""

else
  # ============================================================================
  # INTERACTIVE MODE - Run in two separate terminals
  # ============================================================================
  
  echo "💡 INTERACTIVE MODE requires 2 terminals:"
  echo ""
  echo "Terminal 1 (Monitoring):"
  echo "  ./monitor.sh $SERVICE $REGION $NAMESPACE $DURATION"
  echo ""
  echo "Terminal 2 (Load Test):"
  echo "  ./loadtest.sh $SERVICE $REGION $NAMESPACE $COMMANDS_FILE"
  echo ""
  echo "OR run both in background with:"
  echo "  ./run-test.sh --background $SERVICE $REGION $NAMESPACE $DURATION"
  echo ""
  echo "Continue with monitoring only? (y/n)"
  read -r response
  
  if [[ "$response" =~ ^[Yy]$ ]]; then
    echo ""
    echo "Starting monitoring (you'll need to run loadtest separately)..."
    ./monitor.sh "$SERVICE" "$REGION" "$NAMESPACE" "$DURATION"
  else
    echo "Cancelled. Run commands separately or use --background flag."
  fi
fi
