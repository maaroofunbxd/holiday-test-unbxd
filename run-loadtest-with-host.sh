#!/bin/bash
# Comprehensive wrapper to run load tests by auto-discovering service host
# 
# Usage: ./run-loadtest-with-host.sh <SERVICE> <REGION> [COMMANDS_FILE]
# 
# Examples:
#   ./run-loadtest-with-host.sh qcs-demo use-1d
#   ./run-loadtest-with-host.sh ner-demo ap-southeast-1
#   ./run-loadtest-with-host.sh reranker-demo gcp-us
#   ./run-loadtest-with-host.sh reranker-demo gcp-us ai
#   ./run-loadtest-with-host.sh qcs-demo use-1d ai @custom-commands.txt

set -e  # Exit on error

# ============================================================================
# CONFIGURATION
# ============================================================================

SERVICE=${1:-qcs-demo}
REGION=${2:-use-1d}
NAMESPACE=${3:-search}
COMMANDS_FILE=${4:-@loadtestcluster-commands.sh}

# Ensure commands file has @ prefix
if [[ ! "$COMMANDS_FILE" == @* ]]; then
  COMMANDS_FILE="@${COMMANDS_FILE}"
fi

# Remove @ to check if file exists
FILE_CHECK="${COMMANDS_FILE:1}"
if [ ! -f "$FILE_CHECK" ]; then
  echo "❌ Error: Commands file not found: $FILE_CHECK"
  echo "💡 Expected: loadtestcluster-commands.sh"
  exit 1
fi

# ============================================================================
# DISPLAY CONFIGURATION
# ============================================================================

echo ""
echo "🚀 LOAD TEST RUNNER"
echo "═══════════════════════════════════════════════════════════"
echo "  🎯 Service:          $SERVICE"
echo "  🌍 Region:           $REGION"
echo "  📝 Commands File:    $FILE_CHECK"
echo "═══════════════════════════════════════════════════════════"
echo ""

# ============================================================================
# STEP 1: GET SERVICE HOST
# ============================================================================

echo "📡 Step 1: Getting service host from cluster..."
echo "   Running: ./accesscluster.sh $REGION \"./get-service-host.sh $SERVICE $NAMESPACE\""
echo ""

# Get the full output to show to user
FULL_OUTPUT=$(./accesscluster.sh $REGION "./get-service-host.sh $SERVICE $NAMESPACE" 2>&1)
echo "$FULL_OUTPUT"
echo ""

# Extract just the ELB hostname
HOST_VALUE=$(echo "$FULL_OUTPUT" | grep -oE '[a-z0-9-]+\.[a-z0-9-]+\.elb\.amazonaws\.com' | head -1)

if [ -z "$HOST_VALUE" ]; then
  echo "❌ Error: Could not extract service host from output"
  echo ""
  echo "💡 Troubleshooting:"
  echo "   1. Check if service '$SERVICE' exists in region '$REGION'"
  echo "   2. Verify the service has a LoadBalancer with hostname"
  echo "   3. Try running manually: ./accesscluster.sh $REGION \"./get-service-host.sh $SERVICE $NAMESPACE\""
  exit 1
fi

HOST="http://${HOST_VALUE}"

echo "✅ Successfully retrieved host"
echo "   HOST=$HOST"
echo ""

# ============================================================================
# STEP 2: RUN LOAD TEST
# ============================================================================

echo "🔥 Step 2: Running load test commands..."
echo "   HOST=$HOST"
echo "   REGION=$REGION"
echo "   Running: ./accessloadtestcluster.sh $COMMANDS_FILE"
echo ""

# Run the load test with the discovered host
HOST=$HOST REGION=$REGION ./accessloadtestcluster.sh $COMMANDS_FILE

# ============================================================================
# COMPLETION
# ============================================================================

echo ""
echo "✅ Load test completed!"
echo ""
echo "📊 Next Steps:"
echo "   1. Check k6 output above for results"
echo "   2. Download logs: ./accesscluster.sh $REGION \"./uploadtos3.sh $SERVICE\""
echo "   3. Process logs: sh ./process_logs.sh ${SERVICE}-${REGION}-logs ${SERVICE} ${SERVICE} ${REGION}"
echo "   4. Analyze results with plot_k6_metrics.py"
echo ""

